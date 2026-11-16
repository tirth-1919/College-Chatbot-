"""HTML Parsing, Table Extraction, and Content Normalization Engine.

Strips navigational boilerplate, ads, and scripts.
Converts tables into structured markdown format.
Extracts title, meta description, heading hierarchy, and clean textual corpus.
Computes SHA-256 content hashes for change detection and deduplication.
"""

import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from app.services.url_validator import is_crawleable_resource, normalize_url

# HTML Tags to purge completely (boilerplates, styling, scripts, media)
UNWANTED_TAGS: Set[str] = {
    "script", "style", "noscript", "svg", "canvas", "nav", "footer",
    "header", "aside", "form", "iframe", "embed", "object", "video",
    "audio", "source", "picture", "map", "area", "dialog"
}

# CSS class or ID keywords commonly used for non-informational UI clutter
BOILERPLATE_SELECTORS: List[str] = [
    ".cookie-banner", ".cookie-consent", "#cookie-notice",
    ".nav-menu", ".navbar", ".site-navigation",
    ".site-footer", ".footer-links", "#footer",
    ".sidebar", "#sidebar", ".advertisement", ".ad-container",
    ".modal-overlay", ".popup", ".share-buttons"
]


class ExtractedPageContent:
    """Structured container for clean parsed web page data."""

    def __init__(
        self,
        url: str,
        title: str,
        meta_description: str,
        canonical_url: Optional[str],
        cleaned_text: str,
        content_hash: str,
        headings: List[Dict[str, str]],
        tables_markdown: List[str],
        discovered_links: List[str],
        requires_js: bool = False,
    ):
        self.url = url
        self.title = title
        self.meta_description = meta_description
        self.canonical_url = canonical_url
        self.cleaned_text = cleaned_text
        self.content_hash = content_hash
        self.content_length = len(cleaned_text)
        self.headings = headings
        self.tables_markdown = tables_markdown
        self.discovered_links = discovered_links
        self.requires_js = requires_js


def extract_table_as_markdown(table_tag: Tag) -> str:
    """Converts an HTML <table> into clean, LLM-friendly Markdown table formatting."""
    rows: List[List[str]] = []

    for tr in table_tag.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        row_data = [
            re.sub(r"\s+", " ", cell.get_text(strip=True)).replace("|", "\\|")
            for cell in cells
        ]
        rows.append(row_data)

    if not rows:
        return ""

    # Normalize column count to longest row
    max_cols = max(len(r) for r in rows)
    if max_cols == 0:
        return ""

    normalized_rows = [r + [""] * (max_cols - len(r)) for r in rows]

    # Build Markdown table
    header = normalized_rows[0]
    header_line = "| " + " | ".join(header) + " |"
    separator_line = "| " + " | ".join(["---"] * max_cols) + " |"

    body_lines = []
    for r in normalized_rows[1:]:
        body_lines.append("| " + " | ".join(r) + " |")

    return "\n".join([header_line, separator_line] + body_lines)


def parse_and_clean_html(
    html: str,
    page_url: str,
    encoding: str = "utf-8"
) -> ExtractedPageContent:
    """Parses raw HTML content into structured text, tables, metadata, and normalized links.

    Args:
        html: Raw HTML string returned by HTTP request.
        page_url: URL where the HTML was fetched from.
        encoding: Character encoding.

    Returns:
        ExtractedPageContent with cleaned text, SHA-256 hash, and internal links.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Remove HTML Comments
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # 2. Extract Metadata before stripping tags
    # Title
    title = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()

    # Meta Description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    if not meta_tag:
        meta_tag = soup.find("meta", attrs={"property": re.compile(r"^og:description$", re.I)})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"].strip()

    # Canonical Link
    canonical_url: Optional[str] = None
    canonical_tag = soup.find("link", rel=lambda val: val and "canonical" in val)
    if canonical_tag and canonical_tag.get("href"):
        canonical_url = normalize_url(canonical_tag["href"], page_url)

    # 3. Detect SPA / Client-Side Rendering indicators
    requires_js = False
    body = soup.find("body")
    body_text_length = len(body.get_text(strip=True)) if body else 0
    if body_text_length < 80:
        if (
            soup.find("div", id=re.compile(r"^(root|app|__next)$", re.I))
            or soup.find("noscript")
        ):
            requires_js = True

    # 4. Extract Discovered Links before modifying DOM
    discovered_links: List[str] = []
    seen_links: Set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        raw_href = a_tag["href"].strip()
        if not raw_href or raw_href.startswith("#") or raw_href.startswith("javascript:") or raw_href.startswith("mailto:") or raw_href.startswith("tel:"):
            continue

        resolved = normalize_url(raw_href, page_url)
        if resolved and resolved not in seen_links and is_crawleable_resource(resolved):
            seen_links.add(resolved)
            discovered_links.append(resolved)

    # 5. Extract Headings Hierarchy
    headings: List[Dict[str, str]] = []
    for h in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        h_text = h.get_text(strip=True)
        if h_text:
            headings.append({"level": h.name.lower(), "text": h_text})

    # If title was missing, fall back to first H1
    if not title and headings:
        for h in headings:
            if h["level"] == "h1":
                title = h["text"]
                break

    # 6. Extract Tables into Markdown Format
    tables_md: List[str] = []
    for table in soup.find_all("table"):
        md_table = extract_table_as_markdown(table)
        if md_table:
            tables_md.append(md_table)
            # Replace table in DOM with markdown marker so surrounding context is preserved
            table.replace_with(soup.new_string(f"\n\n{md_table}\n\n"))

    # 7. Strip unwanted tags and boilerplate classes
    for tag_name in UNWANTED_TAGS:
        for element in soup.find_all(tag_name):
            element.decompose()

    for selector in BOILERPLATE_SELECTORS:
        try:
            for element in soup.select(selector):
                element.decompose()
        except Exception:
            pass

    # 8. Extract Clean Text
    main_container = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", attrs={"role": "main"})
        or soup.find("div", id=re.compile(r"(content|main|page)", re.I))
        or soup.body
        or soup
    )

    raw_text = main_container.get_text(separator="\n")

    # Normalize whitespace, excessive newlines, and trailing spaces
    cleaned_lines = []
    for line in raw_text.splitlines():
        line_clean = re.sub(r"[ \t]+", " ", line).strip()
        if line_clean:
            cleaned_lines.append(line_clean)

    cleaned_text = "\n\n".join(cleaned_lines)

    # Compute SHA-256 Hash of clean textual content
    content_hash = hashlib.sha256(cleaned_text.encode(encoding, errors="replace")).hexdigest()

    return ExtractedPageContent(
        url=page_url,
        title=title or "Untitled Page",
        meta_description=meta_desc,
        canonical_url=canonical_url,
        cleaned_text=cleaned_text,
        content_hash=content_hash,
        headings=headings,
        tables_markdown=tables_md,
        discovered_links=discovered_links,
        requires_js=requires_js,
    )

