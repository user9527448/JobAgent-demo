"""Core recruitment persistence models for the MVP data pipeline."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobagent.core.exceptions import JsonValue
from jobagent.db.models.base import Base, TimestampMixin, UTCDateTime


class Source(TimestampMixin, Base):
    """A configured public recruitment information source."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("crawl_interval_minutes > 0", name="crawl_interval_positive"),
        Index("ix_sources_enabled_category", "enabled", "category"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    adapter: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    crawl_interval_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1440,
        server_default=text("1440"),
    )

    crawl_runs: Mapped[list[CrawlRun]] = relationship(
        back_populates="source",
        passive_deletes=True,
    )
    raw_documents: Mapped[list[RawDocument]] = relationship(
        back_populates="source",
        passive_deletes=True,
    )


class CrawlRun(Base):
    """One observable execution of a source collection attempt."""

    __tablename__ = "crawl_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'partial', 'failed', 'cancelled')",
            name="status_valid",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="finish_after_start",
        ),
        Index("ix_crawl_runs_source_started", "source_id", "started_at"),
        Index("ix_crawl_runs_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    started_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    stats: Mapped[dict[str, JsonValue]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = relationship(back_populates="crawl_runs")


class RawDocument(Base):
    """Immutable source announcement content and its provenance."""

    __tablename__ = "raw_documents"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "canonical_url",
            "version",
            name="uq_raw_documents_source_canonical_url_version",
        ),
        CheckConstraint(
            "raw_html IS NOT NULL OR raw_text IS NOT NULL",
            name="content_present",
        ),
        CheckConstraint(
            "content_hash ~ '^[0-9a-f]{64}$'",
            name="content_hash_sha256",
        ),
        CheckConstraint("version > 0", name="version_positive"),
        CheckConstraint(
            "supersedes_id IS NULL OR supersedes_id <> id",
            name="supersedes_other_version",
        ),
        Index(
            "uq_raw_documents_source_current_url",
            "source_id",
            "canonical_url",
            unique=True,
            postgresql_where=text("is_current"),
        ),
        Index("ix_raw_documents_source_published", "source_id", "published_at"),
        Index("ix_raw_documents_content_hash", "content_hash"),
        Index("ix_raw_documents_supersedes_id", "supersedes_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_html: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    fetched_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.now(),
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    etag: Mapped[str | None] = mapped_column(Text)
    last_modified: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    supersedes_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"),
    )

    source: Mapped[Source] = relationship(back_populates="raw_documents")
    supersedes: Mapped[RawDocument | None] = relationship(
        remote_side="RawDocument.id",
        foreign_keys=[supersedes_id],
    )
    attachments: Mapped[list[Attachment]] = relationship(
        back_populates="document",
        passive_deletes=True,
    )
    job_post: Mapped[JobPost | None] = relationship(
        back_populates="document",
        passive_deletes=True,
    )
    evidence_records: Mapped[list[FieldEvidence]] = relationship(
        back_populates="source_document",
        foreign_keys="FieldEvidence.source_document_id",
        passive_deletes=True,
    )


class Attachment(Base):
    """An attachment discovered on a raw announcement."""

    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint("document_id", "url", name="uq_attachments_document_url"),
        CheckConstraint(
            "parse_status IN ('pending', 'parsed', 'ocr_required', 'unsupported', 'failed')",
            name="parse_status_valid",
        ),
        CheckConstraint(
            "sha256 IS NULL OR sha256 ~ '^[0-9a-f]{64}$'",
            name="sha256_valid",
        ),
        CheckConstraint(
            "download_status IN ('pending', 'stored', 'failed')",
            name="download_status_valid",
        ),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0",
            name="size_bytes_nonnegative",
        ),
        CheckConstraint(
            "download_status <> 'stored' OR "
            "(mime_type IS NOT NULL AND sha256 IS NOT NULL "
            "AND local_path IS NOT NULL AND size_bytes IS NOT NULL "
            "AND downloaded_at IS NOT NULL)",
            name="stored_metadata_present",
        ),
        Index("ix_attachments_document_status", "document_id", "parse_status"),
        Index("ix_attachments_download_status", "download_status"),
        Index("ix_attachments_sha256", "sha256"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(127))
    sha256: Mapped[str | None] = mapped_column(String(64))
    local_path: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    download_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    downloaded_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    parse_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.now(),
    )
    parsed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    document: Mapped[RawDocument] = relationship(back_populates="attachments")
    evidence_records: Mapped[list[FieldEvidence]] = relationship(
        back_populates="source_attachment",
        foreign_keys="FieldEvidence.source_attachment_id",
        passive_deletes=True,
    )


class JobPost(TimestampMixin, Base):
    """Announcement-level structured recruitment information."""

    __tablename__ = "job_posts"
    __table_args__ = (
        CheckConstraint(
            "deadline IS NULL OR start_at IS NULL OR deadline >= start_at",
            name="deadline_after_start",
        ),
        Index("ix_job_posts_category_region", "category", "region"),
        Index("ix_job_posts_deadline", "deadline"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    organization: Mapped[str | None] = mapped_column(String(300))
    category: Mapped[str | None] = mapped_column(String(50))
    region: Mapped[str | None] = mapped_column(String(100))
    apply_url: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    deadline: Mapped[datetime | None] = mapped_column(UTCDateTime())

    document: Mapped[RawDocument] = relationship(back_populates="job_post")
    positions: Mapped[list[JobPosition]] = relationship(
        back_populates="post",
        passive_deletes=True,
    )


class JobPosition(Base):
    """A position row belonging to a structured recruitment post."""

    __tablename__ = "job_positions"
    __table_args__ = (
        CheckConstraint("headcount IS NULL OR headcount > 0", name="headcount_positive"),
        Index("ix_job_positions_post", "post_id"),
        Index("ix_job_positions_location_education", "location", "education"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("job_posts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    department: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(100))
    education: Mapped[str | None] = mapped_column(String(100))
    major: Mapped[str | None] = mapped_column(Text)
    headcount: Mapped[int | None] = mapped_column(Integer)
    requirements: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.now(),
    )

    post: Mapped[JobPost] = relationship(back_populates="positions")


class FieldEvidence(Base):
    """Trace a structured field back to a document, page, quote, or cell."""

    __tablename__ = "field_evidence"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('job_post', 'job_position')",
            name="entity_type_valid",
        ),
        CheckConstraint(
            "source_type IN ('document', 'attachment')",
            name="source_type_valid",
        ),
        CheckConstraint(
            "(source_type = 'document' AND source_document_id IS NOT NULL "
            "AND source_attachment_id IS NULL) OR "
            "(source_type = 'attachment' AND source_attachment_id IS NOT NULL "
            "AND source_document_id IS NULL)",
            name="source_reference_matches_type",
        ),
        CheckConstraint(
            "quote_text IS NOT NULL OR page_number IS NOT NULL OR cell_reference IS NOT NULL",
            name="locator_present",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="page_number_positive",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_range",
        ),
        Index("ix_field_evidence_entity", "entity_type", "entity_id", "field_name"),
        Index("ix_field_evidence_document", "source_document_id"),
        Index("ix_field_evidence_attachment", "source_attachment_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_documents.id", ondelete="RESTRICT")
    )
    source_attachment_id: Mapped[int | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="RESTRICT")
    )
    quote_text: Mapped[str | None] = mapped_column(Text)
    page_number: Mapped[int | None] = mapped_column(Integer)
    cell_reference: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        server_default=func.now(),
    )

    source_document: Mapped[RawDocument | None] = relationship(
        back_populates="evidence_records",
        foreign_keys=[source_document_id],
    )
    source_attachment: Mapped[Attachment | None] = relationship(
        back_populates="evidence_records",
        foreign_keys=[source_attachment_id],
    )
