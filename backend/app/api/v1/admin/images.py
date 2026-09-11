from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_IMAGES_MANAGE
from backend.app.models.image import AitImage, ImageProvenance
from backend.app.models.user import User
from backend.app.images.crawler import ait_image_crawler

router = APIRouter(prefix="/images", tags=["Admin Image Management"])

@router.get("")
def list_images(
    category: Optional[str] = None,
    verified_only: Optional[bool] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(AitImage)
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
            "verified": img.verified,
            "verification_status": img.verification_status,
            "content_hash": img.content_hash,
            "width": img.width,
            "height": img.height,
            "license_basis": img.license_basis,
            "provenance": {
                "extracted_page": img.provenance.extracted_page if img.provenance else img.source_page,
                "verified_by": img.provenance.verified_by if img.provenance else "AIT Ingestion Pipeline",
                "method": img.provenance.verification_method if img.provenance else "Official Domain Whitelist"
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
    img = db.query(AitImage).filter(AitImage.id == image_id).first()
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
    current_user: User = Depends(require_permission(PERM_IMAGES_MANAGE)),
    db: Session = Depends(get_db)
):
    discovered = ait_image_crawler.discover_official_images()
    added = 0
    for item in discovered:
        existing = db.query(AitImage).filter(AitImage.content_hash == item["content_hash"]).first()
        if not existing:
            img = AitImage(
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
    img = db.query(AitImage).filter(AitImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    db.delete(img)
    db.commit()
    log_admin_audit(db, current_user, "DELETE_IMAGE", "IMAGE", {"id": image_id})
    return {"message": "Image removed from official repository"}
