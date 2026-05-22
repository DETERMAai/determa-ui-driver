from typing import Any, Dict, List


def evaluate_epistemic_freeze_status(
    confidence_result: Dict[str, Any],
    boundary_result: Dict[str, Any],
    conflict_result: Dict[str, Any],
    ambiguity_result: Dict[str, Any],
) -> Dict[str, Any]:
    confidence = dict(confidence_result.get("confidence", {}) or {})
    boundaries = dict(boundary_result or {})
    conflicts = dict(conflict_result or {})
    ambiguity = dict(ambiguity_result or {})

    overall_conf = float(confidence.get("overall_confidence", 0.0) or 0.0)
    ambiguity_score = float(ambiguity.get("ambiguity_score", 0.0) or 0.0)

    reasons: List[Dict[str, Any]] = []
    if overall_conf < 0.40:
        reasons.append(
            {
                "trigger": "certainty_too_low",
                "severity": "high",
                "value": round(overall_conf, 4),
                "threshold": 0.40,
            }
        )

    if ambiguity_score > 0.70:
        reasons.append(
            {
                "trigger": "ambiguity_too_high",
                "severity": "high",
                "value": round(ambiguity_score, 4),
                "threshold": 0.70,
            }
        )

    if bool(conflicts.get("unresolved_conflict", False)):
        reasons.append(
            {
                "trigger": "interpretation_conflict_unresolved",
                "severity": "critical",
                "value": int(conflicts.get("conflict_count", 0) or 0),
            }
        )

    boundary_alerts = list(boundaries.get("knowledge_boundary_alerts", []))
    high_boundary_count = len([alert for alert in boundary_alerts if alert.get("severity") == "high"])
    if high_boundary_count > 0:
        reasons.append(
            {
                "trigger": "knowledge_boundary_high_severity",
                "severity": "high",
                "value": high_boundary_count,
            }
        )

    frozen = len(reasons) > 0
    return {
        "status": "ok",
        "frozen": frozen,
        "freeze_scope": "epistemic_execution_gate",
        "reasons": reasons,
        "can_resume_when": [
            "overall_confidence_recovers",
            "ambiguity_reduced",
            "interpretation_conflicts_resolved",
            "knowledge_boundaries_clarified",
        ],
    }
