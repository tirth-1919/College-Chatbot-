"""Supabase Private Storage Service.

Manages private, encrypted storage of institutional documents in Supabase Storage
with tenant-scoped directory paths, short-lived signed URLs, and local offline fallback.
"""

import logging
import os
from pathlib import Path
from typing import Optional
import uuid

from app.core.config import settings

logger = logging.getLogger("college_chatbot.storage")


class DocumentStorageService:
    """Interface for private document storage operations."""

    def __init__(self):
        self.bucket_name = settings.SUPABASE_STORAGE_BUCKET_DOCS
        self.supabase_url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.local_storage_dir = Path("storage/college-documents")
        self.local_storage_dir.mkdir(parents=True, exist_ok=True)
        self._supabase_client = None

    @property
    def is_supabase_configured(self) -> bool:
        """Checks if real Supabase Cloud credentials are configured."""
        return (
            self.supabase_url
            and not self.supabase_url.startswith("https://placeholder")
            and self.service_key
            and not self.service_key.startswith("placeholder")
        )

    def _get_supabase(self):
        """Lazy initialization of Supabase client."""
        if self._supabase_client is None and self.is_supabase_configured:
            try:
                import importlib
                supabase_mod = importlib.import_module("supabase")
                create_client = getattr(supabase_mod, "create_client")
                self._supabase_client = create_client(self.supabase_url, self.service_key)
            except Exception as e:
                logger.error("Could not initialize configured Supabase Storage client: %s", str(e))
        if self.is_supabase_configured and self._supabase_client is None:
            raise RuntimeError("Supabase Storage is configured but the client could not be initialized.")
        return self._supabase_client

    def build_storage_path(self, college_id: uuid.UUID, document_id: uuid.UUID) -> str:
        """Generates tenant-scoped relative storage path."""
        return f"{college_id}/{document_id}.pdf"

    async def upload_file(
        self,
        college_id: uuid.UUID,
        document_id: uuid.UUID,
        file_bytes: bytes,
        mime_type: str = "application/pdf",
    ) -> str:
        """Uploads a PDF file into private storage.

        Returns:
            Relative storage path string.
        """
        storage_path = self.build_storage_path(college_id, document_id)

        # 1. Upload to Supabase when configured. Never report a cloud upload as
        # successful after silently writing only to the local development disk.
        supabase = self._get_supabase()
        if supabase:
            try:
                supabase.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=file_bytes,
                    # A collision must fail rather than overwrite an existing
                    # document object; this also makes post-upload cleanup safe.
                    file_options={"content-type": mime_type, "upsert": "false"},
                )
                logger.info("Uploaded document %s to Supabase Storage bucket %s", storage_path, self.bucket_name)
                return storage_path
            except Exception as e:
                logger.error("Supabase Storage upload failed for bucket %s path %s: %s", self.bucket_name, storage_path, str(e))
                raise RuntimeError("Document could not be uploaded to private storage.") from e

        # 2. Local Secure Storage Fallback
        target_path = self.local_storage_dir / str(college_id) / f"{document_id}.pdf"
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        logger.info("Saved document %s to local secure fallback storage at %s", storage_path, target_path)
        return storage_path

    async def get_file_bytes(self, college_id: uuid.UUID, storage_path: str) -> bytes:
        """Retrieves raw binary file content for text and OCR processing."""
        # 1. Attempt Supabase Storage Download
        supabase = self._get_supabase()
        if supabase:
            try:
                data = supabase.storage.from_(self.bucket_name).download(storage_path)
                if data:
                    return data
            except Exception as e:
                logger.warning("Supabase Storage download failed for bucket %s path %s: %s", self.bucket_name, storage_path, str(e))
                raise FileNotFoundError(
                    f"Document binary not found in configured storage bucket '{self.bucket_name}'."
                ) from e
            raise FileNotFoundError(
                f"Document binary not found in configured storage bucket '{self.bucket_name}'."
            )

        # 2. Local Fallback Check
        target_path = self.local_storage_dir / storage_path
        if target_path.exists():
            with open(target_path, "rb") as f:
                return f.read()

        raise FileNotFoundError(f"Document binary not found at storage path '{storage_path}'.")

    async def get_signed_url(
        self,
        college_id: uuid.UUID,
        storage_path: str,
        expires_in: int = 3600,
    ) -> str:
        """Generates a short-lived signed URL for authorized viewing or downloading.

        Default expiration: 3600 seconds (1 hour).
        """
        supabase = self._get_supabase()
        if supabase:
            try:
                signed = supabase.storage.from_(self.bucket_name).create_signed_url(
                    path=storage_path,
                    expires_in=expires_in,
                )
                if isinstance(signed, dict) and "signedURL" in signed:
                    return signed["signedURL"]
            except Exception as e:
                logger.warning("Supabase signed URL generation failed: %s", str(e))
                raise FileNotFoundError(
                    f"Document object was not found in configured storage bucket '{self.bucket_name}'."
                ) from e

            raise RuntimeError("Supabase did not return a signed URL for the stored document.")

        # Secure local preview endpoint alias
        return f"/api/v1/college-admin/documents/raw/{storage_path}"

    async def delete_file(self, college_id: uuid.UUID, storage_path: str) -> bool:
        """Permanently removes a document file from private storage."""
        deleted = False

        supabase = self._get_supabase()
        if supabase:
            try:
                supabase.storage.from_(self.bucket_name).remove([storage_path])
                deleted = True
            except Exception as e:
                logger.warning("Supabase Storage delete failed: %s", str(e))
                return False

        if not supabase:
            target_path = self.local_storage_dir / storage_path
            if target_path.exists():
                target_path.unlink()
                deleted = True

        return deleted


# Singleton instance
document_storage_service = DocumentStorageService()

