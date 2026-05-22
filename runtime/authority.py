from typing import Any, Dict

from authority_token_service import validate_authority_token
from execution_sandbox import validate_sandbox_execution
from permission_scope_engine import validate_scope


def authority_gate(
    job_id: str,
    action_name: str,
    req_payload: Dict[str, Any],
    token: Dict[str, Any],
    expected_scope: str,
    runtime_context: Dict[str, Any],
) -> Dict[str, Any]:
    token_validation = validate_authority_token(
        token,
        expected_action_id=job_id,
        expected_scope=expected_scope,
    )
    if not token_validation.get("valid", False):
        return {
            "allowed": False,
            "reason": "authority_token_invalid",
            "token_validation": token_validation,
            "scope_validation": None,
            "sandbox_validation": None,
        }

    scope_validation = validate_scope(action_name, runtime_context)
    if not scope_validation.get("allowed", False):
        return {
            "allowed": False,
            "reason": "scope_validation_failed",
            "token_validation": token_validation,
            "scope_validation": scope_validation,
            "sandbox_validation": None,
        }

    sandbox_validation = validate_sandbox_execution(
        str(scope_validation.get("required_scope", action_name)),
        req_payload,
        runtime_context,
    )
    if not sandbox_validation.get("allowed", False):
        return {
            "allowed": False,
            "reason": "sandbox_validation_failed",
            "token_validation": token_validation,
            "scope_validation": scope_validation,
            "sandbox_validation": sandbox_validation,
        }

    return {
        "allowed": True,
        "reason": "authority_passed",
        "token_validation": token_validation,
        "scope_validation": scope_validation,
        "sandbox_validation": sandbox_validation,
        "authority_token": token,
    }
