from typing import Any, Dict


MAX_RECOVERY_RETRIES = 3


def recover_from_failed_transition(session: Dict[str, Any], failure_reason: str) -> Dict[str, Any]:
    retry_count = int(session.get("retry_count", 0))

    if retry_count >= MAX_RECOVERY_RETRIES:
        return {
            "strategy": "abort_session",
            "status": "ABORTED",
            "requires_governance": False,
            "retry_count_increment": 0,
            "difference_reason": failure_reason,
            "message": "maximum_retries_reached",
        }

    if retry_count == 0:
        return {
            "strategy": "wait_and_retry",
            "status": "RECOVERY_PENDING",
            "requires_governance": False,
            "retry_count_increment": 1,
            "suggested_wait_ms": 1200,
            "difference_reason": failure_reason,
            "message": "waiting_before_reobserve",
        }

    if retry_count == 1:
        return {
            "strategy": "refresh_screen",
            "status": "RECOVERY_PENDING",
            "requires_governance": False,
            "retry_count_increment": 1,
            "difference_reason": failure_reason,
            "message": "refresh_and_reobserve",
        }

    if retry_count == 2:
        return {
            "strategy": "retry_click",
            "status": "AWAITING_RETRY_APPROVAL",
            "requires_governance": True,
            "retry_count_increment": 1,
            "difference_reason": failure_reason,
            "message": "retry_requires_governed_approval",
        }

    return {
        "strategy": "escalate_governance",
        "status": "ESCALATED",
        "requires_governance": True,
        "retry_count_increment": 0,
        "difference_reason": failure_reason,
        "message": "escalate_to_governance_layer",
    }
