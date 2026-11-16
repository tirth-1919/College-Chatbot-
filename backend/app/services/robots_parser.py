"""Robots.txt Parser & Politeness Policy Engine.

Fetches and caches robots.txt directives, respects Disallow/Allow paths,
identifies sitemaps, and extracts Crawl-delay recommendations for polite crawling.
"""

import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import httpx

from app.services.url_validator import validate_url_security

logger = logging.getLogger("college_chatbot.robots_parser")

CRAWLER_USER_AGENT = "CampusAI-Crawler/1.0 (+https://campusai.edu/crawler-bot; crawler@campusai.edu)"
DEFAULT_CRAWL_DELAY = 0.5  # Seconds between requests
MAX_CRAWL_DELAY = 10.0     # Cap to avoid server DOS/hanging workers
MIN_CRAWL_DELAY = 0.1      # Polite floor


class DomainRobotsPolicy:
    """Represents parsed robots.txt rules for a specific origin host."""

    def __init__(self, origin: str):
        self.origin: str = origin
        self.disallow_rules: List[str] = []
        self.allow_rules: List[str] = []
        self.sitemaps: List[str] = []
        self.crawl_delay: float = DEFAULT_CRAWL_DELAY
        self.fetched_at: float = time.time()
        self.ttl: float = 3600.0  # 1 hour cache TTL

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.fetched_at) > self.ttl

    def can_fetch(self, url: str) -> bool:
        """Evaluates path against Allow and Disallow directives."""
        parsed = urlparse(url)
        path = parsed.path or "/"

        # Check explicit Allow rules first (most specific wins)
        for rule in self.allow_rules:
            if self._path_matches(path, rule):
                return True

        # Check Disallow rules
        for rule in self.disallow_rules:
            if self._path_matches(path, rule):
                return False

        return True

    @staticmethod
    def _path_matches(path: str, rule: str) -> bool:
        """Matches path against a robots.txt pattern (supporting wildcard '*' and end-of-path '$')."""
        if not rule:
            return False

        # Convert robots.txt pattern to regex
        # Escape special regex characters except * and $
        escaped = re.escape(rule).replace(r"\*", ".*")
        if escaped.endswith(r"\$"):
            escaped = escaped[:-2] + "$"
        else:
            escaped = escaped + ".*"

        pattern = f"^{escaped}"
        return bool(re.match(pattern, path))


class RobotsPolicyManager:
    """Singleton/manager for retrieving and caching robots.txt directives across tenants."""

    def __init__(self):
        self._cache: Dict[str, DomainRobotsPolicy] = {}
        self._lock = asyncio.Lock()

    async def get_policy(self, url: str, client: Optional[httpx.AsyncClient] = None) -> DomainRobotsPolicy:
        """Retrieves or fetches the robots.txt policy for the URL's origin domain."""
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}".lower()

        async with self._lock:
            existing = self._cache.get(origin)
            if existing and not existing.is_expired:
                return existing

        # Fetch and parse fresh policy
        policy = await self._fetch_and_parse(origin, client)

        async with self._lock:
            self._cache[origin] = policy

        return policy

    async def _fetch_and_parse(self, origin: str, client: Optional[httpx.AsyncClient]) -> DomainRobotsPolicy:
        """Safely fetches /robots.txt using SSRF validation."""
        policy = DomainRobotsPolicy(origin)
        robots_url = urljoin(origin, "/robots.txt")

        try:
            # SSRF validation before request
            validate_url_security(robots_url)

            headers = {"User-Agent": CRAWLER_USER_AGENT, "Accept": "text/plain,*/*"}

            close_client = False
            if client is None:
                client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
                close_client = True

            try:
                resp = await client.get(robots_url, headers=headers)
                if resp.status_code == 200:
                    self._parse_content(resp.text, policy)
                elif resp.status_code in (401, 403):
                    # Forbidden robots.txt is often treated as disallowing all
                    logger.warning("Robots.txt access restricted (HTTP %d) on %s", resp.status_code, origin)
                else:
                    # 404 or other: entire site is allowed
                    logger.debug("No robots.txt found (HTTP %d) on %s, default permit", resp.status_code, origin)
            finally:
                if close_client:
                    await client.aclose()

        except Exception as e:
            logger.warning("Failed to fetch robots.txt for %s: %s (defaulting to standard policy)", origin, str(e))

        return policy

    def _parse_content(self, text: str, policy: DomainRobotsPolicy) -> None:
        """Parses robots.txt text format line-by-line."""
        current_agents: Set[str] = set()
        matched_relevant_agent = False
        default_agent_matched = False

        for raw_line in text.splitlines():
            line = raw_line.strip()
            # Strip comments
            if "#" in line:
                line = line[: line.index("#")].strip()
            if not line:
                # Blank line may reset agent block in standard robots.txt
                continue

            parts = line.split(":", 1)
            if len(parts) != 2:
                continue

            directive = parts[0].strip().lower()
            value = parts[1].strip()

            if directive == "user-agent":
                agent_val = value.lower()
                current_agents.add(agent_val)
                if "campusai" in agent_val or agent_val == "*":
                    matched_relevant_agent = True
                    if agent_val == "*":
                        default_agent_matched = True

            elif directive == "sitemap":
                if value and value.startswith("http"):
                    policy.sitemaps.append(value)

            elif matched_relevant_agent or default_agent_matched:
                if directive == "disallow":
                    if value:  # Disallow with path
                        policy.disallow_rules.append(value)
                elif directive == "allow":
                    if value:
                        policy.allow_rules.append(value)
                elif directive == "crawl-delay":
                    try:
                        delay = float(value)
                        policy.crawl_delay = max(MIN_CRAWL_DELAY, min(MAX_CRAWL_DELAY, delay))
                    except ValueError:
                        pass


# Singleton instance
robots_policy_manager = RobotsPolicyManager()

