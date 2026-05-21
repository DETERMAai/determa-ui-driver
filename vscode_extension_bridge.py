import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from ide_context_engine import detect_ide_context


_bridge_lock = Lock()
_last_editor_state: Dict[str, Any] = {}
_DEFAULT_BRIDGE_PATHS = [
    Path(".determa/editor_state.json"),
    Path("data/editor_state.json"),
    Path("/tmp/determa_editor_state.json"),
]


def _read_json_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)
        if isinstance(content, dict):
            return content
        return None
    except Exception:
        return None


def _normalize_editor_state(raw: Dict[str, Any], source: str) -> Dict[str, Any]:
    diagnostics = raw.get("diagnostics", [])
    open_tabs = raw.get("open_tabs", [])
    approval_prompts = raw.get("approval_prompts", [])

    return {
        "source": source,
        "active_ide": str(raw.get("active_ide", "unknown")),
        "active_file": str(raw.get("active_file", "")),
        "open_tabs": [str(tab) for tab in open_tabs if str(tab).strip()],
        "diagnostics": diagnostics if isinstance(diagnostics, list) else [],
        "diff_visible": bool(raw.get("diff_visible", False)),
        "selected_text": str(raw.get("selected_text", "")),
        "terminal_focus": bool(raw.get("terminal_focus", False)),
        "approval_prompts": [str(item) for item in approval_prompts if str(item).strip()],
        "waiting_state": bool(raw.get("waiting_state", False)),
        "terminal_stdout": str(raw.get("terminal_stdout", "")),
        "terminal_stderr": str(raw.get("terminal_stderr", "")),
        "terminal_command": str(raw.get("terminal_command", "")),
        "terminal_command_status": str(raw.get("terminal_command_status", "")),
    }


def _load_from_bridge_file() -> Optional[Dict[str, Any]]:
    configured_path = os.environ.get("DETERMA_EDITOR_STATE_FILE", "").strip()
    candidate_paths: List[Path] = []
    if configured_path:
        candidate_paths.append(Path(configured_path))
    candidate_paths.extend(_DEFAULT_BRIDGE_PATHS)

    for path in candidate_paths:
        state = _read_json_file(path)
        if state is not None:
            return _normalize_editor_state(state, source=f"bridge_file:{path}")
    return None


def get_editor_state(ui_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    with _bridge_lock:
        native_state = _load_from_bridge_file()
        if native_state is not None:
            _last_editor_state.clear()
            _last_editor_state.update(native_state)
            return dict(native_state)

        if ui_state is not None:
            fallback = detect_ide_context(ui_state)
            ocr_state = {
                "source": "ocr_fallback",
                "active_ide": str(fallback.get("active_ide", "unknown")),
                "active_file": str(fallback.get("open_file", "")),
                "open_tabs": [],
                "diagnostics": [],
                "diff_visible": bool(fallback.get("diff_view", False)),
                "selected_text": "",
                "terminal_focus": bool(fallback.get("terminal_focus", False)),
                "approval_prompts": ["approval_prompt_detected"] if bool(fallback.get("approval_prompt", False)) else [],
                "waiting_state": bool(fallback.get("waiting_state", False)),
                "terminal_stdout": "",
                "terminal_stderr": "",
                "terminal_command": "",
                "terminal_command_status": "",
            }
            _last_editor_state.clear()
            _last_editor_state.update(ocr_state)
            return dict(ocr_state)

        if _last_editor_state:
            return dict(_last_editor_state)

    return {
        "source": "unavailable",
        "active_ide": "unknown",
        "active_file": "",
        "open_tabs": [],
        "diagnostics": [],
        "diff_visible": False,
        "selected_text": "",
        "terminal_focus": False,
        "approval_prompts": [],
        "waiting_state": False,
        "terminal_stdout": "",
        "terminal_stderr": "",
        "terminal_command": "",
        "terminal_command_status": "",
    }
