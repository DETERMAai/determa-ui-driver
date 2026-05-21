from typing import Any, Dict, List

from constitutional_minimality_engine import evaluate_governance_minimality
from governance_complexity_budget import evaluate_governance_complexity_budget
from semantic_entropy_metrics import measure_semantic_entropy


def evaluate_legitimacy_clarity() -> Dict[str, Any]:
    entropy = measure_semantic_entropy()
    minimality = evaluate_governance_minimality()
    budget = evaluate_governance_complexity_budget()

    issues: List[Dict[str, Any]] = []

    if entropy.get("entropy_level") == "HIGH":
        issues.append(
            {
                "type": "high_semantic_entropy",
                "severity": "high",
                "description": "Governance semantics are too entropic for safe operator auditability.",
            }
        )

    if not minimality.get("minimality_valid", False):
        issues.append(
            {
                "type": "minimality_gap",
                "severity": "high",
                "description": "Minimum constitutional invariants or rules are not satisfied.",
            }
        )

    if budget.get("freeze_recommended", False):
        issues.append(
            {
                "type": "complexity_budget_exceeded",
                "severity": "high",
                "description": "Governance complexity budget exceeded with freeze recommendation.",
            }
        )
    elif budget.get("warnings", 0) > 0:
        issues.append(
            {
                "type": "complexity_budget_warning",
                "severity": "medium",
                "description": "Governance complexity approaching unsafe auditability boundary.",
            }
        )

    clarity_score = 1.0
    clarity_score -= float(entropy.get("entropy_score", 0.0)) * 0.45
    clarity_score -= min(1.0, len(issues) / 4.0) * 0.35
    clarity_score -= 0.2 if not minimality.get("minimality_valid", False) else 0.0
    clarity_score = max(0.0, min(1.0, clarity_score))

    if clarity_score >= 0.75 and len(issues) == 0:
        clarity_status = "CLEAR"
    elif clarity_score >= 0.45:
        clarity_status = "DEGRADED"
    else:
        clarity_status = "UNCLEAR"

    return {
        "status": "ok",
        "clarity_status": clarity_status,
        "clarity_score": round(clarity_score, 4),
        "operator_auditability_preserved": clarity_status != "UNCLEAR",
        "legitimacy_boundaries_understandable": clarity_status == "CLEAR",
        "issues": issues,
        "inputs": {
            "entropy": entropy,
            "minimality_valid": minimality.get("minimality_valid", False),
            "budget_within_limits": budget.get("within_budget", False),
        },
    }
