"""Website Crawler SQLAlchemy ORM Models.

Entities for managing website sources, crawl executions, logs, and fetched web pages.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.models.college import College


class WebsiteSource(Base, UUIDPrimaryKeyMixin):
    """Target URL configuration for college website crawling."""

    __tablename__ = "website_sources"

    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_subdomains: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    max_depth: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    max_pages: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    crawl_frequency: Mapped[str] = mapped_column(String(50), default="WEEKLY", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="website_sources")
    crawl_jobs: Mapped[List["CrawlJob"]] = relationship(
        "CrawlJob", back_populates="source", cascade="all, delete-orphan"
    )
    pages: Mapped[List["WebsitePage"]] = relationship(
        "WebsitePage", back_populates="source", cascade="all, delete-orphan"
    )


class CrawlJob(Base, UUIDPrimaryKeyMixin):
    """Execution instance of an asynchronous website crawl."""

    __tablename__ = "crawl_jobs"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("website_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        PG_ENUM(
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            "RUNNING",
            "PAUSED",
            name="crawl_job_status",
            create_type=False,
        ),
        default="PENDING",
        nullable=False,
        index=True,
    )
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="crawl_jobs")
    source: Mapped["WebsiteSource"] = relationship("WebsiteSource", back_populates="crawl_jobs")
    events: Mapped[List["CrawlEvent"]] = relationship(
        "CrawlEvent", back_populates="crawl_job", cascade="all, delete-orphan"
    )
    pages: Mapped[List["WebsitePage"]] = relationship(
        "WebsitePage", back_populates="crawl_job"
    )


class CrawlEvent(Base, UUIDPrimaryKeyMixin):
    """Log events emitted during crawler execution."""

    __tablename__ = "crawl_events"

    crawl_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    log_level: Mapped[str] = mapped_column(String(20), default="INFO", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    crawl_job: Mapped["CrawlJob"] = relationship("CrawlJob", back_populates="events")


class WebsitePage(Base, UUIDPrimaryKeyMixin):
    """Extracted text and metadata from an individual crawled page."""

    __tablename__ = "website_pages"

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("website_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crawl_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crawl_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_length: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, default=200, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="website_pages")
    source: Mapped["WebsiteSource"] = relationship("WebsiteSource", back_populates="pages")
    crawl_job: Mapped[Optional["CrawlJob"]] = relationship("CrawlJob", back_populates="pages")

