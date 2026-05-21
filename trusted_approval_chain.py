from typing import Any, Callable, Dict, List, Optional


def _latest_event(events: List[Dict[str, Any]], event_type: str) -> Optional[Dict[str, Any]]:
    filtered = [event for event in events if str(event.get("event_type", "")) == event_type]
    if not filtered:
        return None
    return filtered[-1]


def build_trusted_approval_chain(
    job_id: str,
    pending_jobs: Dict[str, Dict[str, Any]],
    approved_jobs: set,
    audit_log: List[Dict[str, Any]],
    authority_tokens: Dict[str, Dict[str, Any]],
    execution_proofs: Dict[str, Any],
    verification_result_provider: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    job_events = [event for event in audit_log if str(event.get("job_id", "")) == str(job_id)]
    approval_event = _latest_event(job_events, "APPROVED")
    executed_event = _latest_event(job_events, "EXECUTED")
    failed_event = _latest_event(job_events, "EXECUTION_FAILED")
    blocked_event = _latest_event(job_events, "BLOCKED")

    verification_result = verification_result_provider(str(job_id))
    token = authority_tokens.get(str(job_id))

    return {
        "job_id": str(job_id),
        "human_approval": {
            "approved": str(job_id) in approved_jobs,
            "approval_event": approval_event,
        },
        "governance_validation": verification_result.get("governance_validation", {}),
        "authority_token": token,
        "execution_proof": execution_proofs.get(str(job_id)),
        "verification_result": verification_result,
        "execution_outcome": {
            "executed_event": executed_event,
            "execution_failed_event": failed_event,
            "blocked_event": blocked_event,
        },
        "job_present": str(job_id) in pending_jobs,
    }
