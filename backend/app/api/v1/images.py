from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.image import AitImage
from backend.app.images.retrieval import image_retrieval_engine

router = APIRouter(prefix="/images", tags=["AIT Images"])

@router.get("/query")
def query_images(
    q: str = Query(..., description="Query for campus, library, computer lab, classroom, sports, canteen, etc."),
    db: Session = Depends(get_db)
):
    """
    P0 Verified Real AIT Image retrieval endpoint.
    """
    results = image_retrieval_engine.match_visual_query(db, q)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }

@router.get("/gallery")
def get_gallery(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    q = db.query(AitImage).filter(AitImage.verified == True)
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
