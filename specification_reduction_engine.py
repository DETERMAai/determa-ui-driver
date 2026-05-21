from typing import Any, Dict, List

from governance_inflation_detector import detect_governance_inflation
from spec_registry import spec_registry


def generate_spec_reduction_report() -> Dict[str, Any]:
    specs = list(spec_registry.values())
    inflation = detect_governance_inflation()

    recommendations: List[Dict[str, Any]] = []

    if inflation.get("semantic_duplication_groups"):
        recommendations.append(
            {
                "type": "semantic_deduplication",
                "priority": "high",
                "description": "Merge or retire semantically duplicated specs.",
                "affected_groups": inflation.get("semantic_duplication_groups"),
            }
        )

    superseded_specs = [s for s in specs if s.get("status") == "SUPERSEDED"]
    if superseded_specs:
        recommendations.append(
            {
                "type": "superseded_cleanup",
                "priority": "medium",
                "description": "Archive superseded specifications to reduce governance surface.",
                "count": len(superseded_specs),
            }
        )

    recursive_specs = list(inflation.get("recursive_expansion_specs", []))
    if recursive_specs:
        recommendations.append(
            {
                "type": "recursive_expansion_remediation",
                "priority": "high",
                "description": "Resolve recursive derivation chains and restore acyclic lineage.",
                "spec_ids": recursive_specs,
            }
        )

    deep_lineage_specs = [s for s in specs if isinstance(s.get("derived_from"), str) and s.get("derived_from")]
    if len(deep_lineage_specs) > max(3, len(specs) // 2):
        recommendations.append(
            {
                "type": "lineage_compression",
                "priority": "medium",
                "description": "Consolidate long derivation chains into cleaner canonical revisions.",
                "count": len(deep_lineage_specs),
            }
        )

    if inflation.get("inflation_risk") == "HIGH":
        recommendations.append(
            {
                "type": "governance_freeze",
                "priority": "high",
                "description": "Temporarily restrict new canonicalization until complexity is reduced.",
            }
        )

    return {
        "status": "ok",
        "summary": {
            "spec_count": len(specs),
            "inflation_risk": inflation.get("inflation_risk"),
            "inflation_score": inflation.get("inflation_score"),
        },
        "inflation": inflation,
        "recommendations": recommendations,
    }
