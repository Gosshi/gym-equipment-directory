# app/schemas/equipment.py
from pydantic import BaseModel

class EquipmentSummary(BaseModel):
    id: int
    slug: str
    name: str
    model_config = {
        "from_attributes": True
    }
