from typing import Any, Dict, List


def analyze_terminal_output(text: str) -> Dict[str, Any]:
    raw = str(text or "")
    lowered = raw.lower()
    lines: List[str] = [line.strip() for line in raw.splitlines() if line.strip()]

    tests_passed = any(token in lowered for token in ("tests passed", "passed in", "ok", "all tests passed"))
    tests_failed = any(token in lowered for token in ("tests failed", "failed", "assertionerror", "failures"))
    build_running = any(token in lowered for token in ("building", "compiling", "running build"))
    build_failed = any(token in lowered for token in ("build failed", "compilation error", "syntaxerror"))
    install_running = any(token in lowered for token in ("installing", "downloading", "resolving packages", "pip install"))
    install_completed = any(token in lowered for token in ("installed", "installation complete", "successfully installed"))
    waiting_for_input = any(token in lowered for token in ("press enter", "continue?", "(y/n)", "waiting for input", "confirm"))
    runtime_exception = any(token in lowered for token in ("exception", "traceback", "runtimeerror", "unhandled"))
    stack_trace = any(token in lowered for token in ("traceback", "stack trace", " at "))

    if tests_passed:
        primary_state = "tests_passed"
    elif tests_failed:
        primary_state = "tests_failed"
    elif build_failed:
        primary_state = "build_failed"
    elif runtime_exception:
        primary_state = "runtime_exception"
    elif waiting_for_input:
        primary_state = "waiting_for_input"
    elif build_running:
        primary_state = "build_running"
    elif install_running:
        primary_state = "install_running"
    elif install_completed:
        primary_state = "install_completed"
    else:
        primary_state = "idle"

    return {
        "primary_state": primary_state,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "build_running": build_running,
        "build_failed": build_failed,
        "install_running": install_running,
        "install_completed": install_completed,
        "waiting_for_input": waiting_for_input,
        "runtime_exception": runtime_exception,
        "stack_trace": stack_trace,
        "line_count": len(lines),
    }
