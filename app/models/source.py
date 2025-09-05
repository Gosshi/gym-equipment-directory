from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from app.models.base import Base

class SourceType(PyEnum):
    official_site = "official_site"
    on_site_signage = "on_site_signage"
    user_submission = "user_submission"
    media = "media"
    sns = "sns"
    other = "other"

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(Enum(SourceType), nullable=False)
    title = Column(String, nullable=True)
    url = Column(String, nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)  # 情報取得/撮影日

    created_at = Column(DateTime(timezone=True), server_default=func.now())
