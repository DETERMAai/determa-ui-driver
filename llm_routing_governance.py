from copy import deepcopy
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List

from llm_safety_layer import (
    detect_trust_drift,
    get_safety_status,
    inject_exploration_routing,
    normalize_model_trust,
    rotate_adversarial_sampling,
    safety_gate_before_update,
)

model_registry: Dict[str, Dict[str, Any]] = {}
_registry_lock = Lock()


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _default_entry() -> Dict[str, Any]:
    return {
        "cost_avg": 0.0,
        "quality_score": 0.7,
        "failure_rate": 0.0,
        "adversarial_failure_rate": 0.0,
        "trust_score": 0.7,
        "last_updated": _utc_now_iso(),
    }


def _ensure_model_entry(model_id: str) -> Dict[str, Any]:
    if model_id not in model_registry:
        model_registry[model_id] = _default_entry()
    return model_registry[model_id]


def register_models(model_ids: List[str]) -> None:
    with _registry_lock:
        for model_id in model_ids:
            if model_id:
                _ensure_model_entry(str(model_id))
        normalize_model_trust(model_registry)


def _risk_weights(task: Dict[str, Any]) -> Dict[str, float]:
    risk_level = str(task.get("risk_level", "medium")).lower()
    requires_verification = bool(task.get("requires_verification", False))
    required_accuracy = float(task.get("required_accuracy", 0.75))
    latency_sensitivity = str(task.get("latency_sensitivity", "medium")).lower()

    # Base weights for: quality, cost, failure, adversarial
    weights = {"w1": 0.45, "w2": 0.20, "w3": 0.20, "w4": 0.15}

    if risk_level == "high":
        weights = {"w1": 0.60, "w2": 0.08, "w3": 0.14, "w4": 0.18}
    elif risk_level == "low":
        weights = {"w1": 0.30, "w2": 0.45, "w3": 0.15, "w4": 0.10}

    if requires_verification:
        weights["w4"] += 0.06
        weights["w2"] = max(0.02, weights["w2"] - 0.04)

    if required_accuracy >= 0.9:
        weights["w1"] += 0.07
        weights["w2"] = max(0.02, weights["w2"] - 0.03)

    if latency_sensitivity == "high":
        weights["w2"] += 0.05
        weights["w1"] = max(0.15, weights["w1"] - 0.03)

    # Renormalize to sum to 1
    total = weights["w1"] + weights["w2"] + weights["w3"] + weights["w4"]
    return {key: value / total for key, value in weights.items()}


def select_best_llm_backend(task: Dict[str, Any]) -> Dict[str, Any]:
    available_models = [str(model_id) for model_id in task.get("available_models", []) if str(model_id)]
    if not available_models:
        available_models = list(model_registry.keys())

    if not available_models:
        return {
            "selected_model": "",
            "selection_reason": "no_available_models",
            "confidence": 0.0,
        }

    weights = _risk_weights(task)
    scores: List[Dict[str, Any]] = []

    with _registry_lock:
        normalize_model_trust(model_registry)
        for model_id in available_models:
            entry = _ensure_model_entry(model_id)
            score = (
                float(entry["quality_score"]) * weights["w1"]
                - float(entry["cost_avg"]) * weights["w2"]
                - float(entry["failure_rate"]) * weights["w3"]
                - float(entry["adversarial_failure_rate"]) * weights["w4"]
            )
            scores.append({"model_id": model_id, "score": score})

    scores.sort(key=lambda item: item["score"], reverse=True)
    winner = scores[0]
    runner_up_score = scores[1]["score"] if len(scores) > 1 else winner["score"] - 0.25
    base_confidence = _clamp(0.5 + ((winner["score"] - runner_up_score) * 2.0), 0.0, 1.0)

    ranked_models = [item["model_id"] for item in scores]
    drift_results = detect_trust_drift(model_registry)
    rotation_choice = rotate_adversarial_sampling(ranked_models, drift_results)
    exploration_choice = inject_exploration_routing(task, ranked_models)

    chosen_model = winner["model_id"]
    selection_reason = (
        f"weighted_selection(risk={str(task.get('risk_level', 'medium')).lower()},"
        f"verification={bool(task.get('requires_verification', False))})"
    )
    confidence = round(base_confidence, 4)

    if rotation_choice and rotation_choice.get("selected_model"):
        chosen_model = str(rotation_choice["selected_model"])
        selection_reason = str(rotation_choice.get("selection_reason", "adversarial_rotation_sampling"))
        try:
            choice_conf = float(rotation_choice.get("confidence", base_confidence))
        except Exception:
            choice_conf = base_confidence
        confidence = round(_clamp(choice_conf, 0.0, 1.0), 4)
    elif exploration_choice and exploration_choice.get("selected_model"):
        chosen_model = str(exploration_choice["selected_model"])
        selection_reason = str(exploration_choice.get("selection_reason", "exploration_injection"))
        try:
            choice_conf = float(exploration_choice.get("confidence", base_confidence))
        except Exception:
            choice_conf = base_confidence
        confidence = round(_clamp(choice_conf, 0.0, 1.0), 4)

    return {
        "selected_model": chosen_model,
        "selection_reason": selection_reason,
        "confidence": confidence,
    }


def _recompute_trust(entry: Dict[str, Any]) -> float:
    cost_penalty = _clamp(float(entry["cost_avg"]), 0.0, 1.0)
    trust = (
        float(entry["quality_score"]) * 0.50
        + (1.0 - float(entry["failure_rate"])) * 0.25
        + (1.0 - float(entry["adversarial_failure_rate"])) * 0.25
        - cost_penalty * 0.10
    )
    return _clamp(trust, 0.0, 1.0)


def update_model_trust(model_id: str, execution_result: Dict[str, Any]) -> Dict[str, Any]:
    alpha = 0.20
    with _registry_lock:
        entry = _ensure_model_entry(str(model_id))
        proposed = dict(entry)

        try:
            observed_cost = float(execution_result.get("cost", 0.0))
        except Exception:
            observed_cost = 0.0
        proposed["cost_avg"] = round((1.0 - alpha) * float(entry["cost_avg"]) + alpha * observed_cost, 6)

        success = bool(execution_result.get("success", True))
        observed_failure = 0.0 if success else 1.0
        proposed["failure_rate"] = round(
            (1.0 - alpha) * float(entry["failure_rate"]) + alpha * observed_failure,
            6,
        )

        verification_passed = execution_result.get("verification_passed")
        if isinstance(verification_passed, bool):
            observed_quality = 1.0 if verification_passed else 0.0
        else:
            observed_quality = 0.7 if success else 0.2
        proposed["quality_score"] = round(
            (1.0 - alpha) * float(entry["quality_score"]) + alpha * observed_quality,
            6,
        )

        adversarial_failed = bool(execution_result.get("adversarial_failed", False))
        observed_adv_failure = 1.0 if adversarial_failed else 0.0
        proposed["adversarial_failure_rate"] = round(
            (1.0 - alpha) * float(entry["adversarial_failure_rate"]) + alpha * observed_adv_failure,
            6,
        )

        proposed["trust_score"] = round(_recompute_trust(proposed), 6)
        proposed["last_updated"] = _utc_now_iso()

        gate_result = safety_gate_before_update(str(model_id), proposed, model_registry)
        if not gate_result.get("allowed", False):
            current_snapshot = deepcopy(entry)
            current_snapshot["safety_rejected"] = True
            current_snapshot["safety_reject_reason"] = gate_result.get("reason", "safety_gate_rejected")
            return current_snapshot

        entry.update(proposed)
        normalize_model_trust(model_registry)
        detect_trust_drift(model_registry)

        return deepcopy(entry)


def get_model_status() -> Dict[str, Any]:
    with _registry_lock:
        registry_copy = deepcopy(model_registry)

    ranking_order = sorted(
        (
            {
                "model_id": model_id,
                "trust_score": float(entry.get("trust_score", 0.0)),
                "quality_score": float(entry.get("quality_score", 0.0)),
                "cost_avg": float(entry.get("cost_avg", 0.0)),
            }
            for model_id, entry in registry_copy.items()
        ),
        key=lambda item: item["trust_score"],
        reverse=True,
    )

    return {
        "model_registry": registry_copy,
        "ranking_order": ranking_order,
    }


def get_llm_safety_status() -> Dict[str, Any]:
    with _registry_lock:
        registry_copy = deepcopy(model_registry)
    return get_safety_status(registry_copy)
