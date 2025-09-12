from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class GymImage(Base):
    __tablename__ = "gym_images"

    id = Column(Integer, primary_key=True)
    gym_id = Column(Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    source = Column(String, nullable=True)
    verified = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
