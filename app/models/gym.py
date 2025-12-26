from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class Gym(Base):
    __tablename__ = "gyms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    chain_name = Column(String, nullable=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    canonical_id = Column(UUID(as_uuid=False), unique=True, nullable=False)
    address = Column(String, nullable=True)
    pref = Column(String, nullable=True)
    city = Column(String, nullable=True)
    official_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    affiliate_url = Column(String, nullable=True)
    owner_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_verified_at_cached = Column(DateTime, nullable=True)
    # Geolocation (nullable)
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    parsed_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Category: gym, pool, court, hall, field, martial_arts, archery
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, default="gym")
