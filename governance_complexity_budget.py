from itertools import combinations
from typing import Any, Dict, List, Set

from constitutional_lineage_guard import MAX_LINEAGE_DEPTH
from spec_registry import get_canonical_specs, spec_registry


COMPLEXITY_BUDGET = {
    "max_lineage_depth": MAX_LINEAGE_DEPTH,
    "max_governance_rules": 25,
    "max_canonical_scopes": 8,
    "max_invariant_overlap": 0.7,
}


def _as_set(content: Dict[str, Any], key: str) -> Set[str]:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def _lineage_depth(spec_id: str) -> int:
    depth = 0
    seen = set()
    node = spec_registry.get(str(spec_id))
    while node is not None:
        node_id = str(node.get("spec_id"))
        if node_id in seen:
            depth += 1
            break
        seen.add(node_id)
        depth += 1
        parent_id = node.get("derived_from")
        node = spec_registry.get(str(parent_id)) if parent_id else None
    return depth


def evaluate_governance_complexity_budget() -> Dict[str, Any]:
    specs = list(spec_registry.values())
    canonical_specs = get_canonical_specs()

    max_depth = 0
    for spec in specs:
        max_depth = max(max_depth, _lineage_depth(str(spec.get("spec_id"))))

    governance_rules: Set[str] = set()
    invariant_sets: Dict[str, Set[str]] = {}

    for spec in canonical_specs:
        spec_id = str(spec.get("spec_id"))
        content = dict(spec.get("content", {}) or {})
        governance_rules.update(_as_set(content, "governance_requirements"))
        invariant_sets[spec_id] = _as_set(content, "invariants")

    scopes = {str(spec.get("scope", "default")) for spec in canonical_specs}

    overlap_ratios: List[float] = []
    for left_id, right_id in combinations(sorted(invariant_sets.keys()), 2):
        left = invariant_sets[left_id]
        right = invariant_sets[right_id]
        denom = max(1, min(len(left), len(right)))
        overlap_ratios.append(len(left.intersection(right)) / float(denom))
    max_overlap = max(overlap_ratios) if overlap_ratios else 0.0

    breaches: List[Dict[str, Any]] = []
    if max_depth > COMPLEXITY_BUDGET["max_lineage_depth"]:
        breaches.append(
            {
                "dimension": "lineage_depth",
                "value": max_depth,
                "limit": COMPLEXITY_BUDGET["max_lineage_depth"],
                "severity": "high",
            }
        )
    if len(governance_rules) > COMPLEXITY_BUDGET["max_governance_rules"]:
        breaches.append(
            {
                "dimension": "governance_rules",
                "value": len(governance_rules),
                "limit": COMPLEXITY_BUDGET["max_governance_rules"],
                "severity": "medium",
            }
        )
    if len(scopes) > COMPLEXITY_BUDGET["max_canonical_scopes"]:
        breaches.append(
            {
                "dimension": "canonical_scopes",
                "value": len(scopes),
                "limit": COMPLEXITY_BUDGET["max_canonical_scopes"],
                "severity": "high",
            }
        )
    if max_overlap > COMPLEXITY_BUDGET["max_invariant_overlap"]:
        breaches.append(
            {
                "dimension": "invariant_overlap",
                "value": round(max_overlap, 4),
                "limit": COMPLEXITY_BUDGET["max_invariant_overlap"],
                "severity": "medium",
            }
        )

    freeze_recommendation = len([b for b in breaches if b.get("severity") == "high"]) > 0

    return {
        "status": "ok",
        "budget": dict(COMPLEXITY_BUDGET),
        "usage": {
            "max_lineage_depth": max_depth,
            "governance_rules": len(governance_rules),
            "canonical_scopes": len(scopes),
            "max_invariant_overlap": round(max_overlap, 4),
        },
        "breaches": breaches,
        "warnings": len(breaches),
        "freeze_recommended": freeze_recommendation,
        "within_budget": len(breaches) == 0,
    }
