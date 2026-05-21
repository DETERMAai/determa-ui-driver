from typing import Any, Dict


def validate_development_action(action: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    action_name = str(action.get("action", "")).strip().lower()
    git_state = state.get("git_state", {})
    terminal_state = state.get("terminal_state", {})
    ide_state = state.get("ide_state", {})

    conflicts = list(git_state.get("conflicts", []))
    tests_failed = bool(terminal_state.get("tests_failed")) or bool(terminal_state.get("build_failed"))
    diff_view = bool(ide_state.get("diff_view"))
    approval_prompt = bool(ide_state.get("approval_prompt"))

    if action_name == "click_approve":
        if not approval_prompt:
            return {
                "allowed": False,
                "policy_reason": "Auto-approve blocked: no explicit approval prompt detected.",
                "requires_human": True,
            }
        if not diff_view:
            return {
                "allowed": False,
                "policy_reason": "Auto-approve blocked: unknown or unreviewed diff context.",
                "requires_human": True,
            }

    if action_name == "run_tests" and tests_failed:
        # Running tests is still allowed; this branch protects against ignoring failures in downstream actioning.
        return {
            "allowed": True,
            "policy_reason": "Allowed: tests should be rerun/validated after failure.",
            "requires_human": False,
        }

    if conflicts and action_name not in {"request_human_review", "inspect_terminal"}:
        return {
            "allowed": False,
            "policy_reason": "Blocked: merge conflicts present; must not bypass conflict handling.",
            "requires_human": True,
        }

    if action_name in {"commit_code", "auto_commit"}:
        return {
            "allowed": False,
            "policy_reason": "Blocked: automatic commits are disallowed by policy.",
            "requires_human": True,
        }

    if tests_failed and action_name in {"click_continue", "click_approve"}:
        return {
            "allowed": False,
            "policy_reason": "Blocked: failing tests/build must not be ignored.",
            "requires_human": True,
        }

    return {
        "allowed": True,
        "policy_reason": "Allowed: action is compliant with development policy.",
        "requires_human": False,
    }
