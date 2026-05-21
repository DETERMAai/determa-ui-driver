from datetime import datetime
from typing import Any, Dict, List, Optional


SPEC_STATUS_DRAFT = "DRAFT"
SPEC_STATUS_UNDER_REVIEW = "UNDER_REVIEW"
SPEC_STATUS_CANONICAL = "CANONICAL"
SPEC_STATUS_SUPERSEDED = "SUPERSEDED"
SPEC_STATUS_REJECTED = "REJECTED"

_VALID_STATUSES = {
    SPEC_STATUS_DRAFT,
    SPEC_STATUS_UNDER_REVIEW,
    SPEC_STATUS_CANONICAL,
    SPEC_STATUS_SUPERSEDED,
    SPEC_STATUS_REJECTED,
}

spec_registry: Dict[str, Dict[str, Any]] = {}
spec_history: List[Dict[str, Any]] = []
_spec_counter = 0


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _next_spec_id() -> str:
    global _spec_counter
    _spec_counter += 1
    return f"spec-{_spec_counter}"


def _append_history(spec_id: str, action: str, data: Optional[Dict[str, Any]] = None):
    spec_history.append(
        {
            "timestamp": _utc_now_iso(),
            "spec_id": spec_id,
            "action": action,
            "data": dict(data or {}),
        }
    )
    if len(spec_history) > 5000:
        del spec_history[0 : len(spec_history) - 5000]


def register_spec(
    scope: str,
    content: Dict[str, Any],
    status: str = SPEC_STATUS_DRAFT,
    title: str = "",
    derived_from: Optional[str] = None,
    proposed_by: str = "operator",
    governance_approvals: Optional[List[str]] = None,
) -> Dict[str, Any]:
    normalized_status = str(status or SPEC_STATUS_DRAFT).upper()
    if normalized_status not in _VALID_STATUSES:
        normalized_status = SPEC_STATUS_DRAFT

    spec_id = _next_spec_id()
    now = _utc_now_iso()
    record = {
        "spec_id": spec_id,
        "title": str(title or ""),
        "scope": str(scope or "default"),
        "content": dict(content or {}),
        "status": normalized_status,
        "derived_from": str(derived_from) if derived_from else None,
        "superseded_by": None,
        "proposed_by": str(proposed_by or "operator"),
        "governance_approvals": list(governance_approvals or []),
        "created_at": now,
        "updated_at": now,
    }
    spec_registry[spec_id] = record
    _append_history(spec_id, "REGISTERED", {"status": normalized_status})
    return record


def get_spec(spec_id: str) -> Optional[Dict[str, Any]]:
    return spec_registry.get(str(spec_id))


def get_canonical_specs(scope: Optional[str] = None) -> List[Dict[str, Any]]:
    specs = [spec for spec in spec_registry.values() if spec.get("status") == SPEC_STATUS_CANONICAL]
    if scope is not None:
        specs = [spec for spec in specs if str(spec.get("scope")) == str(scope)]
    specs.sort(key=lambda item: str(item.get("updated_at", "")))
    return specs


def get_specs_history() -> List[Dict[str, Any]]:
    return list(spec_history)


def mark_spec_canonical(spec_id: str, reason: str = "") -> Dict[str, Any]:
    record = spec_registry.get(str(spec_id))
    if record is None:
        return {"ok": False, "reason": "spec_not_found", "spec_id": spec_id}
    record["status"] = SPEC_STATUS_CANONICAL
    record["updated_at"] = _utc_now_iso()
    _append_history(str(spec_id), "CANONICALIZED", {"reason": str(reason or "")})
    return {"ok": True, "spec": record}


def supersede_spec(spec_id: str, superseded_by: Optional[str] = None, reason: str = "") -> Dict[str, Any]:
    record = spec_registry.get(str(spec_id))
    if record is None:
        return {"ok": False, "reason": "spec_not_found", "spec_id": spec_id}
    record["status"] = SPEC_STATUS_SUPERSEDED
    record["superseded_by"] = str(superseded_by) if superseded_by else record.get("superseded_by")
    record["updated_at"] = _utc_now_iso()
    _append_history(
        str(spec_id),
        "SUPERSEDED",
        {
            "superseded_by": record.get("superseded_by"),
            "reason": str(reason or ""),
        },
    )
    return {"ok": True, "spec": record}


def reject_spec(spec_id: str, reason: str = "") -> Dict[str, Any]:
    record = spec_registry.get(str(spec_id))
    if record is None:
        return {"ok": False, "reason": "spec_not_found", "spec_id": spec_id}
    record["status"] = SPEC_STATUS_REJECTED
    record["updated_at"] = _utc_now_iso()
    _append_history(str(spec_id), "REJECTED", {"reason": str(reason or "")})
    return {"ok": True, "spec": record}
