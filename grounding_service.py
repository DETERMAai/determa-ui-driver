from typing import Any, Dict, Optional


def _center_of(button: Dict[str, Any]) -> Dict[str, int]:
    return {
        "x": int(button.get("x", 0) + (button.get("w", 0) // 2)),
        "y": int(button.get("y", 0) + (button.get("h", 0) // 2)),
    }


def ground_action(action_name: str, ui_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    action = str(action_name or "").lower().strip()
    buttons = ui_state.get("buttons", [])
    if not isinstance(buttons, list):
        return None

    if action == "approve":
        candidates = [button for button in buttons if "approve" in str(button.get("text", "")).lower()]
        if not candidates:
            candidates = [button for button in buttons if any(token in str(button.get("text", "")).lower() for token in ("accept", "allow", "confirm", "yes"))]
    elif action == "continue":
        candidates = [button for button in buttons if any(token in str(button.get("text", "")).lower() for token in ("continue", "next", "proceed", "run"))]
    else:
        candidates = [button for button in buttons if action in str(button.get("text", "")).lower()]

    if not candidates:
        return None

    target = candidates[0]
    center = _center_of(target)
    return {
        "action": action,
        "x": center["x"],
        "y": center["y"],
        "target": target,
        "confidence": float(target.get("confidence", 0.0)),
    }
