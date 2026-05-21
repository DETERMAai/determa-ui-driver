import re
from typing import Any, Dict, List, Optional


_FILE_PATTERN = re.compile(r"\b[\w\-.]+\.(py|ts|tsx|js|jsx|json|md|yaml|yml|txt|go|rs)\b", re.IGNORECASE)


def _detect_open_file(terminal_lines: List[str]) -> Optional[str]:
    for line in terminal_lines:
        match = _FILE_PATTERN.search(line)
        if match:
            return match.group(0)
    return None


def detect_ide_context(ui_state: Dict[str, Any]) -> Dict[str, Any]:
    active_window = str(ui_state.get("active_window", ""))
    terminal_lines = [str(line) for line in ui_state.get("terminal_lines", [])]
    dialogs = [str(item) for item in ui_state.get("dialogs", [])]
    detected_actions = [str(item).lower() for item in ui_state.get("detected_actions", [])]

    combined = " ".join([active_window] + terminal_lines + dialogs).lower()
    if "cursor" in combined:
        active_ide = "cursor"
    elif "vscode" in combined or "visual studio code" in combined:
        active_ide = "vscode"
    elif "codex" in combined:
        active_ide = "codex"
    elif "pycharm" in combined:
        active_ide = "pycharm"
    else:
        active_ide = "unknown"

    open_file = _detect_open_file(terminal_lines)
    diff_view = any(token in combined for token in ("diff", "---", "+++", "@@", "review changes"))
    approval_prompt = ("approve" in detected_actions) or any("approve" in dialog.lower() or "allow" in dialog.lower() for dialog in dialogs)
    waiting_state = any(token in combined for token in ("waiting for input", "continue?", "(y/n)", "press enter"))
    terminal_focus = any(token in combined for token in ("terminal", "powershell", "bash", "cmd.exe", "$ ", ">>"))

    return {
        "active_ide": active_ide,
        "open_file": open_file or "",
        "diff_view": bool(diff_view),
        "approval_prompt": bool(approval_prompt),
        "waiting_state": bool(waiting_state),
        "terminal_focus": bool(terminal_focus),
    }
