from typing import Any, Dict, List, Set

from constitutional_principles import CONSTITUTIONAL_PRINCIPLES
from spec_registry import get_canonical_specs


MIN_REQUIRED_INVARIANTS = {
    "execution_safety_invariant",
    "causality_invariant",
    "integrity_invariant",
    "authority_invariant",
}
MIN_REQUIRED_GOVERNANCE_RULES = {
    "approval_required",
    "authority_validation",
    "invariant_validation",
}


def _as_set(content: Dict[str, Any], key: str) -> Set[str]:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def evaluate_governance_minimality() -> Dict[str, Any]:
    canonical_specs = get_canonical_specs()

    observed_invariants: Set[str] = set()
    observed_governance_rules: Set[str] = set()

    for spec in canonical_specs:
        content = dict(spec.get("content", {}) or {})
        observed_invariants.update(_as_set(content, "invariants"))
        observed_governance_rules.update(_as_set(content, "governance_requirements"))

    missing_required_invariants = sorted(list(MIN_REQUIRED_INVARIANTS - observed_invariants))
    missing_required_rules = sorted(list(MIN_REQUIRED_GOVERNANCE_RULES - observed_governance_rules))

    extra_invariants = sorted(list(observed_invariants - MIN_REQUIRED_INVARIANTS))
    extra_rules = sorted(list(observed_governance_rules - MIN_REQUIRED_GOVERNANCE_RULES))

    unnecessary_constitutional_expansion = []
    if extra_invariants:
        unnecessary_constitutional_expansion.append(
            {
                "type": "extra_invariants",
                "count": len(extra_invariants),
                "items": extra_invariants,
            }
        )
    if extra_rules:
        unnecessary_constitutional_expansion.append(
            {
                "type": "extra_governance_rules",
                "count": len(extra_rules),
                "items": extra_rules,
            }
        )

    minimality_ok = len(missing_required_invariants) == 0 and len(missing_required_rules) == 0

    return {
        "status": "ok",
        "constitution": {
            "name": CONSTITUTIONAL_PRINCIPLES.get("name"),
            "version": CONSTITUTIONAL_PRINCIPLES.get("version"),
        },
        "minimal_required_invariants": sorted(list(MIN_REQUIRED_INVARIANTS)),
        "minimal_required_governance_rules": sorted(list(MIN_REQUIRED_GOVERNANCE_RULES)),
        "observed_invariants": sorted(list(observed_invariants)),
        "observed_governance_rules": sorted(list(observed_governance_rules)),
        "missing_required_invariants": missing_required_invariants,
        "missing_required_governance_rules": missing_required_rules,
        "unnecessary_constitutional_expansion": unnecessary_constitutional_expansion,
        "minimality_valid": minimality_ok,
    }
