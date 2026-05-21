from typing import Any, Dict, List, TypedDict


class UIState(TypedDict):
    buttons: List[Dict[str, Any]]
    dialogs: List[str]
    terminal_lines: List[str]
    active_window: str
    detected_actions: List[str]


def detect_approve_buttons(buttons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    keywords = ("approve", "accept", "allow", "confirm", "yes")
    return [button for button in buttons if any(keyword in button.get("text", "").lower() for keyword in keywords)]


def detect_continue_buttons(buttons: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    keywords = ("continue", "next", "proceed", "run")
    return [button for button in buttons if any(keyword in button.get("text", "").lower() for keyword in keywords)]


def detect_terminal_errors(terminal_lines: List[str]) -> List[str]:
    keywords = ("error", "exception", "traceback", "failed", "denied")
    return [line for line in terminal_lines if any(keyword in line.lower() for keyword in keywords)]


def detect_diff_prompts(terminal_lines: List[str]) -> List[str]:
    keywords = ("diff", "---", "+++", "@@", "apply patch", "review changes")
    return [line for line in terminal_lines if any(keyword in line.lower() for keyword in keywords)]


def build_ui_state(ocr_result: Dict[str, Any], capture_metadata: Dict[str, Any]) -> UIState:
    words = ocr_result.get("words", [])
    full_text = str(ocr_result.get("full_text", ""))
    terminal_lines = [line.strip() for line in full_text.splitlines() if line.strip()]

    # Heuristic button detection from OCR boxes.
    buttons: List[Dict[str, Any]] = []
    for item in words:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        normalized = text.lower()
        if normalized in {"ok", "yes", "no", "cancel"} or len(normalized) <= 24:
            if any(
                keyword in normalized
                for keyword in ("approve", "accept", "allow", "continue", "confirm", "next", "run", "yes", "ok")
            ):
                buttons.append(
                    {
                        "text": text,
                        "x": int(item.get("left", 0)),
                        "y": int(item.get("top", 0)),
                        "w": int(item.get("width", 0)),
                        "h": int(item.get("height", 0)),
                        "confidence": float(item.get("confidence", 0.0)),
                    }
                )

    dialogs = [line for line in terminal_lines if any(token in line.lower() for token in ("confirm", "warning", "dialog", "approve"))]

    approve_buttons = detect_approve_buttons(buttons)
    continue_buttons = detect_continue_buttons(buttons)
    terminal_errors = detect_terminal_errors(terminal_lines)
    diff_prompts = detect_diff_prompts(terminal_lines)

    detected_actions: List[str] = []
    if approve_buttons:
        detected_actions.append("approve")
    if continue_buttons:
        detected_actions.append("continue")
    if diff_prompts:
        detected_actions.append("review_diff")
    if terminal_errors:
        detected_actions.append("inspect_error")

    return UIState(
        buttons=buttons,
        dialogs=dialogs,
        terminal_lines=terminal_lines,
        active_window=str(capture_metadata.get("active_window", "")),
        detected_actions=detected_actions,
    )
