from typing import Any, Dict, List


def evaluate_teleological_freeze_status(
    intent_integrity: Dict[str, Any],
    goal_drift: Dict[str, Any],
    mission_continuity: Dict[str, Any],
    optimization_corruption: Dict[str, Any],
) -> Dict[str, Any]:
    integrity = dict(intent_integrity or {})
    drift = dict(goal_drift or {})
    continuity = dict(mission_continuity or {})
    corruption = dict(optimization_corruption or {})

    reasons: List[Dict[str, Any]] = []

    if str(integrity.get("integrity_status", "")) == "CORRUPTED":
        reasons.append(
            {
                "trigger": "intent_corruption_detected",
                "severity": "critical",
                "description": "Canonical intent integrity reached corrupted state.",
            }
        )

    if float(drift.get("drift_score", 0.0) or 0.0) >= 0.70:
        reasons.append(
            {
                "trigger": "mission_drift_critical",
                "severity": "high",
                "description": "Goal drift score crossed critical threshold.",
            }
        )

    if str(corruption.get("corruption_level", "")) in {"CRITICAL", "HIGH"} and bool(corruption.get("corruption_detected", False)):
        reasons.append(
            {
                "trigger": "optimization_detached_from_canonical_purpose",
                "severity": "high",
                "description": "Optimization corruption indicates detachment from real mission objectives.",
            }
        )

    if float(continuity.get("mission_continuity_score", 0.0) or 0.0) < 0.45:
        reasons.append(
            {
                "trigger": "mission_continuity_collapse",
                "severity": "high",
                "description": "Mission continuity dropped below safe survivability boundary.",
            }
        )

    frozen = len(reasons) > 0
    return {
        "status": "ok",
        "frozen": frozen,
        "freeze_scope": "teleological_execution_gate",
        "reasons": reasons,
        "resume_requirements": [
            "restore_intent_integrity",
            "reduce_goal_drift",
            "resolve_optimization_corruption",
            "recover_mission_continuity",
        ],
    }
