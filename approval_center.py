from typing import Any, Callable, Dict, List, Optional


def _find_related_session_id(job_id: str, job_data: Dict[str, Any], workflow_sessions: Dict[str, Dict[str, Any]]) -> str:
    semantic_action = str(job_data.get("semantic_action", "")).strip().lower()

    for session_id, session in workflow_sessions.items():
        if str(session.get("retry_job_id", "")) == job_id:
            return session_id

    for session_id, session in workflow_sessions.items():
        status = str(session.get("status", "")).upper()
        if status == "AWAITING_APPROVAL":
            last_action = str(session.get("last_action", "")).strip().lower()
            if semantic_action and last_action == semantic_action:
                return session_id

    return ""


def get_pending_approvals(
    pending_jobs: Dict[str, Dict[str, Any]],
    approved_jobs: set,
    workflow_sessions: Dict[str, Dict[str, Any]],
    development_sessions: Dict[str, Dict[str, Any]],
    reasoning_snapshot_provider: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for job_id, job_data in pending_jobs.items():
        if job_id in approved_jobs:
            continue
        if bool(job_data.get("rejected", False)):
            continue

        session_id = _find_related_session_id(str(job_id), job_data, workflow_sessions)
        workflow_state = workflow_sessions.get(session_id, {})
        development_state = development_sessions.get(session_id, {})
        snapshot = reasoning_snapshot_provider(session_id) if (reasoning_snapshot_provider and session_id) else None

        risk_level = "unknown"
        reasoning = "No explicit reasoning available."
        if snapshot:
            next_action = snapshot.get("next_action", {})
            risk_level = str(next_action.get("risk_level", "unknown"))
            reasoning = str(next_action.get("reasoning", reasoning))

        items.append(
            {
                "job_id": str(job_id),
                "action": job_data.get("semantic_action") or job_data.get("action"),
                "reasoning": reasoning,
                "risk_level": risk_level,
                "workflow_state": workflow_state,
                "git_state": development_state.get("last_git_state", {}),
                "terminal_state": development_state.get("last_terminal_state", {}),
                "session_id": session_id or None,
            }
        )

    return items


def approve_action(
    job_id: str,
    pending_jobs: Dict[str, Dict[str, Any]],
    approved_jobs: set,
    emit_event: Callable[[str, str, Dict[str, Any]], Dict[str, Any]],
    publish_event: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    if job_id not in pending_jobs:
        emit_event("BLOCKED", job_id, {"reason": "job_not_found"})
        publish_event({"event_type": "approval_blocked", "payload": {"job_id": job_id, "reason": "job_not_found"}})
        return {"status": "NOT_FOUND", "job_id": job_id}

    approved_jobs.add(job_id)
    pending_jobs[job_id]["rejected"] = False
    emit_event("APPROVED", job_id, {"source": "approval_center"})
    publish_event({"event_type": "job_approved", "payload": {"job_id": job_id, "source": "approval_center"}})
    return {"status": "APPROVED", "job_id": job_id}


def reject_action(
    job_id: str,
    pending_jobs: Dict[str, Dict[str, Any]],
    approved_jobs: set,
    emit_event: Callable[[str, str, Dict[str, Any]], Dict[str, Any]],
    publish_event: Callable[[Dict[str, Any]], Dict[str, Any]],
    reason: str = "rejected_by_operator",
) -> Dict[str, Any]:
    if job_id not in pending_jobs:
        emit_event("BLOCKED", job_id, {"reason": "job_not_found"})
        publish_event({"event_type": "approval_blocked", "payload": {"job_id": job_id, "reason": "job_not_found"}})
        return {"status": "NOT_FOUND", "job_id": job_id}

    approved_jobs.discard(job_id)
    pending_jobs[job_id]["rejected"] = True
    pending_jobs[job_id]["rejected_reason"] = str(reason)
    emit_event("BLOCKED", job_id, {"reason": str(reason), "source": "approval_center"})
    publish_event(
        {
            "event_type": "job_rejected",
            "payload": {"job_id": job_id, "reason": str(reason), "source": "approval_center"},
        }
    )
    return {"status": "REJECTED", "job_id": job_id, "reason": str(reason)}
