from typing import Any, Dict, List


SAFE_AUTONOMY_ACTIONS = {
    "continue",
    "click_continue",
    "run_tests",
    "terminal.run.tests",
    "open_diff",
    "inspect_terminal",
    "screen_observe",
    "click",
    "move",
    "type",
}

RESTRICTED_ACTIONS = {
    "git.commit",
    "git_merge",
    "git.merge",
    "commit_code",
    "shell.execute",
    "shell_execute",
    "filesystem.delete",
    "external.network",
    "destructive_shell",
}


def _normalize_action(action: str, context: Dict[str, Any]) -> str:
    action_value = str(action or "").strip().lower()
    semantic = str(context.get("semantic_action", "")).strip().lower()
    if semantic:
        return semantic
    return action_value


def validate_autonomy_boundary(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
    normalized = _normalize_action(action, context)
    allow_restricted = bool(context.get("allow_restricted_autonomy", False))

    if normalized in RESTRICTED_ACTIONS and not allow_restricted:
        return {
            "allowed": False,
            "zone": "RESTRICTED",
            "action": normalized,
            "reason": "restricted_action_requires_human",
            "requires_human": True,
        }

    if normalized in SAFE_AUTONOMY_ACTIONS:
        return {
            "allowed": True,
            "zone": "SAFE_AUTONOMY",
            "action": normalized,
            "reason": "safe_action_allowed",
            "requires_human": False,
        }

    # Unknown actions are treated conservatively as restricted.
    if not allow_restricted:
        return {
            "allowed": False,
            "zone": "RESTRICTED",
            "action": normalized,
            "reason": "unknown_action_restricted",
            "requires_human": True,
        }

    return {
        "allowed": True,
        "zone": "RESTRICTED",
        "action": normalized,
        "reason": "restricted_override_allowed",
        "requires_human": True,
    }


def get_autonomy_policy() -> Dict[str, List[str]]:
    return {
        "safe_autonomy": sorted(list(SAFE_AUTONOMY_ACTIONS)),
        "restricted": sorted(list(RESTRICTED_ACTIONS)),
    }
