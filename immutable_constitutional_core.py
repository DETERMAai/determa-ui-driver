from typing import Any, Dict, List, Set

IMMUTABLE_CONSTITUTIONAL_CORE: Dict[str, Any] = {
    "name": "DETERMA Immutable Constitutional Core",
    "version": "1.0",
    "immutable_principles": [
        {
            "id": "IC-001",
            "name": "replayability",
            "description": "Replay guarantees must not be weakened.",
        },
        {
            "id": "IC-002",
            "name": "bounded_autonomy",
            "description": "Autonomy boundaries may not widen autonomously.",
        },
        {
            "id": "IC-003",
            "name": "human_override_authority",
            "description": "Human override and approval authority must remain intact.",
        },
        {
            "id": "IC-004",
            "name": "append_only_audit_history",
            "description": "Audit trail semantics must remain append-only and auditable.",
        },
    ],
}


def _as_set(content: Dict[str, Any], key: str) -> Set[str]:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def validate_immutable_core_mutation(old_content: Dict[str, Any], new_content: Dict[str, Any]) -> Dict[str, Any]:
    old_content = dict(old_content or {})
    new_content = dict(new_content or {})

    violations: List[Dict[str, Any]] = []

    old_replay = _as_set(old_content, "replay_guarantees")
    new_replay = _as_set(new_content, "replay_guarantees")
    removed_replay = sorted(list(old_replay - new_replay))
    if removed_replay:
        violations.append(
            {
                "type": "immutable_replayability_weakened",
                "severity": "critical",
                "removed_replay_guarantees": removed_replay,
            }
        )

    old_rules = _as_set(old_content, "governance_requirements")
    new_rules = _as_set(new_content, "governance_requirements")
    required_override_rules = {"approval_required", "authority_validation"}
    missing_override_rules = sorted(list(required_override_rules - new_rules))
    if missing_override_rules:
        violations.append(
            {
                "type": "human_override_authority_weakened",
                "severity": "critical",
                "missing_governance_requirements": missing_override_rules,
            }
        )

    if bool(new_content.get("allow_governance_bypass", False)) or bool(new_content.get("bypass_governance", False)):
        violations.append(
            {
                "type": "authority_bypass_attempt",
                "severity": "critical",
            }
        )

    old_audit_mode = str(old_content.get("audit_mode") or "append_only").strip().lower()
    new_audit_mode = str(new_content.get("audit_mode") or old_audit_mode or "append_only").strip().lower()
    if old_audit_mode == "append_only" and new_audit_mode != "append_only":
        violations.append(
            {
                "type": "append_only_audit_history_weakened",
                "severity": "critical",
                "from": old_audit_mode,
                "to": new_audit_mode,
            }
        )

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "immutable_core": dict(IMMUTABLE_CONSTITUTIONAL_CORE),
    }
