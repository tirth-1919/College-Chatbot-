"""Services registry."""

from app.services.auth_service import AuthService
from app.services.tenant_service import TenantService
from app.services.crawler_service import WebsiteCrawlerService, crawler_service
from app.services.robots_parser import RobotsPolicyManager, robots_policy_manager
from app.services.url_validator import (
    validate_url_security,
    is_url_in_college_domain,
    normalize_url,
    SSRFProtectionError,
    DomainBoundaryError,
)
from app.services.pdf_validator import validate_pdf_file, PDFValidationError, PDFPasswordProtectedError
from app.services.storage_service import DocumentStorageService, document_storage_service
from app.services.ocr_service import TesseractOCREngine, ocr_engine
from app.services.pdf_processor import PDFProcessor, pdf_processor
from app.services.document_service import DocumentProcessingService, document_service

__all__ = [
    "AuthService",
    "TenantService",
    "WebsiteCrawlerService",
    "crawler_service",
    "RobotsPolicyManager",
    "robots_policy_manager",
    "validate_url_security",
    "is_url_in_college_domain",
    "normalize_url",
    "SSRFProtectionError",
    "DomainBoundaryError",
    "validate_pdf_file",
    "PDFValidationError",
    "PDFPasswordProtectedError",
    "DocumentStorageService",
    "document_storage_service",
    "TesseractOCREngine",
    "ocr_engine",
    "PDFProcessor",
    "pdf_processor",
    "DocumentProcessingService",
    "document_service",
]
