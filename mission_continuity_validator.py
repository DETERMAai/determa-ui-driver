from typing import Any, Dict, List


def validate_mission_continuity(
    intent_integrity: Dict[str, Any],
    goal_drift: Dict[str, Any],
    operator_trust: Dict[str, Any],
    runtime_status: Dict[str, Any],
    system_state: Dict[str, Any],
) -> Dict[str, Any]:
    integrity = dict(intent_integrity or {})
    drift = dict(goal_drift or {})
    trust = dict(operator_trust or {})
    runtime = dict(runtime_status or {})
    replay_state = dict(system_state or {})

    concerns: List[Dict[str, Any]] = []

    integrity_score = float(integrity.get("integrity_score", 0.0) or 0.0)
    drift_score = float(drift.get("drift_score", 0.0) or 0.0)
    operator_trust_score = float(trust.get("operator_trust_score", 0.0) or 0.0)
    workflow_trust_score = float(trust.get("workflow_trust_score", 0.0) or 0.0)
    anomaly_count = len(replay_state.get("anomalies", []))
    runtime_core = runtime.get("runtime", {}) if isinstance(runtime, dict) else {}
    stalled_cycles = int(runtime_core.get("stalled_cycles", 0) or 0)

    if integrity_score < 0.55:
        concerns.append(
            {
                "type": "OBJECTIVE_CONTINUITY_WEAK",
                "severity": "high",
                "description": "Canonical mission alignment is below continuity threshold.",
            }
        )

    if drift_score >= 0.50:
        concerns.append(
            {
                "type": "MISSION_DRIFT_ACTIVE",
                "severity": "high" if drift_score >= 0.70 else "medium",
                "description": "Goal drift indicators are actively degrading continuity.",
            }
        )

    if operator_trust_score < 50.0 or workflow_trust_score < 45.0:
        concerns.append(
            {
                "type": "OPERATOR_INTENT_PRESERVATION_RISK",
                "severity": "medium",
                "description": "Operator/workflow trust trend indicates mission intent may not be preserved.",
            }
        )

    if anomaly_count > 0 or stalled_cycles > 10:
        concerns.append(
            {
                "type": "MISSION_SURVIVABILITY_PRESSURE",
                "severity": "medium",
                "description": "Runtime instability threatens long-term mission survivability.",
            }
        )

    continuity_score = max(
        0.0,
        min(
            1.0,
            (integrity_score * 0.45)
            + (max(0.0, 1.0 - drift_score) * 0.30)
            + (operator_trust_score / 100.0 * 0.15)
            + (workflow_trust_score / 100.0 * 0.10),
        ),
    )

    return {
        "status": "ok",
        "mission_continuity_score": round(continuity_score, 4),
        "long_term_objective_continuity": continuity_score >= 0.60,
        "operator_intent_preserved": operator_trust_score >= 50.0,
        "mission_survivability": "HIGH" if continuity_score >= 0.75 else "MEDIUM" if continuity_score >= 0.50 else "LOW",
        "continuity_concerns": concerns,
    }
