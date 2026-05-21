import os
from typing import Any, Dict, List


ALLOWED_COMMAND_WHITELIST = [
    "pytest",
    "python -m pytest",
    "npm test",
    "go test",
    "cargo test",
]

DISALLOWED_COMMAND_TOKENS = [
    "rm -rf",
    "del /s",
    "format ",
    "mkfs",
    "shutdown",
    "reboot",
    "powershell -enc",
    "curl ",
    "wget ",
]

RESTRICTED_PATH_MARKERS = [
    "..",
    "/etc",
    "/bin",
    "/usr",
    "/root",
    "c:\\windows",
    "c:\\program files",
]

MAX_RETRY_BOUND = 3


def is_command_whitelisted(command: str) -> bool:
    normalized = str(command or "").strip().lower()
    return any(normalized.startswith(prefix.lower()) for prefix in ALLOWED_COMMAND_WHITELIST)


def filter_shell_command(command: str) -> Dict[str, Any]:
    normalized = str(command or "").strip().lower()
    if not normalized:
        return {"allowed": False, "reason": "empty_command"}

    for token in DISALLOWED_COMMAND_TOKENS:
        if token in normalized:
            return {"allowed": False, "reason": f"disallowed_token:{token}"}

    if not is_command_whitelisted(command):
        return {"allowed": False, "reason": "command_not_whitelisted"}

    return {"allowed": True, "reason": "command_allowed"}


def _paths_from_payload(payload: Dict[str, Any]) -> List[str]:
    paths: List[str] = []
    for key in ("path", "paths", "target_path", "target_paths"):
        value = payload.get(key)
        if isinstance(value, str):
            paths.append(value)
        elif isinstance(value, list):
            paths.extend(str(item) for item in value)
    return paths


def _validate_paths(paths: List[str]) -> Dict[str, Any]:
    normalized_paths = [str(path).strip().lower().replace("/", os.sep.lower()) for path in paths if str(path).strip()]
    for path in normalized_paths:
        for marker in RESTRICTED_PATH_MARKERS:
            if marker.replace("/", os.sep.lower()) in path:
                return {"allowed": False, "reason": f"restricted_path:{marker}"}
    return {"allowed": True, "reason": "paths_allowed"}


def validate_sandbox_execution(action: str, payload: Dict[str, Any], runtime_context: Dict[str, Any]) -> Dict[str, Any]:
    retry_count = int(runtime_context.get("retry_count", 0))
    if retry_count > MAX_RETRY_BOUND:
        return {"allowed": False, "reason": "retry_bound_exceeded"}

    action_key = str(action or "").strip().lower()
    if action_key in {"shell.execute", "shell_execute"}:
        command_check = filter_shell_command(str(payload.get("command", "")))
        if not command_check.get("allowed", False):
            return {"allowed": False, "reason": command_check.get("reason", "command_blocked")}

    if action_key in {"filesystem.delete", "external.network"} and not bool(runtime_context.get("allow_critical", False)):
        return {"allowed": False, "reason": "critical_action_blocked"}

    path_check = _validate_paths(_paths_from_payload(payload))
    if not path_check.get("allowed", False):
        return {"allowed": False, "reason": path_check.get("reason", "path_blocked")}

    return {"allowed": True, "reason": "sandbox_valid"}
