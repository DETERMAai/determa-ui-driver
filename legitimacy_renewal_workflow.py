from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


legitimacy_renewal_state: Dict[str, Any] = {
    "frozen": False,
    "frozen_at": None,
    "last_renewal_at": None,
    "last_renewal_status": "never_run",
    "last_reasons": [],
}


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def run_legitimacy_renewal(
    revalidation_result: Dict[str, Any],
    drift_result: Dict[str, Any],
    authority_decay_result: Dict[str, Any],
    freeze_execution_fn: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    reasons: List[Dict[str, Any]] = []

    legitimacy_status = str(revalidation_result.get("legitimacy_status", "UNKNOWN"))
    if legitimacy_status in {"DEGRADED", "INVALID"}:
        reasons.append(
            {
                "reason": "legitimacy_weakened",
                "severity": "high" if legitimacy_status == "INVALID" else "medium",
            }
        )

    if bool(drift_result.get("drift_detected", False)):
        reasons.append(
            {
                "reason": "assumption_drift_detected",
                "severity": "high"
                if any(item.get("severity") == "high" for item in drift_result.get("drift_alerts", []))
                else "medium",
            }
        )

    if bool(authority_decay_result.get("renewal_required", False)):
        reasons.append(
            {
                "reason": "authority_decay_detected",
                "severity": "high" if authority_decay_result.get("expired_authorities") else "medium",
            }
        )

    freeze_required = len(reasons) > 0
    freeze_result: Dict[str, Any] = {"status": "not_applied"}
    if freeze_required:
        if callable(freeze_execution_fn):
            try:
                freeze_result = dict(freeze_execution_fn() or {})
            except Exception as exc:
                freeze_result = {"status": "error", "error": str(exc)}
        legitimacy_renewal_state["frozen"] = True
        legitimacy_renewal_state["frozen_at"] = legitimacy_renewal_state.get("frozen_at") or _now_iso()
    else:
        legitimacy_renewal_state["frozen"] = False
        legitimacy_renewal_state["frozen_at"] = None

    required_actions: List[str] = []
    if freeze_required:
        required_actions.extend(
            [
                "require_governance_review",
                "require_constitutional_revalidation",
                "renew_authority_lineage",
            ]
        )
        if bool(drift_result.get("drift_detected", False)):
            required_actions.append("review_runtime_assumptions")

    legitimacy_renewal_state["last_renewal_at"] = _now_iso()
    legitimacy_renewal_state["last_renewal_status"] = "renewal_required" if freeze_required else "healthy"
    legitimacy_renewal_state["last_reasons"] = reasons

    return {
        "status": "ok",
        "renewal_required": freeze_required,
        "execution_frozen": bool(legitimacy_renewal_state.get("frozen", False)),
        "freeze_result": freeze_result,
        "authority_lineage_targets": authority_decay_result.get("renewal_required_for", []),
        "required_actions": required_actions,
        "reasons": reasons,
        "renewal_state": dict(legitimacy_renewal_state),
    }


def get_legitimacy_renewal_state() -> Dict[str, Any]:
    return dict(legitimacy_renewal_state)
