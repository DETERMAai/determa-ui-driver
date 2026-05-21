from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from worker_manager import get_workers_state, restart_worker


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", ""))
    except Exception:
        return None


def evaluate_runtime_health(
    runtime_state: Dict[str, Any],
    workers_state: Dict[str, Any],
    recent_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    now = datetime.utcnow()
    findings: List[Dict[str, Any]] = []
    workers = workers_state.get("workers", {})

    queue_size = int(runtime_state.get("queue_size", 0))
    processed = int(runtime_state.get("processed_events_count", 0))
    stalled_cycles = int(runtime_state.get("stalled_cycles", 0))

    if queue_size > 0 and stalled_cycles >= 10:
        findings.append(
            {
                "type": "stalled_queue",
                "severity": "high",
                "description": f"Queue is non-empty ({queue_size}) with stalled cycles={stalled_cycles}.",
            }
        )

    if int(runtime_state.get("excessive_retries_count", 0)) > 3:
        findings.append(
            {
                "type": "excessive_retries",
                "severity": "high",
                "description": "Runtime reports repeated retries beyond safe threshold.",
            }
        )

    last_terminal_event_at = _parse_iso(str(runtime_state.get("last_terminal_event_at", "")))
    if last_terminal_event_at is not None and (now - last_terminal_event_at) > timedelta(minutes=5):
        findings.append(
            {
                "type": "silent_terminal_stream",
                "severity": "medium",
                "description": "No terminal events observed for more than 5 minutes.",
            }
        )

    if int(runtime_state.get("recovery_loop_count", 0)) > 5:
        findings.append(
            {
                "type": "runaway_recovery_loop",
                "severity": "critical",
                "description": "Recovery loop appears runaway and needs escalation.",
            }
        )

    for worker_name, worker in workers.items():
        state = str(worker.get("state", "STOPPED"))
        heartbeat = _parse_iso(str(worker.get("last_heartbeat", "")))
        if state in {"CRASHED", "STOPPED"}:
            findings.append(
                {
                    "type": "dead_worker",
                    "severity": "high",
                    "worker": worker_name,
                    "description": f"Worker {worker_name} is {state}.",
                }
            )
        elif heartbeat is not None and (now - heartbeat) > timedelta(seconds=30):
            findings.append(
                {
                    "type": "stale_worker_heartbeat",
                    "severity": "medium",
                    "worker": worker_name,
                    "description": f"Worker {worker_name} heartbeat is stale.",
                }
            )

    # Recent critical events are always surfaced for deterministic supervision.
    for event in recent_events[-20:]:
        event_type = str(event.get("event_type", "")).lower()
        if "policy_violation" in event_type:
            findings.append(
                {
                    "type": "policy_violation_event",
                    "severity": "critical",
                    "description": "Policy violation event seen in recent stream.",
                }
            )

    status = "HEALTHY"
    if any(item.get("severity") == "critical" for item in findings):
        status = "CRITICAL"
    elif findings:
        status = "DEGRADED"

    return {
        "status": status,
        "findings": findings,
        "workers_checked": len(workers),
        "queue_size": queue_size,
        "processed_events_count": processed,
    }


def apply_worker_restart_policy(
    health_report: Dict[str, Any],
    restart_guard: Optional[Callable[[str], bool]] = None,
) -> Dict[str, Any]:
    actions: List[Dict[str, Any]] = []
    for finding in health_report.get("findings", []):
        if finding.get("type") in {"dead_worker", "stale_worker_heartbeat"}:
            worker_name = str(finding.get("worker", "")).strip()
            if worker_name:
                if restart_guard is not None and not bool(restart_guard(worker_name)):
                    actions.append(
                        {
                            "worker": worker_name,
                            "action": "restart_skipped",
                            "reason": "restart_guard_blocked",
                        }
                    )
                    continue
                actions.append(
                    {
                        "worker": worker_name,
                        "action": "restart",
                        "result": restart_worker(worker_name),
                    }
                )
    return {
        "actions": actions,
        "action_count": len(actions),
    }


def run_supervision_cycle(
    runtime_state: Dict[str, Any],
    recent_events: List[Dict[str, Any]],
    escalation_handler: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    restart_guard: Optional[Callable[[str], bool]] = None,
) -> Dict[str, Any]:
    workers_state = get_workers_state()
    health_report = evaluate_runtime_health(runtime_state, workers_state, recent_events)
    restart_report = apply_worker_restart_policy(health_report, restart_guard=restart_guard)

    escalation = None
    if escalation_handler and health_report.get("status") in {"CRITICAL", "DEGRADED"}:
        escalation = escalation_handler(
            "runtime_supervision_alert",
            {
                "health_report": health_report,
                "restart_report": restart_report,
            },
        )

    return {
        "health_report": health_report,
        "restart_report": restart_report,
        "escalation": escalation,
        "workers_state": workers_state,
    }
