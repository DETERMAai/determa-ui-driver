from typing import Any, Dict, List


def detect_interpretation_conflicts(
    ui_state: Dict[str, Any],
    replay_state: Dict[str, Any],
    authority_validation: Dict[str, Any],
    truth_results: Dict[str, Any],
) -> Dict[str, Any]:
    ui_data = dict(ui_state or {})
    replay_data = dict(replay_state or {})
    authority_data = dict(authority_validation or {})
    truths = dict(truth_results or {})

    conflicts: List[Dict[str, Any]] = []
    actions = [str(action) for action in ui_data.get("detected_actions", [])]
    button_texts = [str(button.get("text", "")).strip().lower() for button in ui_data.get("buttons", [])]
    button_texts = [item for item in button_texts if item]

    if "approve" in actions and "inspect_error" in actions:
        conflicts.append(
            {
                "type": "CONFLICTING_SEMANTIC_INTERPRETATIONS",
                "severity": "high",
                "description": "UI suggests both approval and error inspection paths simultaneously.",
                "source_layers": ["ui_state", "semantic_interpretation"],
            }
        )

    has_positive_approve = any("approve" in text or "accept" in text for text in button_texts)
    has_negative_approve = any("reject" in text or "cancel" in text or "deny" in text for text in button_texts)
    if has_positive_approve and has_negative_approve:
        conflicts.append(
            {
                "type": "CONFLICTING_UI_INTERPRETATIONS",
                "severity": "medium",
                "description": "UI contains simultaneous positive and negative approval controls.",
                "source_layers": ["ui_state"],
            }
        )

    replay_anomalies = list(replay_data.get("anomalies", []))
    authority_violations = list(authority_data.get("violations", []))
    if replay_anomalies and not authority_violations:
        conflicts.append(
            {
                "type": "CONFLICTING_REPLAY_OUTCOMES",
                "severity": "medium",
                "description": "Replay anomalies exist without corresponding authority violations.",
                "source_layers": ["replay_system", "authority_validation"],
            }
        )

    truth_statuses = [str(item.get("truth_status", "")) for item in truths.values() if isinstance(item, dict)]
    has_valid = any(status == "VALID" for status in truth_statuses)
    has_invalid = any(status == "INVALID" for status in truth_statuses)
    if has_valid and has_invalid:
        conflicts.append(
            {
                "type": "CONFLICTING_LEGITIMACY_CONCLUSIONS",
                "severity": "high",
                "description": "Different jobs yield mutually conflicting legitimacy outcomes.",
                "source_layers": ["truth_resolution", "authority_validation", "integrity"],
            }
        )

    unresolved = len([conflict for conflict in conflicts if conflict.get("severity") in {"critical", "high"}]) > 0
    return {
        "status": "ok",
        "conflict_detected": len(conflicts) > 0,
        "unresolved_conflict": unresolved,
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }
