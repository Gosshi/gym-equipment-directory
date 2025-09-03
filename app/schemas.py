# app/schemas.py
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# --- 共通 ---

class GymBasic(BaseModel):
    id: int
    slug: str
    name: str
    chain_name: Optional[str] = None
    address: Optional[str] = None
    prefecture: Optional[str] = None
    city: Optional[str] = None

    model_config = {"from_attributes": True}

class EquipmentHighlight(BaseModel):
    equipment_slug: str
    availability: str
    count: Optional[int] = None
    max_weight_kg: Optional[int] = None
    verification_status: str
    last_verified_at: Optional[datetime] = None

class SearchItem(BaseModel):
    gym: GymBasic
    highlights: List[EquipmentHighlight] = []
    last_verified_at: Optional[datetime] = None
    score: float = Field(0.0, description="並び替え用の簡易スコア")

class SearchResponse(BaseModel):
    items: List[SearchItem]
    page: int
    per_page: int
    total: int

class EquipmentRow(BaseModel):
    equipment_slug: str
    equipment_name: str
    category: str
    availability: str
    count: Optional[int] = None
    max_weight_kg: Optional[int] = None
    verification_status: str
    last_verified_at: Optional[datetime] = None

class SourceRow(BaseModel):
    type: str
    title: Optional[str] = None
    url: Optional[str] = None
    captured_at: Optional[datetime] = None

class GymDetailResponse(BaseModel):
    gym: GymBasic
    equipments: List[EquipmentRow]
    sources: List[SourceRow] = []
    updated_at: Optional[datetime] = None
