import hashlib
import json
from typing import Any, Dict, List


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def derive_tasks_from_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    content = dict((spec or {}).get("content", {}) or {})
    scope = str((spec or {}).get("scope", "default"))
    spec_id = str((spec or {}).get("spec_id", ""))

    allowed_actions = content.get("autonomy_allowed_actions", [])
    if not isinstance(allowed_actions, list):
        allowed_actions = []

    tasks: List[Dict[str, Any]] = []
    max_retries_default = int(content.get("max_retries", 2))
    governance_requirements = list(content.get("governance_requirements", ["approval_required"]))
    verification_checkpoints = list(
        content.get(
            "verification_checkpoints",
            ["authority_validation", "scope_validation", "invariant_validation", "replay_consistency"],
        )
    )
    execution_constraints = {
        "max_retries": max(0, min(max_retries_default, 5)),
        "requires_approval": True,
        "bounded": True,
        "scope": scope,
    }

    for idx, action in enumerate(allowed_actions):
        action_name = str(action).strip()
        if not action_name:
            continue
        tasks.append(
            {
                "task_id": f"{spec_id}-task-{idx + 1}",
                "action": action_name,
                "constraints": dict(execution_constraints),
                "governance_requirements": list(governance_requirements),
                "verification_checkpoints": list(verification_checkpoints),
            }
        )

    derivation_payload = {
        "spec_id": spec_id,
        "scope": scope,
        "tasks": tasks,
        "constraints": execution_constraints,
        "governance_requirements": governance_requirements,
        "verification_checkpoints": verification_checkpoints,
    }
    return {
        **derivation_payload,
        "derivation_hash": _stable_hash(derivation_payload),
    }
