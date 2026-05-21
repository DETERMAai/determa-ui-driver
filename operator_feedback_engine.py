from datetime import datetime
from typing import Any, Dict, List, Optional


operator_feedback_events: List[Dict[str, Any]] = []
_MAX_FEEDBACK_EVENTS = 2000


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def record_operator_feedback(
    feedback_type: str,
    payload: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    event = {
        "timestamp": _now_iso(),
        "feedback_type": str(feedback_type or "unknown_feedback"),
        "session_id": session_id,
        "job_id": job_id,
        "payload": dict(payload or {}),
    }
    operator_feedback_events.append(event)
    if len(operator_feedback_events) > _MAX_FEEDBACK_EVENTS:
        del operator_feedback_events[0 : len(operator_feedback_events) - _MAX_FEEDBACK_EVENTS]
    return event


def generate_operator_trust_snapshot(
    workflow_sessions: Dict[str, Dict[str, Any]],
    escalation_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    approvals = sum(1 for item in operator_feedback_events if item.get("feedback_type") == "approval_approved")
    rejects = sum(1 for item in operator_feedback_events if item.get("feedback_type") == "approval_rejected")
    overrides = sum(
        1
        for item in operator_feedback_events
        if item.get("feedback_type") in {"operator_override", "runtime_paused", "workflow_stopped"}
    )
    escalation_comments = sum(1 for item in operator_feedback_events if item.get("feedback_type") == "escalation_comment")
    trust_degradation_signals = sum(
        1
        for item in operator_feedback_events
        if item.get("feedback_type") in {"approval_rejected", "approval_failed", "trust_degradation_indicator"}
    )

    workflow_total = max(1, len(workflow_sessions))
    completed = sum(1 for item in workflow_sessions.values() if str(item.get("status", "")).upper() == "COMPLETED")
    workflow_trust_score = round((float(completed) / float(workflow_total)) * 100.0, 2)

    operator_trust_score = round(
        max(
            0.0,
            min(
                100.0,
                75.0
                + (approvals * 0.8)
                - (rejects * 1.2)
                - (overrides * 1.0)
                - (trust_degradation_signals * 1.5),
            ),
        ),
        2,
    )

    autonomy_confidence_trend = "stable"
    if trust_degradation_signals > approvals:
        autonomy_confidence_trend = "declining"
    elif approvals > (rejects + overrides):
        autonomy_confidence_trend = "improving"

    return {
        "operator_trust_score": operator_trust_score,
        "workflow_trust_score": workflow_trust_score,
        "autonomy_confidence_trend": autonomy_confidence_trend,
        "signals": {
            "approvals": approvals,
            "rejected_actions": rejects,
            "operator_overrides": overrides,
            "escalation_comments": escalation_comments,
            "trust_degradation_indicators": trust_degradation_signals,
            "escalation_events": len(escalation_events),
        },
        "recent_feedback": operator_feedback_events[-100:],
    }
