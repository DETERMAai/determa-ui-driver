from typing import Any, Dict, List


def _as_set(content: Dict[str, Any], key: str) -> set:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def validate_semantic_admissibility(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> Dict[str, Any]:
    old_content = dict((old_spec or {}).get("content", {}) or {})
    new_content = dict((new_spec or {}).get("content", {}) or {})

    violations: List[Dict[str, Any]] = []

    old_autonomy = _as_set(old_content, "autonomy_allowed_actions")
    new_autonomy = _as_set(new_content, "autonomy_allowed_actions")
    added_autonomy = sorted(list(new_autonomy - old_autonomy))
    if added_autonomy:
        violations.append(
            {
                "type": "autonomy_expansion",
                "details": {"added_actions": added_autonomy},
                "severity": "high",
            }
        )

    old_replay = _as_set(old_content, "replay_guarantees")
    new_replay = _as_set(new_content, "replay_guarantees")
    removed_replay = sorted(list(old_replay - new_replay))
    if removed_replay:
        violations.append(
            {
                "type": "replay_guarantee_weakening",
                "details": {"removed_guarantees": removed_replay},
                "severity": "high",
            }
        )

    old_scopes = _as_set(old_content, "authority_scopes")
    new_scopes = _as_set(new_content, "authority_scopes")
    widened_scopes = sorted(list(new_scopes - old_scopes))
    if widened_scopes:
        violations.append(
            {
                "type": "authority_scope_widening",
                "details": {"added_scopes": widened_scopes},
                "severity": "high",
            }
        )

    old_invariants = _as_set(old_content, "invariants")
    new_invariants = _as_set(new_content, "invariants")
    removed_invariants = sorted(list(old_invariants - new_invariants))
    if removed_invariants:
        violations.append(
            {
                "type": "invariant_removal",
                "details": {"removed_invariants": removed_invariants},
                "severity": "medium",
            }
        )

    governance_bypass = bool(new_content.get("allow_governance_bypass", False)) or bool(
        new_content.get("bypass_governance", False)
    )
    if governance_bypass:
        violations.append(
            {
                "type": "governance_bypass_attempt",
                "details": {"flag": True},
                "severity": "critical",
            }
        )

    if any(item.get("severity") == "critical" for item in violations):
        semantic_risk = "CRITICAL"
    elif any(item.get("severity") == "high" for item in violations):
        semantic_risk = "HIGH"
    elif violations:
        semantic_risk = "MEDIUM"
    else:
        semantic_risk = "LOW"

    return {
        "admissible": len(violations) == 0,
        "violations": violations,
        "semantic_risk": semantic_risk,
    }
