import subprocess
from typing import Any, Dict, List


def _run_git(args: List[str]) -> str:
    process = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        return ""
    return (process.stdout or "").strip()


def get_git_state() -> Dict[str, Any]:
    status_output = _run_git(["status", "--porcelain=1", "-b"])
    lines = [line for line in status_output.splitlines() if line.strip()]

    branch = ""
    modified_files: List[str] = []
    staged_files: List[str] = []
    conflicts: List[str] = []
    untracked_files: List[str] = []

    for idx, line in enumerate(lines):
        if idx == 0 and line.startswith("##"):
            branch = line.replace("##", "", 1).strip()
            continue

        if line.startswith("??"):
            untracked_files.append(line[3:].strip())
            continue

        if len(line) < 4:
            continue

        x = line[0]
        y = line[1]
        file_path = line[3:].strip()

        if x in {"U", "A", "D"} and y == "U" or x == "U" or y == "U":
            conflicts.append(file_path)
        if x not in {" ", "?"}:
            staged_files.append(file_path)
        if y not in {" ", "?"}:
            modified_files.append(file_path)

    dirty_workspace = bool(modified_files or staged_files or conflicts or untracked_files)
    return {
        "branch": branch,
        "modified_files": modified_files,
        "staged_files": staged_files,
        "conflicts": conflicts,
        "untracked_files": untracked_files,
        "dirty_workspace": dirty_workspace,
    }


def detect_patch_application_state(git_state: Dict[str, Any]) -> Dict[str, Any]:
    conflicts = list(git_state.get("conflicts", []))
    modified_files = list(git_state.get("modified_files", []))
    staged_files = list(git_state.get("staged_files", []))

    if conflicts:
        return {
            "patch_state": "partial_apply",
            "reason": "merge_conflicts_detected",
        }

    if modified_files or staged_files:
        return {
            "patch_state": "patch_applied",
            "reason": "workspace_changes_detected",
        }

    return {
        "patch_state": "failed_apply",
        "reason": "no_workspace_change_detected",
    }
