from typing import Any, Dict, List


reduction_cycles: List[Dict[str, Any]] = []
_MAX_CYCLES = 200


def run_operational_reduction_cycle(
    reduction_report: Dict[str, Any],
    friction_map: Dict[str, Any],
    daily_status: Dict[str, Any],
) -> Dict[str, Any]:
    report = reduction_report.get("report", reduction_report) if isinstance(reduction_report, dict) else {}
    friction = friction_map.get("friction", friction_map) if isinstance(friction_map, dict) else {}
    active_session = daily_status.get("active_session") if isinstance(daily_status, dict) else None

    governance_friction = float(friction.get("governance_friction_score", 0.0))
    runtime_friction = float(friction.get("runtime_friction_score", 0.0))
    unused_modules = report.get("unused_module_candidates", []) if isinstance(report, dict) else []
    repeated_escalations = float((friction.get("signals", {}) or {}).get("escalation_density", 0.0)) > 0.5

    simplification_recommendations = list(report.get("simplification_recommendations", [])) if isinstance(report, dict) else []
    if governance_friction > 60.0:
        simplification_recommendations.append("Reduce approval friction by consolidating equivalent approval endpoints.")
    if runtime_friction > 60.0:
        simplification_recommendations.append("Reduce runtime friction by limiting retry loops and improving queue backpressure.")
    if repeated_escalations:
        simplification_recommendations.append("Escalation density is high; tighten autonomy boundaries for noisy paths.")

    cycle = {
        "session_id": (active_session or {}).get("session_id"),
        "unused_module_count": len(unused_modules),
        "governance_friction_score": governance_friction,
        "runtime_friction_score": runtime_friction,
        "repeated_escalations_detected": repeated_escalations,
        "runtime_reduction_candidates": unused_modules,
        "simplification_recommendations": simplification_recommendations,
    }
    reduction_cycles.append(cycle)
    if len(reduction_cycles) > _MAX_CYCLES:
        del reduction_cycles[0 : len(reduction_cycles) - _MAX_CYCLES]
    return {
        "cycle": cycle,
        "recent_cycles": reduction_cycles[-20:],
        "cycle_count": len(reduction_cycles),
    }
