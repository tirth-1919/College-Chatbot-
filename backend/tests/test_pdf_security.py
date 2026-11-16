"""PDF & File Upload Security Unit Tests."""

import pytest
from app.services.pdf_validator import (
    validate_pdf_file,
    sanitize_filename,
    PDFValidationError,
    PDF_MAGIC_BYTES,
)


def test_magic_byte_spoofing_detection():
    """Asserts that non-PDF files disguised as .pdf (e.g. PE binaries, zip files) are rejected."""
    # Spoofed file: Starts with Windows PE magic bytes 'MZ', but named brochure.pdf
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"

    with pytest.raises(PDFValidationError) as exc:
        validate_pdf_file(fake_exe_bytes, "brochure.pdf", "application/pdf")
    assert "Document signature does not match PDF magic bytes" in str(exc.value)

    # Spoofed file: Starts with ZIP/PK magic bytes 'PK\x03\x04'
    fake_zip_bytes = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
    with pytest.raises(PDFValidationError) as exc:
        validate_pdf_file(fake_zip_bytes, "archive.pdf", "application/pdf")
    assert "magic bytes" in str(exc.value).lower()


def test_empty_file_rejection():
    """Verifies that 0-byte uploads are rejected immediately."""
    with pytest.raises(PDFValidationError) as exc:
        validate_pdf_file(b"", "empty.pdf")
    assert "empty" in str(exc.value).lower()


def test_oversized_file_rejection():
    """Verifies that files exceeding 50 MB are blocked to prevent memory exhaustion."""
    # 51 MB buffer simulation
    fifty_one_mb = 51 * 1024 * 1024
    oversized_dummy = bytearray(fifty_one_mb)
    oversized_dummy[:5] = PDF_MAGIC_BYTES

    with pytest.raises(PDFValidationError) as exc:
        validate_pdf_file(bytes(oversized_dummy), "huge.pdf")
    assert "exceeds maximum permissible" in str(exc.value).lower()


def test_filename_path_traversal_sanitization():
    """Verifies that malicious path traversal filenames are cleansed safely."""
    # Linux path traversal
    assert sanitize_filename("../../../etc/shadow.pdf") == "etcshadow.pdf"
    assert sanitize_filename("../../boot.ini.pdf") == "boot.ini.pdf"

    # Windows path traversal
    assert sanitize_filename("..\\..\\Windows\\System32\\cmd.exe.pdf") == "WindowsSystem32cmd.exe.pdf"

    # Null byte injection
    assert sanitize_filename("safe_document.pdf\x00.exe") == "safe_document.pdf.exe.pdf"

    # Extension enforcement
    assert sanitize_filename("admission_form") == "admission_form.pdf"


def test_valid_pdf_buffer_acceptance():
    """Verifies that a well-formed PDF buffer passes all signature and integrity checks."""
    valid_pdf_header = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    res = validate_pdf_file(valid_pdf_header, "admissions_2026.pdf", "application/pdf")

    assert res["sanitized_filename"] == "admissions_2026.pdf"
    assert res["file_size_bytes"] == len(valid_pdf_header)
    assert len(res["checksum_sha256"]) == 64

