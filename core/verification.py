from typing import Any, Callable, Dict


def run_canonical_verification(job_id: str, verification_provider: Callable[[str], Dict[str, Any]]) -> Dict[str, Any]:
    snapshot = verification_provider(job_id)
    governance_validation = snapshot.get("governance_validation", {}) if isinstance(snapshot, dict) else {}
    authority_valid = bool(governance_validation.get("authority_validation", {}).get("valid", False))
    invariants_valid = bool(governance_validation.get("invariant_validation", {}).get("valid", False))
    chain_valid = bool(governance_validation.get("chain_verification", {}).get("valid", False))
    truth_status = str(governance_validation.get("truth", {}).get("truth_status", "UNKNOWN"))

    return {
        "authority_valid": authority_valid,
        "invariants_valid": invariants_valid,
        "chain_valid": chain_valid,
        "truth_status": truth_status,
        "raw": snapshot,
    }
