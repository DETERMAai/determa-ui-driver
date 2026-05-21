import hashlib
import json
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Dict, List


_event_bus_lock = Lock()
_event_subscribers: List[Callable[[Dict[str, Any]], None]] = []
_engineering_events: List[Dict[str, Any]] = []
_MAX_EVENTS = 1000


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _hash_event_payload(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def publish_engineering_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event_type = str(event.get("event_type", "unknown")).strip().lower()
    payload = dict(event.get("payload", {}))
    timestamp = str(event.get("timestamp", _utc_now_iso()))
    event_id = _hash_event_payload(
        {
            "event_type": event_type,
            "timestamp": timestamp,
            "payload": payload,
        }
    )

    normalized_event = {
        "event_id": event_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "payload": payload,
    }

    with _event_bus_lock:
        _engineering_events.append(normalized_event)
        if len(_engineering_events) > _MAX_EVENTS:
            del _engineering_events[0 : len(_engineering_events) - _MAX_EVENTS]
        subscribers = list(_event_subscribers)

    for subscriber in subscribers:
        try:
            subscriber(normalized_event)
        except Exception:
            continue

    return normalized_event


def subscribe_engineering_event(handler: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
    with _event_bus_lock:
        _event_subscribers.append(handler)
        subscriber_count = len(_event_subscribers)
    return {
        "status": "subscribed",
        "subscriber_count": subscriber_count,
    }


def get_recent_engineering_events(limit: int = 100) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(int(limit), _MAX_EVENTS))
    with _event_bus_lock:
        return [dict(event) for event in _engineering_events[-safe_limit:]]
