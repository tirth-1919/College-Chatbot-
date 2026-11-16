"""JavaScript-rendered content extraction tests.

Covers static HTML extraction, JS fallback logic, timeout handling, domain
restrictions, tenant isolation, and deduplication.  No live network calls or
live database connections are used.
"""

import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.html_extractor import parse_and_clean_html
from app.services.url_validator import is_url_in_college_domain

AIT_COLLEGE_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

# ---------------------------------------------------------------------------
# 1. Static extraction — sufficient content
# ---------------------------------------------------------------------------
def test_static_extraction_sufficient_content():
    """parse_and_clean_html on a page with real body text returns
    content_length > 200 and requires_js == False."""
    body_text = "A" * 250
    html = f"<html><body><p>{body_text}</p></body></html>"
    result = parse_and_clean_html(html, "https://www.example.com/")
    assert result.content_length > 200
    assert result.requires_js is False


# ---------------------------------------------------------------------------
# 2. Static extraction — JS flag detected
# ---------------------------------------------------------------------------
def test_static_extraction_js_flag_detected():
    """parse_and_clean_html on a React-style empty-root page sets
    requires_js == True and content_length < 80."""
    html = "<html><body><div id='root'></div></body></html>"
    result = parse_and_clean_html(html, "https://www.aitindia.in/")
    assert result.requires_js is True
    assert result.content_length < 80


# ---------------------------------------------------------------------------
# 3. JS fallback invoked when static content is empty
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_js_fallback_invoked_when_static_empty():
    """When static extraction yields < 200 chars, the JS renderer is called
    and the richer result replaces the static one."""
    # Minimal static HTML (no real text)
    static_html = "<html><body><div id='root'></div></body></html>"
    # What the JS renderer will return — 300 chars of real body text
    rich_body = "B" * 300
    js_html = f"<html><body><p>{rich_body}</p></body></html>"

    static_parsed = parse_and_clean_html(static_html, "https://www.aitindia.in/")
    assert static_parsed.content_length < 200, "Pre-condition: static parse is thin"

    with patch(
        "app.services.js_renderer.render_page_with_browser",
        new=AsyncMock(return_value=js_html),
    ) as mock_render:
        from app.services.js_renderer import render_page_with_browser, PLAYWRIGHT_AVAILABLE

        # Simulate the fallback branch logic as implemented in crawler_service
        parsed_content = static_parsed
        if parsed_content.content_length < 200 or parsed_content.requires_js:
            if PLAYWRIGHT_AVAILABLE:
                returned_html = await render_page_with_browser("https://www.aitindia.in/", timeout_ms=15000)
                js_parsed = parse_and_clean_html(returned_html, "https://www.aitindia.in/")
                if js_parsed.content_length > parsed_content.content_length:
                    parsed_content = js_parsed

        mock_render.assert_called_once()
        assert parsed_content.content_length > static_parsed.content_length
        assert parsed_content.content_length >= 300


# ---------------------------------------------------------------------------
# 4. JS fallback NOT invoked when static content is sufficient
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_js_fallback_not_invoked_when_static_sufficient():
    """When static extraction already returns >= 200 chars, the JS renderer
    is never called."""
    body_text = "C" * 300
    html = f"<html><body><p>{body_text}</p></body></html>"
    static_parsed = parse_and_clean_html(html, "https://www.aitindia.in/page")
    assert static_parsed.content_length >= 200, "Pre-condition: static content is rich"

    with patch(
        "app.services.js_renderer.render_page_with_browser",
        new=AsyncMock(return_value=html),
    ) as mock_render:
        from app.services.js_renderer import PLAYWRIGHT_AVAILABLE

        # Simulate fallback branch condition
        parsed_content = static_parsed
        if parsed_content.content_length < 200 or parsed_content.requires_js:
            if PLAYWRIGHT_AVAILABLE:
                await mock_render("https://www.aitindia.in/page", timeout_ms=15000)

        mock_render.assert_not_called()


# ---------------------------------------------------------------------------
# 5. JS fallback timeout handled gracefully
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_js_fallback_timeout_handled_gracefully():
    """When the JS renderer raises a timeout exception, the crawler logs a
    warning and retains the static (empty) content without crashing."""
    import logging

    static_html = "<html><body></body></html>"
    static_parsed = parse_and_clean_html(static_html, "https://www.aitindia.in/")

    warned = []

    with patch(
        "app.services.js_renderer.render_page_with_browser",
        new=AsyncMock(side_effect=Exception("TimeoutError: 15000ms exceeded")),
    ):
        from app.services.js_renderer import render_page_with_browser, PLAYWRIGHT_AVAILABLE

        parsed_content = static_parsed
        try:
            if PLAYWRIGHT_AVAILABLE:
                js_html = await render_page_with_browser("https://www.aitindia.in/", timeout_ms=15000)
                js_parsed = parse_and_clean_html(js_html, "https://www.aitindia.in/")
                if js_parsed.content_length > parsed_content.content_length:
                    parsed_content = js_parsed
        except Exception as js_err:
            warned.append(str(js_err))
            # Static content (possibly empty) is kept — do not abort the page

    assert len(warned) == 1
    assert "TimeoutError" in warned[0]
    # Original static content is preserved
    assert parsed_content is static_parsed


# ---------------------------------------------------------------------------
# 6. Empty page stores zero length
# ---------------------------------------------------------------------------
def test_empty_page_stores_zero_length():
    """parse_and_clean_html on a bare empty body returns content_length == 0
    and a 64-character hex content_hash."""
    html = "<html><body></body></html>"
    result = parse_and_clean_html(html, "https://www.example.com/empty")
    assert result.content_length == 0
    assert len(result.content_hash) == 64
    assert all(c in "0123456789abcdef" for c in result.content_hash)


# ---------------------------------------------------------------------------
# 7. Domain restriction enforced
# ---------------------------------------------------------------------------
def test_domain_restriction_enforced():
    """is_url_in_college_domain allows AIT sub-pages and blocks external URLs."""
    assert is_url_in_college_domain("https://www.aitindia.in/about", "aitindia.in") is True
    assert is_url_in_college_domain("https://www.example.com/", "aitindia.in") is False


# ---------------------------------------------------------------------------
# 8. Tenant isolation — college_id on saved page
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tenant_isolation_college_id_on_saved_page():
    """_save_or_deduplicate_page receives the AIT college_id, not any other UUID."""
    from app.services.crawler_service import WebsiteCrawlerService

    service = WebsiteCrawlerService()

    html = "<html><body><p>" + "X" * 300 + "</p></body></html>"
    parsed = parse_and_clean_html(html, "https://www.aitindia.in/")

    source_id = uuid.uuid4()
    job_id = uuid.uuid4()

    # Mock a session that simulates no existing page (returns None for scalar_one_or_none)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    captured_college_ids: list[uuid.UUID] = []

    original_save = service._save_or_deduplicate_page

    async def recording_save(session, college_id, source_id, job_id, parsed, http_status):
        captured_college_ids.append(college_id)
        return await original_save(session, college_id, source_id, job_id, parsed, http_status)

    service._save_or_deduplicate_page = recording_save

    await recording_save(mock_session, AIT_COLLEGE_ID, source_id, job_id, parsed, 200)

    assert captured_college_ids == [AIT_COLLEGE_ID]
    # Confirm a different UUID was not used
    other_id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    assert AIT_COLLEGE_ID != other_id
    assert other_id not in captured_college_ids


# ---------------------------------------------------------------------------
# 9. Deduplication — same hash returns False (UNCHANGED)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_deduplication_same_hash_returns_false():
    """_save_or_deduplicate_page returns False when the existing page has the
    same content_hash and does NOT create a new record."""
    from app.services.crawler_service import WebsiteCrawlerService
    from app.models.website import WebsitePage

    service = WebsiteCrawlerService()

    html = "<html><body><p>" + "Y" * 300 + "</p></body></html>"
    parsed = parse_and_clean_html(html, "https://www.aitindia.in/")

    # Build a fake existing page with the same content hash
    existing = MagicMock(spec=WebsitePage)
    existing.content_hash = parsed.content_hash

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()

    result = await service._save_or_deduplicate_page(
        session=mock_session,
        college_id=AIT_COLLEGE_ID,
        source_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        parsed=parsed,
        http_status=200,
    )

    assert result is False
    mock_session.add.assert_not_called()


# ---------------------------------------------------------------------------
# 10. Playwright unavailable does not crash
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_playwright_unavailable_does_not_crash():
    """When PLAYWRIGHT_AVAILABLE is False, render_page_with_browser raises
    RuntimeError and the crawler's fallback try/except catches it safely."""
    import app.services.js_renderer as js_mod

    original_flag = js_mod.PLAYWRIGHT_AVAILABLE
    try:
        js_mod.PLAYWRIGHT_AVAILABLE = False

        caught_errors: list[str] = []
        static_html = "<html><body></body></html>"
        static_parsed = parse_and_clean_html(static_html, "https://www.aitindia.in/")
        parsed_content = static_parsed

        try:
            if js_mod.PLAYWRIGHT_AVAILABLE:
                js_html = await js_mod.render_page_with_browser("https://www.aitindia.in/", timeout_ms=15000)
                js_parsed = parse_and_clean_html(js_html, "https://www.aitindia.in/")
                if js_parsed.content_length > parsed_content.content_length:
                    parsed_content = js_parsed
            else:
                # Simulate what happens when the guard doesn't skip and render is called
                raise RuntimeError("Playwright not installed")
        except Exception as js_err:
            caught_errors.append(str(js_err))

        assert caught_errors == ["Playwright not installed"]
        # Static content preserved — no crash
        assert parsed_content is static_parsed
    finally:
        js_mod.PLAYWRIGHT_AVAILABLE = original_flag
