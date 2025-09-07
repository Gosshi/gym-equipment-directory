from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.base import Base


class Gym(Base):
    __tablename__ = "gyms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    chain_name = Column(String, nullable=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    address = Column(String, nullable=True)
    pref = Column(String, nullable=True)
    city = Column(String, nullable=True)
    official_url = Column(String, nullable=True)
    affiliate_url = Column(String, nullable=True)
    owner_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_verified_at_cached = Column(DateTime, nullable=True)
