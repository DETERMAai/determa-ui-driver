from typing import Any, Dict

from governance_complexity_budget import evaluate_governance_complexity_budget
from governance_inflation_detector import detect_governance_inflation
from semantic_compression_engine import generate_semantic_compression_report
from spec_registry import get_canonical_specs, spec_registry


def measure_semantic_entropy() -> Dict[str, Any]:
    compression = generate_semantic_compression_report()
    inflation = detect_governance_inflation()
    budget = evaluate_governance_complexity_budget()

    specs = list(spec_registry.values())
    canonical_specs = get_canonical_specs()

    ambiguous_specs = 0
    for spec in specs:
        title = str(spec.get("title") or "").strip()
        content = dict(spec.get("content", {}) or {})
        if not title:
            ambiguous_specs += 1
        if not content:
            ambiguous_specs += 1

    overlap_signal = len(compression.get("signals", {}).get("equivalent_governance_semantics", []))
    recursive_density = 0.0
    recursive_specs = compression.get("signals", {}).get("recursive_rule_expansion", [])
    if len(specs) > 0:
        recursive_density = len(recursive_specs) / float(len(specs))

    ambiguity_ratio = 0.0
    if len(specs) > 0:
        ambiguity_ratio = min(1.0, ambiguous_specs / float(len(specs) * 2))

    inflation_score = float(inflation.get("inflation_score", 0.0))
    budget_pressure = min(1.0, len(budget.get("breaches", [])) / 4.0)
    semantic_overlap_ratio = min(1.0, overlap_signal / float(max(1, len(canonical_specs))))

    entropy_score = (
        ambiguity_ratio * 0.25
        + semantic_overlap_ratio * 0.25
        + inflation_score * 0.25
        + recursive_density * 0.15
        + budget_pressure * 0.10
    )

    if entropy_score >= 0.75:
        level = "HIGH"
    elif entropy_score >= 0.45:
        level = "MEDIUM"
    else:
        level = "LOW"

    comprehensibility_degradation = min(1.0, entropy_score + (0.1 if budget_pressure > 0 else 0.0))

    return {
        "status": "ok",
        "entropy_level": level,
        "entropy_score": round(entropy_score, 4),
        "metrics": {
            "ambiguity": round(ambiguity_ratio, 4),
            "semantic_overlap": round(semantic_overlap_ratio, 4),
            "governance_inflation": round(inflation_score, 4),
            "recursive_derivation_density": round(recursive_density, 4),
            "operator_comprehensibility_degradation": round(comprehensibility_degradation, 4),
        },
        "sources": {
            "compression_pressure": compression.get("compression_pressure", 0),
            "inflation_risk": inflation.get("inflation_risk"),
            "budget_breaches": budget.get("breaches", []),
        },
    }
