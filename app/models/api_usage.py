from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class ApiUsage(Base):
    """Tracks API usage for cost monitoring."""

    __tablename__ = "api_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False)  # openai, google_maps, etc.
    metric: Mapped[str] = mapped_column(String(64), nullable=False)  # input_tokens, requests, etc.
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("service", "metric", "date", name="uq_api_usage_service_metric_date"),
    )
