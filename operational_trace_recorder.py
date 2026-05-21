import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


operational_traces: List[Dict[str, Any]] = []
_MAX_TRACES = 5000
_pending_approval_started_at: Dict[str, str] = {}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _to_dt(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except Exception:
        return None


def _trace_id(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def append_operational_trace(
    trace_type: str,
    payload: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    job_id: Optional[str] = None,
    actor: str = "runtime",
) -> Dict[str, Any]:
    trace_payload = dict(payload or {})
    timestamp = _now_iso()

    if trace_type == "approval_requested" and job_id:
        _pending_approval_started_at[str(job_id)] = timestamp
    if trace_type == "approval_approved" and job_id:
        started_at = _pending_approval_started_at.get(str(job_id))
        if started_at:
            start_dt = _to_dt(started_at)
            end_dt = _to_dt(timestamp)
            if start_dt and end_dt:
                trace_payload["approval_latency_ms"] = int((end_dt - start_dt).total_seconds() * 1000)
            _pending_approval_started_at.pop(str(job_id), None)

    record = {
        "trace_id": "",
        "trace_type": str(trace_type or "unknown"),
        "timestamp": timestamp,
        "session_id": str(session_id) if session_id else None,
        "job_id": str(job_id) if job_id else None,
        "actor": str(actor or "runtime"),
        "payload": trace_payload,
    }
    record["trace_id"] = _trace_id(record)
    operational_traces.append(record)
    if len(operational_traces) > _MAX_TRACES:
        del operational_traces[0 : len(operational_traces) - _MAX_TRACES]
    return record


def get_recent_operational_traces(limit: int = 100, session_id: Optional[str] = None) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit), _MAX_TRACES))
    traces = operational_traces
    if session_id:
        traces = [item for item in traces if str(item.get("session_id") or "") == str(session_id)]
    recent = traces[-safe_limit:]
    return {
        "traces": recent,
        "count": len(recent),
        "total_recorded": len(traces),
    }


def export_workflow_session(session_id: str) -> Dict[str, Any]:
    traces = [item for item in operational_traces if str(item.get("session_id") or "") == str(session_id)]
    traces.sort(key=lambda item: str(item.get("timestamp", "")))
    return {
        "session_id": session_id,
        "trace_count": len(traces),
        "traces": traces,
    }
