from datetime import datetime
from typing import Any, Dict, List, Optional, Set


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", ""))
    except Exception:
        return datetime.min


def _build_trace_entry(source: str, event_type: str, timestamp: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    lowered = str(event_type).lower()
    category = "events"
    if "approve" in lowered:
        category = "approvals"
    elif any(token in lowered for token in ("verify", "authority", "truth", "invariant", "adversarial", "proof")):
        category = "verification_results"
    elif any(token in lowered for token in ("recover", "retry")):
        category = "recovery_attempts"
    elif "escalat" in lowered:
        category = "escalations"
    elif any(token in lowered for token in ("action", "execution", "executed", "blocked", "queued")):
        category = "actions"
    elif any(token in lowered for token in ("objective", "reason", "policy", "workflow_continuation")):
        category = "reasoning"

    return {
        "source": source,
        "event_type": event_type,
        "timestamp": timestamp,
        "category": category,
        "payload": payload,
    }


def _find_related_job_ids(
    session_id: str,
    workflow_session: Dict[str, Any],
    engineering_events: List[Dict[str, Any]],
) -> Set[str]:
    related: Set[str] = set()

    retry_job_id = workflow_session.get("retry_job_id")
    if retry_job_id:
        related.add(str(retry_job_id))

    for event in engineering_events:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        if str(payload.get("session_id", "")) == session_id and payload.get("job_id"):
            related.add(str(payload.get("job_id")))
    return related


def get_execution_trace(
    session_id: str,
    workflow_session: Optional[Dict[str, Any]],
    development_session: Optional[Dict[str, Any]],
    audit_events: List[Dict[str, Any]],
    engineering_events: List[Dict[str, Any]],
    escalation_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if workflow_session is None:
        return {
            "status": "not_found",
            "session_id": session_id,
            "trace": [],
        }

    related_job_ids = _find_related_job_ids(session_id, workflow_session, engineering_events)
    trace_entries: List[Dict[str, Any]] = []

    for event in audit_events:
        if not related_job_ids:
            continue
        job_id = str(event.get("job_id", ""))
        if job_id not in related_job_ids:
            continue
        trace_entries.append(
            _build_trace_entry(
                source="audit_log",
                event_type=str(event.get("event_type", "")),
                timestamp=str(event.get("timestamp", "")),
                payload={"job_id": job_id, "data": event.get("data", {})},
            )
        )

    for event in engineering_events:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        event_session_id = str(payload.get("session_id", ""))
        if event_session_id != session_id and not (
            payload.get("job_id") and str(payload.get("job_id")) in related_job_ids
        ):
            continue
        trace_entries.append(
            _build_trace_entry(
                source="engineering_event_bus",
                event_type=str(event.get("event_type", "")),
                timestamp=str(event.get("timestamp", "")),
                payload=payload,
            )
        )

    for event in escalation_events:
        context = event.get("context", {}) if isinstance(event.get("context"), dict) else {}
        if str(context.get("session_id", "")) != session_id:
            continue
        trace_entries.append(
            _build_trace_entry(
                source="escalation_manager",
                event_type=str(event.get("reason", "escalation")),
                timestamp=str(event.get("timestamp", "")),
                payload=context,
            )
        )

    for progress in (development_session or {}).get("workflow_progress", []):
        trace_entries.append(
            _build_trace_entry(
                source="development_state_machine",
                event_type="workflow_progress",
                timestamp=str(progress.get("timestamp", "")),
                payload=progress,
            )
        )

    trace_entries.append(
        _build_trace_entry(
            source="workflow_memory",
            event_type="workflow_state_snapshot",
            timestamp=str(datetime.utcnow().isoformat() + "Z"),
            payload=workflow_session,
        )
    )

    trace_entries.sort(key=lambda item: (_parse_ts(item.get("timestamp", "")), item.get("source", "")))
    grouped_counts: Dict[str, int] = {}
    for item in trace_entries:
        category = str(item.get("category", "events"))
        grouped_counts[category] = grouped_counts.get(category, 0) + 1

    return {
        "status": "ok",
        "session_id": session_id,
        "related_job_ids": sorted(list(related_job_ids)),
        "trace": trace_entries,
        "trace_counts": grouped_counts,
    }
