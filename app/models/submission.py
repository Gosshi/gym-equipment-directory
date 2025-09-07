from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.models.base import Base


class SubmissionStatus(PyEnum):
    pending = "pending"
    corroborated = "corroborated"
    approved = "approved"
    rejected = "rejected"


class UserSubmission(Base):
    __tablename__ = "user_submissions"

    id = Column(Integer, primary_key=True)
    gym_id = Column(Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="SET NULL"), nullable=True)

    payload_json = Column(String, nullable=True)  # 後でJSON型に変えてもOK
    photo_url = Column(String, nullable=True)
    visited_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(Enum(SubmissionStatus), nullable=False, default=SubmissionStatus.pending)
    created_by_user_id = Column(Integer, nullable=True)  # 匿名ならNULL

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
