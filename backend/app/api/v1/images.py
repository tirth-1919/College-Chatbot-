from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.api.v1.auth import get_current_user
from backend.app.models.image import AitImage
from backend.app.models.user import User
from backend.app.models.college import College
from backend.app.images.retrieval import image_retrieval_engine

router = APIRouter(prefix="/images", tags=["AIT Images"])

@router.get("/query")
def query_images(
    q: str = Query(..., description="Query for campus, library, computer lab, classroom, sports, canteen, etc."),
    college_id: Optional[str] = Query(None, description="Target college for Super Admins only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    P0 Verified Real AIT Image retrieval endpoint.
    """
    role = (current_user.role or "").upper()
    target_college_id = college_id if role == "SUPER_ADMIN" else current_user.college_id
    if not target_college_id:
        raise HTTPException(status_code=400, detail="An explicit college context is required")
    tenant = db.query(College).filter(
        College.id == target_college_id,
        College.status == "ACTIVE",
        College.registration_status == "APPROVED",
    ).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Target college is not active and approved")
    results = image_retrieval_engine.match_visual_query(db, q, college_id=target_college_id)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }

@router.get("/gallery")
def get_gallery(
    category: Optional[str] = None,
    college_id: Optional[str] = Query(None, description="Target college for Super Admins only"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = (current_user.role or "").upper()
    target_college_id = college_id if role == "SUPER_ADMIN" else current_user.college_id
    if not target_college_id:
        raise HTTPException(status_code=400, detail="An explicit college context is required")
    tenant = db.query(College).filter(
        College.id == target_college_id,
        College.status == "ACTIVE",
        College.registration_status == "APPROVED",
    ).first()
    if not tenant:
        raise HTTPException(status_code=400, detail="Target college is not active and approved")
    q = db.query(AitImage).filter(
        AitImage.verified == True,
        AitImage.college_id.isnot(None),
    )
    if target_college_id:
        q = q.filter(AitImage.college_id == target_college_id)
    else:
        q = q.filter(AitImage.college_id == "__none__")
    if category:
        q = q.filter(AitImage.category == category)
    images = q.all()

    return [
        {
            "id": img.id,
            "title": img.title,
            "description": img.description,
            "category": img.category,
            "image_url": img.image_url,
            "thumbnail_url": img.thumbnail_url or img.image_url,
            "source_url": img.source_url,
            "verified": img.verified,
            "license": img.license_basis
        }
        for img in images
    ]

@router.get("/categories")
def get_categories():
    return [
        "campus", "library", "computer_lab", "classroom", "sports", "canteen", "event", "logo"
    ]
