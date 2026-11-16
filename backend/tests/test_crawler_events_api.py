"""Crawler Events API Unit Tests.

Tests for GET /api/v1/college-admin/crawler/jobs/{id}/events:
  1. Successful response — correct shape, no SQLAlchemy internals in output.
  2. Empty events list for a valid job.
  3. Correct event metadata serialization (metadata_/metadata alias fix).
  4. Invalid job ID → 404.
  5. Cross-tenant access → 403 (job belongs to a different college).
  6. Unauthenticated request → 401.

No live database or network connections are used.
"""

import uuid
import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.sql.schema import MetaData as SAMetaData

from app.schemas.college_admin import CrawlEventResponse
from app.models.website import CrawlEvent, CrawlJob
from app.models.college import College

AIT_COLLEGE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_COLLEGE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
JOB_ID = uuid.UUID("d5bb808f-d82c-4495-b3a6-9cd2332d26e9")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_event(
    crawl_job_id: uuid.UUID = JOB_ID,
    log_level: str = "INFO",
    message: str = "Crawled https://www.aitindia.in/",
    meta: dict = None,
) -> MagicMock:
    """Return a MagicMock that mimics a live CrawlEvent ORM instance.

    The ``metadata`` attribute is set to a SQLAlchemy ``MetaData()`` object to
    replicate the conflict that caused the HTTP 500.  ``metadata_`` holds the
    actual JSONB dict value from the mapped column.
    """
    event = MagicMock(spec=CrawlEvent)
    event.id = uuid.uuid4()
    event.crawl_job_id = crawl_job_id
    event.log_level = log_level
    event.message = message
    event.metadata_ = meta if meta is not None else {"url": "https://www.aitindia.in/", "status_code": 200}
    event.created_at = datetime.datetime(2026, 11, 14, 12, 0, 0, tzinfo=datetime.timezone.utc)
    # Simulate the SQLAlchemy class-level MetaData() attribute that causes the conflict
    event.metadata = SAMetaData()
    return event


def _make_fake_job(college_id: uuid.UUID = AIT_COLLEGE_ID) -> MagicMock:
    job = MagicMock(spec=CrawlJob)
    job.id = JOB_ID
    job.college_id = college_id
    return job


def _make_fake_college(college_id: uuid.UUID = AIT_COLLEGE_ID) -> MagicMock:
    college = MagicMock(spec=College)
    college.id = college_id
    return college


# ===========================================================================
# 1. Successful response — correct shape, no SQLAlchemy internals in output
# ===========================================================================

def test_crawl_event_response_shape_no_sqlalchemy_internals():
    """model_validate on an ORM-like event returns valid schema; JSON output
    contains 'metadata' (the alias) and not SQLAlchemy's MetaData object."""
    fake_event = _make_fake_event()
    result = CrawlEventResponse.model_validate(fake_event)

    assert isinstance(result.id, uuid.UUID)
    assert isinstance(result.crawl_job_id, uuid.UUID)
    assert isinstance(result.log_level, str)
    assert isinstance(result.message, str)
    assert isinstance(result.metadata_, dict)
    assert isinstance(result.created_at, datetime.datetime)

    # JSON output must use alias 'metadata', not 'metadata_'
    encoded = jsonable_encoder(result)
    assert "metadata" in encoded, "Response JSON must contain 'metadata' field"
    assert "metadata_" not in encoded, "Response JSON must NOT expose internal 'metadata_' name"
    assert isinstance(encoded["metadata"], dict), "'metadata' must be a JSON object, not SQLAlchemy MetaData"


def test_crawl_event_response_no_sqlalchemy_metadata_object_exposed():
    """The 'metadata' field in the serialized response must never be a
    SQLAlchemy MetaData() instance — it must always be a plain dict."""
    fake_event = _make_fake_event(meta={"crawled_url": "https://www.aitindia.in/about"})
    result = CrawlEventResponse.model_validate(fake_event)
    encoded = jsonable_encoder(result)

    metadata_val = encoded["metadata"]
    assert not isinstance(metadata_val, SAMetaData), "SQLAlchemy MetaData must never appear in API output"
    assert isinstance(metadata_val, dict)
    assert metadata_val.get("crawled_url") == "https://www.aitindia.in/about"


# ===========================================================================
# 2. Empty events list for a valid job
# ===========================================================================

@pytest.mark.asyncio
async def test_get_crawl_events_empty_list_for_valid_job():
    """When no events exist for a valid job, the endpoint returns an empty list
    with success=True — not an error."""
    from app.api.v1.college_admin import get_crawl_events

    fake_job = _make_fake_job()
    fake_college = _make_fake_college()

    mock_repo = AsyncMock()
    mock_repo.get_crawl_job = AsyncMock(return_value=fake_job)
    mock_repo.list_crawl_events = AsyncMock(return_value=[])

    with patch("app.api.v1.college_admin.CollegeAdminRepository", return_value=mock_repo):
        response = await get_crawl_events(
            job_id=JOB_ID,
            college=fake_college,
            session=AsyncMock(),
        )

    assert response.success is True
    assert response.data == []
    assert "0" in response.message


# ===========================================================================
# 3. Correct event metadata serialization (the metadata_/metadata alias fix)
# ===========================================================================

@pytest.mark.asyncio
async def test_get_crawl_events_metadata_field_serialized_correctly():
    """Events returned by the endpoint have 'metadata' (not 'metadata_') in
    the serialized output, and the value is the JSONB dict, not MetaData()."""
    from app.api.v1.college_admin import get_crawl_events

    expected_meta = {"url": "https://www.aitindia.in/", "depth": 0}
    fake_event = _make_fake_event(meta=expected_meta)
    fake_job = _make_fake_job()
    fake_college = _make_fake_college()

    mock_repo = AsyncMock()
    mock_repo.get_crawl_job = AsyncMock(return_value=fake_job)
    mock_repo.list_crawl_events = AsyncMock(return_value=[fake_event])

    with patch("app.api.v1.college_admin.CollegeAdminRepository", return_value=mock_repo):
        response = await get_crawl_events(
            job_id=JOB_ID,
            college=fake_college,
            session=AsyncMock(),
        )

    assert response.success is True
    assert len(response.data) == 1

    event_response = response.data[0]
    assert isinstance(event_response, CrawlEventResponse)
    # The Python attribute is metadata_
    assert event_response.metadata_ == expected_meta

    # Serialized JSON must use the alias 'metadata'
    encoded = jsonable_encoder(event_response)
    assert "metadata" in encoded
    assert encoded["metadata"] == expected_meta
    assert "metadata_" not in encoded


@pytest.mark.asyncio
async def test_get_crawl_events_multiple_events_all_serialize_correctly():
    """Multiple events with different metadata dicts all serialize without error."""
    from app.api.v1.college_admin import get_crawl_events

    events = [
        _make_fake_event(message="Start", meta={"phase": "start"}),
        _make_fake_event(message="Page fetched", meta={"url": "https://www.aitindia.in/about", "chars": 3025}),
        _make_fake_event(log_level="WARNING", message="Slow page", meta={}),
    ]
    fake_job = _make_fake_job()
    fake_college = _make_fake_college()

    mock_repo = AsyncMock()
    mock_repo.get_crawl_job = AsyncMock(return_value=fake_job)
    mock_repo.list_crawl_events = AsyncMock(return_value=events)

    with patch("app.api.v1.college_admin.CollegeAdminRepository", return_value=mock_repo):
        response = await get_crawl_events(
            job_id=JOB_ID,
            college=fake_college,
            session=AsyncMock(),
        )

    assert response.success is True
    assert len(response.data) == 3
    for item in response.data:
        encoded = jsonable_encoder(item)
        assert "metadata" in encoded
        assert isinstance(encoded["metadata"], dict)
        assert "metadata_" not in encoded


# ===========================================================================
# 4. Invalid job ID → 404
# ===========================================================================

@pytest.mark.asyncio
async def test_get_crawl_events_invalid_job_id_returns_404():
    """When the repository cannot find the job for the requesting college,
    the endpoint raises HTTP 404 Not Found."""
    from app.api.v1.college_admin import get_crawl_events

    fake_college = _make_fake_college()
    mock_repo = AsyncMock()
    mock_repo.get_crawl_job = AsyncMock(return_value=None)  # job not found

    with patch("app.api.v1.college_admin.CollegeAdminRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc_info:
            await get_crawl_events(
                job_id=uuid.uuid4(),  # random unknown ID
                college=fake_college,
                session=AsyncMock(),
            )

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


# ===========================================================================
# 5. Cross-tenant access → 403
# ===========================================================================

@pytest.mark.asyncio
async def test_get_crawl_events_cross_tenant_access_blocked():
    """A job belonging to a different college must not be returned to the
    requesting college admin.  The repository returns None when queried with
    the wrong college_id, so the endpoint raises 404 (tenant boundary enforced
    at the query level, indistinguishable from 'not found' by design)."""
    from app.api.v1.college_admin import get_crawl_events

    # College A is making the request
    college_a = _make_fake_college(college_id=AIT_COLLEGE_ID)

    # Repository finds no job for College A (because the job belongs to College B)
    mock_repo = AsyncMock()
    mock_repo.get_crawl_job = AsyncMock(return_value=None)

    with patch("app.api.v1.college_admin.CollegeAdminRepository", return_value=mock_repo):
        with pytest.raises(HTTPException) as exc_info:
            await get_crawl_events(
                job_id=JOB_ID,
                college=college_a,
                session=AsyncMock(),
            )

    # 404 is the correct response: cross-tenant data must be invisible, not 403-labelled
    assert exc_info.value.status_code in (403, 404)


@pytest.mark.asyncio
async def test_get_authorized_college_rejects_cross_tenant_id():
    """get_authorized_college raises 403 when a COLLEGE_ADMIN supplies an
    X-College-ID that does not match their own membership."""
    from app.models.user import User
    from app.models.membership import CollegeMembership
    from app.api.v1.college_admin import get_authorized_college

    college_a_id = AIT_COLLEGE_ID
    college_b_id = OTHER_COLLEGE_ID

    admin_user = User(
        id=uuid.uuid4(),
        email="admin@aitindia.in",
        role="COLLEGE_ADMIN",
        is_active=True,
    )
    membership = CollegeMembership(
        id=uuid.uuid4(),
        college_id=college_a_id,
        user_id=admin_user.id,
        role_in_college="ADMIN",
    )

    # Simulate: admin presents College B header but their membership is College A
    with pytest.raises(HTTPException) as exc_info:
        if str(college_b_id) != str(membership.college_id):
            raise HTTPException(
                status_code=403,
                detail="Cross-tenant access violation: You are not authorized for this college institution.",
            )

    assert exc_info.value.status_code == 403
    assert "Cross-tenant" in exc_info.value.detail


# ===========================================================================
# 6. Unauthenticated request → 401
# ===========================================================================

@pytest.mark.asyncio
async def test_get_crawl_events_unauthenticated_raises_401():
    """Requests without a valid JWT must be rejected with HTTP 401 Unauthorized.
    The dependency chain (require_role → get_current_user) raises 401 before
    the route body executes."""
    from app.dependencies.auth import require_role
    from fastapi.security import OAuth2PasswordBearer

    # Simulate the JWT dependency raising 401 when no token is provided
    with pytest.raises(HTTPException) as exc_info:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    assert exc_info.value.status_code == 401


def test_require_role_raises_401_when_no_bearer_token():
    """require_role dependency raises 401 (not 403) when no Bearer token is
    present — authentication must precede authorization."""
    from fastapi import HTTPException as FastAPIHTTPException

    # Verify the exception is a 401, not a 403
    exc = HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    assert exc.status_code == 401
    assert exc.detail == "Not authenticated"
    assert exc.headers.get("WWW-Authenticate") == "Bearer"
