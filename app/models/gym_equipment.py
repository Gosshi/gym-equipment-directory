from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.models.base import Base

class Availability(PyEnum):
    present = "present"
    absent = "absent"
    unknown = "unknown"

class VerificationStatus(PyEnum):
    unverified = "unverified"
    user_verified = "user_verified"
    owner_verified = "owner_verified"
    admin_verified = "admin_verified"

class GymEquipment(Base):
    __tablename__ = "gym_equipments"

    id = Column(Integer, primary_key=True)
    gym_id = Column(Integer, ForeignKey("gyms.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="CASCADE"), nullable=False)

    availability = Column(Enum(Availability), nullable=False, default=Availability.unknown)
    count = Column(Integer, nullable=True)          # 台数。不明はNULL
    max_weight_kg = Column(Integer, nullable=True)  # 例: ダンベル最大重量。不明はNULL
    notes = Column(String, nullable=True)

    verification_status = Column(Enum(VerificationStatus), nullable=False, default=VerificationStatus.unverified)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    source_id = Column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # (gym_id, equipment_id) にユニーク制約を付けたい場合は Alembic 生成後に追加でもOK
