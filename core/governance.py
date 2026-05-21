from typing import Any, Dict


def governance_precheck(job_id: str, pending_jobs: Dict[str, Dict[str, Any]], approved_jobs: set) -> Dict[str, Any]:
    if job_id not in pending_jobs:
        return {"allowed": False, "reason": "job_not_found"}
    if job_id not in approved_jobs:
        return {"allowed": False, "reason": "not_approved"}
    return {"allowed": True, "reason": "governance_passed"}
