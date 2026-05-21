import json
from typing import Any, Dict, List

from spec_registry import SPEC_STATUS_CANONICAL, spec_registry


def _fingerprint_content(content: Dict[str, Any]) -> str:
    try:
        return json.dumps(dict(content or {}), sort_keys=True, separators=(",", ":"))
    except Exception:
        return str(content)


def _semantic_duplication_groups(specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[str, List[str]] = {}
    for spec in specs:
        fp = _fingerprint_content(spec.get("content", {}))
        groups.setdefault(fp, []).append(str(spec.get("spec_id")))
    duplicate_sets = [ids for ids in groups.values() if len(ids) > 1]
    return [
        {
            "spec_ids": ids,
            "count": len(ids),
        }
        for ids in duplicate_sets
    ]


def _has_recursive_expansion(spec_id: str) -> bool:
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


def detect_governance_inflation() -> Dict[str, Any]:
    specs = list(spec_registry.values())
    total_specs = len(specs)
    canonical_specs = [s for s in specs if s.get("status") == SPEC_STATUS_CANONICAL]
    superseded_specs = [s for s in specs if s.get("status") == "SUPERSEDED"]
    rejected_specs = [s for s in specs if s.get("status") == "REJECTED"]

    duplicate_groups = _semantic_duplication_groups(specs)
    duplicate_specs = sum(group["count"] for group in duplicate_groups)
    recursive_expansion_specs = [
        str(spec.get("spec_id")) for spec in specs if _has_recursive_expansion(str(spec.get("spec_id")))
    ]

    inflation_score = 0.0
    if total_specs > 0:
        inflation_score += min(1.0, len(superseded_specs) / max(1, total_specs)) * 0.35
        inflation_score += min(1.0, len(rejected_specs) / max(1, total_specs)) * 0.2
        inflation_score += min(1.0, duplicate_specs / max(1, total_specs)) * 0.35
        inflation_score += min(1.0, max(0, len(canonical_specs) - 1) / max(1, total_specs)) * 0.1
        inflation_score += min(1.0, len(recursive_expansion_specs) / max(1, total_specs)) * 0.2

    if inflation_score >= 0.75:
        risk = "HIGH"
    elif inflation_score >= 0.45:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "total_specs": total_specs,
        "canonical_specs": len(canonical_specs),
        "superseded_specs": len(superseded_specs),
        "rejected_specs": len(rejected_specs),
        "semantic_duplication_groups": duplicate_groups,
        "recursive_expansion_specs": recursive_expansion_specs,
        "inflation_score": round(inflation_score, 4),
        "inflation_risk": risk,
        "governance_complexity_bounded": risk != "HIGH",
    }
