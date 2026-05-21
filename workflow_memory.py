import uuid
from typing import Any, Dict, Optional


workflow_sessions: Dict[str, Dict[str, Any]] = {}


def create_workflow_session(
    current_step: str = "",
    last_action: str = "",
    expected_state: str = "",
    observed_state: str = "",
    status: str = "INITIALIZED",
) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "current_step": current_step,
        "last_action": last_action,
        "expected_state": expected_state,
        "observed_state": observed_state,
        "retry_count": 0,
        "status": status,
    }
    workflow_sessions[session_id] = session
    return session


def update_workflow_state(session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    session = workflow_sessions.get(session_id)
    if session is None:
        return None
    session.update(updates)
    return session


def get_workflow_state(session_id: str) -> Optional[Dict[str, Any]]:
    return workflow_sessions.get(session_id)
