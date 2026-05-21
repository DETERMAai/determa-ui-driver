from typing import Any, Dict


def decide_next_action(objective: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
    objective_name = str(objective.get("objective", "")).strip().lower()
    confidence = float(objective.get("confidence", 0.0))
    terminal_state = current_state.get("terminal_state", {})
    ide_state = current_state.get("ide_state", {})

    if objective_name == "request_approval":
        return {
            "action": "click_approve",
            "risk_level": "high",
            "requires_approval": True,
            "reasoning": "Approval prompt detected; governed approval click is required.",
        }

    if objective_name == "continue_generation":
        return {
            "action": "click_continue",
            "risk_level": "low",
            "requires_approval": False,
            "reasoning": "Continuation prompt likely present and low-risk to proceed.",
        }

    if objective_name == "fix_failing_tests":
        return {
            "action": "inspect_terminal",
            "risk_level": "medium",
            "requires_approval": False,
            "reasoning": "Failure signals detected; inspect terminal context first.",
        }

    if objective_name == "run_validation":
        return {
            "action": "run_tests",
            "risk_level": "medium",
            "requires_approval": False,
            "reasoning": "Patch appears applied; execute validation/tests.",
        }

    if objective_name == "review_patch":
        return {
            "action": "open_diff",
            "risk_level": "medium",
            "requires_approval": False,
            "reasoning": "Diff/patch context should be reviewed before progression.",
        }

    if objective_name == "resolve_conflict":
        return {
            "action": "request_human_review",
            "risk_level": "high",
            "requires_approval": True,
            "reasoning": "Merge conflicts are risky and should escalate for review.",
        }

    if objective_name == "complete_task":
        return {
            "action": "abort_workflow",
            "risk_level": "low",
            "requires_approval": False,
            "reasoning": "Workflow appears complete; avoid unnecessary actions.",
        }

    if confidence < 0.6:
        return {
            "action": "request_human_review",
            "risk_level": "high",
            "requires_approval": True,
            "reasoning": "Planner confidence is low; safest next step is escalation.",
        }

    waiting_for_input = bool(terminal_state.get("waiting_for_input")) or bool(ide_state.get("waiting_state"))
    if waiting_for_input:
        return {
            "action": "retry_action",
            "risk_level": "medium",
            "requires_approval": True,
            "reasoning": "Workflow appears paused waiting for action/input; controlled retry suggested.",
        }

    return {
        "action": "inspect_terminal",
        "risk_level": "low",
        "requires_approval": False,
        "reasoning": "Fallback action: gather more terminal evidence before acting.",
    }
