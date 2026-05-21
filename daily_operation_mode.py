from datetime import datetime
from typing import Any, Dict, List, Optional


daily_operation_sessions: List[Dict[str, Any]] = []
_MAX_DAILY_SESSIONS = 60


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def start_daily_operation_session(
    runtime_status: Dict[str, Any],
    git_state: Dict[str, Any],
    restore_result: Dict[str, Any],
    pending_approvals: List[Dict[str, Any]],
    operator_task_intake: Optional[List[str]] = None,
) -> Dict[str, Any]:
    session_id = f"daily-{len(daily_operation_sessions) + 1}"
    session = {
        "session_id": session_id,
        "started_at": _now_iso(),
        "ended_at": None,
        "status": "ACTIVE",
        "checks": {
            "runtime_health_check": runtime_status,
            "git_state_check": git_state,
            "workflow_restore": restore_result,
            "pending_approval_review": {
                "count": len(pending_approvals),
                "items": pending_approvals,
            },
            "operator_task_intake": [str(item) for item in (operator_task_intake or []) if str(item).strip()],
        },
        "stats": {
            "session_duration_sec": 0,
            "workflows_attempted": 0,
            "approvals_required": len(pending_approvals),
            "escalations": 0,
            "recovery_attempts": 0,
        },
    }
    daily_operation_sessions.append(session)
    if len(daily_operation_sessions) > _MAX_DAILY_SESSIONS:
        del daily_operation_sessions[0 : len(daily_operation_sessions) - _MAX_DAILY_SESSIONS]
    return session


def update_daily_operation_stats(
    workflows_attempted: int,
    approvals_required: int,
    escalations: int,
    recovery_attempts: int,
) -> Optional[Dict[str, Any]]:
    if not daily_operation_sessions:
        return None
    session = daily_operation_sessions[-1]
    started_at = session.get("started_at")
    try:
        started_dt = datetime.fromisoformat(str(started_at).replace("Z", ""))
        duration_sec = int((datetime.utcnow() - started_dt).total_seconds())
    except Exception:
        duration_sec = 0

    session["stats"] = {
        "session_duration_sec": duration_sec,
        "workflows_attempted": int(workflows_attempted),
        "approvals_required": int(approvals_required),
        "escalations": int(escalations),
        "recovery_attempts": int(recovery_attempts),
    }
    return session


def get_daily_operation_status() -> Dict[str, Any]:
    current = daily_operation_sessions[-1] if daily_operation_sessions else None
    return {
        "active_session": current,
        "session_count": len(daily_operation_sessions),
        "recent_sessions": daily_operation_sessions[-10:],
    }
