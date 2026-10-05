"Focused regression tests for tenant-scoped verified knowledge retrieval."""
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base
from backend.app.knowledge.database import knowledge_db
from backend.app.models.college import College
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord

def _session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_ait_bca_fee_is_retrieved_with_program_year_and_tenant_scope():
    engine, db = _session()
    now = datetime.now(timezone.utc)
    try:
        ait = College(
            id="ait-default-tenant-0001", name="Ahmedabad Institute of Technology",
            code="AIT", slug="ait", status="ACTIVE", registration_status="APPROVED",
            created_at=now,
        )
        rcti = College(
            id="rcti-tenant", name="R.C. Technical Institute", code="RCTI",
            slug="rcti", status="ACTIVE", registration_status="APPROVED", created_at=now,
        )
        fees = KnowledgeCategory(
            id="fees-category", name="Fees", key="fees", status="ACTIVE", college_id=ait.id,
        )
        rcti_fees = KnowledgeCategory(
            id="rcti-fees-category", name="Fees", key="fees", status="ACTIVE", college_id=rcti.id,
        )
        db.add_all([ait, rcti, fees, rcti_fees])
        db.flush()
        db.add_all([
            KnowledgeRecord(
                id="ait-bca-fee", college_id=ait.id, category_id=fees.id, course="BCA",
                academic_year="2026-27", title="BCA Semester 1 Fee", field_name="Semester Fee",
                value="₹32,000", source_type="ADMIN_VERIFIED", status="ACTIVE", verified=True,
            ),
            KnowledgeRecord(
                id="ait-mca-fee", college_id=ait.id, category_id=fees.id, course="MCA",
                academic_year="2026-27", title="MCA Semester 1 Fee", field_name="Semester Fee",
                value="₹40,000", source_type="ADMIN_VERIFIED", status="ACTIVE", verified=True,
            ),
            KnowledgeRecord(
                id="rcti-bca-fee", college_id=rcti.id, category_id=rcti_fees.id, course="BCA",
                academic_year="2026-27", title="RCTI BCA Fee", field_name="Semester Fee",
                value="₹48,000", source_type="ADMIN_VERIFIED", status="ACTIVE", verified=True,
            ),
        ])
        db.commit()

        query = "What is the BCA fee at Ahmedabad Institute of Technology for the 2026-27 academic year?"
        results = knowledge_db.query_entities(db, query, college_id=ait.id)

        assert any(r["course"] == "BCA" and r["details"]["value"] == "₹32,000" for r in results)
        assert all(r["college_id"] == ait.id for r in results)
        assert not any(r["course"] == "MCA" for r in results)
        assert not any(r["details"].get("value") == "₹48,000" for r in results)
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_canonical_tenant_and_status_boundary_excludes_ait_like_synthetic_records():
    engine, db = _session()
    now = datetime.now(timezone.utc)
    try:
        canonical_ait = College(
            id="canonical-ait", name="Ahmedabad Institute of Technology",
            code="AIT", slug="ait", status="ACTIVE", registration_status="APPROVED", created_at=now,
        )
        synthetic_ait = College(
            id="synthetic-rvmodait", name="Synthetic College AIT-like",
            code="RVMODAIT-001", slug="retrieval-ait-synthetic", status="ACTIVE", registration_status="APPROVED", created_at=now,
        )
        other = College(
            id="other-college", name="Other College", code="OTHER", slug="other", status="ACTIVE", registration_status="APPROVED", created_at=now,
        )
        categories = [
            KnowledgeCategory(id="canonical-fees", name="Fees", key="fees", status="ACTIVE", college_id=canonical_ait.id),
            KnowledgeCategory(id="synthetic-fees", name="Fees", key="fees", status="ACTIVE", college_id=synthetic_ait.id),
            KnowledgeCategory(id="other-fees", name="Fees", key="fees", status="ACTIVE", college_id=other.id),
        ]
        db.add_all([canonical_ait, synthetic_ait, other, *categories])
        db.flush()
        db.add_all([
            KnowledgeRecord(
                id="canonical-bca-fee", college_id=canonical_ait.id, category_id="canonical-fees",
                course="BCA", title="BCA Fee", value="₹32,000", source_type="ADMIN_VERIFIED",
                status="ACTIVE", verified=True,
            ),
            KnowledgeRecord(
                id="synthetic-bca-fee", college_id=synthetic_ait.id, category_id="synthetic-fees",
                course="BCA", title="AIT-like Synthetic BCA Fee", value="₹999", source_type="ADMIN_VERIFIED",
                status="ACTIVE", verified=True,
            ),
            KnowledgeRecord(
                id="other-bca-fee", college_id=other.id, category_id="other-fees",
                course="BCA", title="Matching BCA Fee", value="₹111,000", source_type="ADMIN_VERIFIED",
                status="ACTIVE", verified=True,
            ),
            KnowledgeRecord(
                id="unverified-bca-fee", college_id=canonical_ait.id, category_id="canonical-fees",
                course="BCA", title="Unverified BCA Fee", value="₹1", source_type="ADMIN_VERIFIED",
                status="ACTIVE", verified=False,
            ),
            KnowledgeRecord(
                id="draft-bca-fee", college_id=canonical_ait.id, category_id="canonical-fees",
                course="BCA", title="Draft BCA Fee", value="₹2", source_type="ADMIN_VERIFIED",
                status="DRAFT", verified=True,
            ),
            KnowledgeRecord(
                id="pending-bca-fee", college_id=canonical_ait.id, category_id="canonical-fees",
                course="BCA", title="Pending BCA Fee", value="₹3", source_type="ADMIN_VERIFIED",
                status="PENDING_REVIEW", verified=True,
            ),
            KnowledgeRecord(
                id="inactive-bca-fee", college_id=canonical_ait.id, category_id="canonical-fees",
                course="BCA", title="Inactive BCA Fee", value="₹4", source_type="ADMIN_VERIFIED",
                status="INACTIVE", verified=True,
            ),
        ])
        db.commit()

        results = knowledge_db.query_entities(db, "BCA fee", college_id=canonical_ait.id)
        result_ids = {row["id"] for row in results}
        assert result_ids == {"canonical-bca-fee"}
        assert results[0]["details"]["value"] == "₹32,000"
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
