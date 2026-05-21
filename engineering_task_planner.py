from typing import Any, Dict


def infer_engineering_objective(
    terminal_state: Dict[str, Any],
    git_state: Dict[str, Any],
    ide_state: Dict[str, Any],
    workflow_state: Dict[str, Any],
) -> Dict[str, Any]:
    tests_failed = bool(terminal_state.get("tests_failed"))
    tests_passed = bool(terminal_state.get("tests_passed"))
    build_failed = bool(terminal_state.get("build_failed")) or bool(terminal_state.get("runtime_exception"))
    waiting_for_input = bool(terminal_state.get("waiting_for_input"))

    conflicts = list(git_state.get("conflicts", []))
    patch_state = str(git_state.get("patch_state", ""))
    dirty_workspace = bool(git_state.get("dirty_workspace"))

    approval_prompt = bool(ide_state.get("approval_prompt"))
    diff_view = bool(ide_state.get("diff_view"))
    waiting_state = bool(ide_state.get("waiting_state"))

    workflow_status = str(workflow_state.get("status", ""))
    retry_count = int(workflow_state.get("retry_count", 0))

    if conflicts:
        return {
            "objective": "resolve_conflict",
            "confidence": 0.95,
            "reasoning": "Git conflicts are present and must be resolved first.",
        }

    if tests_failed or build_failed:
        return {
            "objective": "fix_failing_tests",
            "confidence": 0.92,
            "reasoning": "Terminal indicates failing tests/build and requires remediation.",
        }

    if approval_prompt:
        return {
            "objective": "request_approval",
            "confidence": 0.9,
            "reasoning": "IDE/UI is waiting for explicit approval action.",
        }

    if diff_view and patch_state in {"patch_applied", "partial_apply"}:
        return {
            "objective": "review_patch",
            "confidence": 0.82,
            "reasoning": "Patch artifacts are present and should be reviewed before continuation.",
        }

    if patch_state == "failed_apply" and waiting_for_input:
        return {
            "objective": "continue_generation",
            "confidence": 0.7,
            "reasoning": "No patch applied yet and terminal appears to wait for continuation.",
        }

    if patch_state == "patch_applied" and not tests_passed:
        return {
            "objective": "run_validation",
            "confidence": 0.86,
            "reasoning": "Patch is applied and validation/tests should run.",
        }

    if tests_passed and (not dirty_workspace or workflow_status == "COMPLETED"):
        return {
            "objective": "complete_task",
            "confidence": 0.88,
            "reasoning": "Validation succeeded and workflow appears complete.",
        }

    if retry_count > 0 or waiting_state:
        return {
            "objective": "continue_generation",
            "confidence": 0.65,
            "reasoning": "Workflow is mid-flight and likely needs continuation/retry.",
        }

    return {
        "objective": "apply_patch",
        "confidence": 0.58,
        "reasoning": "Defaulting to patch progression due to limited strong signals.",
    }
