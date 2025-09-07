from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.models.base import Base


class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)  # 例: スクワットラック
    slug = Column(String, unique=True, nullable=False)  # 例: squat-rack
    category = Column(String, nullable=False)  # free_weight | machine | cardio | other
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
