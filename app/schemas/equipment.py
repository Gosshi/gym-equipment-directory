# app/schemas/equipment.py
from pydantic import BaseModel

class EquipmentSummary(BaseModel):
    id: int
    slug: str
    name: str
    class Config:
        from_attributes = True
