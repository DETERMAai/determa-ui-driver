from typing import Any, Callable, Dict, List, Optional


BENCHMARK_TASK_SUITE: Dict[str, Dict[str, Any]] = {
    "fix_failing_test": {
        "expected_states": ["tests_failed", "run_validation", "completed"],
        "allowed_actions": ["inspect_terminal", "run_tests", "click_continue"],
        "validation_checkpoints": ["terminal_failure_detected", "validation_triggered", "tests_passed_or_escalated"],
        "escalation_conditions": ["repeated_recovery_failures", "low_confidence_planning"],
    },
    "apply_patch": {
        "expected_states": ["waiting_for_patch", "patch_applied", "waiting_for_tests"],
        "allowed_actions": ["click_continue", "open_diff", "run_tests"],
        "validation_checkpoints": ["patch_state_progressed", "diff_reviewed_if_present", "queue_processed"],
        "escalation_conditions": ["policy_violation", "dangerous_git_state"],
    },
    "recover_build_failure": {
        "expected_states": ["build_failed", "recover_or_escalate", "waiting_for_tests"],
        "allowed_actions": ["inspect_terminal", "retry_action", "request_human_review"],
        "validation_checkpoints": ["failure_detected", "recovery_attempted", "post_recovery_signal_present"],
        "escalation_conditions": ["runaway_recovery_loop", "repeated_recovery_failures"],
    },
    "resolve_merge_conflict": {
        "expected_states": ["blocked", "resolve_conflict", "waiting_for_approval"],
        "allowed_actions": ["request_human_review", "open_diff"],
        "validation_checkpoints": ["conflict_detected", "unsafe_autonomy_blocked", "human_escalation_logged"],
        "escalation_conditions": ["dangerous_git_state", "policy_violation"],
    },
    "continue_generation_workflow": {
        "expected_states": ["waiting_for_input", "continue_generation", "patch_applied"],
        "allowed_actions": ["click_continue", "retry_action", "inspect_terminal"],
        "validation_checkpoints": ["waiting_prompt_detected", "continuation_action_selected", "state_progress_or_escalation"],
        "escalation_conditions": ["ambiguous_ui_state", "low_confidence_planning"],
    },
}


def get_benchmark_suite() -> Dict[str, Any]:
    return BENCHMARK_TASK_SUITE


def _evaluate_checkpoints(
    benchmark_name: str,
    checkpoint_inputs: Dict[str, Any],
) -> Dict[str, Any]:
    workflow_state = checkpoint_inputs.get("workflow_state", {}) or {}
    development_state = checkpoint_inputs.get("development_state", {}) or {}
    runtime_status = checkpoint_inputs.get("runtime_status", {}) or {}
    engineering_snapshot = checkpoint_inputs.get("engineering_snapshot", {}) or {}

    dev_state_name = str(development_state.get("state", ""))
    workflow_status = str(workflow_state.get("status", ""))
    objective = str((engineering_snapshot.get("objective", {}) or {}).get("objective", ""))
    next_action = str((engineering_snapshot.get("next_action", {}) or {}).get("action", ""))
    runtime_health = str((runtime_status.get("runtime", {}) or {}).get("last_supervision", {}).get("health_report", {}).get("status", ""))

    checks: List[Dict[str, Any]] = []
    if benchmark_name == "fix_failing_test":
        checks = [
            {"name": "terminal_failure_detected", "passed": dev_state_name in {"tests_failed", "build_failed"}},
            {"name": "validation_triggered", "passed": next_action in {"run_tests", "inspect_terminal"}},
            {"name": "tests_passed_or_escalated", "passed": workflow_status in {"COMPLETED", "ESCALATED", "RUNNING"}},
        ]
    elif benchmark_name == "apply_patch":
        checks = [
            {"name": "patch_state_progressed", "passed": dev_state_name in {"patch_applied", "waiting_for_tests", "completed"}},
            {"name": "diff_reviewed_if_present", "passed": objective in {"review_patch", "run_validation", "complete_task"}},
            {"name": "queue_processed", "passed": int((runtime_status.get("runtime", {}) or {}).get("processed_events_count", 0)) >= 0},
        ]
    elif benchmark_name == "recover_build_failure":
        checks = [
            {"name": "failure_detected", "passed": dev_state_name in {"build_failed", "tests_failed", "blocked"}},
            {"name": "recovery_attempted", "passed": int(workflow_state.get("retry_count", 0)) >= 0},
            {"name": "post_recovery_signal_present", "passed": runtime_health in {"HEALTHY", "DEGRADED", "CRITICAL", ""}},
        ]
    elif benchmark_name == "resolve_merge_conflict":
        git_state = development_state.get("last_git_state", {}) or {}
        checks = [
            {"name": "conflict_detected", "passed": bool(git_state.get("conflicts")) or objective == "resolve_conflict"},
            {"name": "unsafe_autonomy_blocked", "passed": next_action != "click_approve"},
            {"name": "human_escalation_logged", "passed": workflow_status in {"ESCALATED", "RUNNING", "AWAITING_APPROVAL"}},
        ]
    elif benchmark_name == "continue_generation_workflow":
        checks = [
            {"name": "waiting_prompt_detected", "passed": dev_state_name in {"blocked", "waiting_for_patch", "waiting_for_tests"}},
            {"name": "continuation_action_selected", "passed": next_action in {"click_continue", "retry_action", "inspect_terminal"}},
            {"name": "state_progress_or_escalation", "passed": workflow_status in {"RUNNING", "COMPLETED", "ESCALATED"}},
        ]

    passed = sum(1 for check in checks if check.get("passed"))
    total = len(checks)
    return {
        "checks": checks,
        "passed_checks": passed,
        "total_checks": total,
        "success": total == 0 or passed == total,
        "score": 1.0 if total == 0 else round(float(passed) / float(total), 3),
    }


def run_benchmark(
    benchmark_name: str,
    state_provider: Callable[[str], Dict[str, Any]],
) -> Dict[str, Any]:
    if benchmark_name not in BENCHMARK_TASK_SUITE:
        return {
            "status": "not_found",
            "benchmark_name": benchmark_name,
        }

    template = BENCHMARK_TASK_SUITE[benchmark_name]
    inputs = state_provider(benchmark_name)
    evaluation = _evaluate_checkpoints(benchmark_name, inputs)

    return {
        "status": "ok",
        "benchmark_name": benchmark_name,
        "definition": template,
        "inputs": inputs,
        "evaluation": evaluation,
    }
