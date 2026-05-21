from perception_service import capture_screen, extract_screen_text
from ui_state_model import build_ui_state


def get_perception_state():
    capture = capture_screen()
    ocr = extract_screen_text(capture.get("path", ""))
    ui_state = build_ui_state(ocr)
    return {
        "capture": capture,
        "ocr": ocr,
        "ui_state": ui_state,
    }
