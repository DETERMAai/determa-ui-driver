import json
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple

from ai_execution_adapter import call_ai_router
from llm_routing_governance import (
    register_models,
    select_best_llm_backend,
    update_model_trust,
)


class LLMExecutionError(RuntimeError):
    def __init__(self, message: str, failures: List[Dict[str, str]] | None = None):
        super().__init__(message)
        self.failures = failures or []


def _extract_text_from_openai_response(raw: Dict[str, Any]) -> str:
    if isinstance(raw.get("output_text"), str):
        return raw["output_text"]
    output = raw.get("output")
    if isinstance(output, list):
        text_parts: List[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text")
                    if isinstance(text, str):
                        text_parts.append(text)
        if text_parts:
            return "\n".join(text_parts)
    return ""


def _extract_text_from_claude_response(raw: Dict[str, Any]) -> str:
    content = raw.get("content")
    if not isinstance(content, list):
        return ""
    text_parts: List[str] = []
    for block in content:
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            text_parts.append(block["text"])
    return "\n".join(text_parts)


def _normalize_output(
    *,
    output: str,
    model_used: str,
    cost: float,
    started_at: float,
    latency_ms: int | None,
    raw_response: Any,
    backend_failures: List[Dict[str, str]],
    routing: Dict[str, Any],
) -> Dict[str, Any]:
    measured_latency = latency_ms if latency_ms is not None else int((time.time() - started_at) * 1000)
    return {
        "output": output,
        "model_used": model_used,
        "cost": float(cost),
        "latency_ms": int(measured_latency),
        "raw_response": {
            "raw": raw_response,
            "backend_failures": backend_failures,
            "routing": routing,
        },
    }


def _execute_external_router(task: Dict[str, Any], backend_cfg: Dict[str, Any], failures: List[Dict[str, str]]):
    _ = backend_cfg
    started_at = time.time()
    router_payload = {
        "task_type": task["task_type"],
        "input": task["prompt"],
        "risk_level": task["risk_level"],
        "requires_verification": task["requires_verification"],
        "context": task.get("context", {}),
    }
    raw = call_ai_router(router_payload)
    return _normalize_output(
        output=str(raw.get("output", "")),
        model_used=str(raw.get("model_used", "external-router")),
        cost=float(raw.get("cost", 0.0)),
        started_at=started_at,
        latency_ms=int(raw.get("latency_ms", 0)) if "latency_ms" in raw else None,
        raw_response=raw,
        backend_failures=failures,
        routing={},
    )


def _execute_codex_cli(task: Dict[str, Any], backend_cfg: Dict[str, Any], failures: List[Dict[str, str]]):
    command = str(backend_cfg.get("command") or os.getenv("CODEX_CLI_COMMAND") or "").strip()
    if not command:
        raise RuntimeError("codex_cli_not_configured")

    started_at = time.time()
    process = subprocess.run(
        shlex.split(command),
        input=json.dumps(task),
        capture_output=True,
        text=True,
        timeout=float(backend_cfg.get("timeout_sec", os.getenv("LLM_BACKEND_TIMEOUT_SEC", "45"))),
        check=False,
    )
    if process.returncode != 0:
        stderr = (process.stderr or "").strip()
        raise RuntimeError(f"codex_cli_failed:{process.returncode}:{stderr}")

    stdout = (process.stdout or "").strip()
    parsed: Dict[str, Any]
    try:
        parsed = json.loads(stdout) if stdout else {}
    except Exception:
        parsed = {}

    output = str(parsed.get("output", stdout))
    model_used = str(parsed.get("model_used", backend_cfg.get("model", "codex-cli")))
    cost = float(parsed.get("cost", 0.0)) if str(parsed.get("cost", "")).strip() else 0.0
    latency_ms = int(parsed.get("latency_ms")) if "latency_ms" in parsed else None

    return _normalize_output(
        output=output,
        model_used=model_used,
        cost=cost,
        started_at=started_at,
        latency_ms=latency_ms,
        raw_response=parsed if parsed else stdout,
        backend_failures=failures,
        routing={},
    )


def _execute_gpt_api(task: Dict[str, Any], backend_cfg: Dict[str, Any], failures: List[Dict[str, str]]):
    api_key = str(backend_cfg.get("api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("gpt_api_not_configured")

    endpoint = str(
        backend_cfg.get("endpoint")
        or os.getenv("OPENAI_API_ENDPOINT")
        or "https://api.openai.com/v1/responses"
    ).strip()
    model = str(backend_cfg.get("model") or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini").strip()
    timeout_sec = float(backend_cfg.get("timeout_sec", os.getenv("LLM_BACKEND_TIMEOUT_SEC", "45")))

    started_at = time.time()
    payload = {
        "model": model,
        "input": task["prompt"],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"gpt_api_request_failed:{exc}") from exc

    raw = json.loads(body)
    output = _extract_text_from_openai_response(raw)
    usage = raw.get("usage") if isinstance(raw, dict) else {}
    cost = 0.0
    if isinstance(usage, dict) and usage.get("total_cost") is not None:
        try:
            cost = float(usage["total_cost"])
        except Exception:
            cost = 0.0
    latency_ms = int((time.time() - started_at) * 1000)

    return _normalize_output(
        output=output,
        model_used=model,
        cost=cost,
        started_at=started_at,
        latency_ms=latency_ms,
        raw_response=raw,
        backend_failures=failures,
        routing={},
    )


def _execute_claude_api(task: Dict[str, Any], backend_cfg: Dict[str, Any], failures: List[Dict[str, str]]):
    api_key = str(backend_cfg.get("api_key") or os.getenv("ANTHROPIC_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("claude_api_not_configured")

    endpoint = str(
        backend_cfg.get("endpoint")
        or os.getenv("ANTHROPIC_API_ENDPOINT")
        or "https://api.anthropic.com/v1/messages"
    ).strip()
    model = str(backend_cfg.get("model") or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-latest").strip()
    timeout_sec = float(backend_cfg.get("timeout_sec", os.getenv("LLM_BACKEND_TIMEOUT_SEC", "45")))

    started_at = time.time()
    payload = {
        "model": model,
        "max_tokens": int(backend_cfg.get("max_tokens", 1024)),
        "messages": [{"role": "user", "content": task["prompt"]}],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"claude_api_request_failed:{exc}") from exc

    raw = json.loads(body)
    output = _extract_text_from_claude_response(raw)
    usage = raw.get("usage") if isinstance(raw, dict) else {}
    cost = 0.0
    if isinstance(usage, dict) and usage.get("total_cost") is not None:
        try:
            cost = float(usage["total_cost"])
        except Exception:
            cost = 0.0
    latency_ms = int((time.time() - started_at) * 1000)

    return _normalize_output(
        output=output,
        model_used=model,
        cost=cost,
        started_at=started_at,
        latency_ms=latency_ms,
        raw_response=raw,
        backend_failures=failures,
        routing={},
    )


def _build_backend_plan(backend_config: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    backends = backend_config.get("backends")
    if isinstance(backends, list) and backends:
        plan: List[Tuple[str, Dict[str, Any]]] = []
        for item in backends:
            if isinstance(item, str):
                plan.append((item, {}))
            elif isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                cfg = item.get("config", {})
                if name:
                    plan.append((name, cfg if isinstance(cfg, dict) else {}))
        if plan:
            return plan

    plan: List[Tuple[str, Dict[str, Any]]] = []
    if os.getenv("AI_ROUTER_URL") or os.getenv("AI_ROUTER_COMMAND"):
        plan.append(("external_router", {}))
    if os.getenv("OPENAI_API_KEY"):
        plan.append(("gpt_api", {}))
    if os.getenv("ANTHROPIC_API_KEY"):
        plan.append(("claude_api", {}))
    if os.getenv("CODEX_CLI_COMMAND"):
        plan.append(("codex_cli", {}))
    if not plan:
        plan.append(("external_router", {}))
    return plan


def _model_id_for_backend(backend_name: str, backend_cfg: Dict[str, Any]) -> str:
    model_name = str(backend_cfg.get("model", "")).strip()
    if model_name:
        return f"{backend_name}:{model_name}"
    return backend_name


def execute_llm_task(task: Dict[str, Any], backend_config: Dict[str, Any] | None):
    required_fields = {"task_type", "prompt", "context", "risk_level", "requires_verification"}
    missing = [field for field in required_fields if field not in task]
    if missing:
        raise LLMExecutionError(f"missing_required_fields:{','.join(sorted(missing))}")

    cfg = backend_config if isinstance(backend_config, dict) else {}
    plan = _build_backend_plan(cfg)
    plan_records = [
        {
            "backend_name": backend_name,
            "backend_cfg": backend_cfg,
            "model_id": _model_id_for_backend(backend_name, backend_cfg),
        }
        for backend_name, backend_cfg in plan
    ]
    register_models([record["model_id"] for record in plan_records])

    selection_task = {
        "task_type": task.get("task_type"),
        "risk_level": task.get("risk_level"),
        "requires_verification": task.get("requires_verification"),
        "required_accuracy": (task.get("context", {}) or {}).get("required_accuracy", 0.75),
        "latency_sensitivity": (task.get("context", {}) or {}).get("latency_sensitivity", "medium"),
        "available_models": [record["model_id"] for record in plan_records],
    }
    routing_decision = select_best_llm_backend(selection_task)
    selected_model = str(routing_decision.get("selected_model", ""))

    if selected_model:
        selected_records = [record for record in plan_records if record["model_id"] == selected_model]
        other_records = [record for record in plan_records if record["model_id"] != selected_model]
        plan_records = selected_records + other_records

    failures: List[Dict[str, str]] = []

    executors = {
        "external_router": _execute_external_router,
        "gpt_api": _execute_gpt_api,
        "claude_api": _execute_claude_api,
        "codex_cli": _execute_codex_cli,
    }

    for record in plan_records:
        backend_name = record["backend_name"]
        backend_cfg = record["backend_cfg"]
        model_id = record["model_id"]
        executor = executors.get(backend_name)
        if executor is None:
            failures.append({"backend": backend_name, "model_id": model_id, "error": "unknown_backend"})
            update_model_trust(
                model_id,
                {
                    "success": False,
                    "verification_passed": False,
                    "adversarial_failed": False,
                    "cost": 0.0,
                },
            )
            continue

        try:
            result = executor(task, backend_cfg, failures)
            update_model_trust(
                model_id,
                {
                    "success": True,
                    "verification_passed": None,
                    "adversarial_failed": False,
                    "cost": float(result.get("cost", 0.0)),
                },
            )
            if isinstance(result.get("raw_response"), dict):
                result["raw_response"]["routing"] = {
                    "selected_model": selected_model,
                    "selection_reason": routing_decision.get("selection_reason"),
                    "confidence": routing_decision.get("confidence"),
                    "chosen_model_id": model_id,
                }
            return result
        except Exception as exc:
            failures.append({"backend": backend_name, "model_id": model_id, "error": str(exc)})
            update_model_trust(
                model_id,
                {
                    "success": False,
                    "verification_passed": False,
                    "adversarial_failed": False,
                    "cost": 0.0,
                },
            )

    raise LLMExecutionError("all_backends_failed", failures=failures)
