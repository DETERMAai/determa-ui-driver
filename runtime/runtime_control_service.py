from datetime import datetime
from typing import Any, Callable, Dict, Set


quarantined_workers: Set[str] = set()


def pause_runtime(
    stop_runtime_fn: Callable[[], Dict[str, Any]],
    publish_event_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    result = stop_runtime_fn()
    publish_event_fn(
        {
            "event_type": "runtime_paused",
            "payload": {"result": result, "timestamp": datetime.utcnow().isoformat() + "Z"},
        }
    )
    return {"status": "paused", "result": result}


def resume_runtime(
    start_runtime_fn: Callable[[], Dict[str, Any]],
    publish_event_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    result = start_runtime_fn()
    publish_event_fn(
        {
            "event_type": "runtime_resumed",
            "payload": {"result": result, "timestamp": datetime.utcnow().isoformat() + "Z"},
        }
    )
    return {"status": "running", "result": result}


def stop_workflow(
    session_id: str,
    get_workflow_state_fn: Callable[[str], Dict[str, Any]],
    update_workflow_state_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    publish_event_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    session = get_workflow_state_fn(session_id)
    if session is None:
        return {"status": "not_found", "session_id": session_id}

    updated = update_workflow_state_fn(
        session_id,
        {
            "status": "STOPPED",
            "current_step": "STOPPED_BY_OPERATOR",
            "stopped_at": datetime.utcnow().isoformat() + "Z",
        },
    )
    publish_event_fn(
        {
            "event_type": "workflow_stopped",
            "payload": {"session_id": session_id, "status": "STOPPED"},
        }
    )
    return {"status": "stopped", "session_id": session_id, "workflow": updated}


def quarantine_worker(
    worker_id: str,
    stop_worker_fn: Callable[[str], Dict[str, Any]],
    publish_event_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    quarantined_workers.add(str(worker_id))
    stop_result = stop_worker_fn(str(worker_id))
    publish_event_fn(
        {
            "event_type": "worker_quarantined",
            "payload": {"worker_id": str(worker_id), "stop_result": stop_result},
        }
    )
    return {
        "status": "quarantined",
        "worker_id": str(worker_id),
        "stop_result": stop_result,
    }


def force_escalation(
    session_id: str,
    get_workflow_state_fn: Callable[[str], Dict[str, Any]],
    get_development_session_fn: Callable[[str], Dict[str, Any]],
    escalate_fn: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    publish_event_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    workflow = get_workflow_state_fn(session_id)
    if workflow is None:
        return {"status": "not_found", "session_id": session_id}

    development = get_development_session_fn(session_id) or {}
    escalation = escalate_fn(
        "forced_operator_escalation",
        {
            "session_id": session_id,
            "workflow_state": workflow,
            "development_state": development,
        },
    )
    publish_event_fn(
        {
            "event_type": "operator_forced_escalation",
            "payload": {"session_id": session_id, "escalation": escalation},
        }
    )
    return {"status": "escalated", "session_id": session_id, "escalation": escalation}


def is_worker_quarantined(worker_id: str) -> bool:
    return str(worker_id) in quarantined_workers


def get_runtime_control_state() -> Dict[str, Any]:
    return {
        "quarantined_workers": sorted(list(quarantined_workers)),
        "quarantined_count": len(quarantined_workers),
    }
