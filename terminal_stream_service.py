from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

from engineering_event_bus import publish_engineering_event
from terminal_intelligence import analyze_terminal_output


_terminal_lock = Lock()
_MAX_LINES = 500
_MAX_EVENTS = 500

terminal_stream_state: Dict[str, Any] = {
    "stdout": [],
    "stderr": [],
    "process_lifecycle": [],
    "command_state": {
        "command": "",
        "status": "idle",
    },
    "last_analysis": {},
    "last_flags": {},
    "events": [],
    "last_updated": "",
}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _append_limited(items: List[Any], value: Any, max_size: int):
    items.append(value)
    if len(items) > max_size:
        del items[0 : len(items) - max_size]


def _emit_terminal_events(prev_flags: Dict[str, Any], current: Dict[str, Any]):
    mappings = [
        ("tests_started", "tests_running"),
        ("tests_passed", "tests_passed"),
        ("tests_failed", "tests_failed"),
        ("build_started", "build_running"),
        ("build_failed", "build_failed"),
        ("runtime_exception", "runtime_exception"),
    ]

    emitted: List[Dict[str, Any]] = []
    for event_type, flag_name in mappings:
        current_value = bool(current.get(flag_name, False))
        prev_value = bool(prev_flags.get(flag_name, False))
        if current_value and not prev_value:
            emitted.append(
                publish_engineering_event(
                    {
                        "event_type": event_type,
                        "payload": {
                            "primary_state": current.get("primary_state", "idle"),
                            "line_count": int(current.get("line_count", 0)),
                        },
                    }
                )
            )

    return emitted


def stream_terminal_output(
    stdout: Optional[str] = None,
    stderr: Optional[str] = None,
    process_event: Optional[Dict[str, Any]] = None,
    command: Optional[str] = None,
    command_status: Optional[str] = None,
) -> Dict[str, Any]:
    with _terminal_lock:
        if stdout is not None and str(stdout).strip():
            _append_limited(terminal_stream_state["stdout"], str(stdout), _MAX_LINES)
        if stderr is not None and str(stderr).strip():
            _append_limited(terminal_stream_state["stderr"], str(stderr), _MAX_LINES)
        if process_event is not None:
            normalized = {
                "timestamp": _now_iso(),
                "event": dict(process_event),
            }
            _append_limited(terminal_stream_state["process_lifecycle"], normalized, _MAX_EVENTS)
            _append_limited(
                terminal_stream_state["events"],
                publish_engineering_event(
                    {
                        "event_type": "terminal_process_event",
                        "payload": normalized,
                    }
                ),
                _MAX_EVENTS,
            )

        if command is not None:
            terminal_stream_state["command_state"]["command"] = str(command)
        if command_status is not None and str(command_status).strip():
            terminal_stream_state["command_state"]["status"] = str(command_status)

        combined_text = "\n".join(
            [str(line) for line in terminal_stream_state["stdout"][-100:]]
            + [str(line) for line in terminal_stream_state["stderr"][-100:]]
        )
        analysis = analyze_terminal_output(combined_text)

        if terminal_stream_state["command_state"]["status"] == "running" and "test" in str(
            terminal_stream_state["command_state"]["command"]
        ).lower():
            analysis["tests_running"] = True
        else:
            analysis["tests_running"] = False

        prev_flags = dict(terminal_stream_state.get("last_flags", {}))
        emitted = _emit_terminal_events(prev_flags, analysis)
        for event in emitted:
            _append_limited(terminal_stream_state["events"], event, _MAX_EVENTS)

        terminal_stream_state["last_analysis"] = analysis
        terminal_stream_state["last_flags"] = {
            "tests_running": bool(analysis.get("tests_running", False)),
            "tests_passed": bool(analysis.get("tests_passed", False)),
            "tests_failed": bool(analysis.get("tests_failed", False)),
            "build_running": bool(analysis.get("build_running", False)),
            "build_failed": bool(analysis.get("build_failed", False)),
            "runtime_exception": bool(analysis.get("runtime_exception", False)),
        }
        terminal_stream_state["last_updated"] = _now_iso()

        return {
            "stdout_tail": terminal_stream_state["stdout"][-50:],
            "stderr_tail": terminal_stream_state["stderr"][-50:],
            "process_lifecycle": terminal_stream_state["process_lifecycle"][-50:],
            "command_state": dict(terminal_stream_state["command_state"]),
            "analysis": dict(terminal_stream_state["last_analysis"]),
            "events": terminal_stream_state["events"][-50:],
            "last_updated": terminal_stream_state["last_updated"],
        }
