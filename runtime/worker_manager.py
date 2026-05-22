import time
from collections import deque
from datetime import datetime
from threading import Event, Lock, Thread
from typing import Any, Callable, Deque, Dict, Optional


WORKER_NAMES = [
    "perception_worker",
    "terminal_worker",
    "git_worker",
    "reasoning_worker",
    "execution_worker",
    "verification_worker",
]

_lock = Lock()
_workers: Dict[str, Dict[str, Any]] = {}
_worker_threads: Dict[str, Thread] = {}
_worker_stop_events: Dict[str, Event] = {}
_worker_event_queues: Dict[str, Deque[Dict[str, Any]]] = {}
_worker_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _default_handler(_: Dict[str, Any]):
    return


def _ensure_worker_state(worker_name: str):
    if worker_name not in _workers:
        _workers[worker_name] = {
            "name": worker_name,
            "state": "STOPPED",
            "last_heartbeat": "",
            "crash_count": 0,
            "restart_count": 0,
            "processed_events": 0,
            "last_error": "",
            "last_event_type": "",
        }
    if worker_name not in _worker_event_queues:
        _worker_event_queues[worker_name] = deque()
    if worker_name not in _worker_handlers:
        _worker_handlers[worker_name] = _default_handler


def register_worker_handler(worker_name: str, handler: Callable[[Dict[str, Any]], None]):
    with _lock:
        _ensure_worker_state(worker_name)
        _worker_handlers[worker_name] = handler
        _workers[worker_name]["handler_registered"] = True


def _worker_loop(worker_name: str, interval_sec: float):
    stop_event = _worker_stop_events[worker_name]
    while not stop_event.is_set():
        try:
            event = None
            with _lock:
                _ensure_worker_state(worker_name)
                queue = _worker_event_queues[worker_name]
                if queue:
                    event = queue.popleft()
                    _workers[worker_name]["queued_events"] = len(queue)
                _workers[worker_name]["last_heartbeat"] = _now_iso()
                _workers[worker_name]["state"] = "RUNNING"

            if event is not None:
                handler = _worker_handlers.get(worker_name, _default_handler)
                handler(event)
                with _lock:
                    _workers[worker_name]["processed_events"] += 1
                    _workers[worker_name]["last_event_type"] = str(event.get("event_type", ""))
                    _workers[worker_name]["last_heartbeat"] = _now_iso()
            else:
                time.sleep(max(0.05, float(interval_sec)))
        except Exception as exc:
            with _lock:
                _ensure_worker_state(worker_name)
                _workers[worker_name]["crash_count"] += 1
                _workers[worker_name]["state"] = "CRASHED"
                _workers[worker_name]["last_error"] = str(exc)
                _workers[worker_name]["last_heartbeat"] = _now_iso()
            time.sleep(max(0.1, float(interval_sec)))

    with _lock:
        _ensure_worker_state(worker_name)
        _workers[worker_name]["state"] = "STOPPED"
        _workers[worker_name]["last_heartbeat"] = _now_iso()


def start_worker(worker_name: str, interval_sec: float = 0.25) -> Dict[str, Any]:
    with _lock:
        _ensure_worker_state(worker_name)
        existing = _worker_threads.get(worker_name)
        if existing and existing.is_alive():
            return {"status": "already_running", "worker": dict(_workers[worker_name])}

        stop_event = Event()
        _worker_stop_events[worker_name] = stop_event
        thread = Thread(
            target=_worker_loop,
            args=(worker_name, interval_sec),
            daemon=True,
            name=f"determa-{worker_name}",
        )
        _worker_threads[worker_name] = thread
        _workers[worker_name]["state"] = "STARTING"
        _workers[worker_name]["last_heartbeat"] = _now_iso()
        _workers[worker_name]["interval_sec"] = float(interval_sec)

    thread.start()
    return {"status": "started", "worker": get_worker_state(worker_name)}


def stop_worker(worker_name: str, join_timeout_sec: float = 1.5) -> Dict[str, Any]:
    with _lock:
        _ensure_worker_state(worker_name)
        stop_event = _worker_stop_events.get(worker_name)
        thread = _worker_threads.get(worker_name)
        if stop_event is None or thread is None:
            _workers[worker_name]["state"] = "STOPPED"
            return {"status": "already_stopped", "worker": dict(_workers[worker_name])}
        stop_event.set()

    thread.join(timeout=max(0.1, float(join_timeout_sec)))
    with _lock:
        _workers[worker_name]["state"] = "STOPPED"
        _workers[worker_name]["last_heartbeat"] = _now_iso()
    return {"status": "stopped", "worker": get_worker_state(worker_name)}


def restart_worker(worker_name: str) -> Dict[str, Any]:
    with _lock:
        _ensure_worker_state(worker_name)
        interval = float(_workers[worker_name].get("interval_sec", 0.25))
        _workers[worker_name]["restart_count"] += 1
    stop_worker(worker_name)
    return start_worker(worker_name, interval_sec=interval)


def dispatch_event_to_worker(worker_name: str, event: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        _ensure_worker_state(worker_name)
        queue = _worker_event_queues[worker_name]
        queue.append(dict(event))
        _workers[worker_name]["queued_events"] = len(queue)
        _workers[worker_name]["last_heartbeat"] = _now_iso()
    return {"status": "queued", "worker_name": worker_name, "queued_events": len(queue)}


def get_worker_state(worker_name: str) -> Dict[str, Any]:
    with _lock:
        _ensure_worker_state(worker_name)
        return dict(_workers[worker_name])


def get_workers_state() -> Dict[str, Any]:
    with _lock:
        snapshot = {name: dict(state) for name, state in _workers.items()}
    return {
        "workers": snapshot,
        "worker_names": list(snapshot.keys()),
    }


def initialize_default_workers() -> Dict[str, Any]:
    with _lock:
        for worker_name in WORKER_NAMES:
            _ensure_worker_state(worker_name)
    return get_workers_state()
