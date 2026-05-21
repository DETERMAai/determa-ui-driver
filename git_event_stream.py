import subprocess
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List

from engineering_event_bus import publish_engineering_event
from git_state_engine import detect_patch_application_state, get_git_state


_git_lock = Lock()
_MAX_EVENTS = 500
_recent_git_events: List[Dict[str, Any]] = []
_last_git_snapshot: Dict[str, Any] = {}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _run_git(args: List[str]) -> str:
    try:
        proc = subprocess.run(["git"] + args, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return ""
        return (proc.stdout or "").strip()
    except Exception:
        return ""


def _append_event(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = publish_engineering_event(
        {
            "event_type": event_type,
            "payload": {
                **payload,
                "timestamp": _now_iso(),
            },
        }
    )
    _recent_git_events.append(normalized)
    if len(_recent_git_events) > _MAX_EVENTS:
        del _recent_git_events[0 : len(_recent_git_events) - _MAX_EVENTS]
    return normalized


def watch_git_events() -> Dict[str, Any]:
    with _git_lock:
        current_state = get_git_state()
        current_state.update(detect_patch_application_state(current_state))
        current_state["head"] = _run_git(["rev-parse", "HEAD"])

        events: List[Dict[str, Any]] = []
        if not _last_git_snapshot:
            events.append(_append_event("git_snapshot_initialized", {"git_state": current_state}))
            _last_git_snapshot.clear()
            _last_git_snapshot.update(current_state)
            return {
                "git_state": dict(current_state),
                "events": events,
            }

        if current_state.get("branch") != _last_git_snapshot.get("branch"):
            events.append(
                _append_event(
                    "git_branch_changed",
                    {
                        "from": _last_git_snapshot.get("branch", ""),
                        "to": current_state.get("branch", ""),
                    },
                )
            )

        if current_state.get("head") and current_state.get("head") != _last_git_snapshot.get("head"):
            events.append(
                _append_event(
                    "git_commit_created",
                    {
                        "from": _last_git_snapshot.get("head", ""),
                        "to": current_state.get("head", ""),
                    },
                )
            )

        for key in ("modified_files", "staged_files", "untracked_files"):
            before = list(_last_git_snapshot.get(key, []))
            after = list(current_state.get(key, []))
            if before != after:
                events.append(
                    _append_event(
                        f"git_{key}_changed",
                        {
                            "before": before,
                            "after": after,
                        },
                    )
                )

        before_conflicts = list(_last_git_snapshot.get("conflicts", []))
        after_conflicts = list(current_state.get("conflicts", []))
        if before_conflicts != after_conflicts:
            events.append(
                _append_event(
                    "git_conflicts_changed",
                    {
                        "before": before_conflicts,
                        "after": after_conflicts,
                    },
                )
            )

        if current_state.get("patch_state") != _last_git_snapshot.get("patch_state"):
            events.append(
                _append_event(
                    "git_patch_state_changed",
                    {
                        "from": _last_git_snapshot.get("patch_state", ""),
                        "to": current_state.get("patch_state", ""),
                    },
                )
            )

        _last_git_snapshot.clear()
        _last_git_snapshot.update(current_state)
        return {
            "git_state": dict(current_state),
            "events": events,
        }


def get_recent_git_events(limit: int = 100) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit), _MAX_EVENTS))
    with _git_lock:
        return {
            "events": [dict(event) for event in _recent_git_events[-safe_limit:]],
            "last_snapshot": dict(_last_git_snapshot),
        }
