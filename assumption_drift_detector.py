from datetime import datetime
from typing import Any, Dict, List, Tuple


_assumption_baseline: Dict[str, Any] = {}
assumption_drift_history: List[Dict[str, Any]] = []
_MAX_HISTORY = 1000


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _as_sorted_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).strip() for item in value if str(item).strip()})


def _as_numeric_dict(value: Any) -> Dict[str, float]:
    if not isinstance(value, dict):
        return {}
    normalized: Dict[str, float] = {}
    for key, raw in value.items():
        try:
            normalized[str(key)] = float(raw)
        except Exception:
            continue
    return normalized


def _normalize_snapshot(current_assumptions: Dict[str, Any]) -> Dict[str, Any]:
    current = dict(current_assumptions or {})
    return {
        "runtime_assumptions": _as_sorted_list(current.get("runtime_assumptions", [])),
        "operator_behavior": _as_numeric_dict(current.get("operator_behavior", {})),
        "threat_conditions": _as_sorted_list(current.get("threat_conditions", [])),
        "autonomy_capabilities": _as_sorted_list(current.get("autonomy_capabilities", [])),
    }


def _list_drift(previous: List[str], current: List[str]) -> Tuple[List[str], List[str]]:
    previous_set = set(previous)
    current_set = set(current)
    return sorted(list(current_set - previous_set)), sorted(list(previous_set - current_set))


def detect_assumption_drift(current_assumptions: Dict[str, Any]) -> Dict[str, Any]:
    global _assumption_baseline

    current = _normalize_snapshot(current_assumptions)
    alerts: List[Dict[str, Any]] = []

    if not _assumption_baseline:
        _assumption_baseline = dict(current)
        result = {
            "status": "ok",
            "timestamp": _now_iso(),
            "drift_detected": False,
            "drift_score": 0.0,
            "drift_alerts": [],
            "revalidation_recommendations": [],
            "baseline_initialized": True,
        }
        assumption_drift_history.append(result)
        return result

    runtime_added, runtime_removed = _list_drift(
        _assumption_baseline.get("runtime_assumptions", []),
        current.get("runtime_assumptions", []),
    )
    if runtime_added or runtime_removed:
        alerts.append(
            {
                "type": "RUNTIME_ASSUMPTION_DRIFT",
                "severity": "medium",
                "added": runtime_added,
                "removed": runtime_removed,
            }
        )

    threat_added, threat_removed = _list_drift(
        _assumption_baseline.get("threat_conditions", []),
        current.get("threat_conditions", []),
    )
    if threat_added or threat_removed:
        alerts.append(
            {
                "type": "THREAT_CONDITION_DRIFT",
                "severity": "high",
                "added": threat_added,
                "removed": threat_removed,
            }
        )

    autonomy_added, autonomy_removed = _list_drift(
        _assumption_baseline.get("autonomy_capabilities", []),
        current.get("autonomy_capabilities", []),
    )
    if autonomy_added or autonomy_removed:
        alerts.append(
            {
                "type": "AUTONOMY_CAPABILITY_DRIFT",
                "severity": "high",
                "added": autonomy_added,
                "removed": autonomy_removed,
            }
        )

    previous_behavior = _assumption_baseline.get("operator_behavior", {})
    current_behavior = current.get("operator_behavior", {})
    for metric_name, current_value in current_behavior.items():
        previous_value = float(previous_behavior.get(metric_name, 0.0))
        if previous_value == 0.0:
            delta_ratio = 1.0 if current_value != 0.0 else 0.0
        else:
            delta_ratio = abs(current_value - previous_value) / abs(previous_value)
        if delta_ratio >= 0.35 and abs(current_value - previous_value) >= 1.0:
            alerts.append(
                {
                    "type": "OPERATOR_BEHAVIOR_DRIFT",
                    "severity": "medium",
                    "metric": metric_name,
                    "previous": previous_value,
                    "current": current_value,
                    "delta_ratio": round(delta_ratio, 4),
                }
            )

    drift_score = min(1.0, len(alerts) / 6.0)
    recommendations: List[str] = []
    if alerts:
        recommendations.append("run_legitimacy_revalidation")
        recommendations.append("review_governance_relevance")
    if any(alert.get("severity") == "high" for alert in alerts):
        recommendations.append("trigger_legitimacy_renewal")
        recommendations.append("require_constitutional_revalidation")

    result = {
        "status": "ok",
        "timestamp": _now_iso(),
        "drift_detected": len(alerts) > 0,
        "drift_score": round(drift_score, 4),
        "drift_alerts": alerts,
        "revalidation_recommendations": sorted(set(recommendations)),
        "baseline_initialized": True,
    }
    assumption_drift_history.append(result)
    if len(assumption_drift_history) > _MAX_HISTORY:
        del assumption_drift_history[0 : len(assumption_drift_history) - _MAX_HISTORY]
    return result
