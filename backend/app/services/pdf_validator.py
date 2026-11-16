"""PDF File Validation, Sanitization & Anti-Malware Protection Engine.

Enforces strict magic byte verification (%PDF-), MIME type checking,
decompression bomb prevention (page limits & file size), and path traversal defense.
"""

import hashlib
import io
import re
from typing import Any, Dict, Optional, Tuple

PDF_MAGIC_BYTES = b"%PDF-"
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 Megabytes
MAX_PAGE_COUNT = 200                    # Maximum pages allowed per document
ALLOWED_MIME_TYPES = {"application/pdf", "application/x-pdf"}


class PDFValidationError(ValueError):
    """Raised when an uploaded document fails security, integrity, or structure validation."""
    pass


class PDFPasswordProtectedError(PDFValidationError):
    """Raised when an uploaded PDF document is encrypted or requires a password."""
    pass


def sanitize_filename(filename: str) -> str:
    """Sanitizes an uploaded filename to defend against path traversal and malicious filenames."""
    if not filename:
        return "document.pdf"

    # Remove path traversal characters (/, \, ..) and null bytes
    clean = re.sub(r"[\x00/\\:*?\"<>|]", "", filename)
    clean = clean.replace("..", "").strip()

    if not clean:
        clean = "document.pdf"

    if not clean.lower().endswith(".pdf"):
        clean += ".pdf"

    return clean[:255]


def validate_pdf_file(
    file_bytes: bytes,
    original_filename: str,
    declared_mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Performs rigorous security and structure checks on an uploaded PDF file buffer.

    Args:
        file_bytes: Raw binary content of the uploaded document.
        original_filename: Client-submitted filename.
        declared_mime_type: Optional HTTP Content-Type header value.

    Returns:
        Dict containing checksum_sha256, total_pages, sanitized_filename, file_size_bytes.

    Raises:
        PDFValidationError: If file fails signature, size, or structure checks.
    """
    if not file_bytes:
        raise PDFValidationError("The uploaded file is empty (0 bytes).")

    file_size = len(file_bytes)

    # 1. File size limit validation
    if file_size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        raise PDFValidationError(
            f"File size ({actual_mb:.1f} MB) exceeds maximum permissible platform limit of {max_mb} MB."
        )

    # 2. Magic byte verification (%PDF-)
    # The PDF specification requires the header to start with %PDF- (within first 1024 bytes)
    header_chunk = file_bytes[:1024]
    magic_idx = header_chunk.find(PDF_MAGIC_BYTES)
    if magic_idx == -1:
        raise PDFValidationError(
            "Invalid file format: Document signature does not match PDF magic bytes (%PDF-). "
            "Renamed executables, archives, or non-PDF files are prohibited."
        )

    # 3. MIME type verification
    if declared_mime_type:
        mime_clean = declared_mime_type.split(";")[0].strip().lower()
        if mime_clean not in ALLOWED_MIME_TYPES and mime_clean != "application/octet-stream":
            raise PDFValidationError(
                f"Invalid MIME type '{declared_mime_type}'. Expected 'application/pdf'."
            )

    # 4. Filename sanitization
    clean_name = sanitize_filename(original_filename)

    # 5. Cryptographic Checksum (SHA-256)
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # 6. PDF Readability and Decompression Bomb Defense via PyMuPDF (fitz)
    total_pages = 0
    try:
        import importlib
        fitz = None
        try:
            fitz = importlib.import_module("fitz")
        except Exception:
            pass

        if fitz is not None:
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            # Check for encryption / password lock
            if doc.is_encrypted:
                raise PDFPasswordProtectedError(
                    "Uploaded PDF is password-protected or encrypted. Please remove password encryption before upload."
                )

            total_pages = len(doc)
            if total_pages == 0:
                raise PDFValidationError("The PDF file does not contain any readable pages.")

            if total_pages > MAX_PAGE_COUNT:
                raise PDFValidationError(
                    f"Document exceeds maximum page threshold: {total_pages} pages detected (limit is {MAX_PAGE_COUNT} pages)."
                )

            # Quick probe of first page to verify rasterization readability
            try:
                _ = doc[0].get_text("text")
            except Exception as probe_err:
                raise PDFValidationError(f"Malformed PDF stream detected on page 1: {str(probe_err)}")

            metadata = doc.metadata or {}
            doc.close()
        else:
            # Fallback if PyMuPDF not available in host environment
            matches = re.findall(rb"/Type\s*/Page\b", file_bytes)
            total_pages = max(1, len(matches))
            metadata = {}

    except (PDFValidationError, PDFPasswordProtectedError):
        raise
    except Exception as exc:
        raise PDFValidationError(f"Corrupted or malformed PDF structure: {str(exc)}")

    return {
        "checksum_sha256": sha256_hash,
        "total_pages": total_pages,
        "sanitized_filename": clean_name,
        "file_size_bytes": file_size,
        "metadata": metadata,
    }

