SYSTEM_CONTRACT = {
    "guarantees": [
        "Any EXECUTED action was previously APPROVED.",
        "All events are immutably recorded in audit_log and persisted to the JSONL event store.",
        "Cryptographic integrity is verifiable via hash-chain validation per job.",
        "System state is fully reconstructable from the event stream via replay_system.",
        "Authority violations are always detectable via validate_authority.",
        "Global invariants are enforceable via check_system_invariants."
    ],
    "failures": [
        "Execution failure is not equivalent to system failure.",
        "Audit persistence failure is a system degradation state.",
        "Integrity failure is a system invalid state.",
        "Replay failure indicates partial system corruption."
    ],
    "assumptions": [
        "Single runtime instance without distributed consensus.",
        "Event ordering is deterministic per job.",
        "The JSONL event store is append-only and reliable."
    ],
    "invariants": [
        "EXECUTION_SAFETY_INVARIANT",
        "CAUSALITY_INVARIANT",
        "INTEGRITY_INVARIANT",
        "TEMPORAL_INVARIANT",
        "AUTHORITY_INVARIANT"
    ],
    "execution_semantics": {
        "model": "governed_event_sourced_runtime",
        "phases": ["PROPOSE", "APPROVE", "EXECUTE"],
        "policy": "No execution is permitted without explicit approval.",
        "truth_layers": [
            "replay_system (historical truth)",
            "verify_chain (cryptographic integrity truth)",
            "validate_authority (normative/legal truth)",
            "resolve_truth (canonical truth resolution)"
        ],
        "integrity_priority": [
            "CRYPTOGRAPHIC_INTEGRITY",
            "AUTHORITY_LEGALITY",
            "EXECUTION_HISTORY"
        ]
    }
}
