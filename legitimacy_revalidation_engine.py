from datetime import datetime
from typing import Any, Dict, List


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _signal_valid(signal: Dict[str, Any]) -> bool:
    if "valid" in signal:
        return bool(signal.get("valid"))
    if "allowed" in signal:
        return bool(signal.get("allowed"))
    if "safe" in signal:
        return bool(signal.get("safe"))
    if "consistent" in signal:
        return bool(signal.get("consistent"))
    if "healthy" in signal:
        return bool(signal.get("healthy"))
    return False


def revalidate_legitimacy(
    constitutional_coherence: Dict[str, Any],
    governance_relevance: Dict[str, Any],
    autonomy_safety: Dict[str, Any],
    replay_guarantees: Dict[str, Any],
    operational_validity: Dict[str, Any],
) -> Dict[str, Any]:
    checks = {
        "constitutional_coherence": dict(constitutional_coherence or {}),
        "governance_relevance": dict(governance_relevance or {}),
        "autonomy_safety": dict(autonomy_safety or {}),
        "replay_guarantees": dict(replay_guarantees or {}),
        "operational_validity": dict(operational_validity or {}),
    }

    failed: List[Dict[str, Any]] = []
    for name, signal in checks.items():
        if not _signal_valid(signal):
            failed.append(
                {
                    "dimension": name,
                    "severity": "high" if name in {"constitutional_coherence", "replay_guarantees"} else "medium",
                    "reason": str(signal.get("reason", "revalidation_check_failed")),
                }
            )

    score = max(0.0, min(1.0, 1.0 - (len(failed) / 5.0)))
    if not failed:
        legitimacy_status = "VALID"
    elif any(item.get("dimension") == "constitutional_coherence" for item in failed):
        legitimacy_status = "INVALID"
    elif score < 0.5:
        legitimacy_status = "INVALID"
    else:
        legitimacy_status = "DEGRADED"

    return {
        "status": "ok",
        "timestamp": _now_iso(),
        "legitimacy_status": legitimacy_status,
        "legitimacy_score": round(score, 4),
        "failed_dimensions": failed,
        "checks": checks,
    }
