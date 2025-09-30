from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.scraped_page import ScrapedPage


class CandidateStatus(str, Enum):
    new = "new"
    reviewing = "reviewing"
    approved = "approved"
    rejected = "rejected"


class GymCandidate(Base):
    __tablename__ = "gym_candidates"
    __table_args__ = (
        Index("ix_gym_candidates_status", "status"),
        Index("ix_gym_candidates_pref_city", "pref_slug", "city_slug"),
        Index("ix_gym_candidates_parsed_json", "parsed_json", postgresql_using="gin"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_page_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("scraped_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    address_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    pref_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    city_slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latitude: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    longitude: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    parsed_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[CandidateStatus] = mapped_column(
        SQLEnum(CandidateStatus, name="candidate_status"),
        nullable=False,
        default=CandidateStatus.new,
        server_default=text("'new'::candidate_status"),
    )
    duplicate_of_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("gym_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    source_page: Mapped[ScrapedPage] = relationship(
        "ScrapedPage",
        back_populates="candidates",
        passive_deletes=True,
    )
    duplicate_of: Mapped[GymCandidate | None] = relationship(
        remote_side="GymCandidate.id",
        foreign_keys="GymCandidate.duplicate_of_id",
    )
