from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.sql import expression, func

from app.models.base import Base


class GymSlug(Base):
    __tablename__ = "gym_slugs"

    id = Column(BigInteger, primary_key=True)
    gym_id = Column(
        BigInteger, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug = Column(String, nullable=False, unique=True)
    is_current = Column(Boolean, nullable=False, server_default=expression.false())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
