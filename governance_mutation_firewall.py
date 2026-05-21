from typing import Any, Dict, List, Set

from immutable_constitutional_core import validate_immutable_core_mutation
from semantic_admissibility_engine import validate_semantic_admissibility


def _as_set(content: Dict[str, Any], key: str) -> Set[str]:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def validate_governance_mutation(old_spec: Dict[str, Any], new_spec: Dict[str, Any], mutation_context: Dict[str, Any] = None):
    old_spec = dict(old_spec or {})
    new_spec = dict(new_spec or {})
    mutation_context = dict(mutation_context or {})

    old_content = dict(old_spec.get("content", {}) or {})
    new_content = dict(new_spec.get("content", {}) or {})

    violations: List[Dict[str, Any]] = []

    immutable_core = validate_immutable_core_mutation(old_content, new_content)
    if not immutable_core.get("valid", False):
        violations.extend(list(immutable_core.get("violations", [])))

    if old_spec:
        admissibility = validate_semantic_admissibility(old_spec, new_spec)
        if not admissibility.get("admissible", False):
            for item in admissibility.get("violations", []):
                violations.append(
                    {
                        "type": "semantic_admissibility_block",
                        "severity": item.get("severity", "high"),
                        "details": item,
                    }
                )
    else:
        admissibility = {"admissible": True, "violations": [], "semantic_risk": "LOW"}

    old_rules = _as_set(old_content, "governance_requirements")
    new_rules = _as_set(new_content, "governance_requirements")
    removed_rules = sorted(list(old_rules - new_rules))
    if removed_rules:
        violations.append(
            {
                "type": "auditability_degradation",
                "severity": "high",
                "removed_governance_requirements": removed_rules,
            }
        )

    old_invariants = _as_set(old_content, "invariants")
    new_invariants = _as_set(new_content, "invariants")
    if old_invariants and not old_invariants.issubset(new_invariants):
        removed_invariants = sorted(list(old_invariants - new_invariants))
        violations.append(
            {
                "type": "constitutional_weakening",
                "severity": "critical",
                "removed_invariants": removed_invariants,
            }
        )

    old_autonomy = _as_set(old_content, "autonomy_allowed_actions")
    new_autonomy = _as_set(new_content, "autonomy_allowed_actions")
    widens_autonomy = bool(new_autonomy - old_autonomy)

    risk = "LOW"
    if any(v.get("severity") == "critical" for v in violations):
        risk = "CRITICAL"
    elif any(v.get("severity") == "high" for v in violations):
        risk = "HIGH"
    elif any(v.get("severity") == "medium" for v in violations):
        risk = "MEDIUM"

    return {
        "allowed": len([v for v in violations if v.get("severity") in {"critical", "high"}]) == 0,
        "blocked": len([v for v in violations if v.get("severity") in {"critical", "high"}]) > 0,
        "risk": risk,
        "violations": violations,
        "flags": {
            "widens_autonomy_boundary": widens_autonomy,
        },
        "admissibility": admissibility,
        "immutable_core": immutable_core,
        "mutation_context": mutation_context,
    }
