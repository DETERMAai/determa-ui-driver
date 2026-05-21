import time
from datetime import datetime
from queue import Empty, PriorityQueue
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, Optional, Set

from engineering_event_bus import get_recent_engineering_events, subscribe_engineering_event
from event_priority_engine import prioritize_event
from runtime_supervisor import run_supervision_cycle
from worker_manager import (
    WORKER_NAMES,
    dispatch_event_to_worker,
    get_workers_state,
    initialize_default_workers,
    start_worker,
)


_runtime_lock = Lock()
_runtime_thread: Optional[Thread] = None
_runtime_stop_event: Optional[Event] = None
_event_queue: PriorityQueue = PriorityQueue()
_event_sequence = 0
_subscribed = False
_seen_event_ids: Set[str] = set()

_runtime_state: Dict[str, Any] = {
    "running": False,
    "started_at": "",
    "stopped_at": "",
    "processed_events_count": 0,
    "queue_size": 0,
    "last_processed_event_id": "",
    "last_processed_event_type": "",
    "last_processed_at": "",
    "stalled_cycles": 0,
    "excessive_retries_count": 0,
    "recovery_loop_count": 0,
    "last_terminal_event_at": "",
    "last_supervision_at": "",
}

_hooks: Dict[str, Any] = {
    "worker_handlers": {},
    "escalation_handler": None,
    "worker_start_guard": None,
    "worker_restart_guard": None,
}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def configure_runtime_hooks(
    worker_handlers: Optional[Dict[str, Callable[[Dict[str, Any]], None]]] = None,
    escalation_handler: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    worker_start_guard: Optional[Callable[[str], bool]] = None,
    worker_restart_guard: Optional[Callable[[str], bool]] = None,
):
    with _runtime_lock:
        _hooks["worker_handlers"] = dict(worker_handlers or {})
        _hooks["escalation_handler"] = escalation_handler
        _hooks["worker_start_guard"] = worker_start_guard
        _hooks["worker_restart_guard"] = worker_restart_guard


def _target_worker_for_event(event: Dict[str, Any]) -> str:
    event_type = str(event.get("event_type", "")).lower()
    if "terminal" in event_type or "tests_" in event_type or "build_" in event_type:
        return "terminal_worker"
    if event_type.startswith("git_"):
        return "git_worker"
    if "execution" in event_type or "executed" in event_type or "blocked" in event_type:
        return "execution_worker"
    if any(token in event_type for token in ("verify", "truth", "invariant", "authority", "adversarial", "proof")):
        return "verification_worker"
    if any(token in event_type for token in ("screen", "perception", "ocr", "editor")):
        return "perception_worker"
    return "reasoning_worker"


def _enqueue_event(event: Dict[str, Any]):
    global _event_sequence

    event_id = str(event.get("event_id", ""))
    if event_id and event_id in _seen_event_ids:
        return
    if event_id:
        _seen_event_ids.add(event_id)

    prioritized = prioritize_event(event)
    priority = int(prioritized.get("priority", 1))

    with _runtime_lock:
        _event_sequence += 1
        sequence = _event_sequence

    # PriorityQueue is min-first, so negate priority to process CRITICAL first.
    _event_queue.put((-priority, sequence, prioritized))
    with _runtime_lock:
        _runtime_state["queue_size"] = _event_queue.qsize()


def _engineering_event_subscriber(event: Dict[str, Any]):
    _enqueue_event(event)


def _start_workers():
    initialize_default_workers()
    handlers = dict(_hooks.get("worker_handlers", {}))
    start_guard = _hooks.get("worker_start_guard")
    for worker_name in WORKER_NAMES:
        if start_guard is not None and not bool(start_guard(worker_name)):
            continue
        # Worker handlers are optional. The worker manager defaults to no-op.
        handler = handlers.get(worker_name)
        if handler is not None:
            from worker_manager import register_worker_handler

            register_worker_handler(worker_name, handler)
        start_worker(worker_name)


def _bootstrap_recent_events():
    for event in get_recent_engineering_events(200):
        _enqueue_event(event)


def _runtime_loop():
    supervision_tick = 0
    while _runtime_stop_event is not None and not _runtime_stop_event.is_set():
        try:
            _, _, prioritized = _event_queue.get(timeout=0.5)
            event = dict(prioritized.get("event", {}))
            event_type = str(event.get("event_type", "")).lower()
            worker_name = _target_worker_for_event(event)
            dispatch_event_to_worker(worker_name, event)

            with _runtime_lock:
                _runtime_state["processed_events_count"] = int(_runtime_state["processed_events_count"]) + 1
                _runtime_state["queue_size"] = _event_queue.qsize()
                _runtime_state["last_processed_event_id"] = str(event.get("event_id", ""))
                _runtime_state["last_processed_event_type"] = event_type
                _runtime_state["last_processed_at"] = _now_iso()
                _runtime_state["stalled_cycles"] = 0
                if "terminal" in event_type or "tests_" in event_type or "build_" in event_type:
                    _runtime_state["last_terminal_event_at"] = _now_iso()
                if "recovery" in event_type:
                    _runtime_state["recovery_loop_count"] = int(_runtime_state["recovery_loop_count"]) + 1
                if "retry" in event_type:
                    _runtime_state["excessive_retries_count"] = int(_runtime_state["excessive_retries_count"]) + 1

            _event_queue.task_done()
        except Empty:
            with _runtime_lock:
                _runtime_state["stalled_cycles"] = int(_runtime_state["stalled_cycles"]) + 1
                _runtime_state["queue_size"] = _event_queue.qsize()
            time.sleep(0.1)

        supervision_tick += 1
        if supervision_tick % 20 == 0:
            recent_events = get_recent_engineering_events(100)
            with _runtime_lock:
                state_snapshot = dict(_runtime_state)
                escalation_handler = _hooks.get("escalation_handler")
                restart_guard = _hooks.get("worker_restart_guard")
            supervision = run_supervision_cycle(
                runtime_state=state_snapshot,
                recent_events=recent_events,
                escalation_handler=escalation_handler,
                restart_guard=restart_guard,
            )
            with _runtime_lock:
                _runtime_state["last_supervision_at"] = _now_iso()
                _runtime_state["last_supervision"] = supervision

    with _runtime_lock:
        _runtime_state["running"] = False
        _runtime_state["stopped_at"] = _now_iso()


def start_runtime_loop() -> Dict[str, Any]:
    global _runtime_thread, _runtime_stop_event, _subscribed

    with _runtime_lock:
        if _runtime_thread is not None and _runtime_thread.is_alive():
            return {"status": "already_running", "runtime_state": dict(_runtime_state)}

        _runtime_stop_event = Event()
        _runtime_state["running"] = True
        _runtime_state["started_at"] = _now_iso()
        _runtime_state["stopped_at"] = ""
        _runtime_state["stalled_cycles"] = 0
        _runtime_state["excessive_retries_count"] = 0
        _runtime_state["recovery_loop_count"] = 0

    _start_workers()
    if not _subscribed:
        subscribe_engineering_event(_engineering_event_subscriber)
        _subscribed = True
    _bootstrap_recent_events()

    _runtime_thread = Thread(target=_runtime_loop, daemon=True, name="determa-runtime-event-loop")
    _runtime_thread.start()
    return {"status": "started", "runtime_state": get_runtime_status()}


def stop_runtime_loop(timeout_sec: float = 2.0) -> Dict[str, Any]:
    global _runtime_thread, _runtime_stop_event
    with _runtime_lock:
        stop_event = _runtime_stop_event
        thread = _runtime_thread
        if stop_event is None or thread is None:
            _runtime_state["running"] = False
            _runtime_state["stopped_at"] = _now_iso()
            return {"status": "already_stopped", "runtime_state": dict(_runtime_state)}
        stop_event.set()

    thread.join(timeout=max(0.1, float(timeout_sec)))
    with _runtime_lock:
        _runtime_state["running"] = False
        _runtime_state["stopped_at"] = _now_iso()
    return {"status": "stopped", "runtime_state": get_runtime_status()}


def get_runtime_status() -> Dict[str, Any]:
    with _runtime_lock:
        state = dict(_runtime_state)
        state["queue_size"] = _event_queue.qsize()
    workers = get_workers_state()
    return {
        "runtime": state,
        "workers_summary": {
            "total_workers": len(workers.get("workers", {})),
        },
    }
