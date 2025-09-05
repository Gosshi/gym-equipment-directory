# app/schemas/gym_detail.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

class EquipmentRow(BaseModel):
    equipment_slug: str
    equipment_name: str
    category: Optional[str] = None
    availability: str
    count: Optional[int] = None
    max_weight_kg: Optional[int] = None
    verification_status: str
    last_verified_at: Optional[datetime] = None

class SourceRow(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None

class GymBasic(BaseModel):
    id: int
    name: str
    slug: str
    prefecture: Optional[str] = None
    city: Optional[str] = None

class GymDetailResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "gym": {"id": 101, "slug": "gold-gym-funabashi", "name": "Gold Gym Funabashi", "prefecture": "chiba", "city": "funabashi"},
            "equipments": [
                {"equipment_slug": "dumbbell", "equipment_name": "Dumbbell", "category": "free-weights",
                 "availability": "present", "count": 20, "max_weight_kg": 50,
                 "verification_status": "verified", "last_verified_at": "2025-09-01T12:34:56Z"}
            ],
            "sources": [],
            "updated_at": "2025-09-01T12:34:56Z"
        }
    })
    gym: GymBasic
    equipments: List[EquipmentRow]
    sources: List[SourceRow]
    updated_at: Optional[datetime] = None
