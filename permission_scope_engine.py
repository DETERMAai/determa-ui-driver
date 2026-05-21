from typing import Any, Dict, List


SCOPE_LEVELS: Dict[str, List[str]] = {
    "LOW": [
        "ui.click.approve",
        "ui.click.continue",
    ],
    "MEDIUM": [
        "terminal.run.tests",
        "open.diff",
    ],
    "HIGH": [
        "git.commit",
        "git.merge",
    ],
    "CRITICAL": [
        "shell.execute",
        "filesystem.delete",
        "external.network",
    ],
}


ACTION_SCOPE_MAP: Dict[str, str] = {
    "approve": "ui.click.approve",
    "click_approve": "ui.click.approve",
    "continue": "ui.click.continue",
    "click_continue": "ui.click.continue",
    "click": "ui.click.continue",
    "move": "ui.click.continue",
    "type": "ui.click.continue",
    "run_tests": "terminal.run.tests",
    "terminal.run.tests": "terminal.run.tests",
    "open_diff": "open.diff",
    "git_commit": "git.commit",
    "git_merge": "git.merge",
    "shell_execute": "shell.execute",
    "filesystem_delete": "filesystem.delete",
    "external_network": "external.network",
}


def get_required_scope(action: str, runtime_context: Dict[str, Any]) -> str:
    action_key = str(action or "").strip().lower()
    if action_key in ACTION_SCOPE_MAP:
        return ACTION_SCOPE_MAP[action_key]

    semantic_action = str(runtime_context.get("semantic_action", "")).strip().lower()
    if semantic_action in ACTION_SCOPE_MAP:
        return ACTION_SCOPE_MAP[semantic_action]

    return "ui.click.continue"


def _scope_level(scope: str) -> str:
    for level, scopes in SCOPE_LEVELS.items():
        if scope in scopes:
            return level
    return "LOW"


def validate_scope(action: str, runtime_context: Dict[str, Any]) -> Dict[str, Any]:
    required_scope = get_required_scope(action, runtime_context)
    required_level = _scope_level(required_scope)

    allowed_scopes = runtime_context.get("allowed_scopes")
    if not isinstance(allowed_scopes, list):
        allowed_scopes = list(SCOPE_LEVELS["LOW"]) + list(SCOPE_LEVELS["MEDIUM"])

    allow_high = bool(runtime_context.get("allow_high", False))
    allow_critical = bool(runtime_context.get("allow_critical", False))

    if required_scope not in allowed_scopes:
        return {
            "allowed": False,
            "required_scope": required_scope,
            "required_level": required_level,
            "reason": "scope_not_granted",
        }

    if required_level == "HIGH" and not allow_high:
        return {
            "allowed": False,
            "required_scope": required_scope,
            "required_level": required_level,
            "reason": "high_scope_blocked",
        }

    if required_level == "CRITICAL" and not allow_critical:
        return {
            "allowed": False,
            "required_scope": required_scope,
            "required_level": required_level,
            "reason": "critical_scope_blocked",
        }

    return {
        "allowed": True,
        "required_scope": required_scope,
        "required_level": required_level,
        "reason": "scope_valid",
    }


def get_scope_catalog() -> Dict[str, Any]:
    return {
        "scopes": SCOPE_LEVELS,
        "action_scope_map": ACTION_SCOPE_MAP,
    }
