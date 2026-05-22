from typing import Any, Dict, List


def detect_knowledge_boundaries(
    confidence_result: Dict[str, Any],
    ui_state: Dict[str, Any],
    runtime_context: Dict[str, Any],
) -> Dict[str, Any]:
    confidence = dict(confidence_result.get("confidence", {}) or {})
    ui_data = dict(ui_state or {})
    context = dict(runtime_context or {})

    alerts: List[Dict[str, Any]] = []
    clarifications: List[str] = []

    ocr_reliability = float(confidence.get("ocr_reliability", 0.0) or 0.0)
    semantic_conf = float(confidence.get("semantic_interpretation_confidence", 0.0) or 0.0)
    overall_conf = float(confidence.get("overall_confidence", 0.0) or 0.0)

    terminal_lines = list(ui_data.get("terminal_lines", []))
    actions = list(ui_data.get("detected_actions", []))
    buttons = list(ui_data.get("buttons", []))
    replay_anomaly_count = int(context.get("replay_anomaly_count", 0) or 0)
    unresolved_escalations = int(context.get("unresolved_escalations", 0) or 0)

    if len(terminal_lines) == 0 and len(buttons) == 0:
        alerts.append(
            {
                "type": "INSUFFICIENT_CONTEXT",
                "severity": "high",
                "description": "No terminal lines or actionable UI controls were detected.",
            }
        )
        clarifications.append("capture_additional_runtime_context")

    if semantic_conf < 0.45:
        alerts.append(
            {
                "type": "INCOMPLETE_UNDERSTANDING",
                "severity": "high",
                "description": "Semantic interpretation confidence is below safe threshold.",
            }
        )
        clarifications.append("request_operator_clarification")

    if len(actions) > 1:
        alerts.append(
            {
                "type": "AMBIGUOUS_RUNTIME_STATE",
                "severity": "medium",
                "description": "Multiple competing actionable interpretations detected.",
                "actions": actions,
            }
        )
        clarifications.append("require_explicit_action_selection")

    if ocr_reliability < 0.35:
        alerts.append(
            {
                "type": "UNCERTAIN_SEMANTIC_DERIVATION",
                "severity": "high",
                "description": "OCR reliability is too low for safe autonomous interpretation.",
            }
        )
        clarifications.append("refresh_screen_and_reparse")

    if replay_anomaly_count > 0:
        alerts.append(
            {
                "type": "RUNTIME_STATE_INCONSISTENCY",
                "severity": "medium",
                "description": "Replay anomalies indicate unstable historical interpretation.",
                "count": replay_anomaly_count,
            }
        )
        clarifications.append("run_replay_consistency_review")

    if unresolved_escalations > 0:
        alerts.append(
            {
                "type": "UNRESOLVED_OPERATOR_ESCALATION",
                "severity": "medium",
                "description": "There are unresolved operator escalation items.",
                "count": unresolved_escalations,
            }
        )

    boundary_score = min(1.0, len(alerts) / 6.0 + max(0.0, 0.5 - overall_conf))

    return {
        "status": "ok",
        "knowledge_boundary_detected": len(alerts) > 0,
        "boundary_score": round(boundary_score, 4),
        "knowledge_boundary_alerts": alerts,
        "clarification_requirements": sorted(set(clarifications)),
    }
