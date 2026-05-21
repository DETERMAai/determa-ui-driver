import os
import random
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional


_safety_lock = Lock()
_trust_history: Dict[str, List[float]] = {}
_exploration_events: List[Dict[str, Any]] = []
_selection_counter = 0
_rotation_counter = 0


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _compute_diversity_index(model_registry: Dict[str, Dict[str, Any]]) -> float:
    trust_values = [_as_float(entry.get("trust_score", 0.0), 0.0) for entry in model_registry.values()]
    if len(trust_values) <= 1:
        return 1.0
    mean = sum(trust_values) / len(trust_values)
    if mean <= 0:
        return 0.0
    variance = sum((value - mean) ** 2 for value in trust_values) / len(trust_values)
    normalized_std = (variance ** 0.5) / max(mean, 1e-9)
    return _clamp(1.0 - normalized_std, 0.0, 1.0)


def _dominance_score(model_registry: Dict[str, Dict[str, Any]]) -> float:
    trust_values = [_as_float(entry.get("trust_score", 0.0), 0.0) for entry in model_registry.values()]
    if not trust_values:
        return 0.0
    mean = sum(trust_values) / len(trust_values)
    if mean <= 0:
        return 0.0
    return max(trust_values) / mean


def _record_trust_history(model_registry: Dict[str, Dict[str, Any]]) -> None:
    with _safety_lock:
        for model_id, entry in model_registry.items():
            series = _trust_history.setdefault(model_id, [])
            series.append(_as_float(entry.get("trust_score", 0.0), 0.0))
            if len(series) > 100:
                del series[0 : len(series) - 100]


def normalize_model_trust(model_registry: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not model_registry:
        return model_registry

    trust_values = [_as_float(entry.get("trust_score", 0.0), 0.0) for entry in model_registry.values()]
    mean_trust = sum(trust_values) / len(trust_values)
    if mean_trust <= 0:
        return model_registry

    dominance_limit = 2.0 * mean_trust
    for entry in model_registry.values():
        trust = _as_float(entry.get("trust_score", 0.0), 0.0)
        if trust > dominance_limit:
            excess = trust - dominance_limit
            trust = dominance_limit + (excess * 0.25)
            entry["trust_score"] = round(_clamp(trust, 0.0, 1.0), 6)
        else:
            entry["trust_score"] = round(_clamp(trust, 0.0, 1.0), 6)
    return model_registry


def inject_exploration_routing(task: Dict[str, Any], ranked_models: List[str]) -> Optional[Dict[str, Any]]:
    if len(ranked_models) <= 1:
        return None

    configured_rate = _as_float(task.get("exploration_rate"), _as_float(os.getenv("DETERMA_EXPLORATION_RATE", 0.15), 0.15))
    exploration_rate = _clamp(configured_rate, 0.1, 0.2)

    global _selection_counter
    _selection_counter += 1

    if random.random() >= exploration_rate:
        return None

    candidate_pool = ranked_models[1:]
    if not candidate_pool:
        return None
    selected_model = random.choice(candidate_pool)

    event = {
        "timestamp": _utc_now_iso(),
        "selected_model": selected_model,
        "top_ranked_model": ranked_models[0],
        "exploration_rate": round(exploration_rate, 4),
    }
    with _safety_lock:
        _exploration_events.append(event)
        if len(_exploration_events) > 500:
            del _exploration_events[0 : len(_exploration_events) - 500]

    return {
        "selected_model": selected_model,
        "selection_reason": "exploration_injection",
        "confidence": round(1.0 - exploration_rate, 4),
    }


def detect_trust_drift(model_registry: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    _record_trust_history(model_registry)
    results: List[Dict[str, Any]] = []

    with _safety_lock:
        history_copy = {model_id: list(series) for model_id, series in _trust_history.items()}

    for model_id, series in history_copy.items():
        if len(series) < 6:
            results.append(
                {
                    "model_id": model_id,
                    "drift_detected": False,
                    "severity": "low",
                }
            )
            continue

        short_window = series[-3:]
        long_window = series[:-3] if len(series) > 3 else series
        short_mean = sum(short_window) / len(short_window)
        long_mean = sum(long_window) / len(long_window)
        delta = short_mean - long_mean
        abs_delta = abs(delta)

        drift_detected = abs_delta >= 0.08
        if abs_delta >= 0.25:
            severity = "high"
        elif abs_delta >= 0.15:
            severity = "medium"
        else:
            severity = "low"

        results.append(
            {
                "model_id": model_id,
                "drift_detected": drift_detected,
                "severity": severity,
            }
        )

    return results


def rotate_adversarial_sampling(ranked_models: List[str], drift_results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if len(ranked_models) <= 1:
        return None

    global _rotation_counter
    _rotation_counter += 1
    period = int(_as_float(os.getenv("DETERMA_ROTATION_PERIOD", 5), 5))
    period = max(2, period)

    if _rotation_counter % period != 0:
        return None

    degraded_models = {
        result.get("model_id")
        for result in drift_results
        if bool(result.get("drift_detected")) and result.get("severity") in {"medium", "high"}
    }

    lower_ranked = ranked_models[max(1, len(ranked_models) // 2) :]
    candidate_pool = [model_id for model_id in lower_ranked if model_id]
    candidate_pool.extend(model_id for model_id in degraded_models if model_id and model_id not in candidate_pool)
    if not candidate_pool:
        candidate_pool = ranked_models[1:]
    if not candidate_pool:
        return None

    selected_model = candidate_pool[0]
    return {
        "selected_model": selected_model,
        "selection_reason": "adversarial_rotation_sampling",
        "confidence": 0.55,
    }


def safety_gate_before_update(
    model_id: str,
    proposed_update: Dict[str, Any],
    model_registry: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    registry = model_registry if isinstance(model_registry, dict) else {}
    if not registry:
        return {"allowed": True, "reason": "empty_registry"}

    current_entry = registry.get(str(model_id), {})
    current_trust = _as_float(current_entry.get("trust_score", 0.0), 0.0)
    proposed_trust = _as_float(proposed_update.get("trust_score", current_trust), current_trust)

    if abs(proposed_trust - current_trust) > 0.35:
        return {"allowed": False, "reason": "extreme_variance_spike"}

    current_diversity = _compute_diversity_index(registry)
    simulated_registry = {key: dict(value) for key, value in registry.items()}
    simulated_entry = simulated_registry.setdefault(str(model_id), {})
    simulated_entry["trust_score"] = proposed_trust
    new_diversity = _compute_diversity_index(simulated_registry)

    if new_diversity < 0.12 and (current_diversity - new_diversity) > 0.10:
        return {"allowed": False, "reason": "diversity_collapse_risk"}

    dominance = _dominance_score(simulated_registry)
    if dominance > 2.25:
        return {"allowed": False, "reason": "single_model_dominance_risk"}

    return {"allowed": True, "reason": "accepted"}


def get_safety_status(model_registry: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    drift_results = detect_trust_drift(model_registry)
    diversity_index = round(_compute_diversity_index(model_registry), 6)
    dominance_score = round(_dominance_score(model_registry), 6)

    with _safety_lock:
        exploration_count = len(_exploration_events)
        selection_count = max(_selection_counter, 1)
    exploration_rate = round(exploration_count / selection_count, 6)

    high_drift_count = sum(1 for result in drift_results if result.get("severity") == "high" and result.get("drift_detected"))
    medium_drift_count = sum(1 for result in drift_results if result.get("severity") == "medium" and result.get("drift_detected"))

    if dominance_score > 2.2 or diversity_index < 0.10 or high_drift_count > 0:
        safety_health_status = "CRITICAL"
    elif dominance_score > 1.8 or diversity_index < 0.20 or medium_drift_count > 0:
        safety_health_status = "WARNING"
    else:
        safety_health_status = "HEALTHY"

    return {
        "model_diversity_index": diversity_index,
        "drift_detection_results": drift_results,
        "exploration_rate": exploration_rate,
        "dominance_score": dominance_score,
        "safety_health_status": safety_health_status,
    }
