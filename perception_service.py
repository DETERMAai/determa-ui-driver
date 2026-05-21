import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pyautogui
from PIL import Image

try:
    import pytesseract  # type: ignore
except Exception:
    pytesseract = None


_FRAME_DIR = Path("data/frames")
_LATEST_FRAME_PATH = _FRAME_DIR / "latest_screen.png"


def capture_screen() -> Dict[str, Any]:
    _FRAME_DIR.mkdir(parents=True, exist_ok=True)
    img = pyautogui.screenshot()
    img.save(_LATEST_FRAME_PATH)

    width, height = img.size
    return {
        "image_path": str(_LATEST_FRAME_PATH.resolve()),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "width": int(width),
        "height": int(height),
        "active_window": "",
    }


def extract_screen_text(image: str) -> Dict[str, Any]:
    image_path = Path(image)
    if not image_path.exists():
        return {
            "full_text": "",
            "words": [],
            "ocr_engine": "none",
            "error": "image_not_found",
        }

    if pytesseract is None:
        return {
            "full_text": "",
            "words": [],
            "ocr_engine": "none",
            "error": "pytesseract_not_installed",
        }

    try:
        img = Image.open(image_path)
        full_text = pytesseract.image_to_string(img) or ""
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words = []
        count = len(data.get("text", []))
        for idx in range(count):
            text = str(data["text"][idx]).strip()
            if not text:
                continue
            try:
                confidence = float(data.get("conf", [0])[idx])
            except Exception:
                confidence = 0.0
            words.append(
                {
                    "text": text,
                    "left": int(data.get("left", [0])[idx]),
                    "top": int(data.get("top", [0])[idx]),
                    "width": int(data.get("width", [0])[idx]),
                    "height": int(data.get("height", [0])[idx]),
                    "confidence": confidence,
                }
            )

        return {
            "full_text": full_text,
            "words": words,
            "ocr_engine": "pytesseract",
        }
    except Exception as exc:
        return {
            "full_text": "",
            "words": [],
            "ocr_engine": "pytesseract",
            "error": str(exc),
        }
