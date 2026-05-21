import hashlib
import json
from typing import Any, Dict

from semantic_admissibility_engine import validate_semantic_admissibility
from spec_lineage_engine import build_spec_lineage
from spec_registry import SPEC_STATUS_CANONICAL, get_spec
from spec_task_derivation_engine import derive_tasks_from_spec


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bind_execution_to_spec(job_payload: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
    spec_id = str(spec.get("spec_id"))
    lineage = build_spec_lineage(spec_id)
    derivation = derive_tasks_from_spec(spec)
    bound_payload = dict(job_payload)
    bound_payload["canonical_spec_id"] = spec_id
    bound_payload["lineage_hash"] = lineage.get("lineage_hash")
    bound_payload["derivation_hash"] = derivation.get("derivation_hash")
    bound_payload["derivation_scope"] = spec.get("scope")
    return {
        "job_payload": bound_payload,
        "lineage": lineage,
        "derivation": derivation,
    }


def validate_execution_binding(job_payload: Dict[str, Any]) -> Dict[str, Any]:
    canonical_spec_id = str(job_payload.get("canonical_spec_id", ""))
    lineage_hash = str(job_payload.get("lineage_hash", ""))
    derivation_hash = str(job_payload.get("derivation_hash", ""))
    action_name = str(job_payload.get("semantic_action") or job_payload.get("action") or "").strip().lower()

    if not canonical_spec_id or not lineage_hash or not derivation_hash:
        return {"valid": False, "reason": "missing_spec_binding_fields"}

    spec = get_spec(canonical_spec_id)
    if spec is None:
        return {"valid": False, "reason": "spec_not_found"}
    if str(spec.get("status")) != SPEC_STATUS_CANONICAL:
        return {"valid": False, "reason": "spec_not_canonical"}
    if spec.get("superseded_by"):
        return {"valid": False, "reason": "spec_superseded"}

    lineage = build_spec_lineage(canonical_spec_id)
    if str(lineage.get("lineage_hash", "")) != lineage_hash:
        return {"valid": False, "reason": "lineage_invalid"}

    derivation = derive_tasks_from_spec(spec)
    if str(derivation.get("derivation_hash", "")) != derivation_hash:
        return {"valid": False, "reason": "derivation_hash_mismatch"}

    tasks = derivation.get("tasks", [])
    admissible_actions = {str(task.get("action", "")).strip().lower() for task in tasks}
    if action_name and action_name not in admissible_actions:
        return {
            "valid": False,
            "reason": "derivation_violates_admissibility",
            "admissible_actions": sorted(list(admissible_actions)),
        }

    parent_id = spec.get("derived_from")
    if parent_id:
        parent_spec = get_spec(str(parent_id))
        if parent_spec is not None:
            admissibility = validate_semantic_admissibility(parent_spec, spec)
            if not admissibility.get("admissible", False):
                return {
                    "valid": False,
                    "reason": "semantic_inadmissible_lineage",
                    "admissibility": admissibility,
                }

    return {
        "valid": True,
        "reason": "spec_binding_valid",
        "canonical_spec_id": canonical_spec_id,
        "lineage_hash": lineage_hash,
        "derivation_hash": derivation_hash,
    }
