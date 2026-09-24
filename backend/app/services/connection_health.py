"""
Connection Health Service

Determines whether a college has usable verified knowledge infrastructure.
A college is only "CONNECTED_VERIFIED" when it has:
- ACTIVE status
- Official website configured AND reachable (or recent successful check)
- Verified knowledge records OR RAG documents OR website snapshots

This prevents claiming a college is "officially connected" when it only has
a database row but no actual knowledge sources.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.college import College
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
from backend.app.models.document import Document, VISIBILITY_ADMIN_VERIFIED
from backend.app.models.knowledge_categories import KnowledgeRecord

logger = logging.getLogger(__name__)


class ConnectionHealthService:
    """Service for calculating and updating college connection health status."""

    @classmethod
    def calculate_connection_status(
        cls,
        db: Session,
        college: College,
        force_website_check: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive connection health for a college.
        
        Returns dict with:
        - connection_status: CONNECTED_VERIFIED | CONNECTED_PARTIAL | REGISTERED_PENDING_SETUP | NOT_CONNECTED
        - website_reachable: bool
        - website_pages_indexed: int
        - verified_db_records: int
        - rag_documents: int
        - knowledge_health: HEALTHY | PARTIAL | MISSING
        - issues: List[str] - human-readable issues
        """
        
        if college.status != "ACTIVE":
            return {
                "connection_status": "REGISTERED_PENDING_SETUP" if college.status == "PENDING" else "NOT_CONNECTED",
                "website_reachable": False,
                "website_pages_indexed": 0,
                "verified_db_records": 0,
                "rag_documents": 0,
                "knowledge_health": "MISSING",
                "issues": [f"College status is {college.status}, not ACTIVE"],
            }

        # Check website health
        website_reachable = False
        website_pages = 0
        website_issue = None

        if college.official_website:
            # Check recent website check (within last 24 hours)
            if college.website_last_checked_at:
                # Ensure both datetimes are timezone-aware for comparison
                last_checked = college.website_last_checked_at
                if last_checked.tzinfo is None:
                    last_checked = last_checked.replace(tzinfo=timezone.utc)
                    
                hours_since_check = (datetime.now(timezone.utc) - last_checked).total_seconds() / 3600
                if hours_since_check < 24:
                    # Use cached result
                    website_reachable = college.website_http_status == 200 if college.website_http_status else False
                    website_pages = college.website_pages_indexed or 0
                    if not website_reachable and college.website_error_message:
                        website_issue = college.website_error_message
                elif force_website_check:
                    # Would trigger actual HTTP check here in production
                    # For now, mark as stale
                    website_issue = "Website check is stale (>24h old)"
            
            # Count website snapshots
            website_pages = db.query(func.count(WebsiteSnapshot.id)).filter(
                WebsiteSnapshot.college_id == college.id
            ).scalar() or 0
            
            if website_pages > 0:
                website_reachable = True
        else:
            website_issue = "No official website configured"

        # Check verified database records
        verified_db_records = db.query(func.count(AitEntity.id)).filter(
            AitEntity.college_id == college.id,
            AitEntity.is_verified == True
        ).scalar() or 0

        # Also check knowledge_records table (newer system)
        verified_kr = db.query(func.count(KnowledgeRecord.id)).filter(
            KnowledgeRecord.college_id == college.id,
            KnowledgeRecord.verified == True,
            KnowledgeRecord.status == "ACTIVE"
        ).scalar() or 0
        
        verified_db_records += verified_kr

        # Check RAG documents
        rag_documents = db.query(func.count(Document.id)).filter(
            Document.college_id == college.id,
            Document.visibility == VISIBILITY_ADMIN_VERIFIED
        ).scalar() or 0

        # Determine knowledge health
        total_knowledge_sources = verified_db_records + rag_documents + website_pages
        
        if total_knowledge_sources >= 10:
            knowledge_health = "HEALTHY"
        elif total_knowledge_sources > 0:
            knowledge_health = "PARTIAL"
        else:
            knowledge_health = "MISSING"

        # Determine connection status
        issues = []
        
        if total_knowledge_sources == 0:
            connection_status = "REGISTERED_PENDING_SETUP"
            issues.append("No verified knowledge sources available")
        elif website_reachable and verified_db_records > 0:
            connection_status = "CONNECTED_VERIFIED"
        elif website_reachable or verified_db_records > 0 or rag_documents > 0:
            connection_status = "CONNECTED_PARTIAL"
            if not website_reachable and college.official_website:
                issues.append(website_issue or "Website not verified")
            if verified_db_records == 0:
                issues.append("No verified database records")
            if rag_documents == 0:
                issues.append("No RAG-indexed documents")
        else:
            connection_status = "NOT_CONNECTED"
            issues.append("No knowledge infrastructure connected")

        return {
            "connection_status": connection_status,
            "website_reachable": website_reachable,
            "website_pages_indexed": website_pages,
            "verified_db_records": verified_db_records,
            "rag_documents": rag_documents,
            "knowledge_health": knowledge_health,
            "issues": issues,
            "total_knowledge_sources": total_knowledge_sources,
        }

    @classmethod
    def update_college_health(
        cls,
        db: Session,
        college: College,
        force_website_check: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate and persist connection health to college record.
        Returns the calculated health data.
        """
        health = cls.calculate_connection_status(db, college, force_website_check)
        
        # Update college record
        college.connection_status = health["connection_status"]
        college.website_pages_indexed = health["website_pages_indexed"]
        college.verified_records_count = health["verified_db_records"]
        college.rag_documents_count = health["rag_documents"]
        college.broken_sources_count = len(health["issues"])
        college.knowledge_last_updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(college)
        
        logger.info(
            f"Updated connection health for {college.name} ({college.code}): "
            f"status={health['connection_status']}, health={health['knowledge_health']}"
        )
        
        return health

    @classmethod
    async def check_website_health(
        cls,
        db: Session,
        college: College
    ) -> Dict[str, Any]:
        """
        Perform actual HTTP check of college website.
        Updates website health fields in college record.
        """
        import aiohttp
        import asyncio
        
        if not college.official_website:
            return {
                "reachable": False,
                "http_status": None,
                "error": "No official website configured",
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

        now = datetime.now(timezone.utc)
        college.website_last_checked_at = now
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    college.official_website,
                    timeout=aiohttp.ClientTimeout(total=10),
                    allow_redirects=True
                ) as response:
                    college.website_http_status = response.status
                    
                    if response.status == 200:
                        college.website_last_success_at = now
                        college.website_error_message = None
                        
                        # Count existing snapshots
                        pages_count = db.query(func.count(WebsiteSnapshot.id)).filter(
                            WebsiteSnapshot.college_id == college.id
                        ).scalar() or 0
                        college.website_pages_indexed = pages_count
                        
                        db.commit()
                        
                        return {
                            "reachable": True,
                            "http_status": response.status,
                            "pages_indexed": pages_count,
                            "checked_at": now.isoformat(),
                        }
                    else:
                        college.website_last_failure_at = now
                        college.website_error_message = f"HTTP {response.status}"
                        db.commit()
                        
                        return {
                            "reachable": False,
                            "http_status": response.status,
                            "error": f"HTTP {response.status}",
                            "checked_at": now.isoformat(),
                        }
                        
        except asyncio.TimeoutError:
            college.website_last_failure_at = now
            college.website_http_status = None
            college.website_error_message = "Connection timeout"
            db.commit()
            
            return {
                "reachable": False,
                "http_status": None,
                "error": "Connection timeout",
                "checked_at": now.isoformat(),
            }
            
        except Exception as e:
            college.website_last_failure_at = now
            college.website_http_status = None
            college.website_error_message = str(e)[:500]
            db.commit()
            
            return {
                "reachable": False,
                "http_status": None,
                "error": str(e)[:500],
                "checked_at": now.isoformat(),
            }


connection_health_service = ConnectionHealthService()
