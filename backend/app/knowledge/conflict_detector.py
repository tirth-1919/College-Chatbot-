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
        # Conflicts are tenant-owned. Legacy NULL-tenant entities cannot be
        # safely attributed and are therefore excluded from production scans.
        entities = db.query(AitEntity).filter(AitEntity.college_id.isnot(None)).all()

        for entity in entities:
            # Match the snapshot within the same tenant; URL alone is not an
            # authoritative tenant boundary.
            snapshot = (
                db.query(WebsiteSnapshot)
                .filter(
                    WebsiteSnapshot.url == entity.source_url,
                    WebsiteSnapshot.college_id == entity.college_id,
                )
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
                        KnowledgeConflict.college_id == entity.college_id,
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
                                college_id=entity.college_id,
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
        conflict = db.query(KnowledgeConflict).filter(
            KnowledgeConflict.id == conflict_id,
            KnowledgeConflict.college_id.isnot(None),
        ).first()
        if not conflict:
            return None

        conflict.resolution_status = resolution_status
        conflict.resolved_by = admin_id
        conflict.resolution_notes = notes
        conflict.resolved_at = datetime.now(timezone.utc)
        db.commit()
        return conflict

conflict_detector = ConflictDetector()
