import os
from typing import Dict, Any, Optional
from PIL import Image
import pytesseract
from backend.app.core.config import settings

class VisionEngine:
    @classmethod
    def analyze_image(cls, image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Inspects user-uploaded images, extracts OCR text if available,
        and prepares visual metadata for multimodal reasoning.
        """
        if not os.path.exists(image_path):
            return {"error": "Image file not found", "extracted_text": ""}

        try:
            with Image.open(image_path) as img:
                width, height = img.size
                format_ = img.format

            # Attempt OCR extraction
            extracted_text = ""
            try:
                img_for_ocr = Image.open(image_path)
                extracted_text = pytesseract.image_to_string(img_for_ocr).strip()
            except Exception:
                # If tesseract binary is not installed on the system, OCR fails gracefully
                extracted_text = ""

            return {
                "width": width,
                "height": height,
                "format": format_,
                "extracted_text": extracted_text,
                "has_text": len(extracted_text) > 0,
                "analysis_status": "SUCCESS"
            }
        except Exception as e:
            return {
                "error": str(e),
                "extracted_text": "",
                "analysis_status": "FAILED"
            }

vision_engine = VisionEngine()
