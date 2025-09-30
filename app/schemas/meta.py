# app/schemas/meta.py
from pydantic import BaseModel, Field


class PrefCount(BaseModel):
    pref: str = Field(..., json_schema_extra={"example": "chiba"})
    count: int = Field(..., json_schema_extra={"example": 128})


class CityCount(BaseModel):
    city: str = Field(..., json_schema_extra={"example": "funabashi"})
    count: int = Field(..., json_schema_extra={"example": 42})


class EquipmentOption(BaseModel):
    slug: str = Field(..., json_schema_extra={"example": "smith-machine"})
    name: str = Field(..., json_schema_extra={"example": "スミスマシン"})
    category: str | None = Field(default=None, json_schema_extra={"example": "strength"})
