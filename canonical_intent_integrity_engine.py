from typing import Any, Dict, List


def validate_canonical_intent_integrity(
    canonical_specs: List[Dict[str, Any]],
    system_state: Dict[str, Any],
    operational_traces: List[Dict[str, Any]],
    contracts: Dict[str, Any],
) -> Dict[str, Any]:
    specs = list(canonical_specs or [])
    replay_state = dict(system_state or {})
    traces = list(operational_traces or [])
    contract_data = dict(contracts or {})

    issues: List[Dict[str, Any]] = []
    canonical_count = len(specs)
    anomaly_count = len(replay_state.get("anomalies", []))

    if canonical_count == 0:
        issues.append(
            {
                "type": "MISSING_CANONICAL_INTENT",
                "severity": "critical",
                "description": "No canonical specs available to anchor execution legitimacy.",
            }
        )

    reinterpretation_events = 0
    for item in traces:
        trace_type = str(item.get("trace_type", "")).lower()
        if "override" in trace_type or "forced" in trace_type:
            reinterpretation_events += 1
    if reinterpretation_events > 0:
        issues.append(
            {
                "type": "INTENT_REINTERPRETATION",
                "severity": "medium",
                "description": "Operational overrides indicate possible intent reinterpretation.",
                "count": reinterpretation_events,
            }
        )

    guarantees = contract_data.get("system_contract", {}).get("guarantees", [])
    if not guarantees:
        issues.append(
            {
                "type": "GOVERNANCE_DETACHED_FROM_PURPOSE",
                "severity": "high",
                "description": "System guarantees were unavailable while evaluating intent integrity.",
            }
        )

    if anomaly_count > 0:
        issues.append(
            {
                "type": "MISSION_ALIGNMENT_INSTABILITY",
                "severity": "high",
                "description": "Replay anomalies can break continuity between mission and execution.",
                "count": anomaly_count,
            }
        )

    integrity_score = max(
        0.0,
        min(
            1.0,
            1.0
            - (0.30 if canonical_count == 0 else 0.0)
            - min(0.25, reinterpretation_events * 0.03)
            - min(0.30, anomaly_count * 0.04),
        ),
    )

    return {
        "status": "ok",
        "aligned_with_original_mission": integrity_score >= 0.55 and canonical_count > 0,
        "intent_reinterpretation_detected": reinterpretation_events > 0,
        "governance_detached_from_purpose": any(
            issue.get("type") == "GOVERNANCE_DETACHED_FROM_PURPOSE" for issue in issues
        ),
        "integrity_score": round(integrity_score, 4),
        "integrity_status": "INTACT" if integrity_score >= 0.75 else "DEGRADED" if integrity_score >= 0.45 else "CORRUPTED",
        "issues": issues,
        "inputs": {
            "canonical_spec_count": canonical_count,
            "replay_anomaly_count": anomaly_count,
            "reinterpretation_event_count": reinterpretation_events,
        },
    }
