from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    desc,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class ScrapedPage(Base):
    __tablename__ = "scraped_pages"
    __table_args__ = (
        UniqueConstraint("source_id", "url", name="uq_scraped_pages_source_url"),
        Index("ix_scraped_pages_fetched_at_desc", desc("fetched_at")),
        Index("ix_scraped_pages_content_hash", "content_hash"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_meta: Mapped[dict | None] = mapped_column(
        JSONB(astext_type=Text()),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    candidates: Mapped[list[GymCandidate]] = relationship(
        "GymCandidate",
        back_populates="source_page",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


if TYPE_CHECKING:  # pragma: no cover
    from app.models.gym_candidate import GymCandidate
