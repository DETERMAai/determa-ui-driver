from typing import Any, Dict, List


SAFE_AUTONOMY_PROFILE_V1 = {
    "allowed": [
        "inspect_terminal",
        "terminal_observation",
        "run_tests",
        "terminal.run.tests",
        "open_diff",
        "click_continue",
        "continue",
        "request_approval",
    ],
    "forbidden": [
        "git.commit",
        "git_commit",
        "git.merge",
        "git_merge",
        "commit_code",
        "shell.execute",
        "shell_execute",
        "filesystem.delete",
        "external.network",
        "destructive_shell",
    ],
}


def validate_safe_autonomy(action: str) -> Dict[str, Any]:
    normalized = str(action or "").strip().lower()
    if normalized in SAFE_AUTONOMY_PROFILE_V1["forbidden"]:
        return {
            "allowed": False,
            "action": normalized,
            "reason": "forbidden_in_safe_profile",
            "profile": "safe_autonomy_v1",
        }
    if normalized in SAFE_AUTONOMY_PROFILE_V1["allowed"]:
        return {
            "allowed": True,
            "action": normalized,
            "reason": "allowed_in_safe_profile",
            "profile": "safe_autonomy_v1",
        }
    return {
        "allowed": False,
        "action": normalized,
        "reason": "unknown_action_not_allowed_in_safe_profile",
        "profile": "safe_autonomy_v1",
    }


def get_safe_autonomy_profile() -> Dict[str, List[str]]:
    return SAFE_AUTONOMY_PROFILE_V1
