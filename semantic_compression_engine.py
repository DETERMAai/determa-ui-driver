import hashlib
import json
from itertools import combinations
from typing import Any, Dict, List, Set

from spec_registry import spec_registry


def _as_set(content: Dict[str, Any], key: str) -> Set[str]:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def _content_fingerprint(content: Dict[str, Any]) -> str:
    payload = json.dumps(dict(content or {}), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _has_recursive_derivation(spec_id: str) -> bool:
    seen = set()
    node = spec_registry.get(str(spec_id))
    while node is not None:
        node_id = str(node.get("spec_id"))
        if node_id in seen:
            return True
        seen.add(node_id)
        parent_id = node.get("derived_from")
        node = spec_registry.get(str(parent_id)) if parent_id else None
    return False


def generate_semantic_compression_report() -> Dict[str, Any]:
    specs = list(spec_registry.values())

    invariant_map: Dict[str, List[str]] = {}
    autonomy_map: Dict[str, Set[str]] = {}
    fingerprints: Dict[str, List[str]] = {}

    for spec in specs:
        spec_id = str(spec.get("spec_id"))
        content = dict(spec.get("content", {}) or {})

        invariants = _as_set(content, "invariants")
        for invariant in invariants:
            invariant_map.setdefault(invariant, []).append(spec_id)

        autonomy_map[spec_id] = _as_set(content, "autonomy_allowed_actions")

        fp = _content_fingerprint(content)
        fingerprints.setdefault(fp, []).append(spec_id)

    duplicated_invariants = [
        {"invariant": name, "spec_ids": ids, "count": len(ids)}
        for name, ids in sorted(invariant_map.items())
        if len(ids) > 1
    ]

    overlapping_autonomy_constraints: List[Dict[str, Any]] = []
    for left_id, right_id in combinations(sorted(autonomy_map.keys()), 2):
        overlap = sorted(list(autonomy_map[left_id].intersection(autonomy_map[right_id])))
        if overlap:
            overlapping_autonomy_constraints.append(
                {
                    "spec_pair": [left_id, right_id],
                    "overlap_actions": overlap,
                    "overlap_count": len(overlap),
                }
            )

    equivalent_governance_semantics = [
        {"spec_ids": ids, "count": len(ids)}
        for ids in fingerprints.values()
        if len(ids) > 1
    ]

    recursive_rule_expansion = [
        str(spec.get("spec_id"))
        for spec in specs
        if _has_recursive_derivation(str(spec.get("spec_id")))
    ]

    recommendations: List[Dict[str, Any]] = []
    if duplicated_invariants:
        recommendations.append(
            {
                "type": "invariant_deduplication",
                "priority": "high",
                "description": "Consolidate repeated invariants into canonical invariant bundles.",
                "targets": duplicated_invariants,
            }
        )
    if equivalent_governance_semantics:
        recommendations.append(
            {
                "type": "semantic_merge",
                "priority": "high",
                "description": "Merge semantically equivalent specs to reduce governance entropy.",
                "targets": equivalent_governance_semantics,
            }
        )
    if overlapping_autonomy_constraints:
        recommendations.append(
            {
                "type": "autonomy_constraint_normalization",
                "priority": "medium",
                "description": "Normalize overlapping autonomy constraints into shared templates.",
                "targets": overlapping_autonomy_constraints,
            }
        )
    if recursive_rule_expansion:
        recommendations.append(
            {
                "type": "lineage_compression",
                "priority": "high",
                "description": "Break recursive derivation and compress lineage into acyclic revisions.",
                "targets": recursive_rule_expansion,
            }
        )

    compression_pressure = (
        len(duplicated_invariants)
        + len(overlapping_autonomy_constraints)
        + len(equivalent_governance_semantics)
        + len(recursive_rule_expansion)
    )

    return {
        "status": "ok",
        "signals": {
            "duplicated_invariants": duplicated_invariants,
            "overlapping_autonomy_constraints": overlapping_autonomy_constraints,
            "equivalent_governance_semantics": equivalent_governance_semantics,
            "recursive_rule_expansion": recursive_rule_expansion,
        },
        "compression_pressure": compression_pressure,
        "recommendations": recommendations,
    }
