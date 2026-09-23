import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from backend.app.models.image import AitImage

class ImageRetrievalEngine:
    FACILITY_CATEGORY_MAP = {
        "library": "library",
        "computer lab": "computer_lab",
        "lab": "computer_lab",
        "classroom": "classroom",
        "smart class": "classroom",
        "sports": "sports",
        "sports ground": "sports",
        "ground": "sports",
        "canteen": "canteen",
        "cafeteria": "canteen",
        "campus": "campus",
        "building": "campus",
        "event": "event",
        "annual day": "event",
        "logo": "logo"
    }

    @classmethod
    def match_visual_query(cls, db: Session, query: str,
                           college_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Tenant-scoped image retrieval (§15): only the ACTIVE college's
        verified images can be returned for its conversations."""
        query_lower = query.lower()

        # Identify target facility or category
        target_category = None
        for key, cat in cls.FACILITY_CATEGORY_MAP.items():
            if key in query_lower:
                target_category = cat
                break

        q = db.query(AitImage).filter(AitImage.verified == True)
        if college_id:
            q = q.filter(AitImage.college_id == college_id)

        if target_category:
            q = q.filter(or_(AitImage.category == target_category, AitImage.title.ilike(f"%{target_category}%")))
        else:
            # Match by search keywords
            terms = re.findall(r'\b[a-zA-Z]{3,}\b', query_lower)
            if terms:
                filters = [AitImage.title.ilike(f"%{t}%") for t in terms]
                filters.extend([AitImage.description.ilike(f"%{t}%") for t in terms])
                q = q.filter(or_(*filters))

        images = q.limit(6).all()

        results = []
        for img in images:
            results.append({
                "id": img.id,
                "title": img.title,
                "description": img.description,
                "category": img.category,
                "image_url": img.image_url,
                "thumbnail_url": img.thumbnail_url or img.image_url,
                "source_url": img.source_url,
                "source_page": img.source_page,
                "source_domain": img.source_domain,
                "verified": img.verified,
                "verification_status": img.verification_status,
                "width": img.width,
                "height": img.height,
                "license": img.license_basis
            })

        return results

image_retrieval_engine = ImageRetrievalEngine()
