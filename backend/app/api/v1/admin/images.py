from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_IMAGES_MANAGE, verify_tenant_access
from backend.app.models.image import AitImage, ImageProvenance
from backend.app.models.user import User
from backend.app.models.college import College
from backend.app.images.crawler import ait_image_crawler

router = APIRouter(prefix="/images", tags=["Admin Image Management"])

@router.get("")
def list_images(
    category: Optional[str] = None,
    verified_only: Optional[bool] = None,
    college_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(AitImage)
    # College admins are always constrained by the authenticated tenant.  A
    # request-supplied college_id is intentionally not accepted here.  Legacy
    # rows without ownership are excluded rather than assigned by fallback.
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    if not is_super:
        verify_tenant_access(current_user, current_user.college_id)
        query = query.filter(
            AitImage.college_id.isnot(None),
            AitImage.college_id == current_user.college_id,
        )
    elif college_id:
        query = query.filter(AitImage.college_id == college_id)
    else:
        query = query.filter(AitImage.college_id.isnot(None))
    if category and category != "all":
        query = query.filter(AitImage.category == category)
    if verified_only is not None:
        query = query.filter(AitImage.verified == verified_only)

    images = query.order_by(AitImage.created_at.desc()).all()
    return [
        {
            "id": img.id,
            "title": img.title,
            "category": img.category,
            "image_url": img.image_url,
            "thumbnail_url": img.thumbnail_url,
            "source_url": img.source_url,
            "source_domain": img.source_domain,
            "source_page": img.source_page,
            "college_id": img.college_id,
            "source_type": img.source_type,
            "retrieved_at": img.retrieved_at.isoformat() if img.retrieved_at else None,
            "verified": img.verified,
            "verification_status": img.verification_status,
            "content_hash": img.content_hash,
            "width": img.width,
            "height": img.height,
            "license_basis": img.license_basis,
            "provenance": {
                "source_url": img.provenance.source_url if img.provenance else img.source_url,
                "source_domain": img.provenance.source_domain if img.provenance else img.source_domain,
                "extracted_page": img.provenance.extracted_page if img.provenance else img.source_page,
                "verified_by": img.provenance.verified_by if img.provenance else "Provenance review required",
                "method": img.provenance.verification_method if img.provenance else "Unavailable — provenance record missing"
            } if img.provenance else None
        }
        for img in images
    ]

@router.post("/{image_id}/verify")
def toggle_image_verification(
    image_id: str,
    current_user: User = Depends(require_permission(PERM_IMAGES_MANAGE)),
    db: Session = Depends(get_db)
):
    img_query = db.query(AitImage).filter(AitImage.id == image_id)
    if (current_user.role or "").upper() != "SUPER_ADMIN":
        img_query = img_query.filter(AitImage.college_id == current_user.college_id)
    img = img_query.first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    img.verified = not img.verified
    img.verification_status = "PUBLISHED" if img.verified else "PENDING_REVIEW"
    img.last_verified_at = datetime.now(timezone.utc)
    db.commit()

    log_admin_audit(db, current_user, "TOGGLE_IMAGE_VERIFICATION", "IMAGE", {
        "id": img.id,
        "new_status": img.verification_status
    })

    return {"message": f"Image verification updated to {img.verification_status}", "verified": img.verified}

@router.post("/sync")
def sync_official_images(
    college_id: Optional[str] = Query(None),
    current_user: User = Depends(require_permission(PERM_IMAGES_MANAGE)),
    db: Session = Depends(get_db)
):
    # The synchronizer is tenant-aware. The legacy AIT crawler is used only
    # when the authenticated tenant's own official domain is AIT's domain.
    # Other tenants get no guessed/default source.
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    target_college_id = college_id if is_super and college_id else current_user.college_id
    if not is_super:
        verify_tenant_access(current_user, current_user.college_id)
    tenant = db.query(College).filter(College.id == target_college_id).first() if target_college_id else None
    official_domain = (tenant.official_website or "").lower() if tenant else ""
    if not tenant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An authenticated tenant is required for image synchronization")
    # The existing crawler is explicitly AIT-only.  Never run it for another
    # tenant, even if a college record has incomplete website metadata.
    discovered = ait_image_crawler.discover_official_images() if "aitindia.in" in official_domain else []
    added = 0
    for item in discovered:
        existing = db.query(AitImage).filter(
            AitImage.content_hash == item["content_hash"],
            AitImage.college_id == target_college_id,
        ).first()
        if not existing:
            img = AitImage(
                college_id=target_college_id,
                source_type="OFFICIAL_WEBSITE",
                title=item["title"],
                category=item["category"],
                image_url=item["image_url"],
                thumbnail_url=item["thumbnail_url"],
                source_url=item["source_url"],
                source_page=item["source_page"],
                source_domain=item["source_domain"],
                verified=item["verified"],
                verification_status="PUBLISHED",
                content_hash=item["content_hash"],
                description=item["description"]
            )
            db.add(img)
            db.flush()

            prov = ImageProvenance(
                image_id=img.id,
                source_url=item["source_url"],
                source_domain=item["source_domain"],
                extracted_page=item["source_page"]
            )
            db.add(prov)
            added += 1

    db.commit()
    log_admin_audit(db, current_user, "SYNC_OFFICIAL_IMAGES", "IMAGE", {"added": added})

    return {
        "status": "success",
        "added_images": added,
        "total_discovered": len(discovered)
    }

@router.delete("/{image_id}")
def delete_image(
    image_id: str,
    current_user: User = Depends(require_permission(PERM_IMAGES_MANAGE)),
    db: Session = Depends(get_db)
):
    img_query = db.query(AitImage).filter(AitImage.id == image_id)
    if (current_user.role or "").upper() != "SUPER_ADMIN":
        img_query = img_query.filter(AitImage.college_id == current_user.college_id)
    img = img_query.first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    db.delete(img)
    db.commit()
    log_admin_audit(db, current_user, "DELETE_IMAGE", "IMAGE", {"id": image_id})
    return {"message": "Image removed from official repository"}
