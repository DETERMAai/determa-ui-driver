import json
import os
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from typing import Any, Dict


def _normalize_router_response(raw: Dict[str, Any], started_at: float) -> Dict[str, Any]:
    model_used = str(raw.get("model_used") or raw.get("model") or "unknown")
    output = str(raw.get("output") or raw.get("response") or "")

    try:
        cost = float(raw.get("cost", 0.0))
    except Exception:
        cost = 0.0

    try:
        latency_ms = int(raw.get("latency_ms"))
    except Exception:
        latency_ms = int((time.time() - started_at) * 1000)

    return {
        "model_used": model_used,
        "output": output,
        "cost": cost,
        "latency_ms": latency_ms
    }


def call_ai_router(task_payload: Dict[str, Any]) -> Dict[str, Any]:
    required_fields = {"task_type", "input", "risk_level", "requires_verification"}
    missing = [field for field in required_fields if field not in task_payload]
    if missing:
        raise ValueError(f"missing_required_fields:{','.join(sorted(missing))}")

    router_url = os.getenv("AI_ROUTER_URL")
    router_command = os.getenv("AI_ROUTER_COMMAND")
    timeout_sec = float(os.getenv("AI_ROUTER_TIMEOUT_SEC", "30"))

    if not router_url and not router_command:
        raise RuntimeError("ai_router_not_configured_set_AI_ROUTER_URL_or_AI_ROUTER_COMMAND")

    started_at = time.time()

    if router_url:
        request = urllib.request.Request(
            router_url,
            data=json.dumps(task_payload).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"ai_router_http_error:{exc}") from exc

        try:
            raw_response = json.loads(body)
        except Exception as exc:
            raise RuntimeError("ai_router_invalid_json_response") from exc

        if not isinstance(raw_response, dict):
            raise RuntimeError("ai_router_response_must_be_object")

        return _normalize_router_response(raw_response, started_at)

    command_parts = shlex.split(router_command)
    process = subprocess.run(
        command_parts,
        input=json.dumps(task_payload),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False
    )

    if process.returncode != 0:
        stderr = (process.stderr or "").strip()
        raise RuntimeError(f"ai_router_command_failed:{process.returncode}:{stderr}")

    stdout = (process.stdout or "").strip()
    if not stdout:
        raise RuntimeError("ai_router_empty_response")

    try:
        raw_response = json.loads(stdout)
    except Exception as exc:
        raise RuntimeError("ai_router_invalid_json_response") from exc

    if not isinstance(raw_response, dict):
        raise RuntimeError("ai_router_response_must_be_object")

    return _normalize_router_response(raw_response, started_at)
