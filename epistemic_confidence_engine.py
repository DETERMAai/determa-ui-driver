from typing import Any, Dict, List


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _avg(values: List[float]) -> float:
    clean = [float(v) for v in values]
    if not clean:
        return 0.0
    return sum(clean) / float(len(clean))


def evaluate_epistemic_confidence(
    capture: Dict[str, Any],
    ocr: Dict[str, Any],
    ui_state: Dict[str, Any],
    governance_state: Dict[str, Any],
    execution_state: Dict[str, Any],
) -> Dict[str, Any]:
    capture_data = dict(capture or {})
    ocr_data = dict(ocr or {})
    ui_data = dict(ui_state or {})
    gov_data = dict(governance_state or {})
    exec_data = dict(execution_state or {})

    width = int(capture_data.get("width", 0) or 0)
    height = int(capture_data.get("height", 0) or 0)
    perception_certainty = 1.0 if width > 0 and height > 0 else 0.0

    words = list(ocr_data.get("words", []))
    raw_conf = []
    for word in words:
        try:
            conf = float(word.get("confidence", 0.0))
        except Exception:
            conf = 0.0
        if conf < 0:
            conf = 0.0
        if conf > 1.0:
            conf = conf / 100.0
        raw_conf.append(_clamp(conf))
    ocr_reliability = _avg(raw_conf) if raw_conf else 0.0
    if str(ocr_data.get("ocr_engine", "")) == "none":
        ocr_reliability = 0.0

    detected_actions = list(ui_data.get("detected_actions", []))
    buttons = list(ui_data.get("buttons", []))
    dialogs = list(ui_data.get("dialogs", []))
    terminal_lines = list(ui_data.get("terminal_lines", []))
    semantic_interpretation_confidence = _clamp(
        (0.40 if len(detected_actions) > 0 else 0.0)
        + (0.25 if len(buttons) > 0 else 0.0)
        + (0.15 if len(dialogs) > 0 else 0.0)
        + (0.20 if len(terminal_lines) > 0 else 0.0)
    )

    authority_valid = bool(gov_data.get("authority_valid", False))
    invariants_valid = bool(gov_data.get("invariants_valid", False))
    replay_anomaly_count = int(gov_data.get("replay_anomaly_count", 0) or 0)
    governance_confidence = _clamp(
        (0.45 if authority_valid else 0.0)
        + (0.40 if invariants_valid else 0.0)
        + max(0.0, 0.15 - min(0.15, replay_anomaly_count * 0.03))
    )

    known_jobs = int(exec_data.get("job_count", 0) or 0)
    executed_jobs = int(exec_data.get("executed_job_count", 0) or 0)
    unknown_jobs = int(exec_data.get("unknown_job_count", 0) or 0)
    execution_confidence = _clamp(
        (0.35 if known_jobs > 0 else 0.15)
        + (0.35 if executed_jobs > 0 else 0.0)
        + max(0.0, 0.30 - min(0.30, unknown_jobs * 0.05))
    )

    overall = _clamp(
        perception_certainty * 0.18
        + ocr_reliability * 0.22
        + semantic_interpretation_confidence * 0.22
        + governance_confidence * 0.22
        + execution_confidence * 0.16
    )

    false_confidence_risk = _clamp(
        max(0.0, governance_confidence - semantic_interpretation_confidence) * 0.7
        + max(0.0, governance_confidence - ocr_reliability) * 0.3
    )

    return {
        "status": "ok",
        "confidence": {
            "perception_certainty": round(perception_certainty, 4),
            "ocr_reliability": round(ocr_reliability, 4),
            "semantic_interpretation_confidence": round(semantic_interpretation_confidence, 4),
            "governance_confidence": round(governance_confidence, 4),
            "execution_confidence": round(execution_confidence, 4),
            "overall_confidence": round(overall, 4),
        },
        "false_confidence_risk": round(false_confidence_risk, 4),
        "confidence_status": (
            "HIGH" if overall >= 0.75 else
            "MEDIUM" if overall >= 0.45 else
            "LOW"
        ),
    }
