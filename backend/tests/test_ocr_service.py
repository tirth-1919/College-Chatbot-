import sys
from types import SimpleNamespace
from unittest.mock import Mock

import fitz

from app.services.ocr_service import TesseractOCREngine, ocr_engine
from app.services.pdf_processor import pdf_processor


def test_process_pixmap_uses_pil_image_module(monkeypatch):
    image = object()
    image_module = SimpleNamespace(open=Mock(return_value=image))
    monkeypatch.setitem(sys.modules, "PIL.Image", image_module)
    engine = TesseractOCREngine()
    process_image = Mock(
        return_value={"text": "recognized text", "confidence": 91.0, "word_count": 2, "error": None}
    )
    monkeypatch.setattr(engine, "process_image", process_image)
    pixmap = SimpleNamespace(tobytes=Mock(return_value=b"png-bytes"))

    result = engine.process_pixmap(pixmap)

    image_module.open.assert_called_once()
    process_image.assert_called_once_with(image, lang=None)
    assert result["text"] == "recognized text"


def test_unavailable_ocr_returns_no_extracted_text(monkeypatch):
    engine = TesseractOCREngine()
    monkeypatch.setattr(engine, "_tesseract_available", False)

    result = engine.process_image(object())

    assert result["text"] == ""
    assert result["word_count"] == 0
    assert result["error"] == "Tesseract OCR executable not found on host system."


def test_pdf_processor_does_not_accept_ocr_text_with_error(monkeypatch):
    document = fitz.open()
    document.new_page()
    pdf_bytes = document.tobytes()
    document.close()
    monkeypatch.setattr(
        ocr_engine,
        "process_pixmap",
        lambda pixmap: {
            "text": "placeholder text must not be indexed",
            "confidence": 0.0,
            "word_count": 0,
            "error": "Tesseract OCR executable not found on host system.",
        },
    )

    result = pdf_processor.process_pdf(pdf_bytes, "scanned.pdf")

    assert result["pages"][0].extracted_text == ""
    assert result["pages"][0].ocr_applied is False
    assert result["ocr_applied"] is False
