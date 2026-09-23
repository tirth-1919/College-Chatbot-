from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_WEBSITE_SYNC
from backend.app.models.knowledge import WebsiteSnapshot
from backend.app.models.user import User
from backend.app.knowledge.crawler import website_crawler
from backend.app.knowledge.conflict_detector import conflict_detector

router = APIRouter(prefix="/website", tags=["Admin Website Synchronization"])

@router.get("/snapshots")
def list_website_snapshots(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    q = db.query(WebsiteSnapshot)
    # Phase 9: scope to college
    if current_user.role != "SUPER_ADMIN" and current_user.college_id:
        q = q.filter(WebsiteSnapshot.college_id == current_user.college_id)
    snapshots = q.order_by(WebsiteSnapshot.last_crawled_at.desc()).all()
    return [
        {
            "id": s.id,
            "url": s.url,
            "title": s.title,
            "content_hash": s.content_hash,
            "snippet": s.text_content[:300] + "..." if len(s.text_content) > 300 else s.text_content,
            "status_code": s.status_code,
            "discovery_status": "DISCOVERED",
            "extraction_status": "EXTRACTED" if s.text_content else "EMPTY",
            "indexing_status": "INDEXED" if s.text_content else "NOT_INDEXED",
            "chunk_count": len([chunk for chunk in (s.text_content or '').split('SECTION: ') if chunk.strip()]),
            "source_verification": "Official Website" if s.status_code == 200 and s.text_content else "UNVERIFIED",
            "last_crawled_at": s.last_crawled_at.isoformat() if s.last_crawled_at else None
        }
        for s in snapshots
    ]

@router.post("/sync")
async def trigger_website_sync(
    current_user: User = Depends(require_permission(PERM_WEBSITE_SYNC)),
    db: Session = Depends(get_db)
):
    """
    Executes automated crawler, page hash comparison, change detection,
    and discrepancy conflict scanner.
    """
    import logging
    import traceback

    logger = logging.getLogger(__name__)
    try:
        sync_result = await website_crawler.synchronize_website(db)
        conflicts_found = conflict_detector.scan_for_conflicts(db)
    except Exception as exc:
        # Log the full traceback server-side and return a structured error
        # instead of letting an unhandled exception surface as a bare HTTP
        # 500 to the admin UI.
        logger.error("Website sync failed:\n%s", traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(
            status_code=502,
            detail={"status": "error", "message": f"Website synchronization failed: {exc}"},
        )

    log_admin_audit(db, current_user, "WEBSITE_SYNC_EXECUTED", "WEBSITE", {
        "sync_result": sync_result,
        "conflicts_count": len(conflicts_found)
    })

    return {
        "status": "success",
        "message": "AIT website synchronization completed.",
        "details": sync_result,
        "new_conflicts_detected": len(conflicts_found)
    }
