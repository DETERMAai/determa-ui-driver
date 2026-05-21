from typing import Any, Dict, List


def _active_workflow_items(workflow_sessions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    active = []
    for session in workflow_sessions.values():
        status = str(session.get("status", "")).upper()
        if status not in {"COMPLETED", "ABORTED", "STOPPED"}:
            active.append(session)
    return active


def get_governance_dashboard(
    runtime_status: Dict[str, Any],
    workers_state: Dict[str, Any],
    queue_state: Dict[str, Any],
    workflow_sessions: Dict[str, Dict[str, Any]],
    escalation_events: List[Dict[str, Any]],
    pending_approvals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    active_workflows = _active_workflow_items(workflow_sessions)
    runtime = runtime_status.get("runtime", {})
    last_supervision = runtime.get("last_supervision", {})
    health_report = last_supervision.get("health_report", {})
    runtime_alerts = health_report.get("findings", [])

    return {
        "runtime_status": runtime_status,
        "worker_health": workers_state,
        "queue_status": queue_state,
        "active_workflows": {
            "count": len(active_workflows),
            "items": active_workflows,
        },
        "escalation_count": len(escalation_events),
        "approval_backlog": {
            "count": len(pending_approvals),
            "items": pending_approvals,
        },
        "runtime_alerts": runtime_alerts,
    }
