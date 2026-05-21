from datetime import datetime
from typing import Any, Dict, List, Optional


development_sessions: Dict[str, Dict[str, Any]] = {}


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def create_development_session(session_id: str) -> Dict[str, Any]:
    session = {
        "session_id": session_id,
        "state": "waiting_for_patch",
        "last_terminal_state": {},
        "last_git_state": {},
        "last_ide_state": {},
        "workflow_progress": [],
    }
    development_sessions[session_id] = session
    return session


def get_development_session(session_id: str) -> Optional[Dict[str, Any]]:
    return development_sessions.get(session_id)


def get_development_state() -> Dict[str, Any]:
    return {
        "sessions": development_sessions,
        "session_count": len(development_sessions),
    }


def _determine_state(
    terminal_state: Dict[str, Any],
    git_state: Dict[str, Any],
    ide_state: Dict[str, Any],
) -> str:
    patch_state = str(git_state.get("patch_state", ""))

    if bool(ide_state.get("approval_prompt")):
        return "waiting_for_approval"
    if bool(terminal_state.get("tests_passed")) and patch_state == "patch_applied":
        return "completed"
    if bool(terminal_state.get("tests_failed")):
        return "tests_failed"
    if bool(terminal_state.get("build_failed")) or bool(terminal_state.get("runtime_exception")):
        return "build_failed"
    if patch_state == "patch_applied":
        return "patch_applied"
    if bool(terminal_state.get("build_running")) or bool(terminal_state.get("install_running")):
        return "waiting_for_tests"
    if bool(terminal_state.get("waiting_for_input")):
        return "blocked"
    if patch_state == "partial_apply":
        return "blocked"
    return "waiting_for_patch"


def update_development_session(
    session_id: str,
    terminal_state: Dict[str, Any],
    git_state: Dict[str, Any],
    ide_state: Dict[str, Any],
) -> Dict[str, Any]:
    session = development_sessions.get(session_id) or create_development_session(session_id)

    state = _determine_state(terminal_state, git_state, ide_state)
    next_step = "observe"
    if state == "waiting_for_approval":
        next_step = "request_approval"
    elif state in {"tests_failed", "build_failed", "blocked"}:
        next_step = "recover_or_escalate"
    elif state == "completed":
        next_step = "finalize"
    elif state == "patch_applied":
        next_step = "run_tests"
    elif state == "waiting_for_tests":
        next_step = "wait_for_completion"

    session["state"] = state
    session["last_terminal_state"] = terminal_state
    session["last_git_state"] = git_state
    session["last_ide_state"] = ide_state
    session["workflow_progress"].append(
        {
            "timestamp": _utc_now_iso(),
            "state": state,
            "next_step": next_step,
        }
    )
    if len(session["workflow_progress"]) > 100:
        del session["workflow_progress"][0 : len(session["workflow_progress"]) - 100]

    return session
