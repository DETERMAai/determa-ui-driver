from typing import Any, Dict, List


def evaluate_ambiguity_escalation(
    confidence_result: Dict[str, Any],
    boundary_result: Dict[str, Any],
    conflict_result: Dict[str, Any],
) -> Dict[str, Any]:
    confidence = dict(confidence_result.get("confidence", {}) or {})
    boundaries = dict(boundary_result or {})
    conflicts = dict(conflict_result or {})

    overall_conf = float(confidence.get("overall_confidence", 0.0) or 0.0)
    boundary_score = float(boundaries.get("boundary_score", 0.0) or 0.0)
    conflict_count = int(conflicts.get("conflict_count", 0) or 0)
    unresolved_conflict = bool(conflicts.get("unresolved_conflict", False))

    ambiguity_score = min(
        1.0,
        max(0.0, 1.0 - overall_conf) * 0.45
        + boundary_score * 0.35
        + min(0.20, conflict_count * 0.07),
    )

    actions: List[str] = []
    reduce_autonomy = ambiguity_score >= 0.35
    require_approvals = ambiguity_score >= 0.45 or bool(boundaries.get("knowledge_boundary_detected", False))
    escalate_operator = ambiguity_score >= 0.60 or unresolved_conflict
    block_unsafe_execution = ambiguity_score >= 0.72 or unresolved_conflict

    if reduce_autonomy:
        actions.append("reduce_autonomy")
    if require_approvals:
        actions.append("require_approvals")
    if escalate_operator:
        actions.append("escalate_to_operator")
    if block_unsafe_execution:
        actions.append("block_unsafe_execution")

    status = "NORMAL"
    if block_unsafe_execution:
        status = "BLOCKED"
    elif escalate_operator:
        status = "ESCALATED"
    elif reduce_autonomy or require_approvals:
        status = "RESTRICTED"

    return {
        "status": "ok",
        "ambiguity_status": status,
        "ambiguity_score": round(ambiguity_score, 4),
        "reduce_autonomy": reduce_autonomy,
        "require_approvals": require_approvals,
        "escalate_to_operator": escalate_operator,
        "block_unsafe_execution": block_unsafe_execution,
        "recommended_actions": actions,
    }
