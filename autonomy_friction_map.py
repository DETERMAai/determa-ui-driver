from typing import Any, Dict, List


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(max_value, value))


def generate_autonomy_friction_map(
    workflow_sessions: Dict[str, Dict[str, Any]],
    escalation_events: List[Dict[str, Any]],
    operational_traces: List[Dict[str, Any]],
    replay_validation_runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    workflow_count = max(1, len(workflow_sessions))
    approval_requested = sum(1 for trace in operational_traces if trace.get("trace_type") == "approval_requested")
    approval_rejected = sum(1 for trace in operational_traces if trace.get("trace_type") == "approval_rejected")
    operator_overrides = sum(
        1
        for trace in operational_traces
        if trace.get("trace_type")
        in {"workflow_stopped", "runtime_paused", "runtime_resumed", "worker_quarantined", "operator_override"}
    )
    retry_storms = sum(1 for session in workflow_sessions.values() if int(session.get("retry_count", 0)) >= 3)
    escalation_density = float(len(escalation_events)) / float(workflow_count)
    replay_inconsistencies = sum(1 for run in replay_validation_runs if not bool(run.get("overall_valid", False)))
    replay_runs = max(1, len(replay_validation_runs))
    replay_inconsistency_rate = float(replay_inconsistencies) / float(replay_runs)

    approval_overload = float(approval_requested + approval_rejected) / float(workflow_count)
    retry_storm_rate = float(retry_storms) / float(workflow_count)
    operator_override_rate = float(operator_overrides) / float(workflow_count)

    runtime_friction_score = _clamp(
        100.0
        * (
            (retry_storm_rate * 0.4)
            + (replay_inconsistency_rate * 0.3)
            + (escalation_density * 0.3)
        )
    )

    governance_friction_score = _clamp(
        100.0
        * (
            (approval_overload * 0.5)
            + (escalation_density * 0.3)
            + (operator_override_rate * 0.2)
        )
    )

    trust_indicators = []
    if replay_inconsistency_rate > 0.0:
        trust_indicators.append("replay_inconsistency_detected")
    if escalation_density > 0.5:
        trust_indicators.append("high_escalation_density")
    if approval_overload > 1.0:
        trust_indicators.append("approval_overload")
    if retry_storm_rate > 0.3:
        trust_indicators.append("retry_storm_risk")

    return {
        "runtime_friction_score": round(runtime_friction_score, 2),
        "governance_friction_score": round(governance_friction_score, 2),
        "signals": {
            "approval_overload": round(approval_overload, 3),
            "escalation_density": round(escalation_density, 3),
            "retry_storm_rate": round(retry_storm_rate, 3),
            "replay_inconsistency_rate": round(replay_inconsistency_rate, 3),
            "operator_override_rate": round(operator_override_rate, 3),
        },
        "trust_degradation_indicators": trust_indicators,
    }
