import json
import hashlib
from typing import Any, Callable, Dict, List


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_deterministic_replay_tests(
    replay_system_fn: Callable[[], Dict[str, Any]],
    verify_chain_fn: Callable[[str], Dict[str, Any]],
    validate_authority_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    check_system_invariants_fn: Callable[[Dict[str, Any], Dict[str, Any], Dict[str, Dict[str, Any]]], Dict[str, Any]],
) -> Dict[str, Any]:
    replay_a = replay_system_fn()
    replay_b = replay_system_fn()
    replay_a_hash = _stable_hash(replay_a)
    replay_b_hash = _stable_hash(replay_b)
    replay_consistent = replay_a_hash == replay_b_hash

    authority_a = validate_authority_fn(replay_a)
    authority_b = validate_authority_fn(replay_b)
    authority_consistent = _stable_hash(authority_a) == _stable_hash(authority_b)

    chain_results: Dict[str, Dict[str, Any]] = {}
    for job_id in replay_a.get("jobs", {}):
        chain_results[str(job_id)] = verify_chain_fn(str(job_id))
    chain_valid = all(bool(result.get("valid", False)) for result in chain_results.values())

    invariants = check_system_invariants_fn(replay_a, authority_a, chain_results)
    invariants_valid = bool(invariants.get("valid", False))

    return {
        "workflow_replay_validation": {
            "consistent": replay_consistent,
            "replay_a_hash": replay_a_hash,
            "replay_b_hash": replay_b_hash,
        },
        "execution_consistency_checks": {
            "chain_valid": chain_valid,
            "jobs_checked": len(chain_results),
        },
        "authority_replay_validation": {
            "consistent": authority_consistent,
            "authority_valid": bool(authority_a.get("valid", False)),
        },
        "audit_reproducibility_checks": {
            "invariants_valid": invariants_valid,
            "invariant_violations": len(invariants.get("violations", [])),
        },
        "overall_valid": replay_consistent and authority_consistent and chain_valid and invariants_valid,
    }
