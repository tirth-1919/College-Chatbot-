"""Quick smoke test for the CrawlEventResponse MetaData fix."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import uuid
import datetime
from types import SimpleNamespace
from app.schemas.college_admin import CrawlEventResponse
import sqlalchemy  # bring in real MetaData to simulate the collision

def test_orm_instance_with_metadata_col():
    """model_validate on an ORM-like object with metadata_ attr should work."""
    orm = SimpleNamespace(
        id=uuid.uuid4(),
        crawl_job_id=uuid.uuid4(),
        log_level="INFO",
        message="Crawl started",
        metadata_={"url": "https://example.com", "depth": 1},
        created_at=datetime.datetime.now(datetime.timezone.utc),
        # Simulate the SQLAlchemy class-level attribute collision
        metadata=sqlalchemy.MetaData(),
    )
    r = CrawlEventResponse.model_validate(orm, from_attributes=True)
    assert r.message == "Crawl started"
    assert r.metadata_ == {"url": "https://example.com", "depth": 1}
    print("PASS: ORM instance with real MetaData() collision")

def test_empty_metadata_fallback():
    """metadata_ that is not a dict should fall back to empty dict."""
    orm = SimpleNamespace(
        id=uuid.uuid4(),
        crawl_job_id=uuid.uuid4(),
        log_level="WARN",
        message="Skipped page",
        metadata_=None,  # bad value — should be sanitised to {}
        created_at=datetime.datetime.now(datetime.timezone.utc),
        metadata=sqlalchemy.MetaData(),
    )
    r = CrawlEventResponse.model_validate(orm, from_attributes=True)
    assert r.metadata_ == {}
    print("PASS: None metadata_ sanitised to {}")

def test_dict_path_with_poisoned_metadata():
    """Dict input whose metadata key holds a MetaData() should be sanitised."""
    data = {
        "id": str(uuid.uuid4()),
        "crawl_job_id": str(uuid.uuid4()),
        "log_level": "ERROR",
        "message": "Failed",
        "metadata": sqlalchemy.MetaData(),  # poisoned
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    r = CrawlEventResponse.model_validate(data)
    assert r.metadata_ == {}
    print("PASS: Dict with MetaData() in metadata key sanitised to {}")

if __name__ == "__main__":
    test_orm_instance_with_metadata_col()
    test_empty_metadata_fallback()
    test_dict_path_with_poisoned_metadata()
    print("\nAll CrawlEventResponse tests passed.")
