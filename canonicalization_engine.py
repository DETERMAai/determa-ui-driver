from typing import Any, Callable, Dict, Optional

from semantic_admissibility_engine import validate_semantic_admissibility
from spec_registry import (
    SPEC_STATUS_CANONICAL,
    get_canonical_specs,
    get_spec,
    mark_spec_canonical,
    supersede_spec,
)


def canonicalize_spec(
    spec_id: str,
    emit_event_fn: Optional[Callable[[str, str, Dict[str, Any]], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    target = get_spec(spec_id)
    if target is None:
        return {"ok": False, "reason": "spec_not_found", "spec_id": spec_id}

    scope = str(target.get("scope", "default"))
    existing_canonical = get_canonical_specs(scope=scope)
    current_canonical = existing_canonical[-1] if existing_canonical else None

    admissibility = {"admissible": True, "violations": [], "semantic_risk": "LOW"}
    if current_canonical is not None and str(current_canonical.get("spec_id")) != str(spec_id):
        admissibility = validate_semantic_admissibility(current_canonical, target)
        if not admissibility.get("admissible", False):
            return {
                "ok": False,
                "reason": "semantic_inadmissible",
                "spec_id": spec_id,
                "admissibility": admissibility,
            }

    for canonical_spec in existing_canonical:
        canonical_spec_id = str(canonical_spec.get("spec_id"))
        if canonical_spec_id == str(spec_id):
            continue
        supersede_spec(canonical_spec_id, superseded_by=spec_id, reason="new_canonical_in_scope")
        if emit_event_fn:
            emit_event_fn(
                "SPEC_SUPERSEDED",
                canonical_spec_id,
                {
                    "scope": scope,
                    "superseded_by": spec_id,
                },
            )

    mark_result = mark_spec_canonical(str(spec_id), reason="canonicalized_in_scope")
    if not mark_result.get("ok", False):
        return {
            "ok": False,
            "reason": "canonicalization_update_failed",
            "spec_id": spec_id,
        }
    target = mark_result.get("spec", target)

    if emit_event_fn:
        emit_event_fn(
            "SPEC_CANONICALIZED",
            str(spec_id),
            {"scope": scope, "admissibility": admissibility},
        )

    return {
        "ok": True,
        "spec_id": spec_id,
        "scope": scope,
        "status": SPEC_STATUS_CANONICAL,
        "admissibility": admissibility,
    }
