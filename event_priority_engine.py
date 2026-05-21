from typing import Any, Dict


PRIORITY_CRITICAL = 4
PRIORITY_HIGH = 3
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 1


def prioritize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event_type = str(event.get("event_type", "")).strip().lower()
    payload = event.get("payload", {})
    payload_text = str(payload).lower()

    critical_markers = (
        "merge_conflict",
        "conflict",
        "runtime_crash",
        "runtime_exception",
        "policy_violation",
    )
    high_markers = (
        "tests_failed",
        "build_failed",
        "approval_blocked",
        "blocked",
    )
    medium_markers = (
        "workflow_continuation",
        "review_patch",
        "patch",
    )

    priority = PRIORITY_LOW
    priority_label = "LOW"

    if any(marker in event_type or marker in payload_text for marker in critical_markers):
        priority = PRIORITY_CRITICAL
        priority_label = "CRITICAL"
    elif any(marker in event_type or marker in payload_text for marker in high_markers):
        priority = PRIORITY_HIGH
        priority_label = "HIGH"
    elif any(marker in event_type or marker in payload_text for marker in medium_markers):
        priority = PRIORITY_MEDIUM
        priority_label = "MEDIUM"

    return {
        "priority": priority,
        "priority_label": priority_label,
        "event": event,
    }
