"""Official College Website Crawler Service.

Implements secure, asynchronous, multi-tenant website crawling.
Enforces SSRF prevention, domain boundaries, robots.txt policies,
table formatting, content deduplication, and job state orchestration.

All database sessions in this service use ``tenant_session()`` to ensure the
``app.current_college_id`` GUC is set before every query, activating
PostgreSQL RLS policies for the college tenant scope.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
import xml.etree.ElementTree as ET

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import tenant_session
from app.models.college import College
from app.models.website import CrawlEvent, CrawlJob, WebsitePage, WebsiteSource
from app.models.academic import CollegeGalleryImage
from app.services.html_extractor import parse_and_clean_html
from app.services.robots_parser import (
    CRAWLER_USER_AGENT,
    robots_policy_manager,
)
from app.services.url_validator import (
    DomainBoundaryError,
    SSRFProtectionError,
    is_crawleable_resource,
    is_url_in_college_domain,
    normalize_url,
    validate_url_security,
)

logger = logging.getLogger("college_chatbot.crawler")

# Minimum extracted text length below which JS rendering fallback is attempted
JS_FALLBACK_THRESHOLD = 200


class WebsiteCrawlerService:
    """Manages asynchronous web crawling runs for college institution tenants."""

    def __init__(self, max_concurrency: int = 3, timeout_seconds: float = 12.0):
        self.max_concurrency = max_concurrency
        self.timeout_seconds = timeout_seconds

    async def execute_crawl_job(
        self,
        job_id: uuid.UUID,
        college_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Main execution loop for a website crawler job.

        Scoped strictly to college_id tenant.
        """
        async with tenant_session(college_id=college_id) as session:
            # 1. Tenant Verification & Job Initialization
            college = await session.get(College, college_id)
            if not college:
                await self._fail_job(session, job_id, "College tenant not found.")
                return {"success": False, "error": "College not found"}

            source = await session.get(WebsiteSource, source_id)
            if not source or source.college_id != college_id:
                await self._fail_job(session, job_id, "Website source not found or cross-tenant violation.")
                return {"success": False, "error": "Invalid source"}

            job = await session.get(CrawlJob, job_id)
            if not job or job.college_id != college_id:
                return {"success": False, "error": "Job not found"}

            # Transition to RUNNING.
            # Use flush() instead of commit() so the transaction stays open and
            # the is_local=true RLS GUCs (app.current_college_id etc.) remain
            # active for the _log_event INSERT that follows.  The tenant_session
            # context manager will commit the whole block when it exits.
            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
            await session.flush()

            await self._log_event(
                session, job_id, "INFO",
                f"Starting crawl execution for base URL: {source.base_url} (Max Depth: {source.max_depth}, Max Pages: {source.max_pages})",
                {"base_url": source.base_url, "max_depth": source.max_depth, "max_pages": source.max_pages}
            )

        # Execution parameters
        base_url = source.base_url
        official_domain = college.official_domain
        allowed_subdomains = source.allowed_subdomains
        max_depth = source.max_depth
        max_pages = source.max_pages

        # Crawl tracking structures
        visited_urls: Set[str] = set()
        discovered_urls: Set[str] = set()
        queue: deque[Tuple[str, int]] = deque()  # (url, depth)

        # Validate initial seed URL
        try:
            validate_url_security(base_url)
            if not is_url_in_college_domain(base_url, official_domain, allowed_subdomains):
                raise DomainBoundaryError(
                    f"Base URL '{base_url}' does not belong to authorized domain '{official_domain}'."
                )
            seed_normalized = normalize_url(base_url)
            queue.append((seed_normalized, 0))
            discovered_urls.add(seed_normalized)
        except (SSRFProtectionError, DomainBoundaryError, Exception) as e:
            async with tenant_session(college_id=college_id) as session:
                await self._fail_job(session, job_id, f"Initial URL validation failed: {str(e)}")
            return {"success": False, "error": str(e)}

        pages_crawled = 0
        pages_failed = 0
        changed_page_ids: List[uuid.UUID] = []

        # Create HTTPX client with custom crawler headers
        headers = {
            "User-Agent": CRAWLER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(self.timeout_seconds, connect=6.0),
            follow_redirects=False,  # Redirects manually validated against SSRF!
            verify=True,
        ) as client:

            # 2. Robots.txt Policy Inspection
            policy = await robots_policy_manager.get_policy(base_url, client)
            async with tenant_session(college_id=college_id) as session:
                await self._log_event(
                    session, job_id, "INFO",
                    f"Fetched robots.txt policy for {base_url}. Disallow paths: {len(policy.disallow_rules)}, Crawl-delay: {policy.crawl_delay}s",
                    {"crawl_delay": policy.crawl_delay, "sitemaps": policy.sitemaps}
                )

            # 3. Optional Sitemap Inspection to seed URLs
            if policy.sitemaps and max_depth >= 1:
                for sitemap_url in policy.sitemaps[:3]:
                    try:
                        sitemap_links = await self._fetch_sitemap_urls(client, sitemap_url, official_domain, allowed_subdomains)
                        for link in sitemap_links:
                            if link not in discovered_urls and len(discovered_urls) < max_pages * 2:
                                discovered_urls.add(link)
                                queue.append((link, 1))
                        async with tenant_session(college_id=college_id) as session:
                            await self._log_event(
                                session, job_id, "INFO",
                                f"Discovered {len(sitemap_links)} URLs from sitemap: {sitemap_url}",
                                {"sitemap_url": sitemap_url, "count": len(sitemap_links)}
                            )
                    except Exception as ex:
                        logger.warning("Error reading sitemap %s: %s", sitemap_url, str(ex))

            # 4. Asynchronous Crawling Loop
            while queue and pages_crawled < max_pages:
                # Check for cancellation or pause in DB
                should_continue, current_status = await self._check_job_control_state(job_id, college_id)
                if not should_continue:
                    async with tenant_session(college_id=college_id) as session:
                        await self._log_event(
                            session, job_id, "WARNING",
                            f"Crawl job execution halted due to status transition to {current_status}",
                            {"final_status": current_status}
                        )
                    return {"success": True, "status": current_status}

                current_url, depth = queue.popleft()

                if current_url in visited_urls:
                    continue
                visited_urls.add(current_url)

                # Check robots.txt permissions
                if not policy.can_fetch(current_url):
                    async with tenant_session(college_id=college_id) as session:
                        await self._log_event(
                            session, job_id, "INFO",
                            f"Skipped disallowed path by robots.txt: {current_url}",
                            {"url": current_url, "reason": "ROBOTS_DISALLOWED"}
                        )
                    continue

                # SSRF check before connection
                try:
                    validate_url_security(current_url)
                except SSRFProtectionError as ssrf_err:
                    pages_failed += 1
                    async with tenant_session(college_id=college_id) as session:
                        await self._log_event(
                            session, job_id, "WARNING",
                            f"Blocked SSRF attempt on {current_url}: {str(ssrf_err)}",
                            {"url": current_url, "error": str(ssrf_err)}
                        )
                    continue

                # Polite throttle delay
                if policy.crawl_delay > 0:
                    await asyncio.sleep(min(policy.crawl_delay, 1.5))

                # Fetch page with safe redirect following
                fetch_res = await self._fetch_url_safely(
                    client, current_url, official_domain, allowed_subdomains
                )

                if not fetch_res["success"]:
                    pages_failed += 1
                    async with tenant_session(college_id=college_id) as session:
                        await self._log_event(
                            session, job_id, "WARNING",
                            f"Failed to fetch {current_url}: {fetch_res.get('error')}",
                            {"url": current_url, "error": fetch_res.get("error")}
                        )
                        await self._update_job_progress(session, job_id, len(discovered_urls), pages_crawled, pages_failed)
                    continue

                # Process HTML content
                raw_html = fetch_res["content"]
                final_url = fetch_res["url"]
                http_status = fetch_res["status_code"]

                try:
                    parsed_content = parse_and_clean_html(raw_html, final_url)
                except Exception as parse_err:
                    pages_failed += 1
                    logger.warning("HTML parsing failure for %s: %s", final_url, str(parse_err))
                    continue

                # JS rendering fallback
                if parsed_content.content_length < JS_FALLBACK_THRESHOLD or parsed_content.requires_js:
                    try:
                        from app.services.js_renderer import render_page_with_browser, PLAYWRIGHT_AVAILABLE
                        if PLAYWRIGHT_AVAILABLE:
                            js_html = await render_page_with_browser(final_url, timeout_ms=15000)
                            js_parsed = parse_and_clean_html(js_html, final_url)
                            if js_parsed.content_length > parsed_content.content_length:
                                parsed_content = js_parsed
                                logger.info(
                                    "JS rendering fallback used for %s — %s chars extracted (was %s)",
                                    final_url, parsed_content.content_length, 0
                                )
                    except Exception as js_err:
                        logger.warning("JS rendering fallback failed for %s: %s", final_url, str(js_err))
                        # Static content (possibly empty) is kept — do not abort the page

                # Save or deduplicate page
                async with tenant_session(college_id=college_id) as session:
                    for candidate in parsed_content.image_candidates:
                        try:
                            validate_url_security(candidate["url"])
                            if not is_url_in_college_domain(candidate["url"], official_domain, allowed_subdomains):
                                continue
                        except Exception:
                            continue
                        digest = __import__("hashlib").sha256(candidate["url"].encode()).hexdigest()
                        exists = await session.scalar(select(CollegeGalleryImage.id).where(
                            CollegeGalleryImage.college_id == college_id,
                            CollegeGalleryImage.content_hash == digest,
                        ))
                        if exists:
                            continue
                        context = (candidate["title"] + " " + candidate["description"] + " " + parsed_content.title).lower()
                        category = next((key for terms, key in [
                            (("library",), "LIBRARY"), (("laboratory", "lab"), "LABORATORY"),
                            (("hostel",), "HOSTEL"), (("canteen", "cafeteria"), "CANTEEN"),
                            (("auditorium", "seminar hall"), "AUDITORIUM"), (("event", "festival", "annual day"), "EVENTS"),
                            (("entrance", "gate"), "ENTRANCE"), (("campus", "building"), "CAMPUS")
                        ] if any(term in context for term in terms)), "OTHER")
                        session.add(CollegeGalleryImage(
                            college_id=college_id, image_url=candidate["url"],
                            image_title=candidate["title"][:255] or parsed_content.title,
                            image_description=candidate["description"] or parsed_content.meta_description,
                            image_category=category, source_url=parsed_content.url,
                            verification_status="PENDING", is_active=False, content_hash=digest,
                        ))
                    is_new_or_changed = await self._save_or_deduplicate_page(
                        session=session,
                        college_id=college_id,
                        source_id=source_id,
                        job_id=job_id,
                        parsed=parsed_content,
                        http_status=http_status,
                    )
                    page_id = None
                    if is_new_or_changed:
                        page_lookup = await session.execute(
                            select(WebsitePage).where(
                                WebsitePage.college_id == college_id,
                                WebsitePage.url == parsed_content.url,
                            )
                        )
                        page_rec = page_lookup.scalar_one_or_none()
                        if page_rec:
                            page_id = page_rec.id
                            changed_page_ids.append(page_id)
                    pages_crawled += 1

                    await self._log_event(
                        session, job_id, "INFO",
                        f"Crawled: {final_url} (HTTP {http_status}, {parsed_content.content_length} chars, {'NEW/UPDATED' if is_new_or_changed else 'UNCHANGED'})",
                        {
                            "url": final_url,
                            "title": parsed_content.title,
                            "hash": parsed_content.content_hash,
                            "content_length": parsed_content.content_length,
                            "tables_count": len(parsed_content.tables_markdown),
                            "is_changed": is_new_or_changed,
                        }
                    )
                    await self._update_job_progress(session, job_id, len(discovered_urls), pages_crawled, pages_failed)

                # Internal Link Discovery if depth permits
                if depth < max_depth:
                    for link in parsed_content.discovered_links:
                        if link not in discovered_urls and len(discovered_urls) < max_pages * 3:
                            if is_url_in_college_domain(link, official_domain, allowed_subdomains):
                                discovered_urls.add(link)
                                queue.append((link, depth + 1))

        # 5. Finalize Job Execution
        async with tenant_session(college_id=college_id) as session:
            final_job = await session.get(CrawlJob, job_id)
            if final_job and final_job.status == "RUNNING":
                final_job.status = "COMPLETED"
                final_job.finished_at = datetime.now(timezone.utc)
                final_job.pages_discovered = len(discovered_urls)
                final_job.pages_crawled = pages_crawled
                final_job.pages_failed = pages_failed

            # Update website source timestamp
            src = await session.get(WebsiteSource, source_id)
            if src:
                src.last_crawled_at = datetime.now(timezone.utc)

            await self._log_event(
                session, job_id, "SUCCESS",
                f"Crawl job completed successfully. Discovered {len(discovered_urls)} pages, Crawled {pages_crawled}, Failed {pages_failed}.",
                {
                    "pages_discovered": len(discovered_urls),
                    "pages_crawled": pages_crawled,
                    "pages_failed": pages_failed,
                }
            )
            # flush() not commit() — tenant_session auto-commits on __aexit__.
            # An internal commit() resets is_local GUCs and would break any
            # RLS-gated query run after it in the same session.
            await session.flush()

        if changed_page_ids:
            unique_page_ids = list(dict.fromkeys(changed_page_ids))
            try:
                from app.tasks.knowledge_tasks import dispatch_website_knowledge_processing

                mode = dispatch_website_knowledge_processing(
                    college_id=college_id,
                    page_ids=unique_page_ids,
                )
                logger.info(
                    "Dispatched website knowledge processing for %s changed pages (college=%s, mode=%s)",
                    len(unique_page_ids),
                    college_id,
                    mode,
                )
            except Exception as exc:
                logger.exception(
                    "Failed to dispatch website knowledge processing for %s changed pages in college %s: %s",
                    len(unique_page_ids),
                    college_id,
                    exc,
                )

        return {
            "success": True,
            "status": "COMPLETED",
            "pages_discovered": len(discovered_urls),
            "pages_crawled": pages_crawled,
            "pages_failed": pages_failed,
            "changed_page_ids": list(dict.fromkeys(changed_page_ids)),
        }

    async def _fetch_url_safely(
        self,
        client: httpx.AsyncClient,
        url: str,
        official_domain: str,
        allowed_subdomains: Optional[str],
        max_redirects: int = 5,
    ) -> Dict[str, Any]:
        """Fetches a page over HTTP with explicit SSRF checks on every redirect hop."""
        current_url = url
        redirect_count = 0

        while redirect_count <= max_redirects:
            try:
                # SSRF validation before each request
                validate_url_security(current_url)

                # Domain check
                if not is_url_in_college_domain(current_url, official_domain, allowed_subdomains):
                    return {
                        "success": False,
                        "error": f"Redirect target '{current_url}' escaped college domain boundary.",
                    }

                resp = await client.get(current_url)

                # Check if response is a redirect
                if resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("Location")
                    if not loc:
                        return {"success": False, "error": "Redirect missing Location header."}

                    redirect_count += 1
                    current_url = normalize_url(loc, current_url)
                    continue

                # Ensure response is HTML
                content_type = resp.headers.get("Content-Type", "").lower()
                if resp.status_code == 200 and ("text/html" not in content_type and "application/xhtml" not in content_type):
                    return {
                        "success": False,
                        "error": f"Skipped non-HTML content type: {content_type}",
                    }

                if resp.status_code != 200:
                    return {
                        "success": False,
                        "status_code": resp.status_code,
                        "error": f"HTTP status {resp.status_code}",
                    }

                return {
                    "success": True,
                    "url": current_url,
                    "status_code": resp.status_code,
                    "content": resp.text,
                }

            except (SSRFProtectionError, DomainBoundaryError) as sec_err:
                return {"success": False, "error": f"Security restriction: {str(sec_err)}"}
            except httpx.TimeoutException:
                return {"success": False, "error": "Request timed out."}
            except Exception as ex:
                return {"success": False, "error": str(ex)}

        return {"success": False, "error": f"Exceeded maximum redirects ({max_redirects})."}

    async def _fetch_sitemap_urls(
        self,
        client: httpx.AsyncClient,
        sitemap_url: str,
        official_domain: str,
        allowed_subdomains: Optional[str],
    ) -> List[str]:
        """Parses standard XML sitemaps to discover candidate URLs."""
        validate_url_security(sitemap_url)
        resp = await client.get(sitemap_url)
        if resp.status_code != 200:
            return []

        urls = []
        try:
            root = ET.fromstring(resp.content)
            # Handle XML namespaces
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

            # Standard urlset
            for loc in root.findall(".//sm:loc", ns):
                if loc.text:
                    clean = normalize_url(loc.text.strip())
                    if is_crawleable_resource(clean) and is_url_in_college_domain(clean, official_domain, allowed_subdomains):
                        urls.append(clean)

            # Fallback if without namespace
            if not urls:
                for loc in root.findall(".//loc"):
                    if loc.text:
                        clean = normalize_url(loc.text.strip())
                        if is_crawleable_resource(clean) and is_url_in_college_domain(clean, official_domain, allowed_subdomains):
                            urls.append(clean)
        except Exception as e:
            logger.debug("Failed to parse sitemap XML for %s: %s", sitemap_url, str(e))

        return urls

    async def _save_or_deduplicate_page(
        self,
        session: AsyncSession,
        college_id: uuid.UUID,
        source_id: uuid.UUID,
        job_id: uuid.UUID,
        parsed,
        http_status: int,
    ) -> bool:
        """Saves crawled page or updates timestamp if content hash matches existing record."""
        query = select(WebsitePage).where(
            WebsitePage.college_id == college_id,
            WebsitePage.url == parsed.url,
        )
        res = await session.execute(query)
        existing_page = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if existing_page:
            if existing_page.content_hash == parsed.content_hash:
                existing_page.fetched_at = now
                existing_page.crawl_job_id = job_id
                existing_page.http_status = http_status
                await session.flush()
                return False

            existing_page.title = parsed.title
            existing_page.meta_description = parsed.meta_description
            existing_page.content_hash = parsed.content_hash
            existing_page.cleaned_text = parsed.cleaned_text
            existing_page.content_length = parsed.content_length
            existing_page.http_status = http_status
            existing_page.crawl_job_id = job_id
            existing_page.fetched_at = now
            await session.flush()
            return True

        new_page = WebsitePage(
            id=uuid.uuid4(),
            college_id=college_id,
            source_id=source_id,
            crawl_job_id=job_id,
            url=parsed.url,
            title=parsed.title,
            meta_description=parsed.meta_description,
            content_hash=parsed.content_hash,
            cleaned_text=parsed.cleaned_text,
            content_length=parsed.content_length,
            http_status=http_status,
            fetched_at=now,
        )
        session.add(new_page)
        await session.flush()
        return True

    async def _check_job_control_state(self, job_id: uuid.UUID, college_id: uuid.UUID) -> Tuple[bool, str]:
        """Checks if job was paused or cancelled by college admin."""
        async with tenant_session(college_id=college_id) as session:
            job = await session.get(CrawlJob, job_id)
            if not job:
                return False, "DELETED"

            if job.status == "CANCELLED":
                return False, "CANCELLED"

            if job.status == "PAUSED":
                # Wait while paused (up to 5 minutes before timeout)
                wait_intervals = 0
                while wait_intervals < 60:
                    await asyncio.sleep(5)
                    await session.refresh(job)
                    if job.status == "RUNNING":
                        return True, "RUNNING"
                    if job.status == "CANCELLED":
                        return False, "CANCELLED"
                    wait_intervals += 1
                return False, "PAUSED_TIMEOUT"

            return True, job.status

    async def _update_job_progress(
        self, session: AsyncSession, job_id: uuid.UUID, discovered: int, crawled: int, failed: int
    ) -> None:
        """Updates real-time progress counters on the CrawlJob entity."""
        await session.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job_id)
            .values(
                pages_discovered=discovered,
                pages_crawled=crawled,
                pages_failed=failed,
            )
        )
        # flush() not commit() — the caller's tenant_session block holds the
        # transaction open; a commit() here would reset is_local GUCs and break
        # subsequent RLS-gated inserts in the same session.
        await session.flush()

    async def _log_event(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        log_level: str,
        message: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Appends a granular crawl execution event."""
        event = CrawlEvent(
            id=uuid.uuid4(),
            crawl_job_id=job_id,
            log_level=log_level,
            message=message,
            metadata_=metadata or {},
        )
        session.add(event)
        # flush() not commit() — the caller's tenant_session block holds the
        # transaction open; a commit() here resets is_local GUCs and breaks
        # subsequent RLS-gated operations on the same session.
        await session.flush()

    async def _fail_job(self, session: AsyncSession, job_id: uuid.UUID, reason: str) -> None:
        """Marks a job as FAILED and logs failure reason."""
        job = await session.get(CrawlJob, job_id)
        if job:
            job.status = "FAILED"
            job.failure_reason = reason
            job.finished_at = datetime.now(timezone.utc)
            await self._log_event(
                session, job_id, "ERROR", f"Crawl execution failed: {reason}", {"reason": reason}
            )
            # flush() not commit() — the caller is responsible for committing via
            # tenant_session's auto-commit on __aexit__.  An internal commit()
            # here resets is_local GUCs and silently breaks RLS on the same session.
            await session.flush()


# Singleton crawler service instance
crawler_service = WebsiteCrawlerService()

