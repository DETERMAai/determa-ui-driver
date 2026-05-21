from typing import Any, Dict, List

CONSTITUTIONAL_PRINCIPLES: Dict[str, Any] = {
    "name": "DETERMA Constitutional Governance",
    "version": "1.0",
    "principles": [
        {
            "id": "CP-001",
            "name": "governance_non_bypass",
            "description": "No specification may permit governance bypass.",
        },
        {
            "id": "CP-002",
            "name": "approval_precedes_execution",
            "description": "Execution legitimacy must remain approval-bound.",
        },
        {
            "id": "CP-003",
            "name": "replay_guarantees_preserved",
            "description": "Replay determinism and reconstructability may not be weakened.",
        },
        {
            "id": "CP-004",
            "name": "authority_scope_bounded",
            "description": "Authority scope expansion must remain constitutionally constrained.",
        },
        {
            "id": "CP-005",
            "name": "invariants_preserved",
            "description": "Core system invariants must not be removed.",
        },
        {
            "id": "CP-006",
            "name": "autonomy_drift_bounded",
            "description": "Autonomy expansion must remain measurable and bounded.",
        },
    ],
    "constitutional_invariants": [
        "NO_GOVERNANCE_BYPASS",
        "EXECUTION_REQUIRES_APPROVAL",
        "REPLAY_RECONSTRUCTABLE",
        "AUTHORITY_SCOPE_BOUNDED",
        "SYSTEM_INVARIANTS_PRESERVED",
        "AUTONOMY_DRIFT_MEASURABLE",
    ],
    "override_rule": "constitutional_principles_override_canonical_specs",
}


def get_constitution() -> Dict[str, Any]:
    return dict(CONSTITUTIONAL_PRINCIPLES)
