import hashlib
from datetime import datetime
from typing import Any, Dict, List, Tuple


def _to_dt(value: str):
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except Exception:
        return None


def _parse_target_timestamp(timestamp: str):
    dt = _to_dt(timestamp)
    if dt is not None:
        return dt
    try:
        return datetime.utcfromtimestamp(float(timestamp))
    except Exception:
        return None


def _stable_hash(value: Any) -> str:
    import json

    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _active_canonical_specs_at_time(
    target_dt: datetime,
    spec_history: List[Dict[str, Any]],
) -> List[str]:
    active = set()
    sorted_history = sorted(spec_history, key=lambda item: str(item.get("timestamp", "")))
    for entry in sorted_history:
        entry_dt = _to_dt(str(entry.get("timestamp", "")))
        if entry_dt is None or entry_dt > target_dt:
            continue
        action = str(entry.get("action", ""))
        spec_id = str(entry.get("spec_id", ""))
        if action == "CANONICALIZED":
            active.add(spec_id)
        elif action in {"SUPERSEDED", "REJECTED"}:
            active.discard(spec_id)
    return sorted(active)


def _filter_events_to_time(
    target_dt: datetime,
    audit_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    filtered: List[Tuple[int, Dict[str, Any]]] = []
    for idx, event in enumerate(audit_events):
        event_dt = _to_dt(str(event.get("timestamp", "")))
        if event_dt is None:
            continue
        if event_dt <= target_dt:
            filtered.append((idx, event))
    filtered.sort(key=lambda pair: (_to_dt(str(pair[1].get("timestamp", ""))), pair[0]))
    return [event for _, event in filtered]


def replay_historical_legitimacy(
    timestamp: str,
    audit_events: List[Dict[str, Any]],
    spec_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    target_dt = _parse_target_timestamp(timestamp)
    if target_dt is None:
        return {
            "status": "error",
            "timestamp": timestamp,
            "error": "invalid_timestamp",
        }

    events = _filter_events_to_time(target_dt, list(audit_events or []))
    jobs: Dict[str, Dict[str, Any]] = {}
    violations: List[Dict[str, Any]] = []
    expected_prev_hash: Dict[str, str] = {}

    for event in events:
        job_id = str(event.get("job_id"))
        event_type = str(event.get("event_type"))
        prev = expected_prev_hash.get(job_id, "GENESIS")
        stored_prev = str(event.get("prev_hash", ""))
        if stored_prev != prev:
            violations.append(
                {
                    "job_id": job_id,
                    "event_id": event.get("event_id"),
                    "reason": "BROKEN_HASH_CHAIN",
                }
            )
        recomputed_hash = hashlib.sha256(
            f"{event_type}{job_id}{event.get('timestamp')}{event.get('prev_hash')}".encode("utf-8")
        ).hexdigest()
        if recomputed_hash != str(event.get("event_hash", "")):
            violations.append(
                {
                    "job_id": job_id,
                    "event_id": event.get("event_id"),
                    "reason": "EVENT_HASH_MISMATCH",
                }
            )
        expected_prev_hash[job_id] = str(event.get("event_hash", ""))

        if job_id not in jobs:
            jobs[job_id] = {
                "proposed": False,
                "approved": False,
                "execution_started": False,
                "executed": False,
                "last_event_type": None,
            }

        state = jobs[job_id]
        if event_type == "PROPOSED":
            state["proposed"] = True
            state["last_event_type"] = event_type
        elif event_type == "APPROVED":
            if not state["proposed"]:
                violations.append(
                    {
                        "job_id": job_id,
                        "event_id": event.get("event_id"),
                        "reason": "APPROVED_WITHOUT_PROPOSED",
                    }
                )
            state["approved"] = True
            state["last_event_type"] = event_type
        elif event_type == "EXECUTION_STARTED":
            if not state["approved"]:
                violations.append(
                    {
                        "job_id": job_id,
                        "event_id": event.get("event_id"),
                        "reason": "EXECUTION_STARTED_WITHOUT_APPROVED",
                    }
                )
            state["execution_started"] = True
            state["last_event_type"] = event_type
        elif event_type == "EXECUTED":
            if not state["execution_started"]:
                violations.append(
                    {
                        "job_id": job_id,
                        "event_id": event.get("event_id"),
                        "reason": "EXECUTED_WITHOUT_EXECUTION_STARTED",
                    }
                )
            state["executed"] = True
            state["last_event_type"] = event_type
        elif event_type == "EXECUTION_FAILED":
            if not state["execution_started"]:
                violations.append(
                    {
                        "job_id": job_id,
                        "event_id": event.get("event_id"),
                        "reason": "EXECUTION_FAILED_WITHOUT_EXECUTION_STARTED",
                    }
                )
            state["executed"] = False
            state["last_event_type"] = event_type
        elif event_type == "BLOCKED":
            state["last_event_type"] = event_type

    active_specs = _active_canonical_specs_at_time(target_dt, list(spec_history or []))
    legitimate = len(violations) == 0

    return {
        "status": "ok",
        "timestamp": target_dt.isoformat() + "Z",
        "legitimate": legitimate,
        "violations": violations,
        "evaluated_event_count": len(events),
        "jobs": jobs,
        "active_canonical_specs": active_specs,
        "historical_state_hash": _stable_hash({"events": events, "jobs": jobs, "specs": active_specs}),
    }
