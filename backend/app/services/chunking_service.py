"""Semantic & Structure-Aware Document & Web Chunker.

Divides extracted documents and crawled web pages into semantically cohesive
chunks respecting Markdown heading boundaries, tables, and paragraph breaks.
Attaches categorization, heading hierarchy, and deduplication hashes.
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from app.services.text_normalizer import text_normalizer
from app.services.classifier_service import classifier_service


@dataclass
class ProcessedChunk:
    """Structured representation of an extracted semantic chunk."""

    chunk_text: str
    heading: Optional[str]
    category: str
    confidence: float
    content_hash: str
    token_count: int
    page_number: Optional[int] = None
    source_url: Optional[str] = None
    chunk_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticChunkerService:
    """Performs semantic chunking preserving heading and table contexts."""

    def __init__(
        self,
        target_chunk_size: int = 800,
        max_chunk_size: int = 1200,
        chunk_overlap: int = 100,
    ):
        self.target_chunk_size = target_chunk_size
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_content(
        self,
        content: str,
        source_url: Optional[str] = None,
        page_number: Optional[int] = None,
        default_heading: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[ProcessedChunk]:
        """Segments normalized content into semantic, heading-aware chunks.

        Handles:
        - Markdown heading hierarchy (# Section, ## Subsection)
        - Markdown tables (retained intact)
        - Overlapping paragraphs for contextual continuity
        - Automatic 15-category classification
        - SHA256 content deduplication hashing
        """
        normalized = text_normalizer.normalize_text(content)
        if not normalized:
            return []

        # 1. Split text into sections by Markdown headings
        sections = self._split_by_headings(normalized, default_heading)

        all_chunks: List[ProcessedChunk] = []
        chunk_idx = 0

        for section_heading, section_text in sections:
            # Sub-chunk this section by paragraphs or tables
            sub_chunks = self._chunk_section(section_text, section_heading)

            for text_fragment in sub_chunks:
                clean_fragment = text_fragment.strip()
                if len(clean_fragment) < 40:  # Skip trivial fragments
                    continue

                # Classify chunk
                category, confidence, tags = classifier_service.classify_text(
                    text=clean_fragment,
                    heading=section_heading,
                    source_url=source_url,
                )

                content_hash = text_normalizer.compute_sha256(clean_fragment)
                token_count = text_normalizer.estimate_tokens(clean_fragment)

                meta = {
                    "tags": tags,
                    "target_chunk_size": self.target_chunk_size,
                    "overlap": self.chunk_overlap,
                }
                if extra_metadata:
                    meta.update(extra_metadata)

                chunk = ProcessedChunk(
                    chunk_text=clean_fragment,
                    heading=section_heading,
                    category=category,
                    confidence=confidence,
                    content_hash=content_hash,
                    token_count=token_count,
                    page_number=page_number,
                    source_url=source_url,
                    chunk_index=chunk_idx,
                    metadata=meta,
                )
                all_chunks.append(chunk)
                chunk_idx += 1

        return all_chunks

    def _split_by_headings(
        self, text: str, default_heading: Optional[str]
    ) -> List[tuple[Optional[str], str]]:
        """Splits full text into blocks delineated by Markdown headings."""
        lines = text.split("\n")
        sections: List[tuple[Optional[str], str]] = []
        current_heading = default_heading
        current_lines: List[str] = []

        for line in lines:
            header_match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
            if header_match:
                # Flush previous section
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines)))
                    current_lines = []
                current_heading = header_match.group(2).strip()
                current_lines.append(line)
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines)))

        return sections if sections else [(default_heading, text)]

    def _chunk_section(
        self, section_text: str, heading: Optional[str]
    ) -> List[str]:
        """Chunks a section into chunks bounded by target size and overlap."""
        if len(section_text) <= self.max_chunk_size:
            return [section_text]

        # Break into paragraphs or markdown tables
        paragraphs: List[str] = []
        raw_paras = section_text.split("\n\n")

        for p in raw_paras:
            p_clean = p.strip()
            if not p_clean:
                continue
            # If paragraph contains markdown table, keep it as atomic block
            if "|" in p_clean and "\n|" in p_clean:
                paragraphs.append(p_clean)
            else:
                paragraphs.append(p_clean)

        chunks: List[str] = []
        current_buffer: List[str] = []
        current_len = 0

        for p in paragraphs:
            p_len = len(p)
            if current_len + p_len > self.target_chunk_size and current_buffer:
                # Flush current buffer
                chunk_str = "\n\n".join(current_buffer)
                chunks.append(chunk_str)

                # Maintain overlap from end of previous buffer
                overlap_text = current_buffer[-1] if len(current_buffer[-1]) <= self.chunk_overlap else current_buffer[-1][-self.chunk_overlap:]
                current_buffer = [overlap_text, p]
                current_len = len(overlap_text) + p_len
            else:
                current_buffer.append(p)
                current_len += p_len

        if current_buffer:
            chunks.append("\n\n".join(current_buffer))

        return chunks


chunker_service = SemanticChunkerService()

