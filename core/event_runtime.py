from datetime import datetime
from typing import Any, Callable, Dict


def emit_runtime_continuation(
    publish_event: Callable[[Dict[str, Any]], Dict[str, Any]],
    job_id: str,
    execution_status: str,
    verification: Dict[str, Any],
) -> Dict[str, Any]:
    return publish_event(
        {
            "event_type": "runtime_continuation",
            "payload": {
                "job_id": job_id,
                "execution_status": execution_status,
                "verification": {
                    "authority_valid": verification.get("authority_valid"),
                    "invariants_valid": verification.get("invariants_valid"),
                    "chain_valid": verification.get("chain_valid"),
                    "truth_status": verification.get("truth_status"),
                },
                "timestamp": datetime.utcnow().isoformat() + "Z",
            },
        }
    )
