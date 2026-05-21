from datetime import datetime
from typing import Any, Dict, List


escalation_events: List[Dict[str, Any]] = []


def escalate_to_human(reason: str, context: Dict[str, Any]) -> Dict[str, Any]:
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reason": str(reason or "unspecified_reason"),
        "context": context,
        "status": "ESCALATED_TO_HUMAN",
    }
    escalation_events.append(event)
    if len(escalation_events) > 500:
        del escalation_events[0 : len(escalation_events) - 500]
    return event
