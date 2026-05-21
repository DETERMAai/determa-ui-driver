import hashlib
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


DEFAULT_TOKEN_TTL_SECONDS = 900
_SIGNING_SECRET = os.environ.get("DETERMA_AUTHORITY_SECRET", "determa-authority-secret")


def _utc_now() -> datetime:
    return datetime.utcnow()


def _iso(dt: datetime) -> str:
    return dt.isoformat() + "Z"


def _compute_authority_hash(
    action_id: str,
    signed_by: str,
    scope: str,
    issued_at: str,
    expires_at: str,
) -> str:
    payload = f"{action_id}|{signed_by}|{scope}|{issued_at}|{expires_at}|{_SIGNING_SECRET}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_authority_token(
    action: Dict[str, Any],
    approval_context: Dict[str, Any],
    ttl_seconds: int = DEFAULT_TOKEN_TTL_SECONDS,
) -> Dict[str, Any]:
    action_id = str(
        approval_context.get("action_id")
        or approval_context.get("job_id")
        or action.get("job_id")
        or hashlib.sha256(str(action).encode("utf-8")).hexdigest()[:16]
    )
    signed_by = str(approval_context.get("signed_by", "human_operator"))
    scope = str(approval_context.get("scope", action.get("action") or "unknown"))
    issued_at_dt = _utc_now()
    expires_at_dt = issued_at_dt + timedelta(seconds=max(30, int(ttl_seconds)))
    issued_at = _iso(issued_at_dt)
    expires_at = _iso(expires_at_dt)
    authority_hash = _compute_authority_hash(action_id, signed_by, scope, issued_at, expires_at)

    return {
        "action_id": action_id,
        "signed_by": signed_by,
        "scope": scope,
        "authority_hash": authority_hash,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }


def validate_authority_token(
    token: Optional[Dict[str, Any]],
    expected_action_id: Optional[str] = None,
    expected_scope: Optional[str] = None,
) -> Dict[str, Any]:
    if not isinstance(token, dict):
        return {"valid": False, "reason": "missing_token"}

    required_fields = ("action_id", "signed_by", "scope", "authority_hash", "issued_at", "expires_at")
    for field in required_fields:
        if field not in token:
            return {"valid": False, "reason": f"missing_field:{field}"}

    action_id = str(token.get("action_id", ""))
    signed_by = str(token.get("signed_by", ""))
    scope = str(token.get("scope", ""))
    issued_at = str(token.get("issued_at", ""))
    expires_at = str(token.get("expires_at", ""))
    provided_hash = str(token.get("authority_hash", ""))

    try:
        expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", ""))
    except Exception:
        return {"valid": False, "reason": "invalid_expiry_format"}

    if _utc_now() > expires_at_dt:
        return {"valid": False, "reason": "token_expired"}

    computed_hash = _compute_authority_hash(action_id, signed_by, scope, issued_at, expires_at)
    if computed_hash != provided_hash:
        return {"valid": False, "reason": "invalid_signature"}

    if expected_action_id is not None and str(expected_action_id) != action_id:
        return {"valid": False, "reason": "action_id_mismatch"}

    if expected_scope is not None and str(expected_scope) != scope:
        return {"valid": False, "reason": "scope_mismatch"}

    return {"valid": True, "reason": "ok"}
