from fastapi import FastAPI
from pydantic import BaseModel, Field
import pyautogui
import time
import base64
import hashlib
import json
import os
from io import BytesIO
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from threading import Lock
from system_contract import SYSTEM_CONTRACT
from ai_execution_adapter import call_ai_router
from llm_execution_layer import execute_llm_task, LLMExecutionError
from llm_routing_governance import get_llm_safety_status, get_model_status, select_best_llm_backend, update_model_trust
from perception_service import capture_screen, extract_screen_text
from ui_state_model import build_ui_state
from grounding_service import ground_action
from engineering_event_bus import publish_engineering_event, get_recent_engineering_events
from workflow_memory import create_workflow_session, get_workflow_state, update_workflow_state, workflow_sessions
from state_transition_engine import compare_expected_vs_observed, predict_expected_state
from recovery_engine import recover_from_failed_transition
from terminal_intelligence import analyze_terminal_output
from git_state_engine import detect_patch_application_state, get_git_state
from vscode_extension_bridge import get_editor_state
from terminal_stream_service import stream_terminal_output
from git_event_stream import get_recent_git_events, watch_git_events
from development_state_machine import (
    create_development_session,
    development_sessions,
    get_development_session,
    get_development_state,
    update_development_session,
)
from engineering_task_planner import infer_engineering_objective
from next_action_engine import decide_next_action
from development_policy_engine import validate_development_action
from escalation_manager import escalate_to_human, escalation_events
from event_priority_engine import prioritize_event
from governance_dashboard_service import get_governance_dashboard
from execution_trace_service import get_execution_trace
from approval_center import approve_action, get_pending_approvals, reject_action
from runtime_control_service import (
    force_escalation,
    get_runtime_control_state,
    is_worker_quarantined,
    pause_runtime,
    quarantine_worker,
    resume_runtime,
    stop_workflow,
)
from authority_token_service import generate_authority_token, validate_authority_token
from permission_scope_engine import get_scope_catalog, validate_scope
from execution_sandbox import validate_sandbox_execution
from trusted_approval_chain import build_trusted_approval_chain
from benchmark_task_suite import get_benchmark_suite, run_benchmark
from deterministic_replay_tests import run_deterministic_replay_tests
from failure_atlas import get_recent_failures, record_failure_mode
from red_team_scenarios import get_red_team_catalog, run_red_team_scenario
from runtime_metrics import (
    get_runtime_metrics_snapshot,
    record_benchmark_result,
    record_false_approval_attempt,
    record_red_team_result,
)
from autonomy_boundary_engine import get_autonomy_policy, validate_autonomy_boundary
from autonomy_friction_map import generate_autonomy_friction_map
from daily_operation_mode import (
    get_daily_operation_status,
    start_daily_operation_session,
    update_daily_operation_stats,
)
from operator_feedback_engine import generate_operator_trust_snapshot, record_operator_feedback
from operational_reduction_cycle import run_operational_reduction_cycle
from operational_trace_recorder import (
    append_operational_trace,
    export_workflow_session,
    get_recent_operational_traces,
    operational_traces,
)
from runtime_reduction_engine import build_runtime_reduction_report
from safe_autonomy_profile import get_safe_autonomy_profile, validate_safe_autonomy
from canonical_execution_binding import bind_execution_to_spec, validate_execution_binding
from canonicalization_engine import canonicalize_spec
from constitutional_principles import get_constitution
from constitutional_validation_engine import validate_constitutional_spec
from governance_inflation_detector import detect_governance_inflation
from governance_complexity_budget import evaluate_governance_complexity_budget
from governance_freeze_controller import evaluate_governance_freeze_status
from governance_mutation_firewall import validate_governance_mutation
from immutable_constitutional_core import IMMUTABLE_CONSTITUTIONAL_CORE
from legitimacy_clarity_engine import evaluate_legitimacy_clarity
from legitimacy_stability_monitor import evaluate_legitimacy_stability
from legitimacy_revalidation_engine import revalidate_legitimacy
from assumption_drift_detector import detect_assumption_drift
from temporal_authority_decay import evaluate_temporal_authority_decay
from legitimacy_renewal_workflow import get_legitimacy_renewal_state, run_legitimacy_renewal
from historical_legitimacy_replay import replay_historical_legitimacy
from semantic_compression_engine import generate_semantic_compression_report
from semantic_admissibility_engine import validate_semantic_admissibility
from semantic_entropy_metrics import measure_semantic_entropy
from self_modification_boundary_engine import evaluate_self_modification_boundary
from specification_reduction_engine import generate_spec_reduction_report
from constitutional_minimality_engine import evaluate_governance_minimality
from spec_lineage_engine import build_spec_lineage
from spec_registry import (
    SPEC_STATUS_CANONICAL,
    SPEC_STATUS_DRAFT,
    SPEC_STATUS_REJECTED,
    SPEC_STATUS_SUPERSEDED,
    SPEC_STATUS_UNDER_REVIEW,
    get_canonical_specs,
    get_spec,
    get_specs_history,
    register_spec,
    reject_spec,
    spec_registry,
    supersede_spec,
)
from spec_task_derivation_engine import derive_tasks_from_spec
from worker_manager import (
    WORKER_NAMES,
    get_workers_state,
    initialize_default_workers,
    stop_worker,
)
from runtime_event_loop import (
    configure_runtime_hooks,
    get_runtime_status,
    start_runtime_loop,
    stop_runtime_loop,
)
from core.authority import authority_gate
from core.event_runtime import emit_runtime_continuation
from core.execution import run_canonical_execution_pipeline
from core.governance import governance_precheck
from core.runtime_contract import RUNTIME_CONTRACT
from core.verification import run_canonical_verification

app = FastAPI()

class ExecuteRequest(BaseModel):
    action: str
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    canonical_spec_id: Optional[str] = None
    spec_scope: Optional[str] = "default"
    lineage_hash: Optional[str] = None
    derivation_hash: Optional[str] = None


class AITaskRequest(BaseModel):
    task_type: str
    input: str
    risk_level: str
    requires_verification: bool


class LLMExecuteRequest(BaseModel):
    task_type: str
    prompt: str
    context: dict = Field(default_factory=dict)
    risk_level: str
    requires_verification: bool
    backend_config: Optional[dict] = None


class ScreenActionRequest(BaseModel):
    action: str
    session_id: Optional[str] = None
    observe_delay_ms: int = 800


class WorkflowStartRequest(BaseModel):
    initial_step: str = "SCREEN_WORKFLOW"
    expected_state: str = ""


class WorkflowRecoverRequest(BaseModel):
    observe_delay_ms: int = 1000


class DailyOperationStartRequest(BaseModel):
    operator_tasks: List[str] = Field(default_factory=list)
    session_note: str = ""


class SpecProposeRequest(BaseModel):
    scope: str
    content: dict = Field(default_factory=dict)
    title: str = ""
    derived_from: Optional[str] = None
    proposed_by: str = "operator"
    governance_approvals: List[str] = Field(default_factory=list)
    status: str = SPEC_STATUS_DRAFT


class GovernanceMutationValidationRequest(BaseModel):
    old_spec_id: Optional[str] = None
    new_spec_id: Optional[str] = None
    old_spec: Optional[dict] = None
    new_spec: Optional[dict] = None
    mutation_context: dict = Field(default_factory=dict)


pending_jobs = {}
approved_jobs = set()
audit_log = []
job_counter = 0
EVENT_STORE_PATH = Path("/data/audit_log.jsonl")
execution_queue = []
job_locks = {}
queue_processing = False
queue_state_lock = Lock()
execution_contexts = {}
execution_proofs = {}
authority_tokens = {}
ai_task_counter = 0
llm_task_counter = 0
screen_action_jobs = {}
benchmark_runs = []
red_team_runs = []
replay_validation_runs = []
reduction_reports = []
SYSTEM_PLANES = {
    "control": [],
    "execution": [],
    "verification": []
}
ARCHITECTURE_LAYOUT = {
        "core": [
        "core/governance.py",
        "core/authority.py",
        "core/execution.py",
        "core/verification.py",
        "core/event_runtime.py",
        "core/runtime_contract.py",
        "spec_registry.py",
        "canonicalization_engine.py",
        "semantic_admissibility_engine.py",
        "spec_task_derivation_engine.py",
        "spec_lineage_engine.py",
        "canonical_execution_binding.py",
        "constitutional_principles.py",
        "constitutional_validation_engine.py",
        "specification_reduction_engine.py",
        "governance_inflation_detector.py",
        "constitutional_lineage_guard.py",
        "semantic_compression_engine.py",
        "constitutional_minimality_engine.py",
        "governance_complexity_budget.py",
        "semantic_entropy_metrics.py",
        "legitimacy_clarity_engine.py",
        "immutable_constitutional_core.py",
        "governance_mutation_firewall.py",
        "self_modification_boundary_engine.py",
            "governance_freeze_controller.py",
            "legitimacy_stability_monitor.py",
            "legitimacy_revalidation_engine.py",
            "assumption_drift_detector.py",
            "temporal_authority_decay.py",
            "legitimacy_renewal_workflow.py",
            "historical_legitimacy_replay.py",
        ],
    "extensions": [
        "extensions/perception_extension.py",
        "autonomy_boundary_engine.py",
        "safe_autonomy_profile.py",
    ],
    "integrations": [
        "integrations/ide_integration.py",
        "integrations/terminal_integration.py",
        "integrations/git_integration.py",
    ],
    "operators": [
        "operators/governance_operator.py",
        "operational_trace_recorder.py",
        "autonomy_friction_map.py",
        "daily_operation_mode.py",
        "operator_feedback_engine.py",
        "operational_reduction_cycle.py",
        "runtime_reduction_engine.py",
        "benchmark_task_suite.py",
        "failure_atlas.py",
        "runtime_metrics.py",
        "deterministic_replay_tests.py",
        "red_team_scenarios.py",
    ],
    "ui": [
        "ui/api_surface.py",
        "main.py",
    ],
}

EPISTEMIC_PRIORITY_ORDER = [
    "adversarial_validation",
    "cryptographic_integrity",
    "system_invariants",
    "authority_validation",
    "execution_proof_layer",
    "replay_system",
    "audit_log",
    "execution_context"
]


def _register_system_planes():
    global SYSTEM_PLANES

    SYSTEM_PLANES = {
        "control": [
            "health",
            "startup_restore",
            "propose",
            "approve",
            "ai_execute",
            "llm_execute",
            "get_screen_state",
            "_create_or_get_screen_action_job",
            "screen_act",
            "workflow_start",
            "workflow_recover",
            "_build_development_intelligence",
            "_run_engineering_governance",
            "_runtime_perception_worker",
            "_runtime_terminal_worker",
            "_runtime_git_worker",
            "_runtime_reasoning_worker",
            "_runtime_execution_worker",
            "_runtime_verification_worker",
            "_ensure_runtime_hooks_configured",
            "_start_runtime_with_workers",
            "_stop_runtime_with_workers",
            "_runtime_queue_state_snapshot",
            "_approval_backlog_snapshot",
            "_governance_dashboard_snapshot",
            "_latest_session_ids",
            "_operational_benchmark_state_provider",
            "_run_replay_validation_suite",
            "_red_team_evaluator",
            "_operational_reduction_report_snapshot",
            "_daily_operation_start_payload",
            "_daily_operation_update_stats",
            "_resolve_canonical_spec_for_request",
            "_build_temporal_legitimacy_signals",
            "_build_temporal_legitimacy_assumptions",
            "_bind_pending_job_to_spec",
            "_issue_authority_token_for_job",
            "_build_job_security_context",
            "_validate_execution_security",
            "_security_verification_snapshot",
            "_summarize_ui_state",
            "_is_ai_event_type",
            "_build_control_plane_verification_state",
            "_emit_llm_backend_failure_events",
            "_extract_llm_model_id",
            "select_best_llm_backend",
            "update_model_trust",
            "get_model_status",
            "get_llm_safety_status",
            "validate_authority",
            "check_system_invariants",
            "evaluate_governance_freeze_status",
            "evaluate_self_modification_boundary",
            "validate_governance_mutation",
            "evaluate_legitimacy_stability",
            "_resolve_truth_from_layers",
            "resolve_truth",
            "resolve_final_system_truth",
            "_register_system_planes",
            "validate_authority_endpoint",
            "truth_endpoint",
            "validate_system_endpoint",
            "final_truth_endpoint",
            "system_contract_endpoint",
            "ai_execute_endpoint",
            "llm_execute_endpoint",
            "llm_models_status_endpoint",
            "llm_safety_status_endpoint",
            "screen_state_endpoint",
            "screen_act_endpoint",
            "workflow_start_endpoint",
            "workflow_get_endpoint",
            "workflow_recover_endpoint",
            "development_state_endpoint",
            "development_session_endpoint",
            "engineering_objective_endpoint",
            "engineering_next_action_endpoint",
            "engineering_policy_status_endpoint",
            "editor_state_endpoint",
            "terminal_stream_status_endpoint",
            "git_events_recent_endpoint",
            "runtime_status_endpoint",
            "runtime_workers_endpoint",
            "runtime_start_endpoint",
            "runtime_stop_endpoint",
            "governance_dashboard_endpoint",
            "session_trace_endpoint",
            "pending_approvals_endpoint",
            "approval_action_endpoint",
            "reject_action_endpoint",
            "runtime_pause_endpoint",
            "runtime_resume_endpoint",
            "runtime_stop_workflow_endpoint",
            "runtime_quarantine_worker_endpoint",
            "security_scopes_endpoint",
            "security_authority_endpoint",
            "security_approval_chain_endpoint",
            "runtime_metrics_endpoint",
            "recent_failures_endpoint",
            "run_benchmark_endpoint",
            "run_red_team_endpoint",
            "operations_friction_endpoint",
            "operations_traces_recent_endpoint",
            "operations_reduction_report_endpoint",
            "operations_daily_start_endpoint",
            "operations_daily_status_endpoint",
            "operations_trust_endpoint",
            "operations_reduction_cycle_endpoint",
            "specs_propose_endpoint",
            "specs_canonicalize_endpoint",
            "specs_current_endpoint",
            "specs_history_endpoint",
            "specs_lineage_endpoint",
            "specs_derive_tasks_endpoint",
            "constitution_endpoint",
            "constitution_validate_endpoint",
            "specs_reduction_report_endpoint",
            "specs_governance_inflation_endpoint",
            "governance_entropy_endpoint",
            "governance_minimality_endpoint",
            "governance_complexity_budget_endpoint",
            "governance_clarity_endpoint",
            "governance_stability_endpoint",
            "governance_freeze_status_endpoint",
            "governance_mutation_validate_endpoint",
            "legitimacy_revalidate_endpoint",
            "legitimacy_drift_endpoint",
            "legitimacy_authority_decay_endpoint",
            "legitimacy_renew_endpoint",
            "legitimacy_replay_endpoint",
            "system_architecture_endpoint"
        ],
        "execution": [
            "screenshot",
            "execute_action",
            "execute_llm_task",
            "get_execution_context",
            "process_execution_queue",
            "execute_job",
            "execute_directly_blocked",
            "process_queue_endpoint",
            "execution_context_endpoint",
            "initialize_default_workers",
            "start_runtime_loop",
            "stop_runtime_loop"
        ],
        "verification": [
            "persist_event",
            "_rebuild_runtime_state_from_audit",
            "load_event_store",
            "emit_event",
            "verify_chain",
            "replay_system",
            "_stable_serialize",
            "_stable_hash",
            "generate_execution_proof",
            "_derive_audit_job_state",
            "adversarial_validate_system",
            "stream_terminal_output",
            "watch_git_events",
            "get_recent_git_events",
            "prioritize_event",
            "get_recent_engineering_events",
            "get_runtime_status",
            "get_workers_state",
            "generate_authority_token",
            "validate_authority_token",
            "validate_scope",
            "validate_sandbox_execution",
            "build_trusted_approval_chain",
            "validate_execution_binding",
            "derive_tasks_from_spec",
            "build_spec_lineage",
            "validate_semantic_admissibility",
            "validate_constitutional_spec",
            "generate_spec_reduction_report",
            "detect_governance_inflation",
            "generate_semantic_compression_report",
            "evaluate_governance_minimality",
            "evaluate_governance_complexity_budget",
            "measure_semantic_entropy",
            "evaluate_legitimacy_clarity",
            "evaluate_governance_freeze_status",
            "validate_governance_mutation",
            "evaluate_legitimacy_stability",
            "revalidate_legitimacy",
            "detect_assumption_drift",
            "evaluate_temporal_authority_decay",
            "run_legitimacy_renewal",
            "replay_historical_legitimacy",
            "get_audit",
            "verify_chain_endpoint",
            "replay_system_endpoint",
            "system_restore_endpoint",
            "execution_proof_endpoint",
            "adversarial_validate_endpoint"
        ]
    }

    for plane_name, function_names in SYSTEM_PLANES.items():
        for fn_name in function_names:
            fn = globals().get(fn_name)
            if callable(fn):
                setattr(fn, "__plane__", plane_name)


def screenshot():
    img = pyautogui.screenshot()
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def persist_event(event: dict):
    try:
        EVENT_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n"
        with open(EVENT_STORE_PATH, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        return True
    except Exception:
        # Failure-safe mode: keep in-memory event as source of truth.
        return False


def _rebuild_runtime_state_from_audit():
    global pending_jobs, approved_jobs, authority_tokens, job_counter, execution_queue, job_locks, queue_processing, execution_contexts, execution_proofs, screen_action_jobs

    rebuilt_pending_jobs = {}
    rebuilt_approved_jobs = set()
    rebuilt_authority_tokens = {}
    max_job_id = 0

    indexed_events = list(enumerate(audit_log))
    sorted_events = sorted(
        indexed_events,
        key=lambda pair: (datetime.fromisoformat(pair[1]["timestamp"].replace("Z", "")), pair[0])
    )

    for _, event in sorted_events:
        job_id = str(event.get("job_id"))
        event_type = event.get("event_type")

        try:
            numeric_id = int(job_id)
            if numeric_id > max_job_id:
                max_job_id = numeric_id
        except Exception:
            pass

        if event_type == "PROPOSED":
            data = event.get("data", {})
            request = data.get("request", {}) if isinstance(data, dict) else {}
            rebuilt_pending_jobs[job_id] = request
        elif event_type == "APPROVED":
            rebuilt_approved_jobs.add(job_id)
        elif event_type == "AUTHORITY_TOKEN_ISSUED":
            data = event.get("data", {})
            token = data.get("token", {}) if isinstance(data, dict) else {}
            if isinstance(token, dict):
                rebuilt_authority_tokens[job_id] = token

    pending_jobs = rebuilt_pending_jobs
    approved_jobs = rebuilt_approved_jobs
    authority_tokens = rebuilt_authority_tokens
    job_counter = max_job_id
    with queue_state_lock:
        execution_queue = []
        job_locks = {}
        queue_processing = False
    execution_contexts = {}
    execution_proofs = {}
    screen_action_jobs = {}


def load_event_store():
    global audit_log, pending_jobs, approved_jobs, authority_tokens, job_counter

    if not EVENT_STORE_PATH.exists():
        system_state = replay_system()
        return {
            "restored_event_count": len(audit_log),
            "system_state": system_state
        }

    old_audit_log = list(audit_log)
    old_pending_jobs = dict(pending_jobs)
    old_approved_jobs = set(approved_jobs)
    old_authority_tokens = dict(authority_tokens)
    old_job_counter = job_counter

    try:
        loaded_events = []
        with open(EVENT_STORE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                loaded_events.append(json.loads(stripped))

        audit_log = loaded_events
        _rebuild_runtime_state_from_audit()
        system_state = replay_system()
        return {
            "restored_event_count": len(audit_log),
            "system_state": system_state
        }
    except Exception:
        # Failure-safe mode: keep existing in-memory log and continue operating.
        audit_log = old_audit_log
        pending_jobs = old_pending_jobs
        approved_jobs = old_approved_jobs
        authority_tokens = old_authority_tokens
        job_counter = old_job_counter
        system_state = replay_system()
        return {
            "restored_event_count": len(audit_log),
            "system_state": system_state
        }


def emit_event(event_type: str, job_id: str, data: dict):
    timestamp = datetime.utcnow().isoformat() + "Z"
    event_id = hashlib.sha256(f"{job_id}{event_type}{timestamp}".encode()).hexdigest()
    prev_hash = "GENESIS"
    for event in reversed(audit_log):
        if event["job_id"] == job_id:
            prev_hash = event["event_hash"]
            break
    event_hash = hashlib.sha256(f"{event_type}{job_id}{timestamp}{prev_hash}".encode()).hexdigest()
    event = {
        "event_id": event_id,
        "job_id": job_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "data": data,
        "prev_hash": prev_hash,
        "event_hash": event_hash
    }
    audit_log.append(event)
    persist_event(event)
    return event


def verify_chain(job_id: str):
    job_events = [event for event in audit_log if event["job_id"] == job_id]
    expected_prev_hash = "GENESIS"

    for event in job_events:
        if event.get("prev_hash") != expected_prev_hash:
            return {
                "job_id": job_id,
                "valid": False,
                "broken_at_event_id": event.get("event_id"),
                "reason": "prev_hash_mismatch"
            }

        recomputed_hash = hashlib.sha256(
            f"{event.get('event_type')}{event.get('job_id')}{event.get('timestamp')}{event.get('prev_hash')}".encode()
        ).hexdigest()

        if event.get("event_hash") != recomputed_hash:
            return {
                "job_id": job_id,
                "valid": False,
                "broken_at_event_id": event.get("event_id"),
                "reason": "event_hash_mismatch"
            }

        expected_prev_hash = event.get("event_hash")

    return {
        "job_id": job_id,
        "valid": True
    }


def replay_system():
    system_state = {
        "jobs": {},
        "execution_order": [],
        "anomalies": []
    }
    proposed_jobs = set()

    indexed_events = list(enumerate(audit_log))
    sorted_events = sorted(
        indexed_events,
        key=lambda pair: (datetime.fromisoformat(pair[1]["timestamp"].replace("Z", "")), pair[0])
    )

    for _, event in sorted_events:
        job_id = event["job_id"]
        event_type = event["event_type"]

        if job_id not in system_state["jobs"]:
            system_state["jobs"][job_id] = {
                "status": "UNKNOWN",
                "approved": False,
                "executed": False,
                "last_event_type": None,
                "last_event_hash": None
            }

        job_state = system_state["jobs"][job_id]
        last_event_type = job_state["last_event_type"]

        allowed_prev = {
            "PROPOSED": {None},
            "APPROVED": {"PROPOSED", "BLOCKED"},
            "EXECUTION_STARTED": {"APPROVED", "EXECUTED", "EXECUTION_FAILED", "BLOCKED"},
            "EXECUTED": {"EXECUTION_STARTED"},
            "EXECUTION_FAILED": {"EXECUTION_STARTED"},
            "BLOCKED": {None, "PROPOSED", "APPROVED", "EXECUTION_STARTED", "EXECUTED", "EXECUTION_FAILED", "BLOCKED"}
        }

        if event_type in allowed_prev and last_event_type not in allowed_prev[event_type]:
            system_state["anomalies"].append(
                {
                    "job_id": job_id,
                    "event_id": event.get("event_id"),
                    "reason": "out_of_order_transition",
                    "from_event_type": last_event_type,
                    "to_event_type": event_type
                }
            )

        if event_type == "EXECUTION_STARTED" and job_id not in proposed_jobs:
            system_state["anomalies"].append(
                {
                    "job_id": job_id,
                    "event_id": event.get("event_id"),
                    "reason": "execution_started_without_proposed"
                }
            )

        if event_type == "EXECUTED" and not job_state["approved"]:
            system_state["anomalies"].append(
                {
                    "job_id": job_id,
                    "event_id": event.get("event_id"),
                    "reason": "executed_without_approved"
                }
            )

        if event_type == "PROPOSED":
            proposed_jobs.add(job_id)
            job_state["status"] = "PENDING_APPROVAL"
            job_state["approved"] = False
            job_state["executed"] = False
        elif event_type == "APPROVED":
            job_state["status"] = "APPROVED"
            job_state["approved"] = True
        elif event_type == "EXECUTION_STARTED":
            job_state["status"] = "EXECUTION_STARTED"
            system_state["execution_order"].append(job_id)
        elif event_type == "EXECUTED":
            job_state["status"] = "EXECUTED"
            job_state["executed"] = True
        elif event_type == "EXECUTION_FAILED":
            job_state["status"] = "EXECUTION_FAILED"
            job_state["executed"] = False
        elif event_type == "BLOCKED":
            job_state["status"] = "BLOCKED"

        job_state["last_event_type"] = event_type
        job_state["last_event_hash"] = event.get("event_hash")

    for replay_job_id in system_state["jobs"]:
        chain_result = verify_chain(replay_job_id)
        if not chain_result.get("valid"):
            system_state["anomalies"].append(
                {
                    "job_id": replay_job_id,
                    "event_id": chain_result.get("broken_at_event_id"),
                    "reason": chain_result.get("reason", "broken_hash_chain")
                }
            )

    return system_state


def validate_authority(system_state: dict):
    violations = []
    indexed_events = list(enumerate(audit_log))
    sorted_events = sorted(
        indexed_events,
        key=lambda pair: (datetime.fromisoformat(pair[1]["timestamp"].replace("Z", "")), pair[0])
    )

    for job_id in system_state.get("jobs", {}):
        job_events = [event for _, event in sorted_events if event.get("job_id") == job_id]
        seen_proposed = False
        seen_approved = False
        seen_execution_started = False

        for event in job_events:
            event_type = event.get("event_type")

            if event_type == "PROPOSED":
                seen_proposed = True
            elif event_type == "APPROVED":
                if not seen_proposed:
                    violations.append(
                        {
                            "job_id": job_id,
                            "event_id": event.get("event_id"),
                            "event_type": event_type,
                            "reason": "ILLEGAL_TRANSITION"
                        }
                    )
                seen_approved = True
            elif event_type == "EXECUTION_STARTED":
                if not seen_approved:
                    violations.append(
                        {
                            "job_id": job_id,
                            "event_id": event.get("event_id"),
                            "event_type": event_type,
                            "reason": "ILLEGAL_TRANSITION"
                        }
                    )
                seen_execution_started = True
            elif event_type == "EXECUTED":
                if not seen_execution_started:
                    violations.append(
                        {
                            "job_id": job_id,
                            "event_id": event.get("event_id"),
                            "event_type": event_type,
                            "reason": "ILLEGAL_TRANSITION"
                        }
                    )
            elif event_type == "EXECUTION_FAILED":
                if not seen_execution_started:
                    violations.append(
                        {
                            "job_id": job_id,
                            "event_id": event.get("event_id"),
                            "event_type": event_type,
                            "reason": "ILLEGAL_TRANSITION"
                        }
                    )
            elif event_type == "BLOCKED":
                continue
            else:
                violations.append(
                    {
                        "job_id": job_id,
                        "event_id": event.get("event_id"),
                        "event_type": event_type,
                        "reason": "ILLEGAL_TRANSITION"
                    }
                )

    return {
        "valid": len(violations) == 0,
        "violations": violations
    }


def _resolve_truth_from_layers(job_id: str, system_state: dict, authority_validation: dict, chain_verification: dict):
    jobs = system_state.get("jobs", {})
    job_state = jobs.get(
        job_id,
        {
            "status": "UNKNOWN",
            "approved": False,
            "executed": False
        }
    )

    conflicts = []

    if not chain_verification.get("valid", False):
        conflicts.append(
            {
                "layer": "integrity",
                "issue": chain_verification.get("reason", "chain_verification_failed"),
                "severity": "high"
            }
        )

    authority_violations = [
        violation for violation in authority_validation.get("violations", [])
        if violation.get("job_id") == job_id
    ]
    for violation in authority_violations:
        conflicts.append(
            {
                "layer": "authority",
                "issue": violation.get("reason", "ILLEGAL_TRANSITION"),
                "severity": "medium"
            }
        )

    execution_anomalies = [
        anomaly for anomaly in system_state.get("anomalies", [])
        if anomaly.get("job_id") == job_id
        and anomaly.get("reason") not in {"prev_hash_mismatch", "event_hash_mismatch", "broken_hash_chain"}
    ]
    for anomaly in execution_anomalies:
        conflicts.append(
            {
                "layer": "execution",
                "issue": anomaly.get("reason", "execution_anomaly"),
                "severity": "low"
            }
        )

    if not chain_verification.get("valid", False):
        truth_status = "INVALID"
    elif authority_violations:
        truth_status = "DEGRADED"
    elif execution_anomalies:
        truth_status = "DEGRADED"
    else:
        truth_status = "VALID"

    return {
        "job_id": job_id,
        "truth_status": truth_status,
        "final_state": {
            "status": job_state.get("status", "UNKNOWN"),
            "approved": bool(job_state.get("approved", False)),
            "executed": bool(job_state.get("executed", False))
        },
        "conflicts": conflicts
    }


def resolve_truth(
    job_id: str,
    system_state: Optional[dict] = None,
    authority_validation: Optional[dict] = None,
    chain_verification: Optional[dict] = None
):
    if system_state is None:
        system_state = replay_system()
    if chain_verification is None:
        chain_verification = verify_chain(job_id)
    if authority_validation is None:
        authority_validation = validate_authority(system_state)
    return _resolve_truth_from_layers(job_id, system_state, authority_validation, chain_verification)


def check_system_invariants(system_state: dict, authority_validation: dict, chain_results: dict):
    violations = []

    for job_id, chain_result in chain_results.items():
        if not chain_result.get("valid", False):
            violations.append(
                {
                    "invariant": "INTEGRITY_INVARIANT",
                    "job_id": job_id,
                    "severity": "critical",
                    "description": f"Broken hash chain: {chain_result.get('reason', 'unknown_reason')}"
                }
            )

    indexed_events = list(enumerate(audit_log))
    sorted_events = sorted(
        indexed_events,
        key=lambda pair: (datetime.fromisoformat(pair[1]["timestamp"].replace("Z", "")), pair[0])
    )

    events_by_job = {}
    for _, event in sorted_events:
        events_by_job.setdefault(event.get("job_id"), []).append(event)

    for job_id, job_events in events_by_job.items():
        seen_proposed = False
        seen_approved = False
        seen_execution_started = False

        for event in job_events:
            event_type = event.get("event_type")

            if event_type == "PROPOSED":
                seen_proposed = True
            elif event_type == "APPROVED":
                if not seen_proposed:
                    violations.append(
                        {
                            "invariant": "AUTHORITY_INVARIANT",
                            "job_id": job_id,
                            "severity": "high",
                            "description": "APPROVED occurred before PROPOSED."
                        }
                    )
                seen_approved = True
            elif event_type == "EXECUTION_STARTED":
                if not seen_approved:
                    violations.append(
                        {
                            "invariant": "CAUSALITY_INVARIANT",
                            "job_id": job_id,
                            "severity": "critical",
                            "description": "EXECUTION_STARTED occurred without prior APPROVED."
                        }
                    )
                seen_execution_started = True
            elif event_type == "EXECUTED":
                if not seen_approved:
                    violations.append(
                        {
                            "invariant": "EXECUTION_SAFETY_INVARIANT",
                            "job_id": job_id,
                            "severity": "critical",
                            "description": "EXECUTED occurred without prior APPROVED."
                        }
                    )
                if not seen_execution_started:
                    violations.append(
                        {
                            "invariant": "CAUSALITY_INVARIANT",
                            "job_id": job_id,
                            "severity": "critical",
                            "description": "EXECUTED occurred without prior EXECUTION_STARTED."
                        }
                    )

    for job_id in events_by_job:
        job_events_in_ledger_order = [event for event in audit_log if event.get("job_id") == job_id]
        last_timestamp = None
        for event in job_events_in_ledger_order:
            try:
                current_timestamp = datetime.fromisoformat(event.get("timestamp", "").replace("Z", ""))
            except Exception:
                violations.append(
                    {
                        "invariant": "TEMPORAL_INVARIANT",
                        "job_id": job_id,
                        "severity": "medium",
                        "description": "Invalid timestamp format detected in audit ledger."
                    }
                )
                break
            if last_timestamp is not None and current_timestamp < last_timestamp:
                violations.append(
                    {
                        "invariant": "TEMPORAL_INVARIANT",
                        "job_id": job_id,
                        "severity": "medium",
                        "description": "Event timestamp moved backwards in ledger order."
                    }
                )
                break
            last_timestamp = current_timestamp

    for violation in authority_validation.get("violations", []):
        if violation.get("event_type") == "APPROVED":
            violations.append(
                {
                    "invariant": "AUTHORITY_INVARIANT",
                    "job_id": violation.get("job_id"),
                    "severity": "high",
                    "description": "Authority layer detected APPROVED without PROPOSED."
                }
            )
        elif violation.get("event_type") in {"EXECUTION_STARTED", "EXECUTED", "EXECUTION_FAILED"}:
            violations.append(
                {
                    "invariant": "CAUSALITY_INVARIANT",
                    "job_id": violation.get("job_id"),
                    "severity": "critical",
                    "description": f"Authority layer detected illegal transition at {violation.get('event_type')}."
                }
            )

    return {
        "valid": len(violations) == 0,
        "violations": violations
    }


def _stable_serialize(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _stable_hash(value):
    return hashlib.sha256(_stable_serialize(value).encode()).hexdigest()


def generate_execution_proof(
    job_id: str,
    system_state: Optional[dict] = None,
    chain_verification: Optional[dict] = None,
    authority_validation: Optional[dict] = None,
    invariant_validation: Optional[dict] = None
):
    if system_state is None:
        system_state = replay_system()
    if chain_verification is None:
        chain_verification = verify_chain(job_id)
    if authority_validation is None:
        authority_validation = validate_authority(system_state)
    if invariant_validation is None:
        chain_results = {
            replay_job_id: verify_chain(replay_job_id)
            for replay_job_id in system_state.get("jobs", {})
        }
        invariant_validation = check_system_invariants(system_state, authority_validation, chain_results)

    execution_context = execution_contexts.get(job_id, {})
    relevant_audit_events = [event for event in audit_log if event.get("job_id") == job_id]
    authority_for_job = {
        "valid": authority_validation.get("valid", False),
        "violations": [
            violation for violation in authority_validation.get("violations", [])
            if violation.get("job_id") == job_id
        ]
    }
    invariant_for_job = {
        "valid": invariant_validation.get("valid", False),
        "violations": [
            violation for violation in invariant_validation.get("violations", [])
            if violation.get("job_id") == job_id
        ]
    }

    context_hash = _stable_hash(execution_context)
    audit_hash = _stable_hash(relevant_audit_events)
    chain_hash = _stable_hash(chain_verification)
    authority_hash = _stable_hash(authority_for_job)
    invariant_hash = _stable_hash(invariant_for_job)

    proof_payload = {
        "job_id": job_id,
        "execution_context": execution_context,
        "relevant_audit_events": relevant_audit_events,
        "chain_verification": chain_verification,
        "authority_validation": authority_for_job,
        "invariant_validation": invariant_for_job
    }

    execution_proof = _stable_hash(proof_payload)

    job_authority_violations = authority_for_job.get("violations", [])
    job_invariant_violations = invariant_for_job.get("violations", [])
    determinism_status = "VALID"
    if (
        not chain_verification.get("valid", False)
        or job_authority_violations
        or job_invariant_violations
    ):
        determinism_status = "INVALID"

    return {
        "job_id": job_id,
        "execution_proof": execution_proof,
        "determinism_status": determinism_status,
        "components": {
            "context_hash": context_hash,
            "audit_hash": audit_hash,
            "chain_hash": chain_hash,
            "authority_hash": authority_hash,
            "invariant_hash": invariant_hash
        }
    }


def _derive_audit_job_state(job_id: str):
    indexed_events = list(enumerate(audit_log))
    sorted_events = sorted(
        indexed_events,
        key=lambda pair: (datetime.fromisoformat(pair[1]["timestamp"].replace("Z", "")), pair[0])
    )
    job_events = [event for _, event in sorted_events if event.get("job_id") == job_id]

    state = {
        "status": "UNKNOWN",
        "approved": False,
        "executed": False
    }

    for event in job_events:
        event_type = event.get("event_type")
        if event_type == "PROPOSED":
            state["status"] = "PENDING_APPROVAL"
            state["approved"] = False
            state["executed"] = False
        elif event_type == "APPROVED":
            state["status"] = "APPROVED"
            state["approved"] = True
        elif event_type == "EXECUTION_STARTED":
            state["status"] = "EXECUTION_STARTED"
        elif event_type == "EXECUTED":
            state["status"] = "EXECUTED"
            state["executed"] = True
        elif event_type == "EXECUTION_FAILED":
            state["status"] = "EXECUTION_FAILED"
            state["executed"] = False
        elif event_type == "BLOCKED":
            state["status"] = "BLOCKED"

    return state, job_events


def _is_ai_event_type(event_type: str):
    return (
        event_type == "PROPOSED_AI_TASK"
        or event_type.startswith("AI_")
        or event_type == "PROPOSED_LLM_TASK"
        or event_type.startswith("LLM_")
    )


def _build_control_plane_verification_state(system_state: dict):
    ai_jobs = set()
    for event in audit_log:
        event_type = event.get("event_type", "")
        if _is_ai_event_type(event_type):
            ai_jobs.add(str(event.get("job_id")))

    filtered_jobs = {
        job_id: job_state
        for job_id, job_state in system_state.get("jobs", {}).items()
        if str(job_id) not in ai_jobs
    }
    filtered_execution_order = [
        job_id for job_id in system_state.get("execution_order", [])
        if str(job_id) not in ai_jobs
    ]
    filtered_anomalies = [
        anomaly for anomaly in system_state.get("anomalies", [])
        if str(anomaly.get("job_id")) not in ai_jobs
    ]

    return {
        "jobs": filtered_jobs,
        "execution_order": filtered_execution_order,
        "anomalies": filtered_anomalies
    }


def ai_execute(task: AITaskRequest):
    global ai_task_counter

    with queue_state_lock:
        ai_task_counter += 1
        job_id = f"ai-{ai_task_counter}"

    task_payload = task.model_dump() if hasattr(task, "model_dump") else task.dict()
    emit_event("PROPOSED_AI_TASK", job_id, {"task": task_payload})

    try:
        router_response = call_ai_router(task_payload)
    except Exception as exc:
        emit_event("BLOCKED", job_id, {"reason": "ai_router_error", "error": str(exc)})
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(exc)
        }

    emit_event(
        "AI_EXECUTED",
        job_id,
        {
            "model_used": router_response.get("model_used"),
            "cost": router_response.get("cost"),
            "latency_ms": router_response.get("latency_ms"),
            "output_hash": hashlib.sha256(str(router_response.get("output", "")).encode()).hexdigest()
        }
    )

    system_state = replay_system()
    control_verification_state = _build_control_plane_verification_state(system_state)
    authority_validation = validate_authority(control_verification_state)
    chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in control_verification_state.get("jobs", {})
    }
    invariant_validation = check_system_invariants(
        control_verification_state,
        authority_validation,
        chain_results
    )

    verification_result = {
        "authority_validation": authority_validation,
        "invariant_validation": invariant_validation
    }

    if task.requires_verification:
        chain_verification = verify_chain(job_id)
        execution_proof_result = generate_execution_proof(
            job_id,
            system_state,
            chain_verification,
            authority_validation,
            invariant_validation
        )
        adversarial_result = adversarial_validate_system(
            job_id,
            system_state,
            chain_verification,
            authority_validation,
            invariant_validation,
            execution_proof_result
        )
        verification_result["adversarial_validation"] = adversarial_result
        verification_result["execution_proof"] = execution_proof_result

        if adversarial_result.get("adversarial_status") != "CLEAN":
            return {
                "status": "rejected",
                "job_id": job_id,
                "result": router_response,
                "verification": verification_result,
                "error": "adversarial_validation_failed"
            }

    if not authority_validation.get("valid", False):
        return {
            "status": "rejected",
            "job_id": job_id,
            "result": router_response,
            "verification": verification_result,
            "error": "authority_validation_failed"
        }

    if not invariant_validation.get("valid", False):
        return {
            "status": "rejected",
            "job_id": job_id,
            "result": router_response,
            "verification": verification_result,
            "error": "invariant_validation_failed"
        }

    return {
        "status": "success",
        "job_id": job_id,
        "result": router_response,
        "verification": verification_result
    }


def _emit_llm_backend_failure_events(job_id: str, failures: list):
    for failure in failures:
        emit_event(
            "LLM_BACKEND_FAILED",
            job_id,
            {
                "backend": failure.get("backend"),
                "error": failure.get("error")
            }
        )


def _extract_llm_model_id(llm_result: dict):
    raw_response = llm_result.get("raw_response", {}) if isinstance(llm_result, dict) else {}
    if isinstance(raw_response, dict):
        routing = raw_response.get("routing", {})
        if isinstance(routing, dict):
            chosen_model_id = routing.get("chosen_model_id")
            if chosen_model_id:
                return str(chosen_model_id)
    model_used = llm_result.get("model_used") if isinstance(llm_result, dict) else None
    if model_used:
        return str(model_used)
    return ""


def get_screen_state():
    capture_metadata = capture_screen()
    ocr_result = extract_screen_text(capture_metadata.get("image_path", ""))
    ui_state = build_ui_state(ocr_result, capture_metadata)
    return {
        "capture": capture_metadata,
        "ocr": ocr_result,
        "ui_state": ui_state
    }


def _summarize_ui_state(ui_state: dict):
    if not isinstance(ui_state, dict):
        return "ui_state_unavailable"
    actions = list(ui_state.get("detected_actions", []))
    button_labels = []
    for button in ui_state.get("buttons", [])[:5]:
        label = str(button.get("text", "")).strip()
        if label:
            button_labels.append(label)
    return f"actions={actions};buttons={button_labels}"


def _build_development_intelligence(session_id: str, ui_state: dict):
    safe_ui_state = ui_state if isinstance(ui_state, dict) else {}
    editor_state = get_editor_state(safe_ui_state)

    native_stdout = str(editor_state.get("terminal_stdout", ""))
    native_stderr = str(editor_state.get("terminal_stderr", ""))
    native_command = str(editor_state.get("terminal_command", ""))
    native_command_status = str(editor_state.get("terminal_command_status", ""))
    if native_stdout.strip() or native_stderr.strip() or native_command.strip() or native_command_status.strip():
        terminal_snapshot = stream_terminal_output(
            stdout=native_stdout if native_stdout.strip() else None,
            stderr=native_stderr if native_stderr.strip() else None,
            command=native_command if native_command.strip() else None,
            command_status=native_command_status if native_command_status.strip() else None,
        )
        terminal_text = f"{native_stdout}\n{native_stderr}".strip()
    else:
        terminal_lines = safe_ui_state.get("terminal_lines", [])
        terminal_text = "\n".join(str(line) for line in terminal_lines)
        if terminal_text.strip():
            terminal_snapshot = stream_terminal_output(stdout=terminal_text)
        else:
            terminal_snapshot = stream_terminal_output()
    terminal_state = dict(terminal_snapshot.get("analysis", {}))
    if not terminal_state:
        terminal_state = analyze_terminal_output(terminal_text)

    git_watch = watch_git_events()
    git_state = dict(git_watch.get("git_state", {}))
    if not git_state:
        fallback_git_state = get_git_state()
        patch_state = detect_patch_application_state(fallback_git_state)
        git_state = {**fallback_git_state, **patch_state}

    ide_state = {
        "active_ide": str(editor_state.get("active_ide", "unknown")),
        "open_file": str(editor_state.get("active_file", "")),
        "diff_view": bool(editor_state.get("diff_visible", False)),
        "approval_prompt": bool(editor_state.get("approval_prompts")),
        "waiting_state": bool(editor_state.get("waiting_state", False)),
        "terminal_focus": bool(editor_state.get("terminal_focus", False)),
        "open_tabs": list(editor_state.get("open_tabs", [])),
        "diagnostics": list(editor_state.get("diagnostics", [])),
        "selected_text": str(editor_state.get("selected_text", "")),
        "source": str(editor_state.get("source", "unknown")),
    }

    if get_development_session(session_id) is None:
        create_development_session(session_id)
    development_session = update_development_session(session_id, terminal_state, git_state, ide_state)
    return {
        "terminal_state": terminal_state,
        "terminal_stream": terminal_snapshot,
        "git_state": git_state,
        "git_events": git_watch.get("events", []),
        "editor_state": editor_state,
        "ide_state": ide_state,
        "development_session": development_session,
    }


def _run_engineering_governance(session_id: str, development: dict):
    terminal_state = development.get("terminal_state", {})
    git_state = development.get("git_state", {})
    ide_state = development.get("ide_state", {})
    workflow_state = get_workflow_state(session_id) or {}

    objective = infer_engineering_objective(
        terminal_state=terminal_state,
        git_state=git_state,
        ide_state=ide_state,
        workflow_state=workflow_state,
    )
    next_action = decide_next_action(
        objective=objective,
        current_state={
            "terminal_state": terminal_state,
            "git_state": git_state,
            "ide_state": ide_state,
            "workflow_state": workflow_state,
        },
    )
    policy = validate_development_action(
        action=next_action,
        state={
            "terminal_state": terminal_state,
            "git_state": git_state,
            "ide_state": ide_state,
            "workflow_state": workflow_state,
        },
    )

    escalation = None
    confidence = float(objective.get("confidence", 0.0))
    repeated_recovery = int(workflow_state.get("retry_count", 0)) >= 3
    dangerous_git = bool(git_state.get("conflicts"))
    ambiguous_ui = (ide_state.get("active_ide") == "unknown") and not bool(ide_state.get("terminal_focus"))

    if confidence < 0.6:
        escalation = escalate_to_human(
            reason="low_confidence_planning",
            context={"session_id": session_id, "objective": objective, "next_action": next_action},
        )
    elif repeated_recovery:
        escalation = escalate_to_human(
            reason="repeated_recovery_failures",
            context={"session_id": session_id, "retry_count": workflow_state.get("retry_count", 0)},
        )
    elif dangerous_git:
        escalation = escalate_to_human(
            reason="dangerous_git_state",
            context={"session_id": session_id, "git_state": git_state},
        )
    elif not bool(policy.get("allowed", False)):
        escalation = escalate_to_human(
            reason="policy_violation",
            context={"session_id": session_id, "policy": policy, "next_action": next_action},
        )
    elif ambiguous_ui:
        escalation = escalate_to_human(
            reason="ambiguous_ui_state",
            context={"session_id": session_id, "ide_state": ide_state},
        )

    if escalation is not None:
        update_workflow_state(
            session_id,
            {
                "status": "ESCALATED",
                "current_step": "HUMAN_ESCALATION_REQUIRED",
            },
        )
        append_operational_trace(
            trace_type="escalation_triggered",
            payload={"escalation": escalation, "objective": objective, "next_action": next_action},
            session_id=session_id,
            actor="runtime",
        )
        record_operator_feedback(
            feedback_type="escalation_comment",
            payload={"reason": escalation.get("reason"), "status": escalation.get("status")},
            session_id=session_id,
        )

    return {
        "objective": objective,
        "next_action": next_action,
        "policy": policy,
        "escalation": escalation,
        "continue_autonomously": escalation is None and bool(policy.get("allowed", False)),
    }


def _create_or_get_screen_action_job(action_name: str, grounded_action: dict, key_suffix: str = ""):
    global job_counter

    key = f"{action_name}:{grounded_action.get('x')}:{grounded_action.get('y')}:{key_suffix}"
    existing_job_id = screen_action_jobs.get(key)
    if existing_job_id:
        return existing_job_id, existing_job_id in approved_jobs, False, None

    job_counter += 1
    job_id = str(job_counter)
    pending_jobs[job_id] = {
        "action": "click",
        "x": int(grounded_action.get("x", 0)),
        "y": int(grounded_action.get("y", 0)),
        "text": None,
        "semantic_action": action_name,
        "source": "screen_act",
        "spec_scope": "default",
    }
    spec_binding = _bind_pending_job_to_spec(job_id, pending_jobs[job_id])
    if not spec_binding.get("ok", False):
        pending_jobs.pop(job_id, None)
        emit_event(
            "BLOCKED",
            job_id,
            {
                "reason": "spec_binding_failed",
                "details": spec_binding,
                "source": "screen_act",
            },
        )
        return job_id, False, False, spec_binding

    screen_action_jobs[key] = job_id
    emit_event("PROPOSED", job_id, {"request": pending_jobs[job_id]})
    publish_engineering_event(
        {
            "event_type": "screen_action_proposed",
            "payload": {
                "job_id": job_id,
                "action": action_name,
                "x": pending_jobs[job_id].get("x"),
                "y": pending_jobs[job_id].get("y"),
            },
        }
    )
    return job_id, False, True, None


def screen_act(request: ScreenActionRequest):
    screen_state = get_screen_state()
    ui_state = screen_state.get("ui_state", {})
    action_name = str(request.action or "").strip().lower()
    session = get_workflow_state(request.session_id) if request.session_id else None
    if session is None:
        session = create_workflow_session(
            current_step="PERCEPTION_CAPTURED",
            last_action=action_name,
            expected_state="",
            observed_state=_summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
            status="RUNNING",
        )
    session_id = str(session.get("session_id"))
    expected = predict_expected_state(action_name, ui_state if isinstance(ui_state, dict) else {})
    if get_development_session(session_id) is None:
        create_development_session(session_id)
    update_workflow_state(
        session_id,
        {
            "current_step": "EXPECTED_STATE_PREDICTED",
            "last_action": action_name,
            "expected_state": str(expected.get("expected_state", "")),
            "observed_state": _summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
            "status": "RUNNING",
        },
    )

    detected_actions = ui_state.get("detected_actions", []) if isinstance(ui_state, dict) else []
    if action_name and detected_actions and action_name not in detected_actions:
        emit_event("BLOCKED", f"screen-{action_name}", {"reason": "action_not_detected_on_screen"})
        update_workflow_state(
            session_id,
            {
                "current_step": "ACTION_BLOCKED",
                "status": "BLOCKED",
                "observed_state": _summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
            },
        )
        development = _build_development_intelligence(session_id, ui_state if isinstance(ui_state, dict) else {})
        engineering = _run_engineering_governance(session_id, development)
        return {
            "status": "blocked",
            "error": "action_not_detected_on_screen",
            "action": action_name,
            "detected_actions": detected_actions,
            "workflow": get_workflow_state(session_id),
            "development": development,
            "engineering": engineering,
        }

    grounded = ground_action(action_name, ui_state)
    if grounded is None:
        emit_event("BLOCKED", f"screen-{action_name}", {"reason": "action_not_grounded"})
        update_workflow_state(
            session_id,
            {
                "current_step": "ACTION_UNGROUNDED",
                "status": "BLOCKED",
                "observed_state": _summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
            },
        )
        development = _build_development_intelligence(session_id, ui_state if isinstance(ui_state, dict) else {})
        engineering = _run_engineering_governance(session_id, development)
        return {
            "status": "blocked",
            "error": "action_not_grounded",
            "action": action_name,
            "workflow": get_workflow_state(session_id),
            "development": development,
            "engineering": engineering,
        }

    with queue_state_lock:
        job_id, is_approved, created, spec_binding_error = _create_or_get_screen_action_job(action_name, grounded)
        if spec_binding_error is not None:
            update_workflow_state(
                session_id,
                {
                    "current_step": "SPEC_BINDING_BLOCKED",
                    "status": "BLOCKED",
                    "observed_state": _summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
                },
            )
            development = _build_development_intelligence(session_id, ui_state if isinstance(ui_state, dict) else {})
            engineering = _run_engineering_governance(session_id, development)
            return {
                "status": "blocked",
                "error": "spec_binding_failed",
                "details": spec_binding_error,
                "workflow": get_workflow_state(session_id),
                "development": development,
                "engineering": engineering,
            }
        if not is_approved:
            update_workflow_state(
                session_id,
                {
                    "current_step": "AWAITING_APPROVAL",
                    "status": "AWAITING_APPROVAL",
                    "observed_state": _summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
                },
            )
            append_operational_trace(
                trace_type="approval_requested",
                payload={"source": "screen_act", "action": action_name},
                session_id=session_id,
                job_id=job_id,
                actor="runtime",
            )
            development = _build_development_intelligence(session_id, ui_state if isinstance(ui_state, dict) else {})
            engineering = _run_engineering_governance(session_id, development)
            return {
                "status": "blocked",
                "job_id": job_id,
                "approval_required": True,
                "grounded_action": grounded,
                "created_new_job": created,
                "workflow": get_workflow_state(session_id),
                "development": development,
                "engineering": engineering,
            }

        execution_queue.append(job_id)
        queue_position = len(execution_queue)
        publish_engineering_event(
            {
                "event_type": "execution_queued",
                "payload": {
                    "job_id": job_id,
                    "queue_position": queue_position,
                    "source": "screen_act",
                    "session_id": session_id,
                },
            }
        )

    process_result = process_execution_queue()
    update_workflow_state(
        session_id,
        {
            "current_step": "ACTION_EXECUTED",
            "status": "RUNNING",
            "observed_state": _summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
        },
    )

    wait_ms = max(100, min(int(request.observe_delay_ms), 10000))
    time.sleep(wait_ms / 1000.0)

    observed_screen_state = get_screen_state()
    observed_ui_state = observed_screen_state.get("ui_state", {})
    transition_check = compare_expected_vs_observed(expected, observed_ui_state if isinstance(observed_ui_state, dict) else {})
    development = _build_development_intelligence(session_id, observed_ui_state if isinstance(observed_ui_state, dict) else {})
    engineering = _run_engineering_governance(session_id, development)

    workflow_status = "COMPLETED"
    recovery = None
    if not transition_check.get("match", False):
        failure_reason = str(transition_check.get("difference_reason", "state_transition_mismatch"))
        current_session = get_workflow_state(session_id) or session
        recovery = recover_from_failed_transition(current_session, failure_reason)
        new_retry_count = int((current_session or {}).get("retry_count", 0)) + int(recovery.get("retry_count_increment", 0))

        workflow_status = str(recovery.get("status", "RECOVERY_PENDING"))
        update_payload = {
            "current_step": "RECOVERY_TRIGGERED",
            "status": workflow_status,
            "observed_state": _summarize_ui_state(observed_ui_state if isinstance(observed_ui_state, dict) else {}),
            "retry_count": new_retry_count,
            "last_failure_reason": failure_reason,
        }

        if recovery.get("strategy") == "retry_click":
            retry_job_id, _, _, retry_spec_binding_error = _create_or_get_screen_action_job(
                action_name,
                grounded,
                key_suffix=f"retry-{new_retry_count}",
            )
            if retry_spec_binding_error is not None:
                update_payload["status"] = "ESCALATED"
                update_payload["spec_binding_error"] = retry_spec_binding_error
            else:
                update_payload["retry_job_id"] = retry_job_id
        update_workflow_state(session_id, update_payload)
        append_operational_trace(
            trace_type="workflow_retry",
            payload={"failure_reason": failure_reason, "strategy": recovery.get("strategy")},
            session_id=session_id,
            job_id=job_id,
            actor="runtime",
        )
    else:
        update_workflow_state(
            session_id,
            {
                "current_step": "TRANSITION_VERIFIED",
                "status": workflow_status,
                "observed_state": _summarize_ui_state(observed_ui_state if isinstance(observed_ui_state, dict) else {}),
            },
        )
        append_operational_trace(
            trace_type="workflow_transition_verified",
            payload={"expected": expected, "transition_check": transition_check},
            session_id=session_id,
            job_id=job_id,
            actor="runtime",
        )

    return {
        "status": "queued_for_execution",
        "job_id": job_id,
        "queue_position": queue_position,
        "grounded_action": grounded,
        "process_result": process_result,
        "expected_state": expected,
        "transition_check": transition_check,
        "recovery": recovery,
        "workflow": get_workflow_state(session_id),
        "development": development,
        "engineering": engineering,
    }


def workflow_start(request: WorkflowStartRequest):
    session = create_workflow_session(
        current_step=str(request.initial_step or "SCREEN_WORKFLOW"),
        last_action="",
        expected_state=str(request.expected_state or ""),
        observed_state="",
        status="RUNNING",
    )
    create_development_session(str(session.get("session_id")))
    append_operational_trace(
        trace_type="workflow_started",
        payload={"initial_step": request.initial_step, "expected_state": request.expected_state},
        session_id=str(session.get("session_id")),
        actor="runtime",
    )
    return session


def workflow_recover(session_id: str, request: WorkflowRecoverRequest):
    session = get_workflow_state(session_id)
    if session is None:
        append_operational_trace(
            trace_type="recovery_failed",
            payload={"reason": "session_not_found"},
            session_id=session_id,
            actor="operator",
        )
        return {"status": "not_found", "session_id": session_id}

    failure_reason = str(session.get("last_failure_reason", "manual_recovery_request"))
    append_operational_trace(
        trace_type="recovery_requested",
        payload={"failure_reason": failure_reason},
        session_id=session_id,
        actor="operator",
    )
    recovery = recover_from_failed_transition(session, failure_reason)
    new_retry_count = int(session.get("retry_count", 0)) + int(recovery.get("retry_count_increment", 0))

    if recovery.get("strategy") == "wait_and_retry":
        wait_ms = max(100, min(int(request.observe_delay_ms), 10000))
        time.sleep(wait_ms / 1000.0)
        observed = get_screen_state()
        update_workflow_state(
            session_id,
            {
                "current_step": "RECOVERY_REOBSERVED",
                "retry_count": new_retry_count,
                "observed_state": _summarize_ui_state(observed.get("ui_state", {})),
                "status": "RECOVERY_PENDING",
            },
        )
    elif recovery.get("strategy") == "refresh_screen":
        observed = get_screen_state()
        update_workflow_state(
            session_id,
            {
                "current_step": "SCREEN_REFRESHED",
                "retry_count": new_retry_count,
                "observed_state": _summarize_ui_state(observed.get("ui_state", {})),
                "status": "RECOVERY_PENDING",
            },
        )
    elif recovery.get("strategy") == "retry_click":
        action_name = str(session.get("last_action", "")).strip().lower()
        observed = get_screen_state()
        ui_state = observed.get("ui_state", {})
        grounded = ground_action(action_name, ui_state if isinstance(ui_state, dict) else {})
        if grounded is None:
            update_workflow_state(
                session_id,
                {
                    "current_step": "RETRY_UNGROUNDED",
                    "retry_count": new_retry_count,
                    "status": "ESCALATED",
                },
            )
            append_operational_trace(
                trace_type="recovery_escalated",
                payload={"reason": "retry_not_grounded"},
                session_id=session_id,
                actor="runtime",
            )
            return {
                "status": "escalated",
                "reason": "retry_not_grounded",
                "workflow": get_workflow_state(session_id),
            }

        retry_job_id, _, _, spec_binding_error = _create_or_get_screen_action_job(
            action_name,
            grounded,
            key_suffix=f"retry-{new_retry_count}",
        )
        if spec_binding_error is not None:
            update_workflow_state(
                session_id,
                {
                    "current_step": "RETRY_SPEC_BINDING_BLOCKED",
                    "retry_count": new_retry_count,
                    "status": "ESCALATED",
                },
            )
            return {
                "status": "escalated",
                "reason": "retry_spec_binding_failed",
                "details": spec_binding_error,
                "workflow": get_workflow_state(session_id),
            }
        update_workflow_state(
            session_id,
            {
                "current_step": "RETRY_AWAITING_APPROVAL",
                "retry_count": new_retry_count,
                "status": "AWAITING_RETRY_APPROVAL",
                "retry_job_id": retry_job_id,
                "observed_state": _summarize_ui_state(ui_state if isinstance(ui_state, dict) else {}),
            },
        )
        append_operational_trace(
            trace_type="recovery_retry_queued",
            payload={"retry_job_id": retry_job_id},
            session_id=session_id,
            job_id=retry_job_id,
            actor="runtime",
        )
        return {
            "status": "awaiting_retry_approval",
            "retry_job_id": retry_job_id,
            "workflow": get_workflow_state(session_id),
        }
    else:
        update_workflow_state(
            session_id,
            {
                "current_step": "ESCALATED",
                "retry_count": new_retry_count,
                "status": str(recovery.get("status", "ESCALATED")),
            },
        )
        append_operational_trace(
            trace_type="recovery_escalated",
            payload={"reason": str(recovery.get("status", "ESCALATED"))},
            session_id=session_id,
            actor="runtime",
        )

    append_operational_trace(
        trace_type="recovery_processed",
        payload={"strategy": recovery.get("strategy"), "status": recovery.get("status")},
        session_id=session_id,
        actor="runtime",
    )
    return {
        "status": "recovery_processed",
        "recovery": recovery,
        "workflow": get_workflow_state(session_id),
    }


def _engineering_snapshot_for_session(session_id: str):
    development_session = get_development_session(session_id)
    workflow_state = get_workflow_state(session_id)
    if development_session is None or workflow_state is None:
        return None

    terminal_state = dict(development_session.get("last_terminal_state", {}))
    git_state = dict(development_session.get("last_git_state", {}))
    ide_state = dict(development_session.get("last_ide_state", {}))

    objective = infer_engineering_objective(
        terminal_state=terminal_state,
        git_state=git_state,
        ide_state=ide_state,
        workflow_state=workflow_state,
    )
    next_action = decide_next_action(
        objective=objective,
        current_state={
            "terminal_state": terminal_state,
            "git_state": git_state,
            "ide_state": ide_state,
            "workflow_state": workflow_state,
        },
    )
    policy = validate_development_action(
        action=next_action,
        state={
            "terminal_state": terminal_state,
            "git_state": git_state,
            "ide_state": ide_state,
            "workflow_state": workflow_state,
        },
    )

    return {
        "session_id": session_id,
        "objective": objective,
        "next_action": next_action,
        "policy": policy,
        "workflow_state": workflow_state,
        "development_session": development_session,
    }


def llm_execute(task: LLMExecuteRequest):
    global llm_task_counter

    with queue_state_lock:
        llm_task_counter += 1
        job_id = f"llm-{llm_task_counter}"

    task_payload = {
        "task_type": task.task_type,
        "prompt": task.prompt,
        "context": task.context or {},
        "risk_level": task.risk_level,
        "requires_verification": task.requires_verification
    }
    backend_config = task.backend_config if isinstance(task.backend_config, dict) else {}

    emit_event("PROPOSED_LLM_TASK", job_id, {"task": task_payload})

    pre_system_state = replay_system()
    pre_control_state = _build_control_plane_verification_state(pre_system_state)
    pre_authority = validate_authority(pre_control_state)
    pre_chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in pre_control_state.get("jobs", {})
    }
    pre_invariants = check_system_invariants(pre_control_state, pre_authority, pre_chain_results)
    pre_verification = {
        "authority_validation": pre_authority,
        "invariant_validation": pre_invariants
    }

    if not pre_authority.get("valid", False) or not pre_invariants.get("valid", False):
        emit_event(
            "BLOCKED",
            job_id,
            {
                "reason": "pre_execution_validation_failed",
                "authority_valid": pre_authority.get("valid", False),
                "invariants_valid": pre_invariants.get("valid", False)
            }
        )
        return {
            "status": "rejected",
            "job_id": job_id,
            "verification": pre_verification,
            "error": "pre_execution_validation_failed"
        }

    execution_contexts[job_id] = {
        "job_id": job_id,
        "local_state": {"llm_task": True},
        "execution_snapshot": {
            "job_data": task_payload,
            "approval_state": False,
            "system_metadata": {
                "audit_log_size": len(audit_log),
                "snapshot_timestamp": datetime.utcnow().isoformat() + "Z"
            }
        },
        "screenshot_before": None,
        "screenshot_after": None
    }

    try:
        llm_result = execute_llm_task(task_payload, backend_config)
    except LLMExecutionError as exc:
        _emit_llm_backend_failure_events(job_id, exc.failures)
        emit_event("BLOCKED", job_id, {"reason": "llm_execution_failed", "error": str(exc)})
        execution_contexts[job_id]["local_state"]["result"] = {
            "status": "failed",
            "error": str(exc)
        }
        return {
            "status": "failed",
            "job_id": job_id,
            "error": str(exc),
            "backend_failures": exc.failures
        }

    selected_model_id = _extract_llm_model_id(llm_result)
    raw_response = llm_result.get("raw_response", {})
    backend_failures = raw_response.get("backend_failures", []) if isinstance(raw_response, dict) else []
    _emit_llm_backend_failure_events(job_id, backend_failures)

    emit_event(
        "LLM_EXECUTED",
        job_id,
        {
            "model_used": llm_result.get("model_used"),
            "cost": llm_result.get("cost"),
            "latency_ms": llm_result.get("latency_ms"),
            "output_hash": hashlib.sha256(str(llm_result.get("output", "")).encode()).hexdigest()
        }
    )

    execution_contexts[job_id]["local_state"]["result"] = {
        "status": "success",
        "model_used": llm_result.get("model_used"),
        "cost": llm_result.get("cost"),
        "latency_ms": llm_result.get("latency_ms")
    }

    post_system_state = replay_system()
    post_control_state = _build_control_plane_verification_state(post_system_state)
    post_authority = validate_authority(post_control_state)
    post_chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in post_control_state.get("jobs", {})
    }
    post_invariants = check_system_invariants(post_control_state, post_authority, post_chain_results)

    verification = {
        "authority_validation": post_authority,
        "invariant_validation": post_invariants
    }

    if not post_authority.get("valid", False):
        if selected_model_id:
            update_model_trust(
                selected_model_id,
                {
                    "success": True,
                    "verification_passed": False,
                    "adversarial_failed": False,
                    "cost": float(llm_result.get("cost", 0.0)),
                }
            )
        return {
            "status": "rejected",
            "job_id": job_id,
            "verification": verification,
            "error": "authority_validation_failed"
        }

    if not post_invariants.get("valid", False):
        if selected_model_id:
            update_model_trust(
                selected_model_id,
                {
                    "success": True,
                    "verification_passed": False,
                    "adversarial_failed": False,
                    "cost": float(llm_result.get("cost", 0.0)),
                }
            )
        return {
            "status": "rejected",
            "job_id": job_id,
            "verification": verification,
            "error": "invariant_validation_failed"
        }

    chain_verification = verify_chain(job_id)
    if task.requires_verification:
        proof_result = generate_execution_proof(
            job_id,
            post_system_state,
            chain_verification,
            post_authority,
            post_invariants
        )
        adversarial_result = adversarial_validate_system(
            job_id,
            post_system_state,
            chain_verification,
            post_authority,
            post_invariants,
            proof_result
        )
        verification["execution_proof"] = proof_result
        verification["adversarial_validation"] = adversarial_result
        if adversarial_result.get("adversarial_status") != "CLEAN":
            if selected_model_id:
                update_model_trust(
                    selected_model_id,
                    {
                        "success": True,
                        "verification_passed": False,
                        "adversarial_failed": True,
                        "cost": float(llm_result.get("cost", 0.0)),
                    }
                )
            return {
                "status": "rejected",
                "job_id": job_id,
                "verification": verification,
                "error": "adversarial_validation_failed"
            }

    if str(task.risk_level).lower() == "high":
        proof_result = verification.get("execution_proof") if isinstance(verification, dict) else None
        if proof_result is None:
            proof_result = generate_execution_proof(
                job_id,
                post_system_state,
                chain_verification,
                post_authority,
                post_invariants
            )
            verification["execution_proof"] = proof_result
        adversarial_result = verification.get("adversarial_validation")
        if adversarial_result is None:
            adversarial_result = adversarial_validate_system(
                job_id,
                post_system_state,
                chain_verification,
                post_authority,
                post_invariants,
                proof_result
            )
            verification["adversarial_validation"] = adversarial_result

        final_truth = resolve_final_system_truth(
            job_id,
            adversarial_result,
            chain_verification,
            post_invariants,
            post_authority,
            proof_result,
            post_system_state
        )
        verification["final_truth"] = final_truth
        if final_truth.get("final_truth_status") != "VALID":
            if selected_model_id:
                update_model_trust(
                    selected_model_id,
                    {
                        "success": True,
                        "verification_passed": False,
                        "adversarial_failed": verification.get("adversarial_validation", {}).get("adversarial_status") != "CLEAN",
                        "cost": float(llm_result.get("cost", 0.0)),
                    }
                )
            return {
                "status": "rejected",
                "job_id": job_id,
                "verification": verification,
                "error": "truth_resolution_failed"
            }

    if selected_model_id:
        update_model_trust(
            selected_model_id,
            {
                "success": True,
                "verification_passed": True,
                "adversarial_failed": False,
                "cost": float(llm_result.get("cost", 0.0)),
            }
        )

    return {
        "status": "success",
        "job_id": job_id,
        "result": {
            "output": llm_result.get("output"),
            "model_used": llm_result.get("model_used"),
            "cost": llm_result.get("cost"),
            "latency_ms": llm_result.get("latency_ms")
        },
        "verification": verification
    }


def adversarial_validate_system(
    job_id: str,
    system_state: Optional[dict] = None,
    chain_verification: Optional[dict] = None,
    authority_validation: Optional[dict] = None,
    invariant_validation: Optional[dict] = None,
    execution_proof_result: Optional[dict] = None
):
    if system_state is None:
        system_state = replay_system()
    if chain_verification is None:
        chain_verification = verify_chain(job_id)
    if authority_validation is None:
        authority_validation = validate_authority(system_state)
    if invariant_validation is None:
        chain_results = {
            replay_job_id: verify_chain(replay_job_id)
            for replay_job_id in system_state.get("jobs", {})
        }
        invariant_validation = check_system_invariants(system_state, authority_validation, chain_results)
    if execution_proof_result is None:
        execution_proof_result = generate_execution_proof(
            job_id,
            system_state,
            chain_verification,
            authority_validation,
            invariant_validation
        )

    findings = []

    replay_job_state = system_state.get("jobs", {}).get(
        job_id,
        {"status": "UNKNOWN", "approved": False, "executed": False}
    )
    audit_job_state, audit_job_events = _derive_audit_job_state(job_id)
    context = execution_contexts.get(job_id)

    # 1. Cross-layer consistency checks
    if (
        replay_job_state.get("status") != audit_job_state.get("status")
        or bool(replay_job_state.get("approved")) != bool(audit_job_state.get("approved"))
        or bool(replay_job_state.get("executed")) != bool(audit_job_state.get("executed"))
    ):
        findings.append(
            {
                "type": "REPLAY_AUDIT_MISMATCH",
                "severity": "high",
                "description": "Replay-derived state differs from audit-derived state.",
                "source_layers": ["replay_system", "audit_log"]
            }
        )

    has_execution_events = any(
        event.get("event_type") in {"EXECUTION_STARTED", "EXECUTED", "EXECUTION_FAILED"}
        for event in audit_job_events
    )

    if has_execution_events and context is None:
        findings.append(
            {
                "type": "MISSING_EXECUTION_CONTEXT",
                "severity": "high",
                "description": "Execution events exist but isolated execution context is missing.",
                "source_layers": ["execution_context", "audit_log"]
            }
        )

    if context is not None:
        context_snapshot = context.get("execution_snapshot", {})
        context_local_state = context.get("local_state", {})
        context_result = context_local_state.get("result", {})
        context_status = context_result.get("status")
        context_approval_state = bool(context_snapshot.get("approval_state"))

        if context_approval_state != bool(audit_job_state.get("approved")):
            findings.append(
                {
                    "type": "CONTEXT_AUDIT_MISMATCH",
                    "severity": "high",
                    "description": "Execution context approval snapshot differs from audit-derived approval state.",
                    "source_layers": ["execution_context", "audit_log"]
                }
            )

        if context_status == "success" and not any(event.get("event_type") == "EXECUTED" for event in audit_job_events):
            findings.append(
                {
                    "type": "CONTEXT_AUDIT_MISMATCH",
                    "severity": "high",
                    "description": "Execution context indicates success but EXECUTED event is missing.",
                    "source_layers": ["execution_context", "audit_log"]
                }
            )
        if context_status == "blocked" and not any(event.get("event_type") == "BLOCKED" for event in audit_job_events):
            findings.append(
                {
                    "type": "CONTEXT_AUDIT_MISMATCH",
                    "severity": "medium",
                    "description": "Execution context indicates blocked state but BLOCKED event is missing.",
                    "source_layers": ["execution_context", "audit_log"]
                }
            )

    # 2. Proof validation check
    recomputed_proof = generate_execution_proof(
        job_id,
        system_state,
        chain_verification,
        authority_validation,
        invariant_validation
    )
    stored_proof = execution_proofs.get(job_id)
    if stored_proof is not None and stored_proof != recomputed_proof.get("execution_proof"):
        findings.append(
            {
                "type": "PROOF_DIVERGENCE",
                "severity": "critical",
                "description": "Stored execution proof differs from recomputed execution proof.",
                "source_layers": ["execution_proof", "execution_context", "audit_log"]
            }
        )

    # 3. Chain-replay divergence (determinism across replay runs)
    replay_a = replay_system()
    replay_b = replay_system()
    replay_c = replay_system()
    if _stable_serialize(replay_a) != _stable_serialize(replay_b) or _stable_serialize(replay_b) != _stable_serialize(replay_c):
        findings.append(
            {
                "type": "REPLAY_NON_DETERMINISTIC",
                "severity": "critical",
                "description": "Repeated replay runs produced divergent system state.",
                "source_layers": ["replay_system", "audit_log"]
            }
        )

    # Baseline layer validity findings
    if not chain_verification.get("valid", False):
        findings.append(
            {
                "type": "CHAIN_INVALID",
                "severity": "critical",
                "description": f"Hash chain verification failed: {chain_verification.get('reason', 'unknown_reason')}.",
                "source_layers": ["verify_chain", "audit_log"]
            }
        )

    authority_job_violations = [
        violation for violation in authority_validation.get("violations", [])
        if violation.get("job_id") == job_id
    ]
    if authority_job_violations:
        findings.append(
            {
                "type": "AUTHORITY_INCONSISTENT",
                "severity": "high",
                "description": "Authority validation detected illegal transitions for this job.",
                "source_layers": ["validate_authority", "audit_log", "replay_system"]
            }
        )

    invariant_job_violations = [
        violation for violation in invariant_validation.get("violations", [])
        if violation.get("job_id") == job_id
    ]
    if invariant_job_violations:
        findings.append(
            {
                "type": "INVARIANT_VIOLATION",
                "severity": "high",
                "description": "System invariant violations detected for this job.",
                "source_layers": ["check_system_invariants", "audit_log", "replay_system"]
            }
        )

    # 4. Partial corruption detection
    individual_layers_valid = (
        chain_verification.get("valid", False)
        and len(authority_job_violations) == 0
        and len(invariant_job_violations) == 0
        and execution_proof_result.get("determinism_status") == "VALID"
        and recomputed_proof.get("determinism_status") == "VALID"
    )
    has_cross_layer_findings = any(
        finding.get("type") in {"REPLAY_AUDIT_MISMATCH", "CONTEXT_AUDIT_MISMATCH", "MISSING_EXECUTION_CONTEXT"}
        for finding in findings
    )
    if individual_layers_valid and has_cross_layer_findings:
        findings.append(
            {
                "type": "CROSS_LAYER_INCONSISTENCY",
                "severity": "critical",
                "description": "Individually valid layers produce inconsistent combined interpretation.",
                "source_layers": ["replay_system", "execution_context", "audit_log", "execution_proof"]
            }
        )

    if not findings:
        adversarial_status = "CLEAN"
    elif any(finding.get("severity") == "critical" for finding in findings):
        adversarial_status = "COMPROMISED"
    else:
        adversarial_status = "INCONSISTENT"

    return {
        "job_id": job_id,
        "adversarial_status": adversarial_status,
        "findings": findings
    }


def resolve_final_system_truth(
    job_id: str,
    adversarial_result: Optional[dict] = None,
    chain_verification: Optional[dict] = None,
    invariant_validation: Optional[dict] = None,
    authority_validation: Optional[dict] = None,
    execution_proof_result: Optional[dict] = None,
    system_state: Optional[dict] = None
):
    if system_state is None:
        system_state = replay_system()
    if chain_verification is None:
        chain_verification = verify_chain(job_id)
    if authority_validation is None:
        authority_validation = validate_authority(system_state)
    if invariant_validation is None:
        chain_results = {
            replay_job_id: verify_chain(replay_job_id)
            for replay_job_id in system_state.get("jobs", {})
        }
        invariant_validation = check_system_invariants(system_state, authority_validation, chain_results)
    if execution_proof_result is None:
        execution_proof_result = generate_execution_proof(
            job_id,
            system_state,
            chain_verification,
            authority_validation,
            invariant_validation
        )
    if adversarial_result is None:
        adversarial_result = adversarial_validate_system(
            job_id,
            system_state,
            chain_verification,
            authority_validation,
            invariant_validation,
            execution_proof_result
        )

    replay_job_state = system_state.get("jobs", {}).get(
        job_id,
        {"status": "UNKNOWN", "approved": False, "executed": False}
    )
    replay_job_anomalies = [
        anomaly for anomaly in system_state.get("anomalies", [])
        if anomaly.get("job_id") == job_id
    ]

    audit_job_state, audit_job_events = _derive_audit_job_state(job_id)
    context = execution_contexts.get(job_id)
    authority_job_violations = [
        violation for violation in authority_validation.get("violations", [])
        if violation.get("job_id") == job_id
    ]
    invariant_job_violations = [
        violation for violation in invariant_validation.get("violations", [])
        if violation.get("job_id") == job_id
    ]

    layer_assessments = {
        "adversarial_validation": {
            "valid": adversarial_result.get("adversarial_status") == "CLEAN",
            "conflicted": adversarial_result.get("adversarial_status") == "INCONSISTENT",
            "severity": "critical" if adversarial_result.get("adversarial_status") == "COMPROMISED" else "high",
            "issue": adversarial_result.get("adversarial_status", "UNKNOWN")
        },
        "cryptographic_integrity": {
            "valid": chain_verification.get("valid", False),
            "conflicted": False,
            "severity": "critical",
            "issue": chain_verification.get("reason", "CHAIN_OK")
        },
        "system_invariants": {
            "valid": len(invariant_job_violations) == 0,
            "conflicted": False,
            "severity": "high",
            "issue": "INVARIANT_VIOLATIONS_PRESENT" if invariant_job_violations else "INVARIANTS_OK"
        },
        "authority_validation": {
            "valid": len(authority_job_violations) == 0,
            "conflicted": False,
            "severity": "high",
            "issue": "AUTHORITY_VIOLATIONS_PRESENT" if authority_job_violations else "AUTHORITY_OK"
        },
        "execution_proof_layer": {
            "valid": execution_proof_result.get("determinism_status") == "VALID",
            "conflicted": False,
            "severity": "high",
            "issue": execution_proof_result.get("determinism_status", "UNKNOWN")
        },
        "replay_system": {
            "valid": len(replay_job_anomalies) == 0,
            "conflicted": False,
            "severity": "medium",
            "issue": "REPLAY_ANOMALIES_PRESENT" if replay_job_anomalies else "REPLAY_OK"
        },
        "audit_log": {
            "valid": len(audit_job_events) > 0,
            "conflicted": False,
            "severity": "medium",
            "issue": "NO_AUDIT_EVENTS" if len(audit_job_events) == 0 else "AUDIT_OK"
        },
        "execution_context": {
            "valid": context is not None,
            "conflicted": False,
            "severity": "medium",
            "issue": "MISSING_EXECUTION_CONTEXT" if context is None else "CONTEXT_OK"
        }
    }

    # Explicit cross-layer contradiction surface.
    if (
        replay_job_state.get("status") != audit_job_state.get("status")
        or bool(replay_job_state.get("approved")) != bool(audit_job_state.get("approved"))
        or bool(replay_job_state.get("executed")) != bool(audit_job_state.get("executed"))
    ):
        layer_assessments["replay_system"]["valid"] = False
        layer_assessments["replay_system"]["issue"] = "REPLAY_AUDIT_STATE_MISMATCH"

    winning_layer = EPISTEMIC_PRIORITY_ORDER[-1]
    final_truth_status = "VALID"

    for layer_name in EPISTEMIC_PRIORITY_ORDER:
        assessment = layer_assessments[layer_name]
        if assessment.get("conflicted"):
            winning_layer = layer_name
            final_truth_status = "CONFLICTED"
            break
        if not assessment.get("valid", False):
            winning_layer = layer_name
            final_truth_status = "INVALID"
            break

    conflicts = []
    if final_truth_status != "VALID":
        for layer_name in EPISTEMIC_PRIORITY_ORDER:
            if layer_name == winning_layer:
                continue
            assessment = layer_assessments[layer_name]
            if assessment.get("conflicted") or not assessment.get("valid", False):
                conflicts.append(
                    {
                        "layer": layer_name,
                        "issue": assessment.get("issue", "UNKNOWN"),
                        "severity": assessment.get("severity", "medium"),
                        "lost_to": winning_layer
                    }
                )

    final_state = {
        "approved": bool(replay_job_state.get("approved", False)),
        "executed": bool(replay_job_state.get("executed", False)),
        "validity": final_truth_status
    }

    if not layer_assessments["replay_system"]["valid"]:
        final_state = {
            "approved": bool(audit_job_state.get("approved", False)),
            "executed": bool(audit_job_state.get("executed", False)),
            "validity": final_truth_status
        }
        if context is not None and not layer_assessments["audit_log"]["valid"]:
            final_state = {
                "approved": bool(context.get("execution_snapshot", {}).get("approval_state", False)),
                "executed": bool(context.get("local_state", {}).get("result", {}).get("status") == "success"),
                "validity": final_truth_status
            }

    return {
        "job_id": job_id,
        "final_truth_status": final_truth_status,
        "winning_layer": winning_layer,
        "conflicts": conflicts,
        "final_state": final_state
    }


@app.get("/")
def health():
    return {"status": "determa-ui-driver-live"}


@app.on_event("startup")
def startup_restore():
    load_event_store()
    initialize_default_workers()
    _ensure_runtime_hooks_configured()


def _runtime_perception_worker(event: dict):
    event_type = str(event.get("event_type", "")).lower()
    if any(token in event_type for token in ("screen", "perception", "ocr", "editor")):
        try:
            get_screen_state()
        except Exception:
            return


def _runtime_terminal_worker(event: dict):
    event_type = str(event.get("event_type", "")).lower()
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    if "terminal" in event_type or "tests_" in event_type or "build_" in event_type:
        stream_terminal_output(
            stdout=payload.get("stdout"),
            stderr=payload.get("stderr"),
            process_event=payload.get("process_event"),
            command=payload.get("command"),
            command_status=payload.get("command_status"),
        )


def _runtime_git_worker(event: dict):
    event_type = str(event.get("event_type", "")).lower()
    if event_type.startswith("git_") or "patch" in event_type:
        watch_git_events()


def _runtime_reasoning_worker(event: dict):
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    session_id = str(payload.get("session_id", "")).strip()
    if session_id:
        _engineering_snapshot_for_session(session_id)


def _runtime_execution_worker(event: dict):
    event_type = str(event.get("event_type", "")).lower()
    if any(token in event_type for token in ("execute", "execution", "queued", "blocked", "approve")):
        result = process_execution_queue()
        if int(result.get("processed_jobs_count", 0)) > 0:
            publish_engineering_event(
                {
                    "event_type": "verification_requested",
                    "payload": {
                        "processed_jobs_count": result.get("processed_jobs_count", 0),
                        "queue_state": result.get("queue_state", {}),
                    },
                }
            )


def _runtime_verification_worker(event: dict):
    event_type = str(event.get("event_type", "")).lower()
    if any(token in event_type for token in ("verify", "verification", "executed", "execution_failed", "blocked")):
        system_state = replay_system()
        authority_validation = validate_authority(system_state)
        chain_results = {
            replay_job_id: verify_chain(replay_job_id)
            for replay_job_id in system_state.get("jobs", {})
        }
        invariants = check_system_invariants(system_state, authority_validation, chain_results)
        publish_engineering_event(
            {
                "event_type": "workflow_continuation",
                "payload": {
                    "authority_valid": authority_validation.get("valid", False),
                    "invariants_valid": invariants.get("valid", False),
                    "job_count": len(system_state.get("jobs", {})),
                },
            }
        )


def _ensure_runtime_hooks_configured():
    configure_runtime_hooks(
        worker_handlers={
            "perception_worker": _runtime_perception_worker,
            "terminal_worker": _runtime_terminal_worker,
            "git_worker": _runtime_git_worker,
            "reasoning_worker": _runtime_reasoning_worker,
            "execution_worker": _runtime_execution_worker,
            "verification_worker": _runtime_verification_worker,
        },
        escalation_handler=escalate_to_human,
        worker_start_guard=lambda worker_name: not is_worker_quarantined(worker_name),
        worker_restart_guard=lambda worker_name: not is_worker_quarantined(worker_name),
    )


def _start_runtime_with_workers():
    initialize_default_workers()
    _ensure_runtime_hooks_configured()
    status = start_runtime_loop()
    publish_engineering_event(
        {
            "event_type": "runtime_started",
            "payload": {
                "runtime_status": status,
            },
        }
    )
    return status


def _stop_runtime_with_workers():
    stop_status = stop_runtime_loop()
    worker_stops = []
    for worker_name in WORKER_NAMES:
        worker_stops.append(stop_worker(worker_name))
    publish_engineering_event(
        {
            "event_type": "runtime_stopped",
            "payload": {
                "runtime_status": stop_status,
            },
        }
    )
    return {
        "runtime": stop_status,
        "workers": worker_stops,
    }


def _runtime_queue_state_snapshot():
    with queue_state_lock:
        active_locks = [job_id for job_id, locked in job_locks.items() if locked]
        return {
            "queue_processing": bool(queue_processing),
            "pending_jobs": list(execution_queue),
            "pending_count": len(execution_queue),
            "active_locks": active_locks,
            "active_locks_count": len(active_locks),
        }


def _approval_backlog_snapshot():
    return get_pending_approvals(
        pending_jobs=pending_jobs,
        approved_jobs=approved_jobs,
        workflow_sessions=workflow_sessions,
        development_sessions=development_sessions,
        reasoning_snapshot_provider=_engineering_snapshot_for_session,
    )


def _governance_dashboard_snapshot():
    return get_governance_dashboard(
        runtime_status=get_runtime_status(),
        workers_state=get_workers_state(),
        queue_state=_runtime_queue_state_snapshot(),
        workflow_sessions=workflow_sessions,
        escalation_events=escalation_events,
        pending_approvals=_approval_backlog_snapshot(),
    )


def _latest_session_ids(limit: int = 1):
    if not workflow_sessions:
        return []
    session_ids = list(workflow_sessions.keys())
    return session_ids[-max(1, int(limit)) :]


def _operational_benchmark_state_provider(_: str):
    latest_ids = _latest_session_ids(1)
    session_id = latest_ids[0] if latest_ids else ""
    workflow_state = get_workflow_state(session_id) if session_id else {}
    development_state = get_development_session(session_id) if session_id else {}
    engineering_snapshot = _engineering_snapshot_for_session(session_id) if session_id else {}
    runtime_status = get_runtime_status()
    return {
        "session_id": session_id,
        "workflow_state": workflow_state or {},
        "development_state": development_state or {},
        "engineering_snapshot": engineering_snapshot or {},
        "runtime_status": runtime_status,
    }


def _run_replay_validation_suite():
    result = run_deterministic_replay_tests(
        replay_system_fn=replay_system,
        verify_chain_fn=verify_chain,
        validate_authority_fn=validate_authority,
        check_system_invariants_fn=check_system_invariants,
    )
    replay_validation_runs.append(result)
    if len(replay_validation_runs) > 200:
        del replay_validation_runs[0 : len(replay_validation_runs) - 200]
    return result


def _red_team_evaluator(scenario_name: str, scenario: dict):
    if scenario_name == "poisoned_diffs":
        policy_eval = validate_development_action(
            action={"action": "click_approve", "risk_level": "high", "requires_approval": True},
            state={
                "terminal_state": {"tests_failed": False, "build_failed": False},
                "git_state": {"conflicts": []},
                "ide_state": {"diff_view": False, "approval_prompt": True},
            },
        )
        return {
            "detected": not bool(policy_eval.get("allowed", True)),
            "details": policy_eval,
        }

    if scenario_name == "fake_approval_prompts":
        security_probe = _validate_execution_security(
            "redteam-fake-approval",
            {"action": "click", "semantic_action": "approve", "x": 0, "y": 0},
        )
        return {
            "detected": not bool(security_probe.get("allowed", True)),
            "details": security_probe,
        }

    if scenario_name == "malicious_terminal_output":
        terminal_eval = analyze_terminal_output("ALL TESTS PASSED\nTraceback: critical exception\nRuntimeError")
        detected = bool(terminal_eval.get("runtime_exception")) or bool(terminal_eval.get("stack_trace"))
        return {"detected": detected, "details": terminal_eval}

    if scenario_name == "runaway_retry_conditions":
        retry_counts = [int(item.get("retry_count", 0)) for item in workflow_sessions.values()]
        detected = any(retry > 3 for retry in retry_counts)
        return {
            "detected": detected,
            "details": {
                "retry_counts": retry_counts,
                "max_retry_count": max(retry_counts) if retry_counts else 0,
            },
        }

    if scenario_name == "invalid_authority_token_injection":
        token_validation = validate_authority_token(
            {"action_id": "x", "signed_by": "evil", "scope": "ui.click.approve", "authority_hash": "bad", "issued_at": "2020-01-01T00:00:00Z", "expires_at": "2099-01-01T00:00:00Z"},
            expected_action_id="x",
            expected_scope="ui.click.approve",
        )
        return {"detected": not bool(token_validation.get("valid", True)), "details": token_validation}

    return {"detected": False, "details": {"reason": "unknown_scenario"}}


def _operational_reduction_report_snapshot():
    report = build_runtime_reduction_report(
        architecture_layout=ARCHITECTURE_LAYOUT,
        system_planes=SYSTEM_PLANES,
        operational_traces=operational_traces,
        benchmark_runs=benchmark_runs,
        red_team_runs=red_team_runs,
    )
    reduction_reports.append(report)
    if len(reduction_reports) > 100:
        del reduction_reports[0 : len(reduction_reports) - 100]
    return report


def _daily_operation_start_payload(operator_tasks: Optional[List[str]] = None, session_note: str = ""):
    runtime_status = get_runtime_status()
    git_state = get_git_state()
    restore_result = load_event_store()
    pending = _approval_backlog_snapshot()
    session = start_daily_operation_session(
        runtime_status=runtime_status,
        git_state=git_state,
        restore_result=restore_result,
        pending_approvals=pending,
        operator_task_intake=(operator_tasks or []),
    )
    if session_note:
        session["session_note"] = str(session_note)
    append_operational_trace(
        trace_type="daily_session_started",
        payload={
            "session_id": session.get("session_id"),
            "operator_tasks": operator_tasks or [],
            "pending_approvals": len(pending),
        },
        session_id=str(session.get("session_id")),
        actor="operator",
    )
    return session


def _daily_operation_update_stats():
    workflows_attempted = len(workflow_sessions)
    approvals_required = len(_approval_backlog_snapshot())
    escalations = len(escalation_events)
    recovery_attempts = sum(1 for workflow in workflow_sessions.values() if int(workflow.get("retry_count", 0)) > 0)
    return update_daily_operation_stats(
        workflows_attempted=workflows_attempted,
        approvals_required=approvals_required,
        escalations=escalations,
        recovery_attempts=recovery_attempts,
    )


def _resolve_canonical_spec_for_request(req_payload: dict):
    explicit_spec_id = str(req_payload.get("canonical_spec_id") or "").strip()
    if explicit_spec_id:
        spec = get_spec(explicit_spec_id)
        if spec is None:
            return {"ok": False, "reason": "spec_not_found", "spec_id": explicit_spec_id}
        if str(spec.get("status")) != SPEC_STATUS_CANONICAL:
            return {"ok": False, "reason": "spec_not_canonical", "spec_id": explicit_spec_id}
        if spec.get("superseded_by"):
            return {"ok": False, "reason": "spec_superseded", "spec_id": explicit_spec_id}
        return {"ok": True, "spec": spec}

    scope = str(req_payload.get("spec_scope") or "default")
    current = get_canonical_specs(scope=scope)
    if not current:
        return {"ok": False, "reason": "no_canonical_spec_for_scope", "scope": scope}
    return {"ok": True, "spec": current[-1]}


def _bind_pending_job_to_spec(job_id: str, req_payload: dict):
    spec_res = _resolve_canonical_spec_for_request(req_payload)
    if not spec_res.get("ok", False):
        return {"ok": False, **spec_res}

    spec = spec_res.get("spec", {})
    derivation = derive_tasks_from_spec(spec)
    action_name = str(req_payload.get("semantic_action") or req_payload.get("action") or "").strip().lower()
    admissible_actions = {str(task.get("action", "")).strip().lower() for task in derivation.get("tasks", [])}
    if action_name and action_name not in admissible_actions:
        return {
            "ok": False,
            "reason": "action_not_derived_from_spec",
            "action": action_name,
            "admissible_actions": sorted(list(admissible_actions)),
            "spec_id": spec.get("spec_id"),
        }

    bound = bind_execution_to_spec(req_payload, spec)
    bound_payload = dict(bound.get("job_payload", {}))
    pending_jobs[job_id] = bound_payload
    return {
        "ok": True,
        "spec": spec,
        "binding": bound,
    }


def _issue_authority_token_for_job(job_id: str, signed_by: str = "human_operator"):
    req_payload = pending_jobs.get(job_id)
    if req_payload is None:
        return None

    semantic_action = str(req_payload.get("semantic_action") or req_payload.get("action") or "").strip()
    all_scopes = []
    scope_catalog = get_scope_catalog()
    for scopes in scope_catalog.get("scopes", {}).values():
        all_scopes.extend(list(scopes))

    scope_probe = validate_scope(
        semantic_action,
        {
            "allowed_scopes": all_scopes,
            "allow_high": True,
            "allow_critical": True,
            "semantic_action": semantic_action,
        },
    )
    required_scope = str(scope_probe.get("required_scope", "ui.click.continue"))
    token = generate_authority_token(
        action={"action": semantic_action, "job_id": job_id},
        approval_context={
            "job_id": job_id,
            "action_id": job_id,
            "signed_by": signed_by,
            "scope": required_scope,
        },
    )
    authority_tokens[job_id] = token
    emit_event(
        "AUTHORITY_TOKEN_ISSUED",
        job_id,
        {
            "scope": required_scope,
            "authority_hash": token.get("authority_hash"),
            "token": token,
        },
    )
    publish_engineering_event(
        {
            "event_type": "authority_token_issued",
            "payload": {
                "job_id": job_id,
                "scope": required_scope,
                "signed_by": signed_by,
            },
        }
    )
    return token


def _build_job_security_context(job_id: str, req_payload: dict):
    token = authority_tokens.get(job_id, {})
    allowed_scopes = []
    allow_high = False
    allow_critical = False
    if isinstance(token, dict):
        token_scope = token.get("scope")
        if token_scope:
            token_scope = str(token_scope)
            allowed_scopes.append(token_scope)
            scope_catalog = get_scope_catalog().get("scopes", {})
            if token_scope in scope_catalog.get("HIGH", []):
                allow_high = True
            if token_scope in scope_catalog.get("CRITICAL", []):
                allow_high = True
                allow_critical = True

    return {
        "job_id": job_id,
        "allowed_scopes": allowed_scopes,
        "allow_high": allow_high,
        "allow_critical": allow_critical,
        "retry_count": 0,
        "semantic_action": req_payload.get("semantic_action"),
    }


def _validate_execution_security(job_id: str, req_payload: dict):
    action_name = str(req_payload.get("semantic_action") or req_payload.get("action") or "").strip()
    spec_binding_validation = validate_execution_binding(req_payload)
    if not spec_binding_validation.get("valid", False):
        return {
            "allowed": False,
            "reason": "spec_execution_binding_invalid",
            "spec_binding_validation": spec_binding_validation,
            "safe_autonomy_validation": None,
            "boundary_validation": None,
            "token_validation": None,
            "scope_validation": None,
            "sandbox_validation": None,
        }

    token = authority_tokens.get(job_id)
    context = _build_job_security_context(job_id, req_payload)
    safe_profile_validation = validate_safe_autonomy(action_name)
    if not safe_profile_validation.get("allowed", False):
        return {
            "allowed": False,
            "reason": "safe_autonomy_profile_blocked",
            "spec_binding_validation": spec_binding_validation,
            "safe_autonomy_validation": safe_profile_validation,
            "boundary_validation": None,
            "token_validation": None,
            "scope_validation": None,
            "sandbox_validation": None,
        }
    boundary_validation = validate_autonomy_boundary(action_name, context)
    if not boundary_validation.get("allowed", False):
        return {
            "allowed": False,
            "reason": "autonomy_boundary_blocked",
            "spec_binding_validation": spec_binding_validation,
            "safe_autonomy_validation": safe_profile_validation,
            "boundary_validation": boundary_validation,
            "token_validation": None,
            "scope_validation": None,
            "sandbox_validation": None,
        }

    all_scopes = []
    scope_catalog = get_scope_catalog()
    for scopes in scope_catalog.get("scopes", {}).values():
        all_scopes.extend(list(scopes))
    required_scope_result = validate_scope(
        action_name,
        {
            "allowed_scopes": all_scopes,
            "allow_high": True,
            "allow_critical": True,
            "semantic_action": context.get("semantic_action"),
        },
    )
    expected_scope = str(required_scope_result.get("required_scope", "ui.click.continue"))
    gate_result = authority_gate(
        job_id=job_id,
        action_name=action_name,
        req_payload=req_payload,
        token=token,
        expected_scope=expected_scope,
        runtime_context=context,
    )
    gate_result["spec_binding_validation"] = spec_binding_validation
    gate_result["safe_autonomy_validation"] = safe_profile_validation
    gate_result["boundary_validation"] = boundary_validation
    return gate_result


def _security_verification_snapshot(job_id: str):
    system_state = replay_system()
    authority_validation = validate_authority(system_state)
    chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in system_state.get("jobs", {})
    }
    invariant_validation = check_system_invariants(system_state, authority_validation, chain_results)
    chain_verification = verify_chain(job_id)
    truth_result = resolve_truth(job_id, system_state, authority_validation, chain_verification)
    return {
        "governance_validation": {
            "authority_validation": authority_validation,
            "invariant_validation": invariant_validation,
            "chain_verification": chain_verification,
            "truth": truth_result,
        },
        "system_state": system_state,
    }


def execute_action(req: ExecuteRequest):
    before = screenshot()
    start = time.time()

    try:

        if req.action == "click":
            pyautogui.click(req.x, req.y)

        elif req.action == "move":
            pyautogui.moveTo(req.x, req.y)

        elif req.action == "type":
            pyautogui.write(req.text or "")

        else:
            return {
                "status": "failed",
                "before": before,
                "after": None,
                "execution_time_ms": int((time.time() - start) * 1000),
                "error": "unknown_action"
            }

        time.sleep(0.2)

        after = screenshot()

        return {
            "status": "success",
            "before": before,
            "after": after,
            "execution_time_ms": int((time.time() - start) * 1000),
            "error": None
        }

    except Exception as e:
        return {
            "status": "failed",
            "before": before,
            "after": None,
            "execution_time_ms": int((time.time() - start) * 1000),
            "error": str(e)
        }


def get_execution_context(job_id: str):
    context = execution_contexts.get(job_id)
    if context is None:
        return {
            "job_id": job_id,
            "found": False,
            "context": None
        }
    return {
        "job_id": job_id,
        "found": True,
        "context": context
    }


def process_execution_queue():
    global queue_processing

    with queue_state_lock:
        if queue_processing:
            append_operational_trace(
                trace_type="runtime_stall_detected",
                payload={"reason": "queue_already_processing"},
                actor="runtime",
            )
            return {
                "processed_jobs_count": 0,
                "queue_state": {
                    "status": "already_processing",
                    "pending_jobs": list(execution_queue),
                    "active_locks": [job_id for job_id, locked in job_locks.items() if locked]
                }
            }
        queue_processing = True

    processed_jobs = []
    skipped_jobs = []

    try:
        while True:
            with queue_state_lock:
                if not execution_queue:
                    break
                job_id = execution_queue.pop(0)

                if job_locks.get(job_id, False):
                    skipped_jobs.append({"job_id": job_id, "reason": "lock_exists"})
                    append_operational_trace(
                        trace_type="execution_skipped",
                        payload={"reason": "lock_exists"},
                        job_id=job_id,
                        actor="runtime",
                    )
                    continue

                job_locks[job_id] = True
                req_payload = pending_jobs.get(job_id)
                is_approved = job_id in approved_jobs
                execution_contexts[job_id] = {
                    "job_id": job_id,
                    "local_state": {
                        "lock_acquired": True,
                        "queued_execution": True
                    },
                    "execution_snapshot": {
                        "job_data": req_payload,
                        "approval_state": is_approved,
                        "system_metadata": {
                            "audit_log_size": len(audit_log),
                            "queue_length_after_dequeue": len(execution_queue),
                            "snapshot_timestamp": datetime.utcnow().isoformat() + "Z"
                        }
                    },
                    "screenshot_before": None,
                    "screenshot_after": None
                }
                context = execution_contexts[job_id]

            try:
                canonical_payload = req_payload if isinstance(req_payload, dict) else {}
                governance_result = governance_precheck(job_id, pending_jobs, approved_jobs)
                security_validation = _validate_execution_security(job_id, canonical_payload)
                context["execution_snapshot"]["governance"] = governance_result
                context["execution_snapshot"]["security"] = security_validation

                pipeline_result = run_canonical_execution_pipeline(
                    job_id=job_id,
                    req_payload=canonical_payload,
                    governance_result=governance_result,
                    security_result=security_validation,
                    execute_fn=lambda payload: execute_action(ExecuteRequest(**payload)),
                    emit_event_fn=emit_event,
                    publish_event_fn=publish_engineering_event,
                    verify_fn=lambda _job_id: run_canonical_verification(_job_id, _security_verification_snapshot),
                )

                execution_result = pipeline_result.get("result", {}) if isinstance(pipeline_result, dict) else {}
                context["screenshot_before"] = execution_result.get("before")
                context["screenshot_after"] = execution_result.get("after")
                context["local_state"]["result"] = {
                    "status": pipeline_result.get("status", "failed"),
                    "reason": pipeline_result.get("reason"),
                    "execution_time_ms": execution_result.get("execution_time_ms"),
                    "error": execution_result.get("error"),
                    "security": pipeline_result.get("security"),
                    "verification": pipeline_result.get("verification"),
                }

                emit_runtime_continuation(
                    publish_event=publish_engineering_event,
                    job_id=job_id,
                    execution_status=str(pipeline_result.get("status", "failed")),
                    verification=pipeline_result.get("verification", {}),
                )

                processed_jobs.append(
                    {
                        "job_id": job_id,
                        "status": pipeline_result.get("status", "failed"),
                    }
                )
                pipeline_status = str(pipeline_result.get("status", "failed"))
                if pipeline_status in {"blocked", "failed"}:
                    record_failure_mode(
                        failure_type=f"execution_{pipeline_status}",
                        triggering_conditions={
                            "job_id": job_id,
                            "reason": pipeline_result.get("reason"),
                            "security_reason": (pipeline_result.get("security", {}) or {}).get("reason"),
                        },
                        affected_runtime_layer="execution",
                        recovery_result="pending_or_not_recovered",
                        human_intervention_required=pipeline_status == "blocked",
                    )
                append_operational_trace(
                    trace_type="execution_processed",
                    payload={
                        "status": pipeline_status,
                        "reason": pipeline_result.get("reason"),
                        "security_reason": (pipeline_result.get("security", {}) or {}).get("reason"),
                    },
                    job_id=job_id,
                    actor="runtime",
                )
            finally:
                with queue_state_lock:
                    job_locks.pop(job_id, None)
                if job_id in execution_contexts:
                    execution_contexts[job_id]["local_state"]["lock_released"] = True
    finally:
        with queue_state_lock:
            queue_processing = False
            pending_snapshot = list(execution_queue)
            active_locks = [job_id for job_id, locked in job_locks.items() if locked]

    result = {
        "processed_jobs_count": len(processed_jobs),
        "queue_state": {
            "status": "idle",
            "pending_jobs": pending_snapshot,
            "active_locks": active_locks,
            "processed_jobs": processed_jobs,
            "skipped_jobs": skipped_jobs
        }
    }

    if result["processed_jobs_count"] > 0 or skipped_jobs:
        publish_engineering_event(
            {
                "event_type": "execution_queue_processed",
                "payload": {
                    "processed_jobs_count": result["processed_jobs_count"],
                    "skipped_jobs_count": len(skipped_jobs),
                    "pending_jobs_count": len(pending_snapshot),
                },
            }
        )

    return result


def _build_temporal_legitimacy_signals():
    system_state = replay_system()
    authority_validation = validate_authority(system_state)
    chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in system_state.get("jobs", {})
    }
    invariants = check_system_invariants(system_state, authority_validation, chain_results)
    stability = evaluate_legitimacy_stability()
    clarity = evaluate_legitimacy_clarity()
    freeze_status = evaluate_governance_freeze_status()
    runtime_status = get_runtime_status()

    all_chains_valid = all(result.get("valid", False) for result in chain_results.values()) if chain_results else True
    replay_clean = len(system_state.get("anomalies", [])) == 0
    runtime_core = runtime_status.get("runtime", {}) if isinstance(runtime_status, dict) else {}
    runtime_health = str(runtime_core.get("status", "unknown")) in {"running", "idle", "stopped"}

    constitutional_coherence = {
        "valid": str(stability.get("stability_status", "")) != "UNSTABLE",
        "reason": str(stability.get("stability_status", "UNKNOWN")),
        "details": stability,
    }
    governance_relevance = {
        "valid": str(clarity.get("clarity_status", "")) != "UNCLEAR" and not bool(freeze_status.get("frozen", False)),
        "reason": "governance_frozen" if bool(freeze_status.get("frozen", False)) else str(clarity.get("clarity_status", "UNKNOWN")),
        "details": {"clarity": clarity, "freeze_status": freeze_status},
    }
    autonomy_safety = {
        "valid": bool(validate_safe_autonomy("run_tests").get("allowed", False))
        and not bool(validate_safe_autonomy("git.commit").get("allowed", False)),
        "reason": "safe_profile_violation"
        if bool(validate_safe_autonomy("git.commit").get("allowed", False))
        else "safe_profile_enforced",
        "details": {
            "safe_profile": get_safe_autonomy_profile(),
            "autonomy_policy": get_autonomy_policy(),
        },
    }
    replay_guarantees = {
        "valid": bool(replay_clean and all_chains_valid and invariants.get("valid", False)),
        "reason": "replay_chain_or_invariant_violation"
        if not (replay_clean and all_chains_valid and invariants.get("valid", False))
        else "replay_guarantees_held",
        "details": {
            "anomaly_count": len(system_state.get("anomalies", [])),
            "all_chains_valid": all_chains_valid,
            "invariants_valid": invariants.get("valid", False),
        },
    }
    operational_validity = {
        "valid": bool(runtime_health),
        "reason": "runtime_unhealthy" if not runtime_health else "runtime_healthy",
        "details": runtime_status,
    }

    return {
        "constitutional_coherence": constitutional_coherence,
        "governance_relevance": governance_relevance,
        "autonomy_safety": autonomy_safety,
        "replay_guarantees": replay_guarantees,
        "operational_validity": operational_validity,
        "system_state": system_state,
        "authority_validation": authority_validation,
        "chain_results": chain_results,
        "invariants": invariants,
    }


def _build_temporal_legitimacy_assumptions():
    trust = generate_operator_trust_snapshot(
        workflow_sessions=workflow_sessions,
        escalation_events=escalation_events,
    )
    runtime_status = get_runtime_status()
    system_state = replay_system()
    authority_validation = validate_authority(system_state)
    freeze_status = evaluate_governance_freeze_status()

    runtime_assumptions = [
        "single_runtime_instance",
        "append_only_audit_ledger",
        "human_override_available",
    ]
    if bool(freeze_status.get("frozen", False)):
        runtime_assumptions.append("governance_evolution_frozen")

    threat_conditions = []
    if len(system_state.get("anomalies", [])) > 0:
        threat_conditions.append("replay_anomalies_present")
    if not authority_validation.get("valid", True):
        threat_conditions.append("authority_violations_present")
    if runtime_status.get("runtime", {}).get("stalled_cycles", 0) > 5:
        threat_conditions.append("runtime_stall_pressure")
    if not threat_conditions:
        threat_conditions.append("normal")

    operator_signals = trust.get("signals", {})
    operator_behavior = {
        "approvals": float(operator_signals.get("approvals", 0)),
        "rejected_actions": float(operator_signals.get("rejected_actions", 0)),
        "operator_overrides": float(operator_signals.get("operator_overrides", 0)),
        "escalation_events": float(operator_signals.get("escalation_events", 0)),
    }

    autonomy_policy = get_autonomy_policy()
    autonomy_capabilities = sorted(
        set(get_safe_autonomy_profile().get("allowed", []) + autonomy_policy.get("safe_autonomy", []))
    )

    return {
        "runtime_assumptions": runtime_assumptions,
        "operator_behavior": operator_behavior,
        "threat_conditions": threat_conditions,
        "autonomy_capabilities": autonomy_capabilities,
    }


@app.post("/propose")
def propose(req: ExecuteRequest):
    global job_counter

    job_counter += 1
    job_id = str(job_counter)
    req_payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    pending_jobs[job_id] = dict(req_payload)

    spec_binding = _bind_pending_job_to_spec(job_id, pending_jobs[job_id])
    if not spec_binding.get("ok", False):
        pending_jobs.pop(job_id, None)
        emit_event(
            "BLOCKED",
            job_id,
            {
                "reason": "spec_binding_failed",
                "details": spec_binding,
            },
        )
        record_failure_mode(
            failure_type="spec_binding_failed",
            triggering_conditions={"job_id": job_id, "details": spec_binding},
            affected_runtime_layer="canonical_spec_runtime",
            recovery_result="blocked",
            human_intervention_required=True,
        )
        append_operational_trace(
            trace_type="spec_binding_failed",
            payload={"details": spec_binding},
            job_id=job_id,
            actor="runtime",
        )
        return {
            "job_id": job_id,
            "status": "BLOCKED",
            "error": "spec_binding_failed",
            "details": spec_binding,
        }

    emit_event("PROPOSED", job_id, {"request": pending_jobs[job_id]})
    append_operational_trace(
        trace_type="approval_requested",
        payload={"action": pending_jobs[job_id].get("action"), "source": pending_jobs[job_id].get("source")},
        job_id=job_id,
        actor="runtime",
    )
    publish_engineering_event(
        {
            "event_type": "job_proposed",
            "payload": {
                "job_id": job_id,
                "action": pending_jobs[job_id].get("action"),
                "canonical_spec_id": pending_jobs[job_id].get("canonical_spec_id"),
            },
        }
    )

    return {
        "job_id": job_id,
        "status": "PENDING_APPROVAL",
        "canonical_spec_id": pending_jobs[job_id].get("canonical_spec_id"),
        "lineage_hash": pending_jobs[job_id].get("lineage_hash"),
        "derivation_hash": pending_jobs[job_id].get("derivation_hash"),
    }


@app.post("/approve/{job_id}")
def approve(job_id: str):
    if job_id not in pending_jobs:
        record_false_approval_attempt()
        record_failure_mode(
            failure_type="approval_not_found",
            triggering_conditions={"job_id": job_id},
            affected_runtime_layer="governance",
            recovery_result="blocked",
            human_intervention_required=False,
        )
        emit_event("BLOCKED", job_id, {"reason": "job_not_found"})
        append_operational_trace(
            trace_type="approval_failed",
            payload={"reason": "job_not_found"},
            job_id=job_id,
            actor="operator",
        )
        publish_engineering_event(
            {
                "event_type": "approval_blocked",
                "payload": {
                    "job_id": job_id,
                    "reason": "job_not_found",
                },
            }
        )
        return {
            "job_id": job_id,
            "status": "NOT_FOUND"
        }

    approved_jobs.add(job_id)
    emit_event("APPROVED", job_id, {})
    append_operational_trace(
        trace_type="approval_approved",
        payload={"path": "/approve/{job_id}"},
        job_id=job_id,
        actor="operator",
    )
    token = _issue_authority_token_for_job(job_id, signed_by="human_operator")
    publish_engineering_event(
        {
            "event_type": "job_approved",
            "payload": {
                "job_id": job_id,
            },
        }
    )
    return {
        "job_id": job_id,
        "status": "APPROVED",
        "authority_token": token,
    }


@app.post("/execute/{job_id}")
def execute_job(job_id: str):
    governance_result = governance_precheck(job_id, pending_jobs, approved_jobs)
    if not governance_result.get("allowed", False):
        reason = str(governance_result.get("reason", "governance_blocked"))
        append_operational_trace(
            trace_type="execution_blocked",
            payload={"reason": reason, "path": "/execute/{job_id}"},
            job_id=job_id,
            actor="runtime",
        )
        record_failure_mode(
            failure_type="execution_governance_blocked",
            triggering_conditions={"job_id": job_id, "reason": reason},
            affected_runtime_layer="governance",
            recovery_result="blocked",
            human_intervention_required=reason != "job_not_found",
        )
        emit_event("BLOCKED", job_id, {"reason": reason})
        publish_engineering_event(
            {
                "event_type": "execution_blocked",
                "payload": {
                    "job_id": job_id,
                    "reason": reason,
                },
            }
        )
        return {
            "status": "failed" if reason == "job_not_found" else "blocked",
            "job_id": job_id,
            "before": None,
            "after": None,
            "execution_time_ms": 0,
            "error": reason,
        }

    with queue_state_lock:
        execution_queue.append(job_id)
        queue_position = len(execution_queue)
    append_operational_trace(
        trace_type="execution_queued",
        payload={"queue_position": queue_position, "source": "execute_endpoint"},
        job_id=job_id,
        actor="runtime",
    )
    publish_engineering_event(
        {
            "event_type": "execution_queued",
            "payload": {
                "job_id": job_id,
                "queue_position": queue_position,
                "source": "execute_endpoint",
            },
        }
    )

    return {
        "status": "queued_for_execution",
        "job_id": job_id,
        "queue_position": queue_position
    }


@app.post("/execute")
def execute_directly_blocked():
    return {
        "status": "blocked",
        "error": "direct_execute_disabled_use_propose_approve_execute_job"
    }


@app.get("/audit/{job_id}")
def get_audit(job_id: str):
    return {
        "job_id": job_id,
        "events": [event for event in audit_log if event["job_id"] == job_id]
    }


@app.get("/verify-chain/{job_id}")
def verify_chain_endpoint(job_id: str):
    return verify_chain(job_id)


@app.get("/replay-system")
def replay_system_endpoint():
    return replay_system()


@app.get("/validate-authority")
def validate_authority_endpoint():
    system_state = replay_system()
    authority_validation = validate_authority(system_state)
    return {
        "system_state": system_state,
        "authority_validation": authority_validation
    }


@app.get("/truth/{job_id}")
def truth_endpoint(job_id: str):
    system_state = replay_system()
    chain_verification = verify_chain(job_id)
    authority_validation = validate_authority(system_state)
    return resolve_truth(job_id, system_state, authority_validation, chain_verification)


@app.get("/validate-system")
def validate_system_endpoint():
    system_state = replay_system()
    chain_results = {
        job_id: verify_chain(job_id)
        for job_id in system_state.get("jobs", {})
    }
    authority_validation = validate_authority(system_state)
    invariants = check_system_invariants(system_state, authority_validation, chain_results)
    return {
        "system_state": system_state,
        "chain_results": chain_results,
        "authority_validation": authority_validation,
        "invariant_validation": invariants
    }


@app.get("/system/restore")
def system_restore_endpoint():
    return load_event_store()


@app.get("/system/contract")
def system_contract_endpoint():
    return {
        "system_contract": SYSTEM_CONTRACT,
        "runtime_contract": RUNTIME_CONTRACT,
    }


@app.post("/process-queue")
def process_queue_endpoint():
    return process_execution_queue()


@app.post("/ai/execute")
def ai_execute_endpoint(task: AITaskRequest):
    return ai_execute(task)


@app.post("/llm/execute")
def llm_execute_endpoint(task: LLMExecuteRequest):
    return llm_execute(task)


@app.get("/screen/state")
def screen_state_endpoint():
    return get_screen_state()


@app.post("/screen/act")
def screen_act_endpoint(request: ScreenActionRequest):
    return screen_act(request)


@app.post("/workflow/start")
def workflow_start_endpoint(request: WorkflowStartRequest):
    return workflow_start(request)


@app.get("/workflow/{session_id}")
def workflow_get_endpoint(session_id: str):
    session = get_workflow_state(session_id)
    if session is None:
        return {"status": "not_found", "session_id": session_id}
    return session


@app.post("/workflow/recover/{session_id}")
def workflow_recover_endpoint(session_id: str, request: WorkflowRecoverRequest):
    return workflow_recover(session_id, request)


@app.get("/development/state")
def development_state_endpoint():
    return get_development_state()


@app.get("/development/session/{session_id}")
def development_session_endpoint(session_id: str):
    session = get_development_session(session_id)
    if session is None:
        return {"status": "not_found", "session_id": session_id}
    return session


@app.get("/editor/state")
def editor_state_endpoint():
    return get_editor_state()


@app.get("/terminal/stream/status")
def terminal_stream_status_endpoint():
    return stream_terminal_output()


@app.get("/git/events/recent")
def git_events_recent_endpoint(limit: int = 100):
    watch_git_events()
    return get_recent_git_events(limit)


@app.get("/dashboard/governance")
def governance_dashboard_endpoint():
    return _governance_dashboard_snapshot()


@app.get("/trace/session/{session_id}")
def session_trace_endpoint(session_id: str, limit: int = 500):
    workflow_session = get_workflow_state(session_id)
    development_session = get_development_session(session_id)
    engineering_events = get_recent_engineering_events(limit)
    return get_execution_trace(
        session_id=session_id,
        workflow_session=workflow_session,
        development_session=development_session,
        audit_events=list(audit_log),
        engineering_events=engineering_events,
        escalation_events=list(escalation_events),
    )


@app.get("/approvals/pending")
def pending_approvals_endpoint():
    pending = _approval_backlog_snapshot()
    return {
        "pending_approvals": pending,
        "count": len(pending),
    }


@app.get("/security/scopes")
def security_scopes_endpoint():
    return get_scope_catalog()


@app.get("/security/authority/{job_id}")
def security_authority_endpoint(job_id: str):
    req_payload = pending_jobs.get(job_id, {})
    action_name = str(req_payload.get("semantic_action") or req_payload.get("action") or "").strip()
    all_scopes = []
    scope_catalog = get_scope_catalog()
    for scopes in scope_catalog.get("scopes", {}).values():
        all_scopes.extend(list(scopes))
    required_scope = validate_scope(
        action_name,
        {
            "allowed_scopes": all_scopes,
            "allow_high": True,
            "allow_critical": True,
            "semantic_action": req_payload.get("semantic_action"),
        },
    ).get("required_scope", "ui.click.continue")

    token = authority_tokens.get(job_id)
    token_validation = validate_authority_token(
        token,
        expected_action_id=job_id,
        expected_scope=str(required_scope),
    )
    return {
        "job_id": job_id,
        "required_scope": required_scope,
        "token": token,
        "token_validation": token_validation,
    }


@app.get("/security/approval-chain/{job_id}")
def security_approval_chain_endpoint(job_id: str):
    chain = build_trusted_approval_chain(
        job_id=job_id,
        pending_jobs=pending_jobs,
        approved_jobs=approved_jobs,
        audit_log=audit_log,
        authority_tokens=authority_tokens,
        execution_proofs=execution_proofs,
        verification_result_provider=_security_verification_snapshot,
    )
    return chain


@app.post("/specs/propose")
def specs_propose_endpoint(request: SpecProposeRequest):
    normalized_status = str(request.status or SPEC_STATUS_DRAFT).upper()
    if normalized_status == SPEC_STATUS_CANONICAL:
        normalized_status = SPEC_STATUS_UNDER_REVIEW

    spec = register_spec(
        scope=request.scope,
        content=request.content,
        status=normalized_status,
        title=request.title,
        derived_from=request.derived_from,
        proposed_by=request.proposed_by,
        governance_approvals=request.governance_approvals,
    )
    emit_event(
        "SPEC_PROPOSED",
        str(spec.get("spec_id")),
        {
            "scope": spec.get("scope"),
            "status": spec.get("status"),
            "derived_from": spec.get("derived_from"),
        },
    )
    publish_engineering_event(
        {
            "event_type": "spec_proposed",
            "payload": {
                "spec_id": spec.get("spec_id"),
                "scope": spec.get("scope"),
                "status": spec.get("status"),
            },
        }
    )
    return {
        "status": "ok",
        "spec": spec,
        "note": (
            "canonical_status_not_set_on_propose"
            if str(request.status or "").upper() == SPEC_STATUS_CANONICAL
            else ""
        ),
    }


@app.post("/specs/canonicalize/{spec_id}")
def specs_canonicalize_endpoint(spec_id: str):
    freeze_status = evaluate_governance_freeze_status()
    if freeze_status.get("frozen", False):
        emit_event(
            "SPEC_CANONICALIZE_BLOCKED",
            str(spec_id),
            {
                "reason": "governance_frozen",
                "freeze_status": freeze_status,
            },
        )
        return {
            "status": "blocked",
            "spec_id": spec_id,
            "error": "governance_frozen",
            "freeze_status": freeze_status,
        }

    target_spec = get_spec(spec_id)
    if target_spec is None:
        return {
            "status": "not_found",
            "spec_id": spec_id,
        }

    boundary_check = evaluate_self_modification_boundary(
        {
            "operation": "canonicalize_spec",
            "autonomous": False,
            "targets_constitutional_core": True,
            "widens_autonomy_boundary": False,
        }
    )
    if not boundary_check.get("allowed", False):
        emit_event(
            "SPEC_CANONICALIZE_BLOCKED",
            str(spec_id),
            {
                "reason": "self_modification_boundary_blocked",
                "boundary_check": boundary_check,
            },
        )
        return {
            "status": "blocked",
            "spec_id": spec_id,
            "error": "self_modification_boundary_blocked",
            "boundary_check": boundary_check,
        }

    scope = str(target_spec.get("scope", "default"))
    canonical_in_scope = get_canonical_specs(scope=scope)
    prior_canonical = canonical_in_scope[-1] if canonical_in_scope else {}
    mutation_validation = validate_governance_mutation(
        prior_canonical,
        target_spec,
        {
            "operation": "canonicalize_spec",
            "autonomous": False,
            "scope": scope,
        },
    )
    if not mutation_validation.get("allowed", False):
        reject_spec(spec_id, reason="governance_mutation_blocked")
        emit_event(
            "SPEC_REJECTED",
            str(spec_id),
            {
                "reason": "governance_mutation_blocked",
                "mutation_validation": mutation_validation,
            },
        )
        return {
            "status": "blocked",
            "spec_id": spec_id,
            "error": "governance_mutation_blocked",
            "mutation_validation": mutation_validation,
        }

    constitutional_validation = validate_constitutional_spec(spec_id)
    if not constitutional_validation.get("valid", False):
        reject_spec(spec_id, reason="constitutional_validation_failed")
        emit_event(
            "SPEC_REJECTED",
            str(spec_id),
            {
                "reason": "constitutional_validation_failed",
                "constitutional_validation": constitutional_validation,
            },
        )
        return {
            "status": "blocked",
            "spec_id": spec_id,
            "error": "constitutional_validation_failed",
            "constitutional_validation": constitutional_validation,
        }

    result = canonicalize_spec(spec_id, emit_event_fn=emit_event)
    if not result.get("ok", False):
        if result.get("reason") == "semantic_inadmissible":
            reject_spec(spec_id, reason="semantic_inadmissible")
            emit_event(
                "SPEC_REJECTED",
                str(spec_id),
                {"reason": "semantic_inadmissible", "admissibility": result.get("admissibility", {})},
            )
        return {
            "status": "blocked",
            "spec_id": spec_id,
            "error": result.get("reason"),
            "details": result,
        }

    spec = get_spec(spec_id)
    return {
        "status": "ok",
        "canonicalization": result,
        "spec": spec,
    }


@app.get("/specs/current")
def specs_current_endpoint():
    return {
        "canonical_specs": get_canonical_specs(),
        "count": len(get_canonical_specs()),
    }


@app.get("/specs/history")
def specs_history_endpoint():
    return {
        "specs": list(spec_registry.values()),
        "history": get_specs_history(),
    }


@app.get("/specs/lineage/{spec_id}")
def specs_lineage_endpoint(spec_id: str):
    return build_spec_lineage(spec_id)


@app.post("/specs/derive/tasks/{spec_id}")
def specs_derive_tasks_endpoint(spec_id: str):
    spec = get_spec(spec_id)
    if spec is None:
        return {"status": "not_found", "spec_id": spec_id}
    derivation = derive_tasks_from_spec(spec)
    return {
        "status": "ok",
        "spec_id": spec_id,
        "spec_status": spec.get("status"),
        "derivation": derivation,
    }


@app.get("/constitution")
def constitution_endpoint():
    return get_constitution()


@app.post("/constitution/validate/{spec_id}")
def constitution_validate_endpoint(spec_id: str):
    validation = validate_constitutional_spec(spec_id)
    return validation


@app.get("/specs/reduction-report")
def specs_reduction_report_endpoint():
    return generate_spec_reduction_report()


@app.get("/specs/governance-inflation")
def specs_governance_inflation_endpoint():
    return detect_governance_inflation()


@app.get("/governance/entropy")
def governance_entropy_endpoint():
    compression = generate_semantic_compression_report()
    entropy = measure_semantic_entropy()
    return {
        "status": "ok",
        "compression": compression,
        "entropy": entropy,
    }


@app.get("/governance/minimality")
def governance_minimality_endpoint():
    return evaluate_governance_minimality()


@app.get("/governance/complexity-budget")
def governance_complexity_budget_endpoint():
    return evaluate_governance_complexity_budget()


@app.get("/governance/clarity")
def governance_clarity_endpoint():
    return evaluate_legitimacy_clarity()


@app.get("/governance/stability")
def governance_stability_endpoint():
    return evaluate_legitimacy_stability()


@app.get("/governance/freeze-status")
def governance_freeze_status_endpoint():
    return evaluate_governance_freeze_status()


@app.post("/governance/mutation/validate")
def governance_mutation_validate_endpoint(request: GovernanceMutationValidationRequest):
    old_spec = dict(request.old_spec or {})
    new_spec = dict(request.new_spec or {})

    if not old_spec and request.old_spec_id:
        fetched_old = get_spec(str(request.old_spec_id))
        if fetched_old is not None:
            old_spec = dict(fetched_old)

    if not new_spec and request.new_spec_id:
        fetched_new = get_spec(str(request.new_spec_id))
        if fetched_new is not None:
            new_spec = dict(fetched_new)

    if not new_spec:
        return {
            "status": "blocked",
            "error": "new_spec_required",
            "details": "Provide new_spec or new_spec_id.",
        }

    boundary_context = dict(request.mutation_context or {})
    boundary_check = evaluate_self_modification_boundary(boundary_context)
    mutation_validation = validate_governance_mutation(old_spec, new_spec, boundary_context)
    freeze_status = evaluate_governance_freeze_status()

    allowed = bool(
        boundary_check.get("allowed", False)
        and mutation_validation.get("allowed", False)
        and not freeze_status.get("frozen", False)
    )
    return {
        "status": "ok" if allowed else "blocked",
        "allowed": allowed,
        "boundary_check": boundary_check,
        "mutation_validation": mutation_validation,
        "freeze_status": freeze_status,
        "immutable_core": IMMUTABLE_CONSTITUTIONAL_CORE,
    }


@app.get("/legitimacy/revalidate")
def legitimacy_revalidate_endpoint():
    signals = _build_temporal_legitimacy_signals()
    revalidation = revalidate_legitimacy(
        constitutional_coherence=signals["constitutional_coherence"],
        governance_relevance=signals["governance_relevance"],
        autonomy_safety=signals["autonomy_safety"],
        replay_guarantees=signals["replay_guarantees"],
        operational_validity=signals["operational_validity"],
    )
    return {
        "revalidation": revalidation,
        "signals": {
            "constitutional_coherence": signals["constitutional_coherence"],
            "governance_relevance": signals["governance_relevance"],
            "autonomy_safety": signals["autonomy_safety"],
            "replay_guarantees": signals["replay_guarantees"],
            "operational_validity": signals["operational_validity"],
        },
        "renewal_state": get_legitimacy_renewal_state(),
    }


@app.get("/legitimacy/drift")
def legitimacy_drift_endpoint():
    assumptions = _build_temporal_legitimacy_assumptions()
    drift = detect_assumption_drift(assumptions)
    return {
        "assumptions": assumptions,
        "drift": drift,
    }


@app.get("/legitimacy/authority-decay")
def legitimacy_authority_decay_endpoint():
    decay = evaluate_temporal_authority_decay(authority_tokens)
    return {
        "authority_decay": decay,
    }


@app.post("/legitimacy/renew")
def legitimacy_renew_endpoint():
    signals = _build_temporal_legitimacy_signals()
    revalidation = revalidate_legitimacy(
        constitutional_coherence=signals["constitutional_coherence"],
        governance_relevance=signals["governance_relevance"],
        autonomy_safety=signals["autonomy_safety"],
        replay_guarantees=signals["replay_guarantees"],
        operational_validity=signals["operational_validity"],
    )
    assumptions = _build_temporal_legitimacy_assumptions()
    drift = detect_assumption_drift(assumptions)
    decay = evaluate_temporal_authority_decay(authority_tokens)
    renewal = run_legitimacy_renewal(
        revalidation_result=revalidation,
        drift_result=drift,
        authority_decay_result=decay,
        freeze_execution_fn=lambda: pause_runtime(
            stop_runtime_fn=_stop_runtime_with_workers,
            publish_event_fn=publish_engineering_event,
        ),
    )
    if renewal.get("renewal_required"):
        append_operational_trace(
            trace_type="legitimacy_renewal_required",
            payload={
                "reasons": renewal.get("reasons", []),
                "authority_lineage_targets": renewal.get("authority_lineage_targets", []),
            },
            actor="governance",
        )
    return {
        "revalidation": revalidation,
        "drift": drift,
        "authority_decay": decay,
        "renewal": renewal,
    }


@app.get("/legitimacy/replay/{timestamp}")
def legitimacy_replay_endpoint(timestamp: str):
    return replay_historical_legitimacy(
        timestamp=timestamp,
        audit_events=audit_log,
        spec_history=get_specs_history(),
    )


@app.get("/metrics/runtime")
def runtime_metrics_endpoint():
    replay_state = replay_system()
    replay_validation = _run_replay_validation_suite()
    failures_snapshot = get_recent_failures(500)
    metrics = get_runtime_metrics_snapshot(
        workflow_sessions=workflow_sessions,
        escalation_events=escalation_events,
        audit_log=audit_log,
        runtime_status=get_runtime_status(),
        failure_records=failures_snapshot.get("failures", []),
        replay_state=replay_state,
    )
    return {
        "metrics": metrics,
        "replay_validation": replay_validation,
        "runtime_status": get_runtime_status(),
    }


@app.get("/failures/recent")
def recent_failures_endpoint(limit: int = 100):
    return get_recent_failures(limit)


@app.post("/benchmarks/run/{benchmark_name}")
def run_benchmark_endpoint(benchmark_name: str):
    result = run_benchmark(benchmark_name, _operational_benchmark_state_provider)
    if result.get("status") == "not_found":
        result["available_benchmarks"] = sorted(list(get_benchmark_suite().keys()))
    evaluation = result.get("evaluation", {}) if isinstance(result, dict) else {}
    success = bool(evaluation.get("success", False)) if result.get("status") == "ok" else False
    record_benchmark_result(success)
    if result.get("status") == "ok" and not success:
        record_failure_mode(
            failure_type="benchmark_failed",
            triggering_conditions={
                "benchmark_name": benchmark_name,
                "score": evaluation.get("score"),
                "failed_checks": [check for check in evaluation.get("checks", []) if not check.get("passed", False)],
            },
            affected_runtime_layer="operational_validation",
            recovery_result="none",
            human_intervention_required=False,
        )
    benchmark_runs.append(result)
    if len(benchmark_runs) > 200:
        del benchmark_runs[0 : len(benchmark_runs) - 200]
    return result


@app.post("/redteam/run/{scenario_name}")
def run_red_team_endpoint(scenario_name: str):
    result = run_red_team_scenario(scenario_name, _red_team_evaluator)
    if result.get("status") == "not_found":
        result["available_scenarios"] = sorted(list(get_red_team_catalog().keys()))
    detected = bool(result.get("detected", False)) if result.get("status") == "ok" else False
    record_red_team_result(detected)
    if result.get("status") == "ok" and not detected:
        record_failure_mode(
            failure_type="red_team_detection_missed",
            triggering_conditions={"scenario_name": scenario_name},
            affected_runtime_layer="security_governance",
            recovery_result="none",
            human_intervention_required=True,
        )
    red_team_runs.append(result)
    if len(red_team_runs) > 200:
        del red_team_runs[0 : len(red_team_runs) - 200]
    return result


@app.get("/operations/friction")
def operations_friction_endpoint():
    if not replay_validation_runs:
        _run_replay_validation_suite()
    friction = generate_autonomy_friction_map(
        workflow_sessions=workflow_sessions,
        escalation_events=escalation_events,
        operational_traces=operational_traces,
        replay_validation_runs=replay_validation_runs,
    )
    return {
        "friction": friction,
        "autonomy_policy": get_autonomy_policy(),
    }


@app.get("/operations/traces/recent")
def operations_traces_recent_endpoint(limit: int = 100, session_id: Optional[str] = None):
    if session_id:
        return export_workflow_session(session_id)
    return get_recent_operational_traces(limit=limit)


@app.get("/operations/reduction-report")
def operations_reduction_report_endpoint():
    report = _operational_reduction_report_snapshot()
    return {
        "report": report,
        "generated_reports": len(reduction_reports),
    }


@app.post("/operations/daily/start")
def operations_daily_start_endpoint(request: DailyOperationStartRequest):
    session = _daily_operation_start_payload(
        operator_tasks=request.operator_tasks,
        session_note=request.session_note,
    )
    _daily_operation_update_stats()
    return {
        "status": "started",
        "daily_session": session,
    }


@app.get("/operations/daily/status")
def operations_daily_status_endpoint():
    _daily_operation_update_stats()
    status = get_daily_operation_status()
    status["pending_approvals"] = _approval_backlog_snapshot()
    return status


@app.get("/operations/trust")
def operations_trust_endpoint():
    trust_snapshot = generate_operator_trust_snapshot(
        workflow_sessions=workflow_sessions,
        escalation_events=escalation_events,
    )
    if str(trust_snapshot.get("autonomy_confidence_trend")) == "declining":
        record_operator_feedback(
            feedback_type="trust_degradation_indicator",
            payload={"reason": "autonomy_confidence_declining"},
        )
    friction = generate_autonomy_friction_map(
        workflow_sessions=workflow_sessions,
        escalation_events=escalation_events,
        operational_traces=operational_traces,
        replay_validation_runs=replay_validation_runs,
    )
    return {
        "trust": trust_snapshot,
        "friction": friction,
        "safe_autonomy_profile": get_safe_autonomy_profile(),
    }


@app.get("/operations/reduction-cycle")
def operations_reduction_cycle_endpoint():
    _daily_operation_update_stats()
    if not replay_validation_runs:
        _run_replay_validation_suite()
    daily_status = get_daily_operation_status()
    reduction_report = _operational_reduction_report_snapshot()
    friction = generate_autonomy_friction_map(
        workflow_sessions=workflow_sessions,
        escalation_events=escalation_events,
        operational_traces=operational_traces,
        replay_validation_runs=replay_validation_runs,
    )
    return run_operational_reduction_cycle(
        reduction_report=reduction_report,
        friction_map=friction,
        daily_status=daily_status,
    )


@app.post("/approvals/approve/{job_id}")
def approval_action_endpoint(job_id: str):
    result = approve_action(
        job_id=job_id,
        pending_jobs=pending_jobs,
        approved_jobs=approved_jobs,
        emit_event=emit_event,
        publish_event=publish_engineering_event,
    )
    if str(result.get("status", "")) == "NOT_FOUND":
        record_false_approval_attempt()
        record_operator_feedback(
            feedback_type="approval_override",
            payload={"status": "NOT_FOUND", "path": "/approvals/approve/{job_id}"},
            job_id=job_id,
        )
        append_operational_trace(
            trace_type="approval_failed",
            payload={"path": "/approvals/approve/{job_id}", "reason": "job_not_found"},
            job_id=job_id,
            actor="operator",
        )
    if str(result.get("status")) == "APPROVED":
        result["authority_token"] = _issue_authority_token_for_job(job_id, signed_by="governance_operator")
        record_operator_feedback(
            feedback_type="approval_approved",
            payload={"path": "/approvals/approve/{job_id}"},
            job_id=job_id,
        )
        append_operational_trace(
            trace_type="approval_approved",
            payload={"path": "/approvals/approve/{job_id}"},
            job_id=job_id,
            actor="operator",
        )
    return result


@app.post("/approvals/reject/{job_id}")
def reject_action_endpoint(job_id: str, reason: str = "rejected_by_operator"):
    result = reject_action(
        job_id=job_id,
        pending_jobs=pending_jobs,
        approved_jobs=approved_jobs,
        emit_event=emit_event,
        publish_event=publish_engineering_event,
        reason=reason,
    )
    authority_tokens.pop(job_id, None)
    record_operator_feedback(
        feedback_type="approval_rejected",
        payload={"reason": reason, "path": "/approvals/reject/{job_id}"},
        job_id=job_id,
    )
    append_operational_trace(
        trace_type="approval_rejected",
        payload={"reason": reason, "path": "/approvals/reject/{job_id}"},
        job_id=job_id,
        actor="operator",
    )
    return result


@app.get("/runtime/status")
def runtime_status_endpoint():
    return {
        **get_runtime_status(),
        "control_state": get_runtime_control_state(),
    }


@app.get("/runtime/workers")
def runtime_workers_endpoint():
    return {
        **get_workers_state(),
        "control_state": get_runtime_control_state(),
    }


@app.post("/runtime/pause")
def runtime_pause_endpoint():
    result = pause_runtime(
        stop_runtime_fn=_stop_runtime_with_workers,
        publish_event_fn=publish_engineering_event,
    )
    append_operational_trace(
        trace_type="runtime_paused",
        payload={"status": result.get("status")},
        actor="operator",
    )
    record_operator_feedback(
        feedback_type="operator_override",
        payload={"operation": "runtime_pause", "status": result.get("status")},
    )
    return result


@app.post("/runtime/resume")
def runtime_resume_endpoint():
    result = resume_runtime(
        start_runtime_fn=_start_runtime_with_workers,
        publish_event_fn=publish_engineering_event,
    )
    append_operational_trace(
        trace_type="runtime_resumed",
        payload={"status": result.get("status")},
        actor="operator",
    )
    record_operator_feedback(
        feedback_type="operator_override",
        payload={"operation": "runtime_resume", "status": result.get("status")},
    )
    return result


@app.post("/runtime/workflow/stop/{session_id}")
def runtime_stop_workflow_endpoint(session_id: str):
    result = stop_workflow(
        session_id=session_id,
        get_workflow_state_fn=get_workflow_state,
        update_workflow_state_fn=update_workflow_state,
        publish_event_fn=publish_engineering_event,
    )
    append_operational_trace(
        trace_type="workflow_stopped",
        payload={"status": result.get("status")},
        session_id=session_id,
        actor="operator",
    )
    record_operator_feedback(
        feedback_type="operator_override",
        payload={"operation": "workflow_stop", "status": result.get("status")},
        session_id=session_id,
    )
    return result


@app.post("/runtime/quarantine/{worker_id}")
def runtime_quarantine_worker_endpoint(worker_id: str):
    result = quarantine_worker(
        worker_id=worker_id,
        stop_worker_fn=stop_worker,
        publish_event_fn=publish_engineering_event,
    )
    append_operational_trace(
        trace_type="worker_quarantined",
        payload={"worker_id": worker_id, "status": result.get("status")},
        actor="operator",
    )
    record_operator_feedback(
        feedback_type="operator_override",
        payload={"operation": "worker_quarantine", "worker_id": worker_id, "status": result.get("status")},
    )
    return result


@app.post("/runtime/start")
def runtime_start_endpoint():
    result = _start_runtime_with_workers()
    append_operational_trace(
        trace_type="runtime_started",
        payload={"status": result.get("status")},
        actor="operator",
    )
    return result


@app.post("/runtime/stop")
def runtime_stop_endpoint():
    result = _stop_runtime_with_workers()
    append_operational_trace(
        trace_type="runtime_stopped",
        payload={"status": (result.get("runtime", {}) or {}).get("status")},
        actor="operator",
    )
    return result


@app.get("/engineering/objective/{session_id}")
def engineering_objective_endpoint(session_id: str):
    snapshot = _engineering_snapshot_for_session(session_id)
    if snapshot is None:
        return {"status": "not_found", "session_id": session_id}
    return {
        "session_id": session_id,
        "objective": snapshot["objective"],
    }


@app.get("/engineering/next-action/{session_id}")
def engineering_next_action_endpoint(session_id: str):
    snapshot = _engineering_snapshot_for_session(session_id)
    if snapshot is None:
        return {"status": "not_found", "session_id": session_id}
    return {
        "session_id": session_id,
        "objective": snapshot["objective"],
        "next_action": snapshot["next_action"],
    }


@app.get("/engineering/policy-status/{session_id}")
def engineering_policy_status_endpoint(session_id: str):
    snapshot = _engineering_snapshot_for_session(session_id)
    if snapshot is None:
        return {"status": "not_found", "session_id": session_id}
    return {
        "session_id": session_id,
        "objective": snapshot["objective"],
        "next_action": snapshot["next_action"],
        "policy": snapshot["policy"],
    }


@app.get("/llm/models/status")
def llm_models_status_endpoint():
    return get_model_status()


@app.get("/llm/safety/status")
def llm_safety_status_endpoint():
    return get_llm_safety_status()


@app.get("/execution-context/{job_id}")
def execution_context_endpoint(job_id: str):
    return get_execution_context(job_id)


@app.get("/execution-proof/{job_id}")
def execution_proof_endpoint(job_id: str):
    system_state = replay_system()
    chain_verification = verify_chain(job_id)
    authority_validation = validate_authority(system_state)
    chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in system_state.get("jobs", {})
    }
    invariant_validation = check_system_invariants(system_state, authority_validation, chain_results)
    proof_result = generate_execution_proof(
        job_id,
        system_state,
        chain_verification,
        authority_validation,
        invariant_validation
    )
    execution_proofs[job_id] = proof_result.get("execution_proof")
    return proof_result


@app.get("/adversarial-validate/{job_id}")
def adversarial_validate_endpoint(job_id: str):
    system_state = replay_system()
    chain_verification = verify_chain(job_id)
    authority_validation = validate_authority(system_state)
    chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in system_state.get("jobs", {})
    }
    invariant_validation = check_system_invariants(system_state, authority_validation, chain_results)
    execution_proof_result = generate_execution_proof(
        job_id,
        system_state,
        chain_verification,
        authority_validation,
        invariant_validation
    )
    return adversarial_validate_system(
        job_id,
        system_state,
        chain_verification,
        authority_validation,
        invariant_validation,
        execution_proof_result
    )


@app.get("/final-truth/{job_id}")
def final_truth_endpoint(job_id: str):
    system_state = replay_system()
    authority_validation = validate_authority(system_state)
    chain_results = {
        replay_job_id: verify_chain(replay_job_id)
        for replay_job_id in system_state.get("jobs", {})
    }
    chain_verification = verify_chain(job_id)
    invariant_validation = check_system_invariants(system_state, authority_validation, chain_results)
    execution_proof_result = generate_execution_proof(
        job_id,
        system_state,
        chain_verification,
        authority_validation,
        invariant_validation
    )
    adversarial_result = adversarial_validate_system(
        job_id,
        system_state,
        chain_verification,
        authority_validation,
        invariant_validation,
        execution_proof_result
    )
    return resolve_final_system_truth(
        job_id,
        adversarial_result,
        chain_verification,
        invariant_validation,
        authority_validation,
        execution_proof_result,
        system_state
    )


@app.get("/system/architecture")
def system_architecture_endpoint():
    return {
        "planes": SYSTEM_PLANES,
        "layout": ARCHITECTURE_LAYOUT,
        "canonical_execution_flow": RUNTIME_CONTRACT.get("execution_semantics", {}).get("canonical_flow", []),
    }


_register_system_planes()
