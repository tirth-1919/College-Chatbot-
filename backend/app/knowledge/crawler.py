"""
AIT Website Crawler — SPA-aware, bundle-driven discovery and extraction engine.

Root Cause (verified):
  www.aitindia.in is a React/Vite Single-Page Application.  Every URL—including
  /sitemap.xml, /about/committee, /sitemap_index.xml—returns only a minimal HTML
  shell (<div id="root"></div> + <script src="/assets/index-*.js">).
  BeautifulSoup finds zero links, extracted text is "", hash = e3b0c44...

Fix:
  1. DISCOVERY  — Download the compiled JS bundle once.  Parse all React Router
     route definitions (path:"...") directly from the bundle.  This dynamically
     yields every official route (/about/committee, /placement/cell, etc.)
     without any hard-coding.
  2. EXTRACTION — For each route, extract structured content from the same bundle:
       • /about/committee  → parse committee/squad data structures → rich sections
         (ANTI-RAGGING SQUAD, SPORTS COMMITTEE, LIBRARY COMMITTEE, etc.)
       • All other routes  → extract human-readable text literals from the
         corresponding React component definition in the bundle.
  3. PERSISTENCE — Write every discovered page into WebsiteSnapshot, including
     committee pages, with non-empty content hashes.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urljoin, urlparse, urldefrag

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.knowledge import WebsiteSnapshot, AitEntity, AitKnowledgeVersion

log = logging.getLogger("ait.crawler")

_CSS_PATTERNS = re.compile(
    r'px-|py-|pt-|pb-|pl-|pr-|mx-|my-|mt-|mb-|ml-|mr-|'
    r'text-[a-z0-9]|bg-|font-|flex|grid|w-|h-|border|rounded|hover:|'
    r'transition|stroke|fillRule|viewBox|xmlns|inset|overflow|z-[0-9]|'
    r'sm:|md:|lg:|xl:|gap-|space-|items-|justify-|cursor-|opacity|shadow|'
    r'absolute|relative|sticky|fixed|hidden|block|inline|pointer'
)


class AitWebsiteCrawler:
    def __init__(self, base_url: str = "https://www.aitindia.in"):
        self.base_url = base_url.rstrip("/")
        self.domain = urlparse(self.base_url).netloc
        self._bundle_text: Optional[str] = None
        self._bundle_url: Optional[str] = None
        self._route_map: Dict[str, List[str]] = {}

    # ------------------------------------------------------------------
    # URL normalisation
    # ------------------------------------------------------------------
    def _normalise_url(self, raw: str) -> Optional[str]:
        full = urljoin(self.base_url + "/", raw)
        defragged = urldefrag(full)[0]
        parsed = urlparse(defragged)
        if parsed.scheme not in {"http", "https"}:
            return None
        # Accept both www and non-www variants of the site
        accepted_netlocs = {
            self.domain,
            self.domain.replace("www.", ""),
            f"www.{self.domain.replace('www.', '')}",
        }
        if parsed.netloc not in accepted_netlocs:
            return None
        if parsed.path.lower().endswith(
            (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp",
             ".zip", ".svg", ".css", ".js", ".ico", ".woff", ".woff2")
        ):
            return None
        norm_path = parsed.path.rstrip("/")
        return f"{self.base_url}{norm_path}" if norm_path else self.base_url

    # ------------------------------------------------------------------
    # Bundle management
    # ------------------------------------------------------------------
    async def _load_bundle(self, client: httpx.AsyncClient) -> str:
        """Download and cache the compiled JS bundle from the SPA entry point."""
        if self._bundle_text:
            return self._bundle_text

        log.info("BUNDLE DISCOVERY: fetching %s", self.base_url)
        try:
            r = await client.get(
                self.base_url,
                headers={"User-Agent": "AIT-AI-KnowledgeBot/1.0"}
            )
            js_refs = re.findall(
                r'src=["\'](/assets/[^"\']+\.js)["\']', r.text
            )
            # Fall back to any <script src="...js">
            if not js_refs:
                js_refs = re.findall(r'src=["\'](.*?\.js)["\']', r.text)

            if not js_refs:
                log.warning("BUNDLE DISCOVERY: no JS bundle found in %s", self.base_url)
                return ""

            bundle_url = urljoin(self.base_url, js_refs[0])
            self._bundle_url = bundle_url
            log.info("BUNDLE DISCOVERY: downloading bundle %s", bundle_url)
            r_js = await client.get(
                bundle_url,
                headers={"User-Agent": "AIT-AI-KnowledgeBot/1.0"}
            )
            if r_js.status_code == 200:
                self._bundle_text = r_js.text
                log.info(
                    "BUNDLE DISCOVERY: loaded %d chars", len(self._bundle_text)
                )
                return self._bundle_text
        except Exception as exc:
            log.warning("BUNDLE DISCOVERY: failed: %s", exc)
        return ""

    # ------------------------------------------------------------------
    # Route discovery from bundle
    # ------------------------------------------------------------------
    def _parse_routes(self, bundle: str) -> Dict[str, List[str]]:
        """Parse React Router routes from the compiled JS bundle.

        Looks for patterns such as:
            path:"/about/committee",element:n.jsx(YO,{})
            path:"/",element:n.jsxs(n.Fragment,{children:[...]})
        Returns a dict {path: [component_symbols]}.
        """
        if self._route_map:
            return self._route_map

        route_map: Dict[str, List[str]] = {}

        # Match single-component routes: path:"<p>",element:?.jsx(<Comp>
        for m in re.finditer(
            r'path:\s*["\']([^"\']+)["\'],\s*element:\s*(?:[a-zA-Z0-9_$.]+)\.jsx\(([a-zA-Z0-9_$]+)',
            bundle
        ):
            path = m.group(1).rstrip("/") or "/"
            comp = m.group(2)
            route_map.setdefault(path, [])
            if comp not in route_map[path]:
                route_map[path].append(comp)

        # Match multi-component (Fragment) routes: path:"<p>",element:?.jsxs(?.Fragment,{children:[?.jsx(C1),?.jsx(C2)...]})
        for m in re.finditer(
            r'path:\s*["\']([^"\']+)["\'],\s*element:\s*(?:[a-zA-Z0-9_$.]+)\.jsxs\(',
            bundle
        ):
            path = m.group(1).rstrip("/") or "/"
            # grab next 600 chars to find child components
            snippet = bundle[m.end(): m.end() + 600]
            comps = re.findall(
                r'(?:[a-zA-Z0-9_$.]+)\.jsx\(([a-zA-Z0-9_$]+)', snippet
            )
            route_map.setdefault(path, [])
            for c in comps:
                if c not in route_map[path]:
                    route_map[path].append(c)

        # Also collect bare paths from any path:"..." literal to catch
        # routes that may use unusual element patterns
        for p in re.findall(r'path:\s*["\'](/[^"\']*)["\']', bundle):
            clean = p.rstrip("/") or "/"
            route_map.setdefault(clean, [])

        self._route_map = route_map
        log.info("ROUTE DISCOVERY: %d routes parsed from bundle", len(route_map))
        return route_map

    # ------------------------------------------------------------------
    # URL discovery (combines bundle routes + sitemap + BFS on <a> links)
    # ------------------------------------------------------------------
    async def _discover_urls(self, client: httpx.AsyncClient) -> Set[str]:
        discovered: Set[str] = {self.base_url}

        # 1. Attempt sitemap / sitemap-index parsing (works on pre-rendered SPAs)
        for sitemap in (
            self.base_url + "/sitemap.xml",
            self.base_url + "/sitemap_index.xml",
            self.base_url + "/sitemap",
        ):
            try:
                r = await client.get(
                    sitemap,
                    headers={"User-Agent": "AIT-AI-KnowledgeBot/1.0"}
                )
                if r.status_code == 200:
                    for loc in BeautifulSoup(r.text, "xml").find_all("loc"):
                        u = self._normalise_url(loc.get_text(strip=True))
                        if u:
                            log.info("DISCOVERED URL: %s  SOURCE: sitemap", u)
                            discovered.add(u)
            except Exception:
                pass

        # 2. Primary SPA route extraction from compiled bundle
        bundle = await self._load_bundle(client)
        if bundle:
            try:
                routes = self._parse_routes(bundle)
            except Exception as exc:
                # Real minified bundles may differ from the regexes' expected
                # shape (or trigger pathological backtracking); degrade to
                # sitemap/BFS discovery instead of failing the whole sync.
                log.warning("Bundle route parsing failed: %s", exc)
                routes = {}
            for path in routes:
                if path.lower() in {"/sitemap", "/terms-of-use", "/privacy-policy", "/newsletter"}:
                    continue  # non-content pages
                url = f"{self.base_url}{path}" if path != "/" else self.base_url
                u = self._normalise_url(url)
                if u:
                    log.info("DISCOVERED URL: %s  SOURCE: spa_bundle", u)
                    discovered.add(u)

        # 3. BFS on <a href> links (helps if the server ever adds SSR or for
        #    any pages not captured by sitemap or bundle parsing)
        queue = list(discovered)
        visited: Set[str] = set()
        while queue and len(visited) < 200:
            page_url = queue.pop(0)
            if page_url in visited:
                continue
            visited.add(page_url)
            try:
                r = await client.get(
                    page_url,
                    headers={"User-Agent": "AIT-AI-KnowledgeBot/1.0"}
                )
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                for tag in soup.find_all("a", href=True):
                    u = self._normalise_url(tag["href"])
                    if u and u not in discovered:
                        log.info("DISCOVERED URL: %s  SOURCE: navigation_bfs", u)
                        discovered.add(u)
                        queue.append(u)
            except Exception:
                pass

        log.info("DISCOVER TOTAL: %d unique URLs found", len(discovered))
        return discovered

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------
    def _is_readable_string(self, s: str) -> bool:
        """Return True if a string literal is human-readable content."""
        if _CSS_PATTERNS.search(s):
            return False
        if any(s.startswith(p) for p in ["/", "http", "M ", "d=", "#", "none"]):
            return False
        # Must contain at least one alphabetic character
        if not any(c.isalpha() for c in s):
            return False
        # Reject looks-like-code strings
        if re.search(r'[{}();=]', s):
            return False
        return True

    def _extract_component_strings(
        self, comp_name: str, bundle: str, window: int = 6000
    ) -> List[str]:
        """Extract readable string literals from a component's code window."""
        m = re.search(
            rf'\b{re.escape(comp_name)}\s*=\s*(?:\([^)]*\)\s*=>|function\s)',
            bundle
        )
        if not m:
            return []
        chunk = bundle[m.start(): m.start() + window]
        out: List[str] = []
        for s in re.findall(r'["\']([^"\'\\]{6,250})["\']', chunk):
            if self._is_readable_string(s) and s not in out:
                out.append(s)
        return out

    # ------------------------------------------------------------------
    # Committee page — rich structured extraction
    # ------------------------------------------------------------------
    def _extract_committee_page(self, bundle: str) -> Dict[str, Any]:
        # Locate the committee data array by its first known committee marker.
        # The complete array can be much larger than one local window, so use
        # the whole bundle for structured committee extraction.
        anchor_positions = [bundle.find(anchor) for anchor in ("ANTI-RAGGING SQUAD", "ANTI-RAGGING", "ACADEMIC COUNCIL", "IQAC")]
        anchor_positions = [p for p in anchor_positions if p != -1]
        if not anchor_positions:
            log.warning("EXTRACTION: committee data anchor not found in bundle")
            return {
                "title": "AIT Committees & Councils",
                "content": "",
                "sections": [],
                "extraction_status": "EMPTY",
            }

        chunk = bundle

        committees = re.findall(
            r'name:\s*["\']([A-Z0-9\s/&—\-\.]+)["\'],\s*members:\s*\[(.*?)\]\}',
            chunk
        )
        sections: List[Dict[str, Any]] = []
        for comm_name, members_str in committees:
            comm_clean = comm_name.strip()
            if not comm_clean:
                continue
            members = re.findall(
                r'name:\s*["\']([^"\']+)["\'],\s*role:\s*["\']([^"\']+)["\']',
                members_str
            )
            if not members:
                continue

            chairmen = [n for n, r in members if "chair" in r.lower()]
            conveners = [n for n, r in members if "convener" in r.lower()]
            others = [
                n for n, r in members
                if "chair" not in r.lower() and "convener" not in r.lower()
            ]
            all_names = [n for n, _ in members]

            lines: List[str] = []
            if chairmen:
                lines.append(f"Chairman: {', '.join(chairmen)}")
            if conveners:
                lines.append(f"Convener: {', '.join(conveners)}")
            if others:
                lines.append(f"Members: {', '.join(others)}")
            lines.append(f"All Members: {', '.join(all_names)}")

            sections.append({"section_title": comm_clean, "content": lines})

        blocks = [
            "SECTION: " + s["section_title"] + "\n" + "\n".join(s["content"])
            for s in sections
        ]
        content = "\n\n".join(blocks)
        log.info(
            "EXTRACTION: /about/committee → %d committees, %d chars",
            len(sections), len(content)
        )
        return {
            "title": "Ahmedabad Institute of Technology — Committees & Governing Councils",
            "content": content,
            "sections": sections,
            "extraction_status": "EXTRACTED" if content else "EMPTY",
        }

    # ------------------------------------------------------------------
    # Intake page — enhanced structured extraction
    # ------------------------------------------------------------------
    def _extract_intake_page(self, bundle: str) -> Dict[str, Any]:
        """Extract intake data from the SPA bundle for the intake page with enhanced patterns."""
        # Search for specific intake-related number combinations in the bundle
        # The bundle contains many intake-related terms but we need to find structured data
        
        extracted_data = {}
        
        # Look for common intake-related numbers that might appear together
        # Search for patterns where intake, courses, total appear near numbers
        all_numbers = re.findall(r'\b(1[0-9]{3}|[1-9][0-9]{2})\b', bundle)
        
        # Filter for plausible intake numbers (intake is typically 1000-2000)
        plausible_intake = [n for n in all_numbers if 1000 <= int(n) <= 2000]
        if plausible_intake:
            extracted_data['intake_candidates'] = plausible_intake[:5]
        
        # Filter for plausible course counts (typically 10-50)
        plausible_courses = [n for n in all_numbers if 10 <= int(n) <= 50]
        if plausible_courses:
            extracted_data['course_candidates'] = plausible_courses[:5]
        
        # Look for specific text patterns that might contain intake information
        # Search for phrases like "total intake", "courses offered", etc.
        text_patterns = [
            r'total\s+intake[:\s]*([0-9]+)',
            r'intake\s+capacity[:\s]*([0-9]+)',
            r'courses\s+offered[:\s]*([0-9]+)',
            r'program\s+count[:\s]*([0-9]+)',
        ]
        
        for pattern in text_patterns:
            matches = re.findall(pattern, bundle, re.IGNORECASE)
            if matches:
                key = pattern.split('[')[0].split('(')[0]
                if key not in extracted_data:
                    extracted_data[key] = matches[0]
        
        # Try to find any JSON-like structures that might contain intake data
        # Look for objects with intake-related keys
        json_intake_patterns = [
            r'["\']intake["\']\s*:\s*([0-9]+)',
            r'["\']totalIntake["\']\s*:\s*([0-9]+)',
            r'["\']totalCourses["\']\s*:\s*([0-9]+)',
            r'["\']ug["\']\s*:\s*([0-9]+)',
            r'["\']pg["\']\s*:\s*([0-9]+)',
            r'["\']diploma["\']\s*:\s*([0-9]+)',
        ]
        
        for pattern in json_intake_patterns:
            matches = re.findall(pattern, bundle, re.IGNORECASE)
            if matches:
                key = pattern.split('[')[0].split("'")[0]
                if key not in extracted_data:
                    extracted_data[key] = matches[0]
        
        # SPA bundle does not reliably expose structured intake data
        # Even if we find numbers, they may not be authoritative
        # Mark as INSUFFICIENT to rely on verified database fallback
        log.warning("EXTRACTION: /about/intake → SPA bundle does not contain authoritative intake data, marking INSUFFICIENT")
        return {
            "title": "Ahmedabad Institute of Technology — Intake",
            "content": "Official intake page for Ahmedabad Institute of Technology.",
            "sections": [{"section_title": "Intake", "content": ["Official intake information available through verified database fallback."]}],
            "extraction_status": "INSUFFICIENT",
        }

    # ------------------------------------------------------------------
    # Generic SPA page extraction
    # ------------------------------------------------------------------
    def _extract_generic_spa_page(self, path: str, bundle: str) -> Dict[str, Any]:
        """Generic SPA page extraction for non-specialized pages."""
        route_map = self._parse_routes(bundle)
        comps = route_map.get(path, [])
        path_label = (path.strip("/").split("/")[-1] or "Home").replace("-", " ").title()
        page_title = f"Ahmedabad Institute of Technology — {path_label}"

        texts: List[str] = []
        for comp in comps[:6]:
            strs = self._extract_component_strings(comp, bundle)
            for s in strs:
                if s not in texts:
                    texts.append(s)

        if not texts and path != "/":
            # fallback: scan vicinity of path literal for readable strings
            for q in (f'"{path}"', f"'{path}'"):
                idx = bundle.find(q)
                if idx != -1:
                    nearby = bundle[max(0, idx - 800): min(len(bundle), idx + 2500)]
                    for s in re.findall(r'["\']([^"\'\\]{8,200})["\']', nearby):
                        if self._is_readable_string(s) and s not in texts:
                            texts.append(s)
                    break

        if not texts:
            texts = [
                f"Official page for {path_label} at Ahmedabad Institute of Technology."
            ]

        sections = [{"section_title": path_label, "content": texts[:30]}]
        blocks = [
            "SECTION: " + s["section_title"] + "\n" + "\n".join(s["content"])
            for s in sections
        ]
        content = "\n\n".join(blocks)
        
        # Classify extraction status based on content quality
        # If content is very short (< 100 chars) or contains only navigation terms, mark as insufficient
        nav_terms = {'home', 'about', 'contact', 'departments', 'engineering', 'menu', 'navigation'}
        is_navigation_only = any(term in content.lower() for term in nav_terms) and len(content) < 150
        
        if is_navigation_only or len(content) < 50:
            extraction_status = "EMPTY"
        elif len(content) < 200:
            extraction_status = "INSUFFICIENT"
        else:
            extraction_status = "EXTRACTED"
        
        log.info(
            "EXTRACTION: %s → %d chars, extraction_status=%s",
            path, len(content), extraction_status
        )
        return {
            "title": page_title,
            "content": content,
            "sections": sections,
            "extraction_status": extraction_status,
        }

    def _extract_placement_page(self, path: str, bundle: str) -> Dict[str, Any]:
        """Extract placement route copy from the official SPA bundle."""
        anchors = {
            "/placement/cell": [
                "The objective of AIT Placement Cell",
                "The Placement Cell conducts expert talks",
            ],
            "/placement/company": [
                "AIT Placement – Companies",
                "AIT Placement - Companies",
                "Explore our top placement partners by domain.",
            ],
            "/placement/drives": ["Placement Drive Dashboard", "Access comprehensive data on campus placements"],
        }
        texts: List[str] = []
        if path == "/placement/cell":
            for anchor in anchors[path]:
                match = re.search(rf"({re.escape(anchor)}[^\"']{{8,1200}})", bundle)
                if match:
                    value = match.group(1).strip()
                    if value not in texts:
                        texts.append(value)
        for anchor in anchors.get(path, []):
            index = bundle.lower().find(anchor.lower())
            if index < 0:
                continue
            window = bundle[max(0, index - 500): index + 14000]
            for value in re.findall(r'["\']([^"\'\\]{8,500})["\']', window):
                if self._is_readable_string(value) and value not in texts:
                    texts.append(value)
        if path == "/placement/company":
            for match in re.finditer(
                r'name:\s*["\']([^"\']+)["\'],category:\s*["\']([^"\']+)["\'],details:\s*["\']([^"\']+)["\']',
                bundle,
            ):
                company, category, details = match.groups()
                texts.append(f"{company} ({category}): {details}")

        texts = [
            text for text in texts
            if not text.startswith(",")
            and text not in {"children:", "children", "className:", "aria-label", "scroll", "smooth", "easeOut"}
            and not any(marker in text.lower() for marker in [
                "scroll to top", "whileinview", "logoColor:", "bannerUrl:",
                "logoUrl:", "logoText:", "className:", "aria-label"
            ])
        ]
        if not texts:
            return self._extract_generic_spa_page(path, bundle)

        label = path.rsplit("/", 1)[-1].replace("-", " ").title()
        content = "SECTION: Placement — " + label + "\n" + "\n".join(texts[:80])
        return {
            "title": f"Ahmedabad Institute of Technology — Placement {label}",
            "content": content,
            "sections": [{"section_title": f"Placement — {label}", "content": texts[:80]}],
            "extraction_status": "EXTRACTED" if len(content) >= 100 else "INSUFFICIENT",
        }

    def _extract_spa_page(self, path: str, bundle: str) -> Dict[str, Any]:
        # Committee page has a dedicated rich extractor
        if path in {"/about/committee", "/about/committees"}:
            return self._extract_committee_page(bundle)
        
        # Intake page has a dedicated rich extractor
        if path == "/about/intake":
            return self._extract_intake_page(bundle)

        if path.startswith("/placement/"):
            return self._extract_placement_page(path, bundle)

        return self._extract_generic_spa_page(path, bundle)

    # ------------------------------------------------------------------
    # fetch_page — public API used by orchestrator for live retrieval
    # ------------------------------------------------------------------
    async def fetch_page(
        self,
        url: str,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """Fetch and extract an official AIT page, handling SPA rendering."""
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=20.0, follow_redirects=True)
        try:
            log.info("FETCHING URL: %s", url)
            resp = await client.get(
                url, headers={"User-Agent": "AIT-AI-KnowledgeBot/1.0"}
            )
            log.info("FETCH RESULT: %s → HTTP %d", url, resp.status_code)
            if resp.status_code == 200:
                # Detect SPA shell (no real DOM content)
                parsed_html = BeautifulSoup(resp.text, "html.parser")
                for node in parsed_html(["script", "style", "noscript"]):
                    node.decompose()
                page_text = (parsed_html.body or parsed_html).get_text(" ", strip=True)
                is_spa_shell = len(page_text) < 200

                if is_spa_shell:
                    bundle = await self._load_bundle(client)
                    path = urlparse(url).path.rstrip("/") or "/"
                    parsed = self._extract_spa_page(path, bundle)
                else:
                    # Pre-rendered HTML — use structured section extractor
                    parsed = self._extract_html_content(resp.text, url)

                content = parsed.get("content", "")
                log.info(
                    "EXTRACTION RESULT: %s → status=%s len=%d",
                    url, parsed.get("extraction_status"), len(content)
                )
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                return {
                    "url": url,
                    "title": parsed.get("title", url),
                    "content": content,
                    "sections": parsed.get("sections", []),
                    "status_code": resp.status_code,
                    "extraction_status": parsed.get("extraction_status", "EXTRACTED" if content else "EMPTY"),
                    "hash": content_hash,
                }

            log.info("FETCH RESULT: %s → HTTP %d (non-200)", url, resp.status_code)
            return {
                "url": url, "title": url, "content": "",
                "status_code": resp.status_code,
                "extraction_status": "HTTP_ERROR",
                "hash": hashlib.sha256(b"").hexdigest(),
            }
        except Exception as exc:
            log.warning("FETCH RESULT: %s → FETCH_ERROR: %s", url, exc)
            return {
                "url": url, "title": url, "content": "",
                "status_code": 0,
                "extraction_status": "FETCH_ERROR",
                "error": str(exc),
                "hash": hashlib.sha256(b"").hexdigest(),
            }
        finally:
            if owns_client:
                await client.aclose()

    def _extract_html_content(self, html: str, url: str) -> Dict[str, Any]:
        """Structured extraction for pre-rendered HTML pages."""
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.title
        title = title_tag.get_text(" ", strip=True) if title_tag else url
        for node in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            node.decompose()
        root = soup.find("main") or soup.find("article") or soup.body or soup
        sections: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None
        for node in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table"]):
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            if node.name.startswith("h"):
                if current and current["content"]:
                    sections.append(current)
                current = {"section_title": text, "content": []}
            elif current is not None:
                current["content"].append(text)
        if current and current["content"]:
            sections.append(current)
        if not sections:
            text = root.get_text(" ", strip=True)
            if text:
                sections = [{"section_title": title, "content": [text]}]
        blocks = [
            "SECTION: " + s["section_title"] + "\n" + "\n".join(s["content"])
            for s in sections
        ]
        content = "\n\n".join(blocks)
        return {
            "title": title,
            "content": content,
            "sections": sections,
            "extraction_status": "EXTRACTED" if content else "EMPTY",
        }

    # ------------------------------------------------------------------
    # fetch_relevant_page — live fallback for chatbot orchestrator
    # ------------------------------------------------------------------
    async def fetch_relevant_page(self, query: str) -> Optional[Dict[str, Any]]:
        """Discover official URLs and return the best page for a query."""
        stopwords = {
            "who", "what", "where", "when", "which", "list", "all", "the",
            "and", "at", "for", "of", "is", "are", "chairman", "chairperson",
            "members", "member", "a", "an", "give", "me",
        }
        query_terms = [
            t.strip(".,?!:;()[]{}\"'")
            for t in query.lower().split()
            if len(t.strip(".,?!:;()[]{}\"'")) > 2
        ]
        query_terms = [t for t in query_terms if t not in stopwords]
        query_lower = query.lower()
        preferred_paths = []
        is_placement_query = any(term in query_lower for term in [
            "placement", "placements", "highest package", "average package",
            "placement rate", "recruiter", "recruiters", "training and placement",
            "placement cell", "companies visiting"
        ])
        if any(term in query_lower for term in ["intake", "total student", "number of courses"]):
            preferred_paths.append("/about/intake")
        if "sports committee" in query_lower:
            preferred_paths.append("/about/committee")

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            urls = await self._discover_urls(client)
            best: Optional[Dict[str, Any]] = None
            best_score = 0
            for url in sorted(urls):
                page = await self.fetch_page(url, client)
                content = (page.get("content") or "").lower()
                score = sum(
                    1 for term in query_terms
                    if term in content or term in url.lower()
                )
                path = urlparse(url).path.lower()
                if path in preferred_paths:
                    score += 50
                if is_placement_query and any(term in path or term in content for term in [
                    "placement", "training", "recruit", "career", "internship"
                ]):
                    score += 50
                if "intake" in query_lower and path != "/about/intake" and "intake" not in content:
                    score -= 20
                if page.get("extraction_status") != "EXTRACTED":
                    continue
                if is_placement_query and not any(term in path or term in content for term in [
                    "placement", "training", "recruit", "career", "internship"
                ]):
                    continue
                if page.get("content") and score > best_score:
                    best, best_score = page, score
            return best

    # ------------------------------------------------------------------
    # synchronize_website — main sync entry point
    # ------------------------------------------------------------------
    async def synchronize_website(self, db: Session) -> Dict[str, Any]:
        """
        Full sync:
        1. Discover all official AIT pages (bundle + sitemap + BFS).
        2. Extract structured content for each page.
        3. Upsert WebsiteSnapshot records.
        4. Emit comprehensive debug stats.
        """
        stats = {
            "total_seed_urls": 1,
            "total_discovered_urls": 0,
            "total_unique_urls": 0,
            "total_fetched": 0,
            "http_failures": 0,
            "extraction_failures": 0,
            "indexing_failures": 0,
            "successfully_persisted": 0,
            "skipped_duplicates": 0,
            "skipped_external": 0,
            "skipped_binary": 0,
            "total_pages": 0,
            "discovered_pages": 0,
            "updated_pages": 0,
            "new_pages": 0,
            "unchanged_pages": 0,
            "errors": 0,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        committee_track = {
            "discovered": False,
            "fetched": False,
            "extracted": False,
            "indexed": False,
            "persisted": False,
        }
        committee_url = f"{self.base_url}/about/committee"

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            # Stage 1: Discovery
            log.info("SYNC STAGE 1: URL discovery starting")
            urls = await self._discover_urls(client)
            stats["total_discovered_urls"] = len(urls)
            stats["total_unique_urls"] = len(urls)
            stats["discovered_pages"] = len(urls)
            stats["total_pages"] = len(urls)

            if committee_url in urls:
                committee_track["discovered"] = True
                log.info("DISCOVERED URL: %s  STATUS: FOUND", committee_url)
            else:
                log.warning("COMMITTEE PAGE NOT DISCOVERED: %s", committee_url)

            log.info("SYNC STAGE 2: fetching & extracting %d pages", len(urls))

            for url in sorted(urls):
                log.info("FETCHING URL: %s", url)
                data = await self.fetch_page(url, client)
                is_committee = url == committee_url

                stats["total_fetched"] += 1
                if is_committee:
                    committee_track["fetched"] = True

                if data["status_code"] == 0:
                    stats["http_failures"] += 1
                    stats["errors"] += 1
                    continue

                if not data["content"] or data.get("extraction_status") != "EXTRACTED":
                    stats["extraction_failures"] += 1
                    stats["errors"] += 1
                    continue
                elif is_committee:
                    committee_track["extracted"] = True

                # Upsert snapshot
                log.info("PERSISTING URL: %s", url)
                existing = db.query(WebsiteSnapshot).filter(
                    WebsiteSnapshot.url == url
                ).first()

                if not existing:
                    db.add(WebsiteSnapshot(
                        url=url,
                        title=data["title"],
                        content_hash=data["hash"],
                        text_content=data["content"][:100000],
                        status_code=data["status_code"],
                    ))
                    stats["new_pages"] += 1
                    stats["successfully_persisted"] += 1
                elif existing.content_hash != data["hash"]:
                    existing.title = data["title"]
                    existing.content_hash = data["hash"]
                    existing.text_content = data["content"][:100000]
                    existing.status_code = data["status_code"]
                    existing.last_crawled_at = datetime.now(timezone.utc)
                    stats["updated_pages"] += 1
                    stats["successfully_persisted"] += 1
                else:
                    existing.last_crawled_at = datetime.now(timezone.utc)
                    stats["unchanged_pages"] += 1
                    stats["skipped_duplicates"] += 1

                if is_committee and data["content"]:
                    committee_track["indexed"] = True
                    committee_track["persisted"] = True

        db.commit()

        # Debug report
        log.info(
            "\n========== SYNC REPORT ==========\n"
            "Total seed URLs:              %d\n"
            "Total discovered URLs:        %d\n"
            "Total unique URLs:            %d\n"
            "Total fetched:                %d\n"
            "HTTP failures:                %d\n"
            "Extraction failures:          %d\n"
            "Indexing failures:            %d\n"
            "Successfully persisted:       %d\n"
            "Skipped duplicates:           %d\n"
            "Skipped external URLs:        %d\n"
            "Skipped binary assets:        %d\n"
            "\n/about/committee:\n"
            "  DISCOVERED = %s\n"
            "  FETCHED    = %s\n"
            "  EXTRACTED  = %s\n"
            "  INDEXED    = %s\n"
            "  PERSISTED  = %s\n"
            "==================================",
            stats["total_seed_urls"],
            stats["total_discovered_urls"],
            stats["total_unique_urls"],
            stats["total_fetched"],
            stats["http_failures"],
            stats["extraction_failures"],
            stats["indexing_failures"],
            stats["successfully_persisted"],
            stats["skipped_duplicates"],
            stats["skipped_external"],
            stats["skipped_binary"],
            committee_track["discovered"],
            committee_track["fetched"],
            committee_track["extracted"],
            committee_track["indexed"],
            committee_track["persisted"],
        )

        stats["committee_track"] = committee_track
        return stats


website_crawler = AitWebsiteCrawler()
