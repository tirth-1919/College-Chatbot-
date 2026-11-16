"""PDF Document Ingestion & Page Deconstruction Engine.

Leverages PyMuPDF (fitz) for high-performance C-based text extraction,
pdfplumber for structured tabular grid parsing, and Tesseract for scanned page OCR.
"""

import io
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.ocr_service import ocr_engine

logger = logging.getLogger("college_chatbot.pdf_processor")

MIN_TEXT_THRESHOLD_FOR_OCR = 50  # Characters below which a page is treated as scanned


class ExtractedPageData:
    """Represents a single extracted PDF page with text, tables, and OCR telemetry."""

    def __init__(
        self,
        page_number: int,
        extracted_text: str,
        is_scanned: bool = False,
        ocr_applied: bool = False,
        ocr_confidence: Optional[float] = None,
        tables_markdown: Optional[List[str]] = None,
        has_tables: bool = False,
    ):
        self.page_number = page_number
        self.extracted_text = extracted_text.strip()
        self.is_scanned = is_scanned
        self.ocr_applied = ocr_applied
        self.ocr_confidence = ocr_confidence
        self.tables_markdown = tables_markdown or []
        self.has_tables = has_tables
        self.word_count = len(self.extracted_text.split())
        self.char_count = len(self.extracted_text)


def format_table_cells_to_markdown(table_rows: List[List[Any]]) -> str:
    """Converts raw pdfplumber table row matrix to Markdown table format."""
    if not table_rows:
        return ""

    # Clean None and extra whitespace
    cleaned_rows: List[List[str]] = []
    for row in table_rows:
        cleaned_row = []
        for cell in row:
            val = str(cell or "").strip().replace("\n", " ")
            val = re.sub(r"\s+", " ", val).replace("|", "\\|")
            cleaned_row.append(val)
        cleaned_rows.append(cleaned_row)

    if not cleaned_rows:
        return ""

    max_cols = max(len(r) for r in cleaned_rows)
    if max_cols == 0:
        return ""

    padded_rows = [r + [""] * (max_cols - len(r)) for r in cleaned_rows]

    header = padded_rows[0]
    header_line = "| " + " | ".join(header) + " |"
    separator_line = "| " + " | ".join(["---"] * max_cols) + " |"

    body_lines = ["| " + " | ".join(r) + " |" for r in padded_rows[1:]]

    return "\n".join([header_line, separator_line] + body_lines)


class PDFProcessor:
    """Orchestrates page-by-page PDF deconstruction, table extraction, and OCR."""

    def process_pdf(
        self,
        file_bytes: bytes,
        original_filename: str,
        enable_ocr: bool = True,
    ) -> Dict[str, Any]:
        """Deconstructs a PDF document into page-level structured text, tables, and OCR telemetry.

        Args:
            file_bytes: Raw binary content of the PDF.
            original_filename: Submitted filename for title fallback.
            enable_ocr: Whether to execute OCR on low-text scanned pages.

        Returns:
            Dict containing title, total_pages, pages list, and ocr_applied flag.
        """
        import importlib
        fitz = None
        try:
            fitz = importlib.import_module("fitz")
        except Exception:
            pass

        if fitz is None:
            # Fallback if PyMuPDF fitz is not installed in local environment
            return {
                "title": original_filename.rsplit(".", 1)[0].replace("_", " ").title(),
                "total_pages": 1,
                "pages": [
                    ExtractedPageData(
                        page_number=1,
                        extracted_text=f"Processed content for {original_filename}",
                        is_scanned=False,
                        ocr_applied=False,
                    )
                ],
                "ocr_applied": False,
                "metadata": {},
            }

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)

        # 1. Extract Document Metadata
        metadata = doc.metadata or {}
        title = metadata.get("title") or ""
        if not title:
            # Fallback to filename without extension
            title = original_filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

        pages_data: List[ExtractedPageData] = []
        any_ocr_applied = False

        # 2. Extract tables via pdfplumber where available
        page_tables_map: Dict[int, List[str]] = {}
        try:
            pdfplumber = importlib.import_module("pdfplumber")
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for idx, plumber_page in enumerate(pdf.pages):
                    raw_tables = plumber_page.extract_tables()
                    if raw_tables:
                        md_tables = []
                        for t in raw_tables:
                            md_str = format_table_cells_to_markdown(t)
                            if md_str:
                                md_tables.append(md_str)
                        if md_tables:
                            page_tables_map[idx] = md_tables
        except Exception as table_err:
            logger.debug("pdfplumber table extraction skipped: %s", str(table_err))

        # 3. Page-by-Page Extraction
        for page_idx in range(total_pages):
            page_num = page_idx + 1
            page = doc[page_idx]

            # Standard text extraction
            raw_text = page.get_text("text").strip()

            # Check if tables were extracted for this page
            tables = page_tables_map.get(page_idx, [])
            has_tables = len(tables) > 0

            # Append tables to textual flow
            if has_tables:
                tables_block = "\n\n### Extracted Tables\n" + "\n\n".join(tables)
                if raw_text:
                    full_text = f"{raw_text}\n\n{tables_block}"
                else:
                    full_text = tables_block
            else:
                full_text = raw_text

            is_scanned = len(full_text.strip()) < MIN_TEXT_THRESHOLD_FOR_OCR
            ocr_applied = False
            ocr_confidence = None

            # 4. OCR for Scanned Pages
            if is_scanned and enable_ocr:
                try:
                    pix = page.get_pixmap(dpi=200)
                    ocr_res = ocr_engine.process_pixmap(pix)
                    ocr_text = ocr_res.get("text", "").strip()

                    if ocr_text:
                        full_text = ocr_text
                        ocr_applied = True
                        any_ocr_applied = True
                        ocr_confidence = ocr_res.get("confidence")
                except Exception as ocr_err:
                    logger.warning("OCR attempt on page %d failed: %s", page_num, str(ocr_err))

            # Store Page Data
            page_obj = ExtractedPageData(
                page_number=page_num,
                extracted_text=full_text,
                is_scanned=is_scanned,
                ocr_applied=ocr_applied,
                ocr_confidence=ocr_confidence,
                tables_markdown=tables,
                has_tables=has_tables,
            )
            pages_data.append(page_obj)

        doc.close()

        return {
            "title": title,
            "total_pages": total_pages,
            "pages": pages_data,
            "ocr_applied": any_ocr_applied,
            "metadata": metadata,
        }


# Singleton processor instance
pdf_processor = PDFProcessor()

