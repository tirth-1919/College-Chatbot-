import os
import hashlib
from typing import Tuple, Dict, Any
from backend.app.core.config import settings

class FileSecurityValidator:
    MIME_WHITELIST = {
        "pdf": ["application/pdf"],
        "docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"],
        "xlsx": ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"],
        "csv": ["text/csv", "text/plain"],
        "txt": ["text/plain"],
        "md": ["text/markdown", "text/plain"],
        "png": ["image/png"],
        "jpg": ["image/jpeg"],
        "jpeg": ["image/jpeg"],
        "webp": ["image/webp"]
    }

    MAGIC_SIGNATURES = {
        b"%PDF": "pdf",
        b"\x89PNG\r\n\x1a\n": "png",
        b"\xff\xd8\xff": "jpg",
        b"RIFF": "webp",
        b"PK\x03\x04": "zip_based"  # docx, xlsx are zip archives
    }

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> Tuple[bool, str, Dict[str, Any]]:
        # 1. Size Check
        if len(content) > settings.MAX_FILE_SIZE_BYTES:
            return False, f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB", {}

        # 2. Path Traversal Check
        clean_filename = os.path.basename(filename)
        if ".." in filename or "/" in filename or "\\" in filename:
            clean_filename = os.path.basename(clean_filename)

        # 3. Extension Whitelist
        ext = clean_filename.split(".")[-1].lower() if "." in clean_filename else ""
        if ext not in settings.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file extension: .{ext}", {}

        # 4. Magic Header Check for binary formats
        if ext in ["pdf", "png", "jpg", "jpeg", "webp"]:
            valid_magic = False
            for sig, f_type in cls.MAGIC_SIGNATURES.items():
                if content.startswith(sig):
                    valid_magic = True
                    break
            if not valid_magic:
                return False, "File header does not match declared extension.", {}

        # 5. Archive Bomb Check (for docx / xlsx zip archives)
        if ext in ["docx", "xlsx"]:
            if len(content) > 15 * 1024 * 1024:
                return False, "Office document exceeds safe decompression limits.", {}

        content_hash = hashlib.sha256(content).hexdigest()

        return True, "VALID", {
            "clean_filename": clean_filename,
            "extension": ext,
            "size": len(content),
            "content_hash": content_hash
        }

file_validator = FileSecurityValidator()
