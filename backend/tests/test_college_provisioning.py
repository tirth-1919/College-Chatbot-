"""
Test College Provisioning and Category Lifecycle

Verifies that categories are properly seeded during college approval
and are tenant-scoped.

Note on re-runnability: these tests run against the real database and are
written to be idempotent — a college/category created by a previous run is
re-used rather than re-inserted (get-or-create). This keeps the tests green
on repeat runs WITHOUT deleting or resetting any database data.
"""
import uuid

import pytest
from sqlalchemy.orm import Session
from backend.app.models.college import College
from backend.app.models.user import User
from backend.app.models.knowledge_categories import KnowledgeCategory
from backend.app.scripts.seed_knowledge_categories import (
    INITIAL_CATEGORIES,
    seed_knowledge_categories,
)


def get_or_create_college(db: Session, **kwargs) -> College:
    """Idempotent college creation for repeat test runs (no data deletion)."""
    college = db.query(College).filter(College.id == kwargs["id"]).first()
    if college:
        return college
    college = College(**kwargs)
    db.add(college)
    db.commit()
    db.refresh(college)
    return college


def test_categories_created_during_approval(db: Session):
    """
    When a college is approved, categories should be auto-created for that college.
    """
    college = get_or_create_college(
        db,
        id="test-college-1",
        name="Test University",
        code="TU1",
        slug="test-university",
        official_email="admin@test-university.edu",
        status="ACTIVE",
        registration_status="APPROVED",
    )

    # Seed categories for this college (idempotent)
    seed_knowledge_categories(db, college_id=college.id)

    # Verify the full category set now exists for this college
    college_categories = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == college.id
    ).all()

    assert len(college_categories) == len(INITIAL_CATEGORIES), \
        f"Expected {len(INITIAL_CATEGORIES)} categories, found {len(college_categories)}"

    # Verify no NULL-tenant categories were created
    global_categories = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == None
    ).all()

    assert len(global_categories) == 0, "NULL-tenant categories were created"


def test_multiple_colleges_can_have_same_category_keys(db: Session):
    """
    Multiple colleges should be able to have categories with the same keys
    (e.g., both can have "fees", "faculty", "courses").
    """
    college_a = get_or_create_college(
        db,
        id="test-college-a",
        name="College A",
        code="COLA",
        slug="college-a",
        official_email="admin@college-a.edu",
        status="ACTIVE",
        registration_status="APPROVED",
    )
    college_b = get_or_create_college(
        db,
        id="test-college-b",
        name="College B",
        code="COLB",
        slug="college-b",
        official_email="admin@college-b.edu",
        status="ACTIVE",
        registration_status="APPROVED",
    )

    # Seed categories for both colleges (idempotent)
    seed_knowledge_categories(db, college_id=college_a.id)
    seed_knowledge_categories(db, college_id=college_b.id)

    college_a_cats = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == college_a.id
    ).all()
    college_b_cats = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == college_b.id
    ).all()

    # Verify both have their own complete category set
    assert len(college_a_cats) == len(INITIAL_CATEGORIES), \
        f"College A expected {len(INITIAL_CATEGORIES)} categories, found {len(college_a_cats)}"
    assert len(college_b_cats) == len(INITIAL_CATEGORIES), \
        f"College B expected {len(INITIAL_CATEGORIES)} categories, found {len(college_b_cats)}"

    # Verify they can have same keys
    keys_a = {cat.key for cat in college_a_cats}
    keys_b = {cat.key for cat in college_b_cats}

    # There should be overlapping keys (like "fees", "faculty")
    overlapping_keys = keys_a & keys_b
    assert len(overlapping_keys) > 0, "No overlapping category keys between colleges"

    print(f"[OK] Both colleges share these category keys: {overlapping_keys}")


def test_category_uniqueness_within_college(db: Session):
    """
    Within a single college, category keys must be unique.
    Attempting to create duplicate categories for the same college should fail.
    """
    college = get_or_create_college(
        db,
        id="test-college-unique",
        name="Unique Test College",
        code="UTC",
        slug="unique-test",
        official_email="admin@unique-test.edu",
        status="ACTIVE",
        registration_status="APPROVED",
    )

    # Create first category (fresh id so repeat runs never collide)
    cat1 = KnowledgeCategory(
        id=f"cat-uniq-{uuid.uuid4().hex[:12]}",
        college_id=college.id,
        name=f"Fees Information {uuid.uuid4().hex[:6]}",
        key=f"fees-uniq-{uuid.uuid4().hex[:8]}",
        status="ACTIVE"
    )
    db.add(cat1)
    db.commit()

    # Attempt to create duplicate category with same key
    cat2 = KnowledgeCategory(
        id=f"cat-uniq-{uuid.uuid4().hex[:12]}",
        college_id=college.id,
        name="Fee Details",
        key=cat1.key,  # Same key as cat1
        status="ACTIVE"
    )
    db.add(cat2)

    # Should raise integrity error
    with pytest.raises(Exception):  # IntegrityError or similar
        db.commit()

    db.rollback()


def test_different_colleges_duplicate_keys_allowed(db: Session):
    """
    Different colleges CAN have categories with the same key.
    This is the core multi-tenant requirement.
    """
    college1 = get_or_create_college(
        db,
        id="test-college-dup-1",
        name="College One",
        code="C1",
        slug="college-one",
        official_email="admin@college-one.edu",
        status="ACTIVE",
    )
    college2 = get_or_create_college(
        db,
        id="test-college-dup-2",
        name="College Two",
        code="C2",
        slug="college-two",
        official_email="admin@college-two.edu",
        status="ACTIVE",
    )

    shared_key = f"fees-dup-{uuid.uuid4().hex[:8]}"
    shared_name = f"Fees {uuid.uuid4().hex[:8]}"

    # Create the same-key category for College 1
    cat1 = KnowledgeCategory(
        id=f"cat-dup-{uuid.uuid4().hex[:12]}",
        college_id=college1.id,
        name=shared_name,
        key=shared_key,
        status="ACTIVE"
    )
    db.add(cat1)
    db.commit()

    # Create same key for College 2 (same key, different college) — must succeed
    cat2 = KnowledgeCategory(
        id=f"cat-dup-{uuid.uuid4().hex[:12]}",
        college_id=college2.id,
        name=shared_name,  # Same name, different college
        key=shared_key,  # Same key, different college
        status="ACTIVE"
    )
    db.add(cat2)
    db.commit()  # Should succeed

    # Verify both exist
    assert db.query(KnowledgeCategory).filter(
        KnowledgeCategory.id == cat1.id
    ).first() is not None

    assert db.query(KnowledgeCategory).filter(
        KnowledgeCategory.id == cat2.id
    ).first() is not None

    print("[OK] Different colleges successfully created categories with same key")


def test_category_seeding_idempotent(db: Session):
    """
    Running category seeding multiple times for the same college should be safe.
    """
    college = get_or_create_college(
        db,
        id="test-college-idem",
        name="Idempotent Test College",
        code="ITC",
        slug="idempotent-test",
        official_email="admin@idempotent-test.edu",
        status="ACTIVE",
    )

    # First seeding
    cats_first = seed_knowledge_categories(db, college_id=college.id)
    first_count = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == college.id
    ).count()

    # Second seeding
    cats_second = seed_knowledge_categories(db, college_id=college.id)
    second_count = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == college.id
    ).count()

    # Count should remain stable
    assert first_count == second_count, "Category count changed on re-run"
    assert cats_second == 0, "Second run should skip existing categories"
    assert first_count == len(INITIAL_CATEGORIES), \
        f"First seeding should create {len(INITIAL_CATEGORIES)} categories, created {first_count}"


def test_categories_contain_college_id(db: Session):
    """
    Every category created during college approval must have the correct college_id.
    """
    college = get_or_create_college(
        db,
        id="test-college-cid",
        name="College ID Test",
        code="CID",
        slug="college-id-test",
        official_email="admin@college-id-test.edu",
        status="ACTIVE",
    )

    # Seed categories
    seed_knowledge_categories(db, college_id=college.id)

    # Get all categories for this college
    categories = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == college.id
    ).all()

    # Verify every category has the correct college_id
    for cat in categories:
        assert cat.college_id == college.id, \
            f"Category '{cat.name}' has wrong college_id: {cat.college_id}"

    # Verify no categories have NULL college_id
    null_categories = db.query(KnowledgeCategory).filter(
        KnowledgeCategory.college_id == None
    ).count()

    assert null_categories == 0, "Found categories with NULL college_id"
