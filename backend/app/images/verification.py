import hashlib
import os
from typing import Dict, Any, Tuple
from urllib.parse import urlparse

class ImageVerificationEngine:
    ALLOWED_DOMAINS = {"aitindia.in", "www.aitindia.in"}

    @classmethod
    def verify_source(cls, source_url: str) -> Tuple[bool, str]:
        """
        Ensures the image originates strictly from official AIT authorized domains.
        """
        parsed = urlparse(source_url)
        domain = parsed.netloc.lower()
        if domain in cls.ALLOWED_DOMAINS:
            return True, "VERIFIED_OFFICIAL_AIT"
        return False, "UNAUTHORIZED_DOMAIN"

    @classmethod
    def compute_hash(cls, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

class ImageDeduplicationEngine:
    @classmethod
    def is_duplicate(cls, new_hash: str, existing_hashes: set) -> bool:
        return new_hash in existing_hashes

class ImageProvenanceManager:
    @classmethod
    def create_provenance_record(
        cls,
        image_id: str,
        source_url: str,
        extracted_page: str,
        alt_text: str = ""
    ) -> Dict[str, Any]:
        return {
            "image_id": image_id,
            "source_url": source_url,
            "source_domain": "aitindia.in",
            "extracted_page": extracted_page,
            "alt_text": alt_text,
            "verified_by": "AIT Official Media Registry",
            "verification_method": "Official Domain Whitelist & Bundle Inspection"
        }
