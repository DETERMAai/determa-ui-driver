from datetime import datetime
from typing import Any, Dict


def _now() -> datetime:
    return datetime.utcnow()


def _now_iso() -> str:
    return _now().isoformat() + "Z"


def _to_dt(value: Any):
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except Exception:
        return None


def evaluate_temporal_authority_decay(
    authority_tokens: Dict[str, Dict[str, Any]],
    renewal_threshold_seconds: int = 300,
) -> Dict[str, Any]:
    now = _now()
    per_job: Dict[str, Dict[str, Any]] = {}
    expired = []
    renewal_required_for = []
    freshness_scores = []

    for job_id, token in (authority_tokens or {}).items():
        token_data = dict(token or {})
        issued_at = _to_dt(token_data.get("issued_at"))
        expires_at = _to_dt(token_data.get("expires_at"))

        if issued_at is None or expires_at is None or expires_at <= issued_at:
            entry = {
                "status": "invalid",
                "freshness_score": 0.0,
                "expires_in_seconds": 0,
                "renewal_required": True,
                "reason": "invalid_token_timestamps",
            }
            per_job[str(job_id)] = entry
            renewal_required_for.append(str(job_id))
            freshness_scores.append(0.0)
            continue

        ttl_seconds = max(1, int((expires_at - issued_at).total_seconds()))
        remaining_seconds = int((expires_at - now).total_seconds())
        expired_now = remaining_seconds <= 0

        if expired_now:
            freshness_score = 0.0
            status = "expired"
            remaining_seconds = 0
            expired.append(str(job_id))
            renewal_required = True
            reason = "authority_expired"
        else:
            freshness_score = max(0.0, min(1.0, remaining_seconds / float(ttl_seconds)))
            renewal_required = remaining_seconds <= max(30, int(renewal_threshold_seconds))
            status = "fresh" if freshness_score >= 0.5 else "stale"
            reason = "near_expiry" if renewal_required else "ok"
            if renewal_required:
                renewal_required_for.append(str(job_id))

        per_job[str(job_id)] = {
            "status": status,
            "freshness_score": round(freshness_score, 4),
            "expires_in_seconds": int(remaining_seconds),
            "renewal_required": renewal_required,
            "reason": reason,
        }
        freshness_scores.append(freshness_score)

    average_freshness = sum(freshness_scores) / len(freshness_scores) if freshness_scores else 1.0
    overall_status = "HEALTHY"
    if expired:
        overall_status = "EXPIRED"
    elif renewal_required_for:
        overall_status = "STALE"

    return {
        "status": "ok",
        "evaluated_at": _now_iso(),
        "authority_status": overall_status,
        "authority_freshness_score": round(average_freshness, 4),
        "expired_authorities": sorted(expired),
        "renewal_required": bool(renewal_required_for),
        "renewal_required_for": sorted(set(renewal_required_for)),
        "authorities": per_job,
    }
