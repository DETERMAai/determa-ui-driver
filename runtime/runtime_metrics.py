import hashlib
import json
from typing import Any, Dict, List


runtime_metrics_state: Dict[str, Any] = {
    "runtime_stall_events": 0,
    "false_approval_attempts": 0,
    "benchmark_runs": 0,
    "benchmark_successes": 0,
    "red_team_runs": 0,
    "red_team_detections": 0,
}


def record_runtime_stall_event() -> int:
    runtime_metrics_state["runtime_stall_events"] = int(runtime_metrics_state.get("runtime_stall_events", 0)) + 1
    return int(runtime_metrics_state["runtime_stall_events"])


def record_false_approval_attempt() -> int:
    runtime_metrics_state["false_approval_attempts"] = int(runtime_metrics_state.get("false_approval_attempts", 0)) + 1
    return int(runtime_metrics_state["false_approval_attempts"])


def record_benchmark_result(success: bool) -> Dict[str, Any]:
    runtime_metrics_state["benchmark_runs"] = int(runtime_metrics_state.get("benchmark_runs", 0)) + 1
    if success:
        runtime_metrics_state["benchmark_successes"] = int(runtime_metrics_state.get("benchmark_successes", 0)) + 1
    return dict(runtime_metrics_state)


def record_red_team_result(detected: bool) -> Dict[str, Any]:
    runtime_metrics_state["red_team_runs"] = int(runtime_metrics_state.get("red_team_runs", 0)) + 1
    if detected:
        runtime_metrics_state["red_team_detections"] = int(runtime_metrics_state.get("red_team_detections", 0)) + 1
    return dict(runtime_metrics_state)


def _hash_state(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_runtime_metrics_snapshot(
    workflow_sessions: Dict[str, Dict[str, Any]],
    escalation_events: List[Dict[str, Any]],
    audit_log: List[Dict[str, Any]],
    runtime_status: Dict[str, Any],
    failure_records: List[Dict[str, Any]],
    replay_state: Dict[str, Any],
) -> Dict[str, Any]:
    total_workflows = len(workflow_sessions)
    completed_workflows = 0
    recovery_total = 0
    recovery_success = 0
    escalated = 0

    for workflow in workflow_sessions.values():
        status = str(workflow.get("status", "")).upper()
        if status == "COMPLETED":
            completed_workflows += 1
        if status == "ESCALATED":
            escalated += 1
        if int(workflow.get("retry_count", 0)) > 0:
            recovery_total += 1
            if status in {"COMPLETED", "RUNNING"}:
                recovery_success += 1

    workflow_completion_rate = 1.0 if total_workflows == 0 else round(float(completed_workflows) / float(total_workflows), 3)
    recovery_success_rate = 1.0 if recovery_total == 0 else round(float(recovery_success) / float(recovery_total), 3)
    escalation_frequency = 0.0 if total_workflows == 0 else round(float(len(escalation_events)) / float(total_workflows), 3)

    runtime = runtime_status.get("runtime", {}) if isinstance(runtime_status, dict) else {}
    stalled_cycles = int(runtime.get("stalled_cycles", 0))
    if stalled_cycles >= 10:
        record_runtime_stall_event()

    anomaly_count = len(replay_state.get("anomalies", [])) if isinstance(replay_state, dict) else 0
    replay_consistency = {
        "anomaly_count": anomaly_count,
        "consistent": anomaly_count == 0,
        "replay_state_hash": _hash_state(replay_state),
    }

    metrics = {
        "workflow_completion_rate": workflow_completion_rate,
        "recovery_success_rate": recovery_success_rate,
        "escalation_frequency": escalation_frequency,
        "runtime_stall_frequency": int(runtime_metrics_state.get("runtime_stall_events", 0)),
        "false_approval_attempts": int(runtime_metrics_state.get("false_approval_attempts", 0)),
        "replay_consistency": replay_consistency,
        "failure_mode_count": len(failure_records),
        "audit_event_count": len(audit_log),
        "benchmark_runs": int(runtime_metrics_state.get("benchmark_runs", 0)),
        "benchmark_success_rate": (
            1.0
            if int(runtime_metrics_state.get("benchmark_runs", 0)) == 0
            else round(
                float(runtime_metrics_state.get("benchmark_successes", 0))
                / float(runtime_metrics_state.get("benchmark_runs", 1)),
                3,
            )
        ),
        "red_team_runs": int(runtime_metrics_state.get("red_team_runs", 0)),
        "red_team_detection_rate": (
            1.0
            if int(runtime_metrics_state.get("red_team_runs", 0)) == 0
            else round(
                float(runtime_metrics_state.get("red_team_detections", 0))
                / float(runtime_metrics_state.get("red_team_runs", 1)),
                3,
            )
        ),
    }
    return metrics
