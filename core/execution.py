from typing import Any, Callable, Dict


def run_canonical_execution_pipeline(
    job_id: str,
    req_payload: Dict[str, Any],
    governance_result: Dict[str, Any],
    security_result: Dict[str, Any],
    execute_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    emit_event_fn: Callable[[str, str, Dict[str, Any]], Dict[str, Any]],
    publish_event_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    verify_fn: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    publish_event_fn(
        {
            "event_type": "canonical_execution_event_received",
            "payload": {"job_id": job_id},
        }
    )

    if not governance_result.get("allowed", False):
        emit_event_fn("BLOCKED", job_id, {"reason": governance_result.get("reason", "governance_blocked")})
        publish_event_fn(
            {
                "event_type": "canonical_execution_blocked",
                "payload": {"job_id": job_id, "reason": governance_result.get("reason", "governance_blocked")},
            }
        )
        verification = verify_fn(job_id)
        return {
            "status": "blocked",
            "reason": governance_result.get("reason", "governance_blocked"),
            "security": security_result,
            "verification": verification,
        }

    if not security_result.get("allowed", False):
        emit_event_fn(
            "BLOCKED",
            job_id,
            {"reason": "security_validation_failed", "details": security_result},
        )
        publish_event_fn(
            {
                "event_type": "canonical_execution_blocked",
                "payload": {"job_id": job_id, "reason": "security_validation_failed", "details": security_result},
            }
        )
        verification = verify_fn(job_id)
        return {
            "status": "blocked",
            "reason": "security_validation_failed",
            "security": security_result,
            "verification": verification,
        }

    emit_event_fn(
        "EXECUTION_STARTED",
        job_id,
        {
            "request": req_payload,
            "context_ref": job_id,
            "security": {
                "scope": security_result.get("scope_validation", {}).get("required_scope"),
                "authority_hash": security_result.get("authority_token", {}).get("authority_hash"),
            },
        },
    )

    try:
        execution_result = execute_fn(req_payload)
    except Exception as exc:
        execution_result = {
            "status": "failed",
            "before": None,
            "after": None,
            "execution_time_ms": 0,
            "error": str(exc),
        }
    if execution_result.get("status") == "success":
        emit_event_fn(
            "EXECUTED",
            job_id,
            {
                "execution_time_ms": execution_result.get("execution_time_ms"),
                "error": execution_result.get("error"),
                "context_ref": job_id,
            },
        )
    else:
        emit_event_fn(
            "EXECUTION_FAILED",
            job_id,
            {
                "execution_time_ms": execution_result.get("execution_time_ms"),
                "error": execution_result.get("error"),
                "context_ref": job_id,
            },
        )

    verification = verify_fn(job_id)
    publish_event_fn(
        {
            "event_type": "canonical_execution_completed",
            "payload": {
                "job_id": job_id,
                "status": execution_result.get("status", "failed"),
                "verification": verification,
            },
        }
    )

    return {
        "status": execution_result.get("status", "failed"),
        "result": execution_result,
        "security": security_result,
        "verification": verification,
    }
