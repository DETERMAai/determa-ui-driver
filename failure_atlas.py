from datetime import datetime
from typing import Any, Dict, List


failure_modes: List[Dict[str, Any]] = []
_MAX_FAILURE_RECORDS = 1000


def record_failure_mode(
    failure_type: str,
    triggering_conditions: Dict[str, Any],
    affected_runtime_layer: str,
    recovery_result: str,
    human_intervention_required: bool,
) -> Dict[str, Any]:
    record = {
        "failure_type": str(failure_type or "unknown_failure"),
        "triggering_conditions": dict(triggering_conditions or {}),
        "affected_runtime_layer": str(affected_runtime_layer or "unknown_layer"),
        "recovery_result": str(recovery_result or "unknown"),
        "human_intervention_required": bool(human_intervention_required),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    failure_modes.append(record)
    if len(failure_modes) > _MAX_FAILURE_RECORDS:
        del failure_modes[0 : len(failure_modes) - _MAX_FAILURE_RECORDS]
    return record


def get_recent_failures(limit: int = 100) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit), _MAX_FAILURE_RECORDS))
    items = failure_modes[-safe_limit:]
    return {
        "failures": items,
        "count": len(items),
        "total_recorded": len(failure_modes),
    }
