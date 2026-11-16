"""Text Normalization & Hygiene Service.

Sanitizes, normalizes, and prepares extracted website and document text
for categorization, chunking, and semantic vector indexing.
Preserves Markdown tables, structural lists, and headings while stripping
boilerplate, repeated headers/footers, and navigation artifacts.
"""

import hashlib
import re
from typing import List, Optional


class TextNormalizer:
    """Enterprise text normalization engine preserving markdown structures."""

    # Navigation / Web boilerplate patterns to scrub
    BOILERPLATE_PATTERNS = [
        r"^(skip to (content|navigation|main|footer|top)).*?$",
        r"^(all rights reserved|copyright ©|\(c\) \d{4}).*?$",
        r"^(cookie policy|privacy policy|terms (of|and) (conditions|service)).*?$",
        r"^(follow us on|social media:|connect with us).*?$",
        r"^(designed and developed by|powered by).*?$",
        r"^(\[.*?\]\(javascript:.*?\))$",
        r"^(click here to view|download brochure here)$",
    ]

    @classmethod
    def normalize_text(cls, raw_text: Optional[str]) -> str:
        """Normalizes text while maintaining markdown tables, lists, and headings.

        - Converts Windows CRLF to standard LF.
        - Unifies unicode quotation marks, en/em-dashes, and special spaces.
        - Preserves Markdown tables (| ... |) and headers (#).
        - Collapses excess blank lines (>2 newlines) into 2 newlines.
        - Strips web chrome and navigational clutter.
        """
        if not raw_text:
            return ""

        text = raw_text

        # 1. Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Normalize unicode punctuation and quotes
        unicode_replacements = {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u2026": "...",
            "\u00a0": " ",
            "\u200b": "",  # zero-width space
            "\ufeff": "",  # byte order mark
        }
        for orig, replacement in unicode_replacements.items():
            text = text.replace(orig, replacement)

        # 3. Process line-by-line to strip web boilerplate while keeping tables/headings
        cleaned_lines: List[str] = []
        lines = text.split("\n")
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # Preserve code/preformatted blocks
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                cleaned_lines.append(line)
                continue

            if in_code_block:
                cleaned_lines.append(line)
                continue

            # Preserve Markdown tables and headings
            if stripped.startswith("|") and stripped.endswith("|"):
                cleaned_lines.append(stripped)
                continue
            if re.match(r"^#{1,6}\s+", stripped):
                cleaned_lines.append(stripped)
                continue

            # Strip known boilerplate lines
            is_boilerplate = False
            for pattern in cls.BOILERPLATE_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    is_boilerplate = True
                    break
            if is_boilerplate:
                continue

            # Collapse horizontal tabs and multiple spaces on normal lines
            normalized_line = re.sub(r"[ \t]+", " ", stripped)
            cleaned_lines.append(normalized_line)

        # 4. Reassemble and collapse excessive vertical whitespace
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result).strip()

        return result

    @classmethod
    def compute_sha256(cls, text: str) -> str:
        """Calculates deterministic SHA256 hex digest of normalized text."""
        normalized = cls.normalize_text(text)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Approximates token count using standard 4-chars-per-token heuristic."""
        if not text:
            return 0
        return max(1, len(text) // 4)


text_normalizer = TextNormalizer()

