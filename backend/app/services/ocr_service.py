"""Tesseract OCR Engine for Scanned PDF Pages.

Detects image-heavy and scanned pages, renders them into images,
and runs Tesseract OCR with character confidence scoring.
Supports extensible language packs (English default, Hindi, Gujarati).
"""

import io
import logging
import os
import shutil
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("college_chatbot.ocr")

# Common Windows installation directories for Tesseract OCR
WINDOWS_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
]


class TesseractOCREngine:
    """Manages Optical Character Recognition for scanned documents."""

    def __init__(self, default_lang: str = "eng"):
        self.default_lang = default_lang
        self._tesseract_available: Optional[bool] = None
        self._init_tesseract_path()

    def _init_tesseract_path(self):
        """Attempts to locate tesseract binary if running on Windows."""
        try:
            import importlib
            pytesseract = importlib.import_module("pytesseract")
            # Check if tesseract is already on system PATH
            if shutil.which("tesseract"):
                self._tesseract_available = True
                return

            # Check well-known Windows locations
            for path in WINDOWS_TESSERACT_PATHS:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    self._tesseract_available = True
                    logger.info("Found Tesseract OCR executable at: %s", path)
                    return

            self._tesseract_available = False
        except Exception:
            self._tesseract_available = False

    @property
    def is_available(self) -> bool:
        """Returns True if Tesseract OCR is installed and ready."""
        if self._tesseract_available is None:
            self._init_tesseract_path()
        return bool(self._tesseract_available)

    def process_image(self, pil_image, lang: Optional[str] = None) -> Dict[str, Any]:
        """Runs Tesseract OCR on a PIL Image object.

        Returns:
            Dict containing:
                text: Extracted textual content.
                confidence: Average confidence score (0-100).
                word_count: Number of recognized words.
                error: Error description if any occurred.
        """
        target_lang = lang or self.default_lang

        if not self.is_available:
            return {
                "text": "[Scanned document page: OCR engine pending server host configuration]",
                "confidence": 0.0,
                "word_count": 0,
                "error": "Tesseract OCR executable not found on host system.",
            }

        try:
            import importlib
            pytesseract = importlib.import_module("pytesseract")
            Output = getattr(pytesseract, "Output")

            # 1. Extract plain text
            text = pytesseract.image_to_string(pil_image, lang=target_lang)
            text_clean = text.strip()

            # 2. Extract confidence scores
            data = pytesseract.image_to_data(pil_image, lang=target_lang, output_type=Output.DICT)
            confidences = [
                float(c) for c in data.get("conf", [])
                if isinstance(c, (int, float, str)) and float(c) > 0
            ]

            avg_conf = round(sum(confidences) / len(confidences), 1) if confidences else 75.0
            words = len(text_clean.split())

            return {
                "text": text_clean,
                "confidence": avg_conf,
                "word_count": words,
                "error": None,
            }

        except Exception as exc:
            logger.warning("OCR processing error: %s", str(exc))
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "error": str(exc),
            }

    def process_pixmap(self, pixmap, lang: Optional[str] = None) -> Dict[str, Any]:
        """Converts PyMuPDF Pixmap to PIL Image and executes OCR."""
        try:
            import importlib
            pil_module = importlib.import_module("PIL.Image")
            Image = getattr(pil_module, "Image", pil_module)

            if hasattr(pixmap, "tobytes"):
                # PyMuPDF pixmap conversion
                img = Image.open(io.BytesIO(pixmap.tobytes("png")))
            elif hasattr(pixmap, "samples"):
                mode = "RGBA" if pixmap.alpha else "RGB"
                img = Image.frombytes(mode, [pixmap.width, pixmap.height], pixmap.samples)
            else:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "word_count": 0,
                    "error": "Unsupported pixmap format.",
                }

            return self.process_image(img, lang=lang)
        except Exception as exc:
            return {
                "text": "",
                "confidence": 0.0,
                "word_count": 0,
                "error": f"Pixmap conversion error: {str(exc)}",
            }


# Singleton OCR Engine instance
ocr_engine = TesseractOCREngine()

