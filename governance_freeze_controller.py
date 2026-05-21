from typing import Any, Dict, List

from governance_complexity_budget import evaluate_governance_complexity_budget
from legitimacy_clarity_engine import evaluate_legitimacy_clarity
from semantic_compression_engine import generate_semantic_compression_report
from semantic_entropy_metrics import measure_semantic_entropy


FREEZE_THRESHOLDS = {
    "entropy_score": 0.75,
    "critical_clarity_status": "UNCLEAR",
}


def evaluate_governance_freeze_status() -> Dict[str, Any]:
    entropy = measure_semantic_entropy()
    clarity = evaluate_legitimacy_clarity()
    complexity = evaluate_governance_complexity_budget()
    compression = generate_semantic_compression_report()

    reasons: List[Dict[str, Any]] = []

    if float(entropy.get("entropy_score", 0.0)) >= FREEZE_THRESHOLDS["entropy_score"]:
        reasons.append(
            {
                "trigger": "entropy_exceeded",
                "severity": "high",
                "value": entropy.get("entropy_score"),
                "threshold": FREEZE_THRESHOLDS["entropy_score"],
            }
        )

    if str(clarity.get("clarity_status")) == FREEZE_THRESHOLDS["critical_clarity_status"]:
        reasons.append(
            {
                "trigger": "critical_clarity_degradation",
                "severity": "high",
                "value": clarity.get("clarity_status"),
            }
        )

    if bool(complexity.get("freeze_recommended", False)):
        reasons.append(
            {
                "trigger": "complexity_budget_collapse",
                "severity": "high",
                "breaches": complexity.get("breaches", []),
            }
        )

    recursive = list(compression.get("signals", {}).get("recursive_rule_expansion", []))
    if recursive:
        reasons.append(
            {
                "trigger": "recursive_governance_expansion_detected",
                "severity": "high",
                "spec_ids": recursive,
            }
        )

    frozen = len(reasons) > 0

    return {
        "status": "ok",
        "frozen": frozen,
        "freeze_scope": "governance_evolution",
        "reasons": reasons,
        "can_recommend_reductions": True,
        "can_mutate_constitutional_foundations": False,
        "thresholds": dict(FREEZE_THRESHOLDS),
        "inputs": {
            "entropy": {
                "entropy_score": entropy.get("entropy_score"),
                "entropy_level": entropy.get("entropy_level"),
            },
            "clarity": {
                "clarity_status": clarity.get("clarity_status"),
                "clarity_score": clarity.get("clarity_score"),
            },
            "complexity": {
                "within_budget": complexity.get("within_budget"),
                "freeze_recommended": complexity.get("freeze_recommended"),
            },
            "recursive_expansion_count": len(recursive),
        },
    }
