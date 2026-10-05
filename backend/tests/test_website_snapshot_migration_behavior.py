"Focused non-destructive WebsiteSnapshot migration behavior tests."""
import hashlib
import importlib.util
from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.core.database import Base
from backend.app.models.college import College
from backend.app.models.knowledge import WebsiteSnapshot
@pytest.fixture
def snapshot_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    db = factory()
    db.add_all([
        College(id="snapshot-a", name="Snapshot A", code="SNA", slug="snapshot-a", status="ACTIVE", registration_status="APPROVED"),
        College(id="snapshot-b", name="Snapshot B", code="SNB", slug="snapshot-b", status="ACTIVE", registration_status="APPROVED"),
    ])
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()

def _snapshot(college_id, url, key):
    return WebsiteSnapshot(
        id=key, college_id=college_id, url=url, title="Test",
        content_hash=hashlib.sha256(key.encode()).hexdigest(),
        text_content="controlled test source", status_code=200,
        last_crawled_at=datetime.now(timezone.utc),
    )

def test_same_college_same_url_is_rejected(snapshot_db):
    snapshot_db.add(_snapshot("snapshot-a", "https://same.test/page", "snap-1"))
    snapshot_db.commit()
    snapshot_db.add(_snapshot("snapshot-a", "https://same.test/page", "snap-2"))
    with pytest.raises(IntegrityError):
        snapshot_db.commit()
    snapshot_db.rollback()

def test_different_colleges_same_url_is_allowed(snapshot_db):
    snapshot_db.add_all([
        _snapshot("snapshot-a", "https://shared.test/page", "snap-a"),
        _snapshot("snapshot-b", "https://shared.test/page", "snap-b"),
    ])
    snapshot_db.commit()
    assert snapshot_db.query(WebsiteSnapshot).count() == 2

def test_null_tenant_is_not_silently_assigned(snapshot_db):
    row = _snapshot(None, "https://legacy.test/page", "snap-null")
    snapshot_db.add(row)
    snapshot_db.commit()
    snapshot_db.refresh(row)
    assert row.college_id is None

def test_existing_duplicate_rows_abort_migration_without_deletion(snapshot_db):
    bind = snapshot_db.get_bind()
    with bind.begin() as connection:
        connection.exec_driver_sql("DROP TABLE website_snapshots")
        connection.exec_driver_sql("""
            CREATE TABLE website_snapshots (
                id VARCHAR(36) PRIMARY KEY,
                college_id VARCHAR(36), url VARCHAR(500) NOT NULL,
                title VARCHAR(255), content_hash VARCHAR(64) NOT NULL,
                text_content TEXT NOT NULL, status_code INTEGER
            )
        """)
        insert_sql = text("""
            INSERT INTO website_snapshots
            (id, college_id, url, title, content_hash, text_content, status_code)
            VALUES (:id, :college_id, :url, :title, :content_hash, :text_content, :status_code)
        """)
        connection.execute(insert_sql, {"id": "dup-1", "college_id": "snapshot-a", "url": "https://duplicate.test/page", "title": "D", "content_hash": "a", "text_content": "one", "status_code": 200})
        connection.execute(insert_sql, {"id": "dup-2", "college_id": "snapshot-a", "url": "https://duplicate.test/page", "title": "D", "content_hash": "b", "text_content": "two", "status_code": 200})
    path = "backend/alembic/versions/20260926_002_website_snapshot_uniqueness.py"
    spec = importlib.util.spec_from_file_location("snapshot_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    class Op:
        @staticmethod
        def get_bind():
            return bind
    original_op = migration.op
    migration.op = Op
    try:
        with pytest.raises(RuntimeError, match="Unresolved duplicate"):
            migration.upgrade()
    finally:
        migration.op = original_op
    assert snapshot_db.execute(text("SELECT COUNT(*) FROM website_snapshots WHERE id IN ('dup-1', 'dup-2')")).scalar_one() == 2
