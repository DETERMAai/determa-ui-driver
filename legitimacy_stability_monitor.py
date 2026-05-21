from typing import Any, Dict

from governance_freeze_controller import evaluate_governance_freeze_status
from governance_inflation_detector import detect_governance_inflation
from legitimacy_clarity_engine import evaluate_legitimacy_clarity
from semantic_entropy_metrics import measure_semantic_entropy
from spec_registry import get_specs_history


def evaluate_legitimacy_stability() -> Dict[str, Any]:
    freeze = evaluate_governance_freeze_status()
    entropy = measure_semantic_entropy()
    clarity = evaluate_legitimacy_clarity()
    inflation = detect_governance_inflation()
    history = get_specs_history()

    canonicalizations = len([h for h in history if h.get("action") == "CANONICALIZED"])
    supersessions = len([h for h in history if h.get("action") == "SUPERSEDED"])
    rejections = len([h for h in history if h.get("action") == "REJECTED"])

    mutation_pressure = canonicalizations + supersessions + rejections
    instability_penalty = 0.0
    instability_penalty += min(1.0, mutation_pressure / 50.0) * 0.30
    instability_penalty += float(entropy.get("entropy_score", 0.0)) * 0.30
    instability_penalty += float(inflation.get("inflation_score", 0.0)) * 0.20
    instability_penalty += 0.20 if bool(freeze.get("frozen", False)) else 0.0

    constitutional_stability = max(0.0, 1.0 - instability_penalty)
    governance_survivability = max(
        0.0,
        min(1.0, constitutional_stability - (0.15 if clarity.get("clarity_status") == "UNCLEAR" else 0.0)),
    )
    long_term_auditability = max(
        0.0,
        min(
            1.0,
            (1.0 - float(entropy.get("metrics", {}).get("operator_comprehensibility_degradation", 0.0)))
            * (0.9 if clarity.get("operator_auditability_preserved", False) else 0.5),
        ),
    )

    if constitutional_stability >= 0.75 and governance_survivability >= 0.70:
        stability_status = "STABLE"
    elif constitutional_stability >= 0.45:
        stability_status = "DEGRADED"
    else:
        stability_status = "UNSTABLE"

    return {
        "status": "ok",
        "stability_status": stability_status,
        "constitutional_stability": round(constitutional_stability, 4),
        "mutation_pressure": mutation_pressure,
        "governance_survivability": round(governance_survivability, 4),
        "long_term_auditability": round(long_term_auditability, 4),
        "inputs": {
            "freeze": freeze,
            "entropy_score": entropy.get("entropy_score"),
            "clarity_status": clarity.get("clarity_status"),
            "inflation_score": inflation.get("inflation_score"),
        },
    }
