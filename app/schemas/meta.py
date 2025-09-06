# app/schemas/meta.py
from pydantic import BaseModel, Field

class PrefCount(BaseModel):
    pref: str = Field(..., example="chiba")
    count: int = Field(..., example=128)

class CityCount(BaseModel):
    city: str = Field(..., example="funabashi")
    count: int = Field(..., example=42)
