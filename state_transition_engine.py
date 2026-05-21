from typing import Any, Dict, List


def _button_texts(ui_state: Dict[str, Any]) -> List[str]:
    buttons = ui_state.get("buttons", [])
    if not isinstance(buttons, list):
        return []
    return [str(button.get("text", "")).strip().lower() for button in buttons]


def predict_expected_state(action: str, current_ui_state: Dict[str, Any]) -> Dict[str, Any]:
    normalized_action = str(action or "").lower().strip()
    current_actions = list(current_ui_state.get("detected_actions", [])) if isinstance(current_ui_state, dict) else []

    if normalized_action == "approve":
        return {
            "action": normalized_action,
            "expected_state": "approval_progressed",
            "must_reduce_action": "approve",
            "fallback_action_present": "continue",
            "baseline_actions": current_actions,
        }
    if normalized_action == "continue":
        return {
            "action": normalized_action,
            "expected_state": "workflow_continued",
            "must_reduce_action": "continue",
            "baseline_actions": current_actions,
        }
    if normalized_action == "run tests":
        return {
            "action": normalized_action,
            "expected_state": "terminal_output_changed",
            "watch_terminal_change": True,
            "baseline_terminal_lines": list(current_ui_state.get("terminal_lines", [])),
        }
    return {
        "action": normalized_action,
        "expected_state": "generic_progress",
        "baseline_actions": current_actions,
    }


def compare_expected_vs_observed(expected: Dict[str, Any], observed: Dict[str, Any]) -> Dict[str, Any]:
    observed_actions = list(observed.get("detected_actions", [])) if isinstance(observed, dict) else []
    observed_buttons = _button_texts(observed if isinstance(observed, dict) else {})
    expected_state = str(expected.get("expected_state", "generic_progress"))
    action = str(expected.get("action", "")).lower()

    if expected_state == "approval_progressed":
        approve_visible = ("approve" in observed_actions) or any("approve" in text for text in observed_buttons)
        continue_visible = ("continue" in observed_actions) or any("continue" in text for text in observed_buttons)
        match = (not approve_visible) or continue_visible
        return {
            "match": bool(match),
            "confidence": 0.85 if match else 0.25,
            "difference_reason": "" if match else "approve_artifacts_still_visible",
        }

    if expected_state == "workflow_continued":
        continue_visible = ("continue" in observed_actions) or any("continue" in text for text in observed_buttons)
        match = not continue_visible
        return {
            "match": bool(match),
            "confidence": 0.8 if match else 0.3,
            "difference_reason": "" if match else "continue_prompt_still_visible",
        }

    if expected_state == "terminal_output_changed":
        baseline_lines = expected.get("baseline_terminal_lines", [])
        observed_lines = observed.get("terminal_lines", [])
        match = baseline_lines != observed_lines
        return {
            "match": bool(match),
            "confidence": 0.75 if match else 0.35,
            "difference_reason": "" if match else "terminal_output_unchanged",
        }

    baseline_actions = expected.get("baseline_actions", [])
    match = baseline_actions != observed_actions
    return {
        "match": bool(match),
        "confidence": 0.7 if match else 0.4,
        "difference_reason": "" if match else f"no_observable_ui_change_for_{action}",
    }
