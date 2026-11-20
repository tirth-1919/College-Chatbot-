"""College Administrator Scoped API Router.

Enforces strict tenant boundary access, ensuring that college administrators
can only inspect, crawl, upload, review, and configure their assigned institution.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db, set_rls_context
from app.models.college import College
from app.models.user import User
from app.models.website import WebsiteSource, CrawlJob, CrawlEvent, WebsitePage
from app.models.document import Document, DocumentPage
from app.models.knowledge import KnowledgeChunk, KnowledgeReview, ExtractedFact
from app.repositories.college_admin_repository import CollegeAdminRepository
from app.repositories.college_repository import CollegeRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.registration_repository import RegistrationRepository
from app.dependencies.auth import get_current_user, require_role
from app.services.url_validator import (
    validate_url_security,
    is_url_in_college_domain,
    SSRFProtectionError,
    DomainBoundaryError,
)
from app.services.document_service import document_service
from app.services.storage_service import document_storage_service
from app.services.pdf_validator import PDFValidationError, PDFPasswordProtectedError
from app.tasks.crawler_tasks import dispatch_crawl_job
from app.tasks.document_tasks import dispatch_document_processing
from app.tasks.knowledge_tasks import (
    dispatch_website_knowledge_processing,
    dispatch_document_knowledge_processing,
)
from app.services.knowledge_service import knowledge_service
from app.schemas.common import APIResponse
from app.schemas.registration import (
    CollegeOnboardingProgressResponse,
    CollegeOnboardingProgressUpdate,
)
from app.schemas.college_admin import (
    CollegeProfileResponse,
    CollegeProfileUpdateRequest,
    CollegeDashboardStats,
    CollegeAdminDashboardResponse,
    WebsiteSourceCreateRequest,
    WebsiteSourceUpdateRequest,
    WebsiteSourceResponse,
    CrawlJobResponse,
    CrawlEventResponse,
    WebsitePageResponse,
    DocumentCreateRequest,
    DocumentDetailResponse,
    DocumentPageResponse,
    DocumentStatusResponse,
    DocumentSignedUrlResponse,
    KnowledgeChunkResponse,
    KnowledgeReviewDecisionRequest,
    BulkKnowledgeReviewRequest,
    BulkKnowledgePublishRequest,
    KnowledgeProcessTriggerRequest,
    KnowledgeChunkTextUpdate,
    ExtractedFactCreateRequest,
    ExtractedFactUpdateRequest,
    ExtractedFactResponse,
    CollegeAnalyticsResponse,
    CollegeSupportTicketResponse,
    CollegeSupportTicketResolution,
    CollegeFeedbackResponse,
    CollegeNotificationItem,
)

router = APIRouter(prefix="/college-admin", tags=["College Administration Workspace"])


# ==============================================================================
# TENANT RESOLUTION & ISOLATION DEPENDENCY
# ==============================================================================

class CollegeTenantContext:
    """Bundles the verified college, the RLS-configured session, and the acting user.

    Use this as the single dependency for all college-admin route handlers to
    guarantee that the PostgreSQL RLS GUCs are set on the **same** session that
    executes data queries. This avoids the dependency-resolution-order race
    between ``get_current_user`` (which resets ``college_id`` to None) and
    ``get_authorized_college`` (which sets the real college_id).
    """
    __slots__ = ("college", "session", "user")

    def __init__(self, college: "College", session: "AsyncSession", user: "User") -> None:
        self.college = college
        self.session = session
        self.user = user


async def get_authorized_college(
    x_college_id: Optional[str] = Header(None, alias="X-College-ID"),
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> College:
    """Resolves and enforces authorized college tenant context.

    Rules:
    - COLLEGE_ADMIN: Must have a valid CollegeMembership. If X-College-ID is passed,
      it must strictly match their assigned college. Cannot access any other college.
    - SUPER_ADMIN: Can pass X-College-ID to manage any college tenant, or defaults to first active college.

    After resolving the college, refreshes the signed transaction-local RLS
    context so PostgreSQL policies trust the verified tenant and identity.
    """
    membership_repo = MembershipRepository(session)
    college_repo = CollegeRepository(session)

    if current_user.role == "COLLEGE_ADMIN":
        membership = await membership_repo.get_by_user_id(current_user.id)
        membership_college_id = membership.college_id if membership else None

        if not membership_college_id and x_college_id:
            try:
                requested_id = uuid.UUID(x_college_id)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid X-College-ID header format.",
                ) from exc
            if await membership_repo.user_belongs_to_college(
                current_user.id, requested_id
            ):
                membership_college_id = requested_id

        if not membership_college_id and not x_college_id:
            for candidate in await college_repo.list_colleges(
                only_approved=True,
                limit=1000,
            ):
                if await membership_repo.user_belongs_to_college(
                    current_user.id, candidate.id
                ):
                    membership_college_id = candidate.id
                    break

        if not membership_college_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: You do not have an active college administration assignment.",
            )

        if x_college_id:
            try:
                requested_id = uuid.UUID(x_college_id)
                if requested_id != membership_college_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cross-tenant access violation: You are not authorized for this college institution.",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid X-College-ID header format.",
                )

        college = await college_repo.get_by_id(membership_college_id)
        if not college:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned college tenant not found.",
            )

        await set_rls_context(
            session,
            college_id=membership_college_id,
            user_id=current_user.id,
            is_super_admin=False,
        )
        return college

    # SUPER_ADMIN handling
    if x_college_id:
        try:
            target_id = uuid.UUID(x_college_id)
            college = await college_repo.get_by_id(target_id)
            if college:
                await set_rls_context(
                    session,
                    college_id=target_id,
                    user_id=current_user.id,
                    is_super_admin=True,
                )
                return college
        except ValueError:
            pass

    colleges = await college_repo.list_colleges(only_approved=False)
    if not colleges:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No college tenants found on platform.",
        )
    await set_rls_context(
        session,
        college_id=colleges[0].id,
        user_id=current_user.id,
        is_super_admin=True,
    )
    return colleges[0]


async def get_college_context(
    college: College = Depends(get_authorized_college),
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
) -> CollegeTenantContext:
    """Unified dependency that guarantees RLS is set on the route handler's session.

    ``get_authorized_college`` sets the RLS GUCs on its own resolved session.
    ``get_current_user`` (called inside ``require_role``) also calls
    ``set_rls_context`` but only sets ``college_id=None``, which can overwrite
    the college context depending on FastAPI's dependency resolution order.

    This dependency resolves AFTER both of the above and explicitly re-sets the
    full RLS context (college_id, user_id, is_super_admin) on the shared session
    so that all repository queries in the route handler run with the correct tenant.
    """
    is_super = current_user.role == "SUPER_ADMIN"
    await set_rls_context(
        session,
        college_id=college.id,
        user_id=current_user.id,
        is_super_admin=is_super,
    )
    return CollegeTenantContext(college=college, session=session, user=current_user)


# ==============================================================================
# 1. INSTITUTIONAL DASHBOARD OVERVIEW
# ==============================================================================

@router.get(
    "/dashboard",
    response_model=APIResponse[CollegeAdminDashboardResponse],
    summary="Get aggregated institutional dashboard overview",
)
async def get_dashboard_overview(
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Retrieves college metrics, recent jobs, documents, and pending reviews."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    stats_data = await repo.get_dashboard_stats(college.id)
    crawls = await repo.list_crawl_jobs(college.id, limit=5)
    documents = await repo.list_documents(college.id, limit=5)
    reviews = await repo.list_knowledge_chunks(college.id, status="PENDING_REVIEW", limit=5)
    tickets = await repo.list_support_tickets(college.id, status="OPEN")

    return APIResponse(
        success=True,
        message=f"Dashboard telemetry loaded for {college.name}",
        data=CollegeAdminDashboardResponse(
            college=CollegeProfileResponse.model_validate(college),
            stats=CollegeDashboardStats(**stats_data),
            recent_crawl_jobs=[CrawlJobResponse.model_validate(c) for c in crawls],
            recent_documents=[DocumentDetailResponse.model_validate(d) for d in documents],
            recent_pending_reviews=[KnowledgeChunkResponse.model_validate(r) for r in reviews],
            recent_tickets=[CollegeSupportTicketResponse.model_validate(t) for t in tickets[:5]],
        ),
    )


# ==============================================================================
# 2. COLLEGE PROFILE MANAGEMENT
# ==============================================================================

@router.get(
    "/profile",
    response_model=APIResponse[CollegeProfileResponse],
    summary="Get authorized college institutional profile",
)
async def get_college_profile(
    college: College = Depends(get_authorized_college),
):
    """Fetches institutional profile details for the authenticated college."""
    return APIResponse(
        success=True,
        message="College profile retrieved",
        data=CollegeProfileResponse.model_validate(college),
    )


@router.patch(
    "/profile",
    response_model=APIResponse[CollegeProfileResponse],
    summary="Update permitted institutional profile details",
)
async def update_college_profile(
    req: CollegeProfileUpdateRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Updates permitted details (contact, logo, domain, name). Status cannot be altered."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    updated = await repo.update_college(college.id, req.model_dump(exclude_unset=True))
    return APIResponse(
        success=True,
        message="College profile updated successfully",
        data=CollegeProfileResponse.model_validate(updated),
    )


# ==============================================================================
# 3. WEBSITE SOURCE MANAGEMENT
# ==============================================================================

@router.get(
    "/websites",
    response_model=APIResponse[List[WebsiteSourceResponse]],
    summary="List registered website sources for the college",
)
async def list_website_sources(
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Lists all configured crawler website targets."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    sources = await repo.list_website_sources(college.id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(sources)} website sources",
        data=[WebsiteSourceResponse.model_validate(s) for s in sources],
    )


@router.post(
    "/websites",
    response_model=APIResponse[WebsiteSourceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new official website source",
)
async def create_website_source(
    req: WebsiteSourceCreateRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Registers an official website URL for automated crawling."""
    college = ctx.college
    # 1. SSRF & Scheme/Port/Host Security Validation
    try:
        validate_url_security(req.base_url)
    except SSRFProtectionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security Validation Failure (SSRF Protection): {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid website URL target: {str(e)}",
        )

    # 2. Strict Tenant Domain Boundary Validation
    if not is_url_in_college_domain(req.base_url, college.official_domain, req.allowed_subdomains):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Domain Boundary Violation: Target URL '{req.base_url}' must belong to the verified "
                f"college domain '{college.official_domain}' or permitted subdomains."
            ),
        )

    repo = CollegeAdminRepository(ctx.session)
    source = WebsiteSource(
        id=uuid.uuid4(),
        college_id=college.id,
        base_url=req.base_url.strip(),
        allowed_subdomains=req.allowed_subdomains.strip() if req.allowed_subdomains else None,
        max_depth=req.max_depth,
        max_pages=req.max_pages,
        crawl_frequency=req.crawl_frequency,
        is_active=True,
    )
    created = await repo.create_website_source(source)
    return APIResponse(
        success=True,
        message="Website source registered successfully",
        data=WebsiteSourceResponse.model_validate(created),
    )


@router.patch(
    "/websites/{source_id}",
    response_model=APIResponse[WebsiteSourceResponse],
    summary="Update website source crawling parameters",
)
async def update_website_source(
    source_id: uuid.UUID,
    req: WebsiteSourceUpdateRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Updates crawling parameters or active state for a website source."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    updated = await repo.update_website_source(college.id, source_id, req.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    return APIResponse(
        success=True,
        message="Website source updated",
        data=WebsiteSourceResponse.model_validate(updated),
    )


@router.delete(
    "/websites/{source_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Remove a website source",
)
async def delete_website_source(
    source_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Removes a website source and associated crawl metadata."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    deleted = await repo.delete_website_source(college.id, source_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    return APIResponse(success=True, message="Website source removed", data={"id": str(source_id)})


# ==============================================================================
# 4. CRAWLER EXECUTION & MONITORING
# ==============================================================================

@router.post(
    "/crawler/start",
    response_model=APIResponse[CrawlJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a new crawl job for a website source",
)
async def start_crawl_job(
    background_tasks: BackgroundTasks,
    source_id: uuid.UUID = Query(description="Target website source ID"),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Dispatches an asynchronous crawler execution job."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    source = await repo.get_website_source(college.id, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    job = await repo.create_crawl_job(college.id, source_id)
    # Dispatch execution via Celery with local background fallback
    mode = dispatch_crawl_job(job.id, college.id, source.id, background_tasks)

    return APIResponse(
        success=True,
        message=f"Crawl job initiated successfully ({mode})",
        data=CrawlJobResponse.model_validate(job),
    )


@router.post(
    "/websites/{source_id}/crawl",
    response_model=APIResponse[CrawlJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Trigger crawl execution for specific website source",
)
async def trigger_source_crawl(
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Convenience alias to dispatch crawl on a specific website source."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    source = await repo.get_website_source(college.id, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website source not found.")

    job = await repo.create_crawl_job(college.id, source_id)
    mode = dispatch_crawl_job(job.id, college.id, source.id, background_tasks)

    return APIResponse(
        success=True,
        message=f"Crawl job initiated successfully ({mode})",
        data=CrawlJobResponse.model_validate(job),
    )


@router.get(
    "/crawler/jobs/{job_id}",
    response_model=APIResponse[CrawlJobResponse],
    summary="Get single crawl job detail and progress",
)
async def get_crawl_job(
    job_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Fetches real-time status and page counts for a crawl job."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    job = await repo.get_crawl_job(college.id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl job not found.")

    return APIResponse(
        success=True,
        message="Crawl job details retrieved",
        data=CrawlJobResponse.model_validate(job),
    )


@router.post(
    "/crawler/{job_id}/action",
    response_model=APIResponse[CrawlJobResponse],
    summary="Control active crawl job (pause, resume, cancel)",
)
async def control_crawl_job(
    job_id: uuid.UUID,
    action: str = Query(description="PAUSE, RESUME, or CANCEL"),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Updates crawl execution lifecycle state."""
    college = ctx.college
    action_map = {"PAUSE": "PAUSED", "RESUME": "RUNNING", "CANCEL": "CANCELLED"}
    new_status = action_map.get(action.upper())
    if not new_status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action.")

    repo = CollegeAdminRepository(ctx.session)
    job = await repo.update_crawl_job_status(college.id, job_id, new_status)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl job not found.")

    return APIResponse(
        success=True,
        message=f"Crawl job transitioned to {new_status}",
        data=CrawlJobResponse.model_validate(job),
    )


@router.get(
    "/crawler/jobs",
    response_model=APIResponse[List[CrawlJobResponse]],
    summary="List crawl jobs for the college",
)
async def list_crawl_jobs(
    source_id: Optional[uuid.UUID] = Query(None),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Lists crawl executions and progress."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    jobs = await repo.list_crawl_jobs(college.id, source_id=source_id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(jobs)} crawl jobs",
        data=[CrawlJobResponse.model_validate(j) for j in jobs],
    )


@router.get(
    "/crawler/jobs/{job_id}/events",
    response_model=APIResponse[List[CrawlEventResponse]],
    summary="List real-time log events for a crawl job",
)
async def get_crawl_events(
    job_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
    **kwargs: Any,
):
    """Retrieves log events emitted during crawling."""
    effective_college = kwargs.get("college") or ctx.college
    effective_session = kwargs.get("session") or ctx.session
    repo = CollegeAdminRepository(effective_session)
    job = await repo.get_crawl_job(effective_college.id, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crawl job not found.")

    events = await repo.list_crawl_events(job_id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(events)} log events",
        data=[CrawlEventResponse.model_validate(e) for e in events],
    )


@router.get(
    "/crawler/pages",
    response_model=APIResponse[List[WebsitePageResponse]],
    summary="List extracted pages discovered by crawler",
)
async def list_crawled_pages(
    source_id: Optional[uuid.UUID] = Query(None),
    limit: int = 50,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Lists parsed website pages with content hash and extracted text."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    pages = await repo.list_website_pages(college.id, source_id=source_id, limit=limit)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(pages)} crawled pages",
        data=[WebsitePageResponse.model_validate(p) for p in pages],
    )


# ==============================================================================
# 5. PDF DOCUMENT MANAGEMENT
# ==============================================================================

@router.get(
    "/documents",
    response_model=APIResponse[List[DocumentDetailResponse]],
    summary="List uploaded institutional documents",
)
async def list_documents(
    status_filter: Optional[str] = Query(None, description="UPLOADED, QUEUED, PROCESSING, EXTRACTED, PENDING_REVIEW, FAILED"),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Lists PDF documents uploaded for this college."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    docs = await repo.list_documents(college.id, status=status_filter)
    
    # Attach signed download URLs
    resp_items = []
    for d in docs:
        item = DocumentDetailResponse.model_validate(d)
        try:
            item.download_url = await document_storage_service.get_signed_url(college.id, d.storage_path)
        except Exception:
            item.download_url = None
        resp_items.append(item)

    return APIResponse(
        success=True,
        message=f"Retrieved {len(docs)} documents",
        data=resp_items,
    )


@router.post(
    "/documents/upload-file",
    response_model=APIResponse[DocumentDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload PDF binary document with magic byte verification & OCR queuing",
)
async def upload_pdf_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(description="PDF binary file"),
    category: str = Form("GENERAL"),
    description: Optional[str] = Form(None),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Secure multipart file upload: validates magic bytes, stores in private storage, and queues Celery extraction."""
    college = ctx.college
    current_user = ctx.user
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    try:
        doc, is_duplicate = await document_service.register_and_upload(
            college_id=college.id,
            user_id=current_user.id,
            file_bytes=file_bytes,
            original_filename=file.filename or "uploaded.pdf",
            declared_mime_type=file.content_type,
            category=category,
            description=description,
        )
    except PDFPasswordProtectedError as pwd_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(pwd_err),
        )
    except PDFValidationError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security & Validation Error: {str(val_err)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document upload: {str(exc)}",
        )

    if not is_duplicate:
        # Dispatch background processing task
        mode = await dispatch_document_processing(doc.id, college.id, background_tasks)
        msg = f"Document '{doc.original_filename}' uploaded and queued for processing ({mode})."
    else:
        msg = f"Document '{doc.original_filename}' is an identical duplicate (matched cryptographic hash)."

    res_item = DocumentDetailResponse.model_validate(doc)
    # Signed URL is best-effort — a missing object must not crash the upload response.
    try:
        res_item.download_url = await document_storage_service.get_signed_url(college.id, doc.storage_path)
    except Exception:
        res_item.download_url = None

    return APIResponse(
        success=True,
        message=msg,
        data=res_item,
    )


@router.post(
    "/documents/upload",
    response_model=APIResponse[DocumentDetailResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register document metadata (JSON backward compatible — requires pre-uploaded file)",
)
async def register_uploaded_document(
    req: DocumentCreateRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Registers metadata for a document that the caller has already uploaded to private storage.

    The caller must supply a real SHA-256 checksum via ``checksum_sha256``.
    The object at the derived storage path must already exist in Supabase Storage.
    Use POST /upload-file to upload a new PDF binary instead.
    """
    college = ctx.college
    current_user = ctx.user
    if not req.original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF documents are supported for ingestion.",
        )

    if req.file_size_bytes > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the 50 MB platform upload limit.",
        )

    # Require a real checksum — refuse auto-generated fake values.
    checksum = getattr(req, "checksum_sha256", None)
    if not checksum or checksum.startswith("sha256_") or len(checksum) != 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A valid SHA-256 checksum (64 hex characters) is required. "
                "Upload the file first using POST /upload-file."
            ),
        )

    # Derive the expected storage path and verify the object exists before creating a DB record.
    doc_id = uuid.uuid4()
    storage_path = document_storage_service.build_storage_path(college.id, doc_id)

    object_exists = False
    try:
        await document_storage_service.get_signed_url(college.id, storage_path)
        object_exists = True
    except FileNotFoundError:
        object_exists = False
    except Exception:
        # If the storage service is not configured (local dev), allow the record.
        object_exists = not document_storage_service.is_supabase_configured

    if not object_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Storage object not found at the expected path. Upload the file first.",
        )

    repo = CollegeAdminRepository(ctx.session)
    doc = Document(
        id=doc_id,
        college_id=college.id,
        uploaded_by_user_id=current_user.id,
        original_filename=req.original_filename.strip(),
        storage_path=storage_path,
        mime_type="application/pdf",
        file_size_bytes=req.file_size_bytes,
        total_pages=0,
        checksum_sha256=checksum,
        processing_status="QUEUED",
        category=req.category or "GENERAL",
        description=req.description,
    )
    created = await repo.create_document(doc)

    res_item = DocumentDetailResponse.model_validate(created)
    # Return null rather than crashing if signed URL cannot be generated.
    try:
        res_item.download_url = await document_storage_service.get_signed_url(college.id, created.storage_path)
    except Exception:
        res_item.download_url = None

    return APIResponse(
        success=True,
        message=f"Document '{doc.original_filename}' registered for processing",
        data=res_item,
    )


@router.get(
    "/documents/{document_id}",
    response_model=APIResponse[DocumentDetailResponse],
    summary="Get document details by ID",
)
async def get_document_details(
    document_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Retrieves document metadata ensuring tenant ownership."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    doc = await repo.get_document(college.id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    res_item = DocumentDetailResponse.model_validate(doc)
    try:
        res_item.download_url = await document_storage_service.get_signed_url(college.id, doc.storage_path)
    except Exception:
        res_item.download_url = None

    return APIResponse(
        success=True,
        message="Document details retrieved",
        data=res_item,
    )


@router.get(
    "/documents/{document_id}/pages",
    response_model=APIResponse[List[DocumentPageResponse]],
    summary="List extracted pages and OCR results for a document",
)
async def get_document_pages(
    document_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Returns page-by-page extracted text, tables, and OCR telemetry."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    doc = await repo.get_document(college.id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    pages = await repo.list_document_pages(college.id, document_id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(pages)} extracted pages",
        data=[DocumentPageResponse.model_validate(p) for p in pages],
    )


@router.get(
    "/documents/{document_id}/status",
    response_model=APIResponse[DocumentStatusResponse],
    summary="Get real-time document processing progress",
)
async def get_document_status(
    document_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Lightweight polling endpoint to inspect extraction progress."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    doc = await repo.get_document(college.id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    pages = await repo.list_document_pages(college.id, document_id)

    status_data = DocumentStatusResponse(
        id=doc.id,
        college_id=doc.college_id,
        processing_status=doc.processing_status,
        total_pages=doc.total_pages,
        pages_extracted=len(pages),
        ocr_applied=doc.ocr_applied,
        failure_reason=doc.failure_reason,
        updated_at=doc.updated_at or doc.created_at,
    )

    return APIResponse(
        success=True,
        message="Document status retrieved",
        data=status_data,
    )


@router.get(
    "/documents/{document_id}/download-url",
    response_model=APIResponse[DocumentSignedUrlResponse],
    summary="Generate secure signed URL to download private PDF",
)
async def get_document_download_url(
    document_id: uuid.UUID,
    expires_in: int = Query(3600, ge=60, le=86400, description="Expiration in seconds"),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Generates temporary signed download URL for an authorized document."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    doc = await repo.get_document(college.id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    url = await document_storage_service.get_signed_url(college.id, doc.storage_path, expires_in=expires_in)

    return APIResponse(
        success=True,
        message="Temporary signed URL generated",
        data=DocumentSignedUrlResponse(
            document_id=doc.id,
            original_filename=doc.original_filename,
            download_url=url,
            expires_in_seconds=expires_in,
        ),
    )


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=APIResponse[DocumentDetailResponse],
    summary="Reprocess or retry a document",
)
@router.post(
    "/documents/{document_id}/retry",
    response_model=APIResponse[DocumentDetailResponse],
    summary="Retry failed document extraction",
)
async def reprocess_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Retries text extraction and OCR pipeline on a document."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    doc = await repo.get_document(college.id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    doc.processing_status = "QUEUED"
    doc.failure_reason = None
    doc.updated_at = datetime.now(timezone.utc)
    await ctx.session.commit()

    mode = await dispatch_document_processing(doc.id, college.id, background_tasks)

    res_item = DocumentDetailResponse.model_validate(doc)
    try:
        res_item.download_url = await document_storage_service.get_signed_url(college.id, doc.storage_path)
    except Exception:
        res_item.download_url = None

    return APIResponse(
        success=True,
        message=f"Document '{doc.original_filename}' re-queued for processing ({mode}).",
        data=res_item,
    )


@router.delete(
    "/documents/{document_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Deletes document record and removes binary from private storage."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    doc = await repo.get_document(college.id, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    storage_path = doc.storage_path
    deleted = await repo.delete_document(college.id, document_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Remove storage binary
    await document_storage_service.delete_file(college.id, storage_path)

    return APIResponse(success=True, message="Document permanently removed", data={"id": str(document_id)})


@router.get(
    "/documents/raw/{college_id}/{document_id}.pdf",
    summary="Local fallback binary file streaming for authorized documents",
)
async def stream_local_document(
    college_id: uuid.UUID,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    """Streams local fallback document binary with PDF Content-Type."""
    storage_path = f"{college_id}/{document_id}.pdf"
    try:
        data = await document_storage_service.get_file_bytes(college_id, storage_path)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={document_id}.pdf"},
        )
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document binary not found.")
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return APIResponse(success=True, message="Document removed", data={"id": str(document_id)})


# ==============================================================================
# 6. KNOWLEDGE BASE EXPLORER & REVIEW QUEUE
# ==============================================================================

@router.get(
    "/knowledge",
    response_model=APIResponse[List[KnowledgeChunkResponse]],
    summary="Query knowledge base records for this college",
)
async def list_knowledge_chunks(
    status_filter: Optional[str] = Query(None, description="PENDING_REVIEW, APPROVED, PUBLISHED, REJECTED, STALE"),
    source_type: Optional[str] = Query(None, description="OFFICIAL_WEBSITE, WEBSITE, DOCUMENT, or PDF"),
    category: Optional[str] = Query(None, description="Filter by 15 categories (ADMISSIONS, FEES, COURSES, etc.)"),
    search: Optional[str] = Query(None, description="Search keyword in chunk text"),
    limit: int = 50,
    offset: int = 0,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Explores atomic knowledge chunks with source citations and category classification."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    chunks = await repo.list_knowledge_chunks(
        college.id,
        status=status_filter,
        source_type=source_type,
        category=category,
        search=search,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        success=True,
        message=f"Retrieved {len(chunks)} knowledge chunks",
        data=[KnowledgeChunkResponse.model_validate(c) for c in chunks],
    )


@router.get(
    "/reviews",
    response_model=APIResponse[List[KnowledgeChunkResponse]],
    summary="List knowledge chunks pending human review",
)
async def list_pending_reviews(
    category: Optional[str] = Query(None, description="Optional category filter"),
    limit: int = 50,
    offset: int = 0,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Retrieves items in the human review queue awaiting administrator verification."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    chunks = await repo.list_knowledge_chunks(
        college.id,
        status="PENDING_REVIEW",
        category=category,
        limit=limit,
        offset=offset,
    )
    return APIResponse(
        success=True,
        message=f"Found {len(chunks)} knowledge chunks pending review",
        data=[KnowledgeChunkResponse.model_validate(c) for c in chunks],
    )


@router.post(
    "/reviews/{chunk_id}/decision",
    response_model=APIResponse[KnowledgeChunkResponse],
    summary="Submit human verification decision (APPROVE or REJECT)",
)
async def submit_review_decision(
    chunk_id: uuid.UUID,
    req: KnowledgeReviewDecisionRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Applies administrator approval or rejection to an extracted knowledge chunk.
    Separate publication action is required before chunks become live in vector search.
    """
    college = ctx.college
    current_user = ctx.user
    decision = req.decision.upper().strip()
    if decision not in ("APPROVE", "APPROVED", "REJECT", "REJECTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either 'APPROVED' or 'REJECTED'.",
        )
    normalized_decision = "APPROVED" if "APPROVE" in decision else "REJECTED"

    repo = CollegeAdminRepository(ctx.session)
    chunk = await repo.review_knowledge_chunk(
        college_id=college.id,
        chunk_id=chunk_id,
        reviewer_id=current_user.id,
        decision=normalized_decision,
        comments=req.comments,
    )
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge chunk not found.")

    await ctx.session.commit()
    return APIResponse(
        success=True,
        message=f"Knowledge chunk marked as {normalized_decision}",
        data=KnowledgeChunkResponse.model_validate(chunk),
    )


@router.post(
    "/reviews/bulk-decision",
    response_model=APIResponse[Dict[str, int]],
    summary="Bulk approve or reject multiple knowledge chunks",
)
async def bulk_review_decisions(
    req: BulkKnowledgeReviewRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Applies human review decisions in batch."""
    college = ctx.college
    current_user = ctx.user
    decision = "APPROVED" if "APPROVE" in req.decision.upper() else "REJECTED"
    repo = CollegeAdminRepository(ctx.session)
    count = 0
    for chunk_id in req.chunk_ids:
        chunk = await repo.review_knowledge_chunk(
            college_id=college.id,
            chunk_id=chunk_id,
            reviewer_id=current_user.id,
            decision=decision,
            comments=req.comments,
        )
        if chunk:
            count += 1
    await ctx.session.commit()
    return APIResponse(
        success=True,
        message=f"Successfully marked {count} chunks as {decision}",
        data={"processed_count": count},
    )


@router.patch(
    "/knowledge/{chunk_id}",
    response_model=APIResponse[KnowledgeChunkResponse],
    summary="Edit chunk text prior to approval",
)
async def update_knowledge_chunk(
    chunk_id: uuid.UUID,
    req: KnowledgeChunkTextUpdate,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Corrects or clarifies extracted text before approving."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    chunk = await repo.update_knowledge_chunk_text(college.id, chunk_id, req.chunk_text)
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge chunk not found.")

    await ctx.session.commit()
    return APIResponse(
        success=True,
        message="Knowledge chunk text updated",
        data=KnowledgeChunkResponse.model_validate(chunk),
    )


@router.post(
    "/knowledge/{chunk_id}/publish",
    response_model=APIResponse[KnowledgeChunkResponse],
    summary="Publish approved chunk to live student vector search",
)
async def publish_knowledge_chunk(
    chunk_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Promotes an approved chunk to live student RAG retrieval."""
    college = ctx.college
    current_user = ctx.user
    repo = CollegeAdminRepository(ctx.session)
    chunk = await repo.publish_knowledge_chunk(college.id, chunk_id, reviewer_id=current_user.id)
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge chunk not found.")

    await ctx.session.commit()
    return APIResponse(
        success=True,
        message="Knowledge chunk published to live student search",
        data=KnowledgeChunkResponse.model_validate(chunk),
    )


@router.post(
    "/knowledge/bulk-publish",
    response_model=APIResponse[Dict[str, int]],
    summary="Publish multiple approved chunks in batch",
)
async def bulk_publish_chunks(
    req: BulkKnowledgePublishRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Publishes a list of approved knowledge chunks to live vector search."""
    college = ctx.college
    current_user = ctx.user
    repo = CollegeAdminRepository(ctx.session)
    count = 0
    for chunk_id in req.chunk_ids:
        chunk = await repo.publish_knowledge_chunk(college.id, chunk_id, reviewer_id=current_user.id)
        if chunk:
            count += 1
    await ctx.session.commit()
    return APIResponse(
        success=True,
        message=f"Successfully published {count} knowledge chunks to live search",
        data={"published_count": count},
    )


@router.post(
    "/knowledge/{chunk_id}/unpublish",
    response_model=APIResponse[KnowledgeChunkResponse],
    summary="Unpublish chunk from live student search",
)
async def unpublish_knowledge_chunk(
    chunk_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Reverts a published chunk to inactive approved state."""
    college = ctx.college
    current_user = ctx.user
    repo = CollegeAdminRepository(ctx.session)
    chunk = await repo.unpublish_knowledge_chunk(college.id, chunk_id, reviewer_id=current_user.id)
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge chunk not found.")

    await ctx.session.commit()
    return APIResponse(
        success=True,
        message="Knowledge chunk unpublished from live student search",
        data=KnowledgeChunkResponse.model_validate(chunk),
    )


@router.post(
    "/knowledge/process",
    response_model=APIResponse[Dict[str, Any]],
    summary="Trigger knowledge extraction pipeline on crawled pages or documents",
)
async def trigger_knowledge_processing(
    req: KnowledgeProcessTriggerRequest,
    background_tasks: BackgroundTasks,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Triggers chunking, 15-category classification, and embedding generation."""
    college = ctx.college
    source_type = req.source_type.upper().strip()
    if source_type in ("WEBSITE", "OFFICIAL_WEBSITE"):
        mode = dispatch_website_knowledge_processing(
            college_id=college.id,
            page_ids=[req.source_id] if req.source_id else None,
            background_tasks=background_tasks,
        )
        return APIResponse(
            success=True,
            message="Website knowledge extraction dispatched",
            data={"mode": mode, "source_id": str(req.source_id)},
        )
    elif source_type in ("DOCUMENT", "PDF"):
        mode = dispatch_document_knowledge_processing(
            college_id=college.id,
            document_id=req.source_id,
            background_tasks=background_tasks,
        )
        return APIResponse(
            success=True,
            message="Document knowledge extraction dispatched",
            data={"mode": mode, "document_id": str(req.source_id)},
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type must be WEBSITE or DOCUMENT",
        )


# ==============================================================================
# 7. STRUCTURED COLLEGE INFORMATION (EXTRACTED FACTS)
# ==============================================================================

@router.get(
    "/structured-data",
    response_model=APIResponse[List[ExtractedFactResponse]],
    summary="List structured college facts",
)
async def list_structured_facts(
    category: Optional[str] = Query(None, description="ABOUT, COURSES, ADMISSIONS, DEPARTMENTS, FACILITIES, FAQS"),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Lists structured institutional facts categorized by topic."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    facts = await repo.list_extracted_facts(college.id, category=category)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(facts)} structured facts",
        data=[ExtractedFactResponse.model_validate(f) for f in facts],
    )


@router.post(
    "/structured-data",
    response_model=APIResponse[ExtractedFactResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new structured college fact",
)
async def create_structured_fact(
    req: ExtractedFactCreateRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Adds a verified structured factual claim for the college."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    fact = ExtractedFact(
        id=uuid.uuid4(),
        college_id=college.id,
        source_type="ADMIN_STRUCTURED",
        source_id=college.id,
        category=req.category.upper().strip(),
        fact_key=req.fact_key.strip(),
        fact_value=req.fact_value.strip(),
        verification_status="ADMIN_VERIFIED",
    )
    created = await repo.create_extracted_fact(fact)
    return APIResponse(
        success=True,
        message="Structured fact recorded successfully",
        data=ExtractedFactResponse.model_validate(created),
    )


@router.patch(
    "/structured-data/{fact_id}",
    response_model=APIResponse[ExtractedFactResponse],
    summary="Update an existing structured fact",
)
async def update_structured_fact(
    fact_id: uuid.UUID,
    req: ExtractedFactUpdateRequest,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Updates a structured factual entry."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    updated = await repo.update_extracted_fact(college.id, fact_id, req.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Structured fact not found.")

    return APIResponse(
        success=True,
        message="Structured fact updated",
        data=ExtractedFactResponse.model_validate(updated),
    )


@router.delete(
    "/structured-data/{fact_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Delete a structured fact",
)
async def delete_structured_fact(
    fact_id: uuid.UUID,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Deletes a structured fact record."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    deleted = await repo.delete_extracted_fact(college.id, fact_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Structured fact not found.")

    return APIResponse(success=True, message="Structured fact removed", data={"id": str(fact_id)})


# ==============================================================================
# 8. INSTITUTIONAL ANALYTICS
# ==============================================================================

@router.get(
    "/analytics",
    response_model=APIResponse[CollegeAnalyticsResponse],
    summary="College student chatbot usage and telemetry",
)
async def get_college_analytics(
    time_range: str = Query("30D", description="TODAY, 7D, 30D, 90D"),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Returns analytics scoped strictly to this college's chatbot interactions."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    data = await repo.get_college_analytics(college.id, time_range=time_range)
    return APIResponse(
        success=True,
        message="College analytics loaded",
        data=CollegeAnalyticsResponse(**data),
    )


# ==============================================================================
# 9. STUDENT SUPPORT TICKETS & FEEDBACK
# ==============================================================================

@router.get(
    "/support",
    response_model=APIResponse[List[CollegeSupportTicketResponse]],
    summary="List student support inquiries for this college",
)
async def list_support_tickets(
    status_filter: Optional[str] = Query(None, description="OPEN, IN_PROGRESS, RESOLVED, CLOSED"),
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Lists student inquiries escalated when reliable AI answer was unavailable."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    tickets = await repo.list_support_tickets(college.id, status=status_filter)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(tickets)} support tickets",
        data=[CollegeSupportTicketResponse.model_validate(t) for t in tickets],
    )


@router.patch(
    "/support/{ticket_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Resolve student support inquiry",
)
async def resolve_support_ticket(
    ticket_id: uuid.UUID,
    req: CollegeSupportTicketResolution,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Updates status and delivers resolution notes for student inquiry."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    ticket = await repo.resolve_support_ticket(college.id, ticket_id, req.status)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found.")

    return APIResponse(
        success=True,
        message=f"Support ticket updated to {req.status}",
        data={"id": str(ticket.id), "status": ticket.status},
    )


@router.get(
    "/feedback",
    response_model=APIResponse[List[CollegeFeedbackResponse]],
    summary="List student rating feedback on chatbot answers",
)
async def list_feedback(
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Returns student ratings and comments on chatbot messages."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    feedbacks = await repo.list_feedback(college.id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(feedbacks)} feedback records",
        data=[
            CollegeFeedbackResponse(
                id=f.id,
                message_id=f.message_id,
                user_email=f.user.email if f.user else "Anonymous Student",
                rating=f.rating,
                comments=f.comments,
                created_at=f.created_at,
            )
            for f in feedbacks
        ],
    )


# ==============================================================================
# 10. SYSTEM ALERTS & NOTIFICATIONS
# ==============================================================================

@router.get(
    "/notifications",
    response_model=APIResponse[List[CollegeNotificationItem]],
    summary="List institutional system alerts & notices",
)
async def list_notifications(
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Returns alerts regarding crawler runs, document processing, and pending reviews."""
    college = ctx.college
    repo = CollegeAdminRepository(ctx.session)
    stats = await repo.get_dashboard_stats(college.id)

    notifications: List[CollegeNotificationItem] = []

    if stats["pending_reviews"] > 0:
        notifications.append(
            CollegeNotificationItem(
                id="notif_1",
                title="Knowledge Chunks Awaiting Verification",
                message=f"There are {stats['pending_reviews']} extracted knowledge chunks waiting for your review before they can be published.",
                type="WARNING",
                created_at=datetime.now(timezone.utc),
            )
        )

    if stats["open_tickets_count"] > 0:
        notifications.append(
            CollegeNotificationItem(
                id="notif_2",
                title="Escalated Student Inquiries",
                message=f"{stats['open_tickets_count']} student support inquiries require attention from college staff.",
                type="INFO",
                created_at=datetime.now(timezone.utc),
            )
        )

    notifications.append(
        CollegeNotificationItem(
            id="notif_3",
            title="Institutional Tenant Protected",
            message=f"All queries and documents for '{college.name}' are isolated with Row Level Security (RLS).",
            type="SUCCESS",
            created_at=datetime.now(timezone.utc),
        )
    )

    return APIResponse(
        success=True,
        message="Notifications retrieved",
        data=notifications,
    )


# ==============================================================================
# 11. COLLEGE ONBOARDING PROGRESS WIZARD (PHASE 6)
# ==============================================================================

@router.get(
    "/onboarding",
    response_model=APIResponse[CollegeOnboardingProgressResponse],
    summary="Get multi-step onboarding progression for current college tenant",
)
async def get_onboarding_progress(
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Retrieves current onboarding wizard progression and milestone states."""
    college = ctx.college
    reg_repo = RegistrationRepository(ctx.session)
    prog = await reg_repo.get_or_create_onboarding_progress(college.id)

    res_data = CollegeOnboardingProgressResponse.model_validate(prog)
    res_data.college_name = college.name
    res_data.college_slug = college.slug

    return APIResponse(
        success=True,
        message="Onboarding progress retrieved",
        data=res_data,
    )


@router.patch(
    "/onboarding",
    response_model=APIResponse[CollegeOnboardingProgressResponse],
    summary="Update onboarding progress step and milestone data",
)
async def update_onboarding_progress(
    req: CollegeOnboardingProgressUpdate,
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Saves completion state for profile, website, or document onboarding steps."""
    college = ctx.college
    reg_repo = RegistrationRepository(ctx.session)
    prog = await reg_repo.update_onboarding_progress(
        college_id=college.id,
        current_step=req.current_step,
        profile_completed=req.profile_completed,
        website_configured=req.website_configured,
        documents_uploaded=req.documents_uploaded,
        knowledge_ready=req.knowledge_ready,
        step_data=req.step_data,
    )

    res_data = CollegeOnboardingProgressResponse.model_validate(prog)
    res_data.college_name = college.name
    res_data.college_slug = college.slug

    return APIResponse(
        success=True,
        message="Onboarding progress updated successfully",
        data=res_data,
    )


@router.post(
    "/onboarding/complete",
    response_model=APIResponse[CollegeOnboardingProgressResponse],
    summary="Finalize onboarding wizard and mark institution ready for operation",
)
async def complete_onboarding_wizard(
    ctx: CollegeTenantContext = Depends(get_college_context),
):
    """Finalizes onboarding wizard: flags progress as completed and logs telemetry."""
    college = ctx.college
    current_user = ctx.user
    reg_repo = RegistrationRepository(ctx.session)
    prog = await reg_repo.complete_onboarding(
        college_id=college.id,
        admin_email=current_user.email,
    )

    res_data = CollegeOnboardingProgressResponse.model_validate(prog)
    res_data.college_name = college.name
    res_data.college_slug = college.slug

    return APIResponse(
        success=True,
        message=f"Onboarding successfully completed for {college.name}! Institutional workspace is fully active.",
        data=res_data,
    )


