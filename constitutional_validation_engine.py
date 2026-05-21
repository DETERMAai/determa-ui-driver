from typing import Any, Dict, List

from constitutional_lineage_guard import validate_constitutional_lineage
from constitutional_principles import CONSTITUTIONAL_PRINCIPLES
from semantic_admissibility_engine import validate_semantic_admissibility
from spec_registry import get_canonical_specs, get_spec, spec_registry


def _as_set(content: Dict[str, Any], key: str) -> set:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def _constitution_invariant_checks(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    content = dict(spec.get("content", {}) or {})

    if bool(content.get("allow_governance_bypass", False)) or bool(content.get("bypass_governance", False)):
        violations.append(
            {
                "type": "governance_bypass_forbidden",
                "severity": "critical",
                "message": "Spec attempts governance bypass, violating constitutional invariants.",
            }
        )

    invariants = _as_set(content, "invariants")
    required_invariants = {
        "execution_safety_invariant",
        "causality_invariant",
        "integrity_invariant",
        "authority_invariant",
    }
    missing = sorted(list(required_invariants - invariants))
    if missing:
        violations.append(
            {
                "type": "constitutional_invariant_missing",
                "severity": "high",
                "message": "Core invariants missing from spec content.",
                "missing_invariants": missing,
            }
        )

    return violations


def _semantic_duplication(spec: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[str]:
    target_content = dict(spec.get("content", {}) or {})
    duplicates: List[str] = []
    for item in candidates:
        if str(item.get("spec_id")) == str(spec.get("spec_id")):
            continue
        if dict(item.get("content", {}) or {}) == target_content:
            duplicates.append(str(item.get("spec_id")))
    return duplicates


def validate_constitutional_spec(spec_id: str) -> Dict[str, Any]:
    spec = get_spec(spec_id)
    if spec is None:
        return {
            "spec_id": spec_id,
            "valid": False,
            "status": "not_found",
            "violations": [
                {
                    "type": "spec_not_found",
                    "severity": "critical",
                    "message": "Specification does not exist.",
                }
            ],
            "semantic_risk": "CRITICAL",
        }

    violations: List[Dict[str, Any]] = []
    violations.extend(_constitution_invariant_checks(spec))

    scope = str(spec.get("scope", "default"))
    canonical_in_scope = get_canonical_specs(scope=scope)
    current_canonical = canonical_in_scope[-1] if canonical_in_scope else None

    admissibility = {
        "admissible": True,
        "violations": [],
        "semantic_risk": "LOW",
    }
    if current_canonical is not None and str(current_canonical.get("spec_id")) != str(spec_id):
        admissibility = validate_semantic_admissibility(current_canonical, spec)
        if not admissibility.get("admissible", False):
            violations.append(
                {
                    "type": "semantic_admissibility_failed",
                    "severity": "high",
                    "details": admissibility,
                }
            )

    lineage_validation = validate_constitutional_lineage(spec_id)
    if not lineage_validation.get("valid", False):
        violations.append(
            {
                "type": "lineage_guard_failed",
                "severity": "high" if lineage_validation.get("reason") == "lineage_depth_exceeded" else "critical",
                "details": lineage_validation,
            }
        )

    all_specs = list(spec_registry.values())
    semantic_duplicates = _semantic_duplication(spec, all_specs)
    if semantic_duplicates:
        violations.append(
            {
                "type": "semantic_duplication_detected",
                "severity": "medium",
                "duplicates": semantic_duplicates,
            }
        )

    if any(v.get("severity") == "critical" for v in violations):
        semantic_risk = "CRITICAL"
    elif any(v.get("severity") == "high" for v in violations):
        semantic_risk = "HIGH"
    elif any(v.get("severity") == "medium" for v in violations):
        semantic_risk = "MEDIUM"
    else:
        semantic_risk = "LOW"

    return {
        "spec_id": str(spec_id),
        "valid": len([v for v in violations if v.get("severity") in {"critical", "high"}]) == 0,
        "status": "ok",
        "constitutional_principles": {
            "name": CONSTITUTIONAL_PRINCIPLES.get("name"),
            "version": CONSTITUTIONAL_PRINCIPLES.get("version"),
            "constitutional_invariants": CONSTITUTIONAL_PRINCIPLES.get("constitutional_invariants", []),
        },
        "admissibility": admissibility,
        "lineage_validation": lineage_validation,
        "violations": violations,
        "semantic_risk": semantic_risk,
    }
