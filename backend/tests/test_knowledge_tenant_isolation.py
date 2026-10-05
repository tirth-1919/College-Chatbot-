"Focused regressions for tenant-preserving KnowledgeRecord mirroring."""
import uuid
from backend.app.api.v1.admin.knowledge_categories import _mirror_to_retrieval
from backend.app.knowledge.database import KnowledgeDatabase
from backend.app.models.college import College
from backend.app.models.knowledge import AitEntity
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord

def _id(prefix):
    return f"{prefix}-{uuid.uuid4().hex}"


def _college(db, label):
    college = College(
        id=_id("college"),
        name=label,
        code=_id("code")[:45],
        slug=_id("slug"),
        status="ACTIVE",
        registration_status="APPROVED",
    )
    db.add(college)
    db.flush()
    return college

def _record(db, college, title, value, *, category_key="fees", course=None):
    category = KnowledgeCategory(
        id=_id("category"),
        name=f"{title} Category",
        key=f"{category_key}-{uuid.uuid4().hex[:8]}",
        college_id=college.id,
        status="ACTIVE",
    )
    record = KnowledgeRecord(
        id=_id("record"),
        college_id=college.id,
        category=category,
        title=title,
        field_name="fee",
        value=value,
        course=course,
        status="ACTIVE",
        verified=True,
    )
    db.add_all([category, record])
    db.flush()
    return record, category

def test_mirror_preserves_three_independent_college_ids(db):
    colleges = [_college(db, f"College {label}") for label in ("A", "B", "C")]
    records = [
        _record(db, college, f"College {label} Fee", str(amount))[0:2]
        for college, label, amount in zip(colleges, ("A", "B", "C"), (100, 200, 300))
    ]

    for record, category in records:
        _mirror_to_retrieval(db, record, category)
    db.flush()

    for (record, _), college in zip(records, colleges):
        mirrored = db.query(AitEntity).filter(
            AitEntity.source_page == f"knowledge-record:{record.id}"
        ).one()
        assert mirrored.college_id == college.id == record.college_id

def test_existing_mirror_update_repairs_wrong_tenant_from_record(db):
    college_a = _college(db, "College A")
    college_b = _college(db, "College B")
    record, category = _record(db, college_b, "College B Fee", "200")
    mirrored = AitEntity(
        id=_id("entity"),
        college_id=college_a.id,
        category=category.key,
        name=record.title,
        source_url="admin://knowledge-db",
        source_page=f"knowledge-record:{record.id}",
        content_hash="old",
        is_verified=True,
    )
    db.add(mirrored)
    db.flush()

    _mirror_to_retrieval(db, record, category)
    db.flush()

    assert mirrored.college_id == record.college_id == college_b.id

def test_retrieval_isolation_for_same_data_in_two_tenants(db):
    college_a = _college(db, "College A")
    college_b = _college(db, "College B")
    record_a, category_a = _record(db, college_a, "BCA Fee", "10000", course="BCA")
    record_b, category_b = _record(db, college_b, "BCA Fee", "20000", course="BCA")
    _mirror_to_retrieval(db, record_a, category_a)
    _mirror_to_retrieval(db, record_b, category_b)
    db.commit()

    a_results = KnowledgeDatabase.query_entities(db, "BCA fee", college_id=college_a.id)
    b_results = KnowledgeDatabase.query_entities(db, "BCA fee", college_id=college_b.id)

    assert any(item["details"].get("fee") == "10000" for item in a_results)
    assert all(item["details"].get("fee") != "20000" for item in a_results)
    assert any(item["details"].get("fee") == "20000" for item in b_results)
    assert all(item["details"].get("fee") != "10000" for item in b_results)


def test_super_admin_multi_college_records_do_not_use_admin_tenant(db):
    colleges = [_college(db, f"College {label}") for label in ("A", "B", "C")]
    records = [_record(db, college, f"Record {label}", label)[0:2]
               for college, label in zip(colleges, ("A", "B", "C"))]

    for record, category in records:
        _mirror_to_retrieval(db, record, category)
    db.commit()

    mirrored = db.query(AitEntity).filter(
        AitEntity.source_page.in_([f"knowledge-record:{record.id}" for record, _ in records])
    ).all()
    assert {entity.college_id for entity in mirrored} == {college.id for college in colleges}


def test_null_record_tenant_is_not_assigned_or_returned_for_scoped_retrieval(db):
    category = KnowledgeCategory(
        id=_id("category"), name="Unscoped Category", key=_id("key"),
        college_id=None, status="ACTIVE",
    )
    record = KnowledgeRecord(
        id=_id("record"), college_id=None, category=category,
        title="Unscoped Fee", field_name="fee", value="999",
        status="ACTIVE", verified=True,
    )
    db.add_all([category, record])
    db.flush()

    _mirror_to_retrieval(db, record, category)
    db.flush()

    mirrored = db.query(AitEntity).filter(
        AitEntity.source_page == f"knowledge-record:{record.id}"
    ).one()
    assert mirrored.college_id is None
    assert KnowledgeDatabase.query_entities(db, "Unscoped Fee", college_id="some-college") == []
