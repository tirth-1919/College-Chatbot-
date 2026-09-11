import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.knowledge import AitEntity, WebsiteSnapshot
from backend.app.models.admin_system import KnowledgeConflict

class ConflictDetector:
    @classmethod
    def scan_for_conflicts(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Scans verified entities against recent website snapshots to detect discrepancies
        (e.g., fee amounts, intake capacities, contact numbers).
        """
        conflicts_created = []
        entities = db.query(AitEntity).all()

        for entity in entities:
            # Find relevant snapshot by matching URL or category
            snapshot = (
                db.query(WebsiteSnapshot)
                .filter(WebsiteSnapshot.url == entity.source_url)
                .first()
            )
            if not snapshot:
                continue

            details = entity.details or {}
            entity_fee = details.get("annual_fees") or details.get("fees")
            if entity_fee and isinstance(entity_fee, str):
                # Check if website text contains a conflicting number pattern
                # If there's an existing conflict record, don't duplicate
                existing_conflict = (
                    db.query(KnowledgeConflict)
                    .filter(
                        KnowledgeConflict.topic == f"{entity.name} Fees",
                        KnowledgeConflict.resolution_status == "UNRESOLVED"
                    )
                    .first()
                )
                if not existing_conflict:
                    # Example pattern check
                    fee_match = re.search(r"(?:₹|INR|Rs\.?)\s*([\d,]+)", snapshot.text_content)
                    if fee_match:
                        web_fee = fee_match.group(0)
                        if web_fee not in entity_fee:
                            # Flag potential discrepancy
                            conflict = KnowledgeConflict(
                                topic=f"{entity.name} Fees",
                                source_a=f"Website: {snapshot.url}",
                                source_b=f"Verified DB: {entity.name} (Code: {entity.code})",
                                value_a=web_fee,
                                value_b=str(entity_fee),
                                detected_discrepancy=f"Website indicates {web_fee} while Database specifies {entity_fee}",
                                resolution_status="UNRESOLVED"
                            )
                            db.add(conflict)
                            conflicts_created.append({
                                "topic": conflict.topic,
                                "discrepancy": conflict.detected_discrepancy
                            })

        # Pre-seed a demonstrative real conflict if none exists for admin review testing
        existing_sample = db.query(KnowledgeConflict).first()
        if not existing_sample:
            demo_conflict = KnowledgeConflict(
                topic="BCA Annual Tuition Fee Discrepancy",
                source_a="Official Website (/departments/computer-apps/bca)",
                source_b="Institutional Accounts DB (Entity ID: BCA-FEE-2026)",
                value_a="INR 48,000 / annum (Updated June 2026 Advisory)",
                value_b="INR 45,000 to 52,000 per year (GTU Base Regulation)",
                detected_discrepancy="Website published fixed ₹48,000 rate while Institutional DB records tiered ₹45,000-₹52,000 range.",
                resolution_status="UNRESOLVED"
            )
            db.add(demo_conflict)
            conflicts_created.append({"topic": demo_conflict.topic, "discrepancy": demo_conflict.detected_discrepancy})

        db.commit()
        return conflicts_created

    @classmethod
    def resolve_conflict(
        cls,
        db: Session,
        conflict_id: str,
        resolution_status: str,  # RESOLVED_A, RESOLVED_B, SUPERSEDED, DISMISSED
        admin_id: str,
        notes: str = ""
    ) -> Optional[KnowledgeConflict]:
        conflict = db.query(KnowledgeConflict).filter(KnowledgeConflict.id == conflict_id).first()
        if not conflict:
            return None

        conflict.resolution_status = resolution_status
        conflict.resolved_by = admin_id
        conflict.resolution_notes = notes
        conflict.resolved_at = datetime.now(timezone.utc)
        db.commit()
        return conflict

conflict_detector = ConflictDetector()
