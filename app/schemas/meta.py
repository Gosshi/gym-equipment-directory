# app/schemas/meta.py
from pydantic import BaseModel, Field

class PrefCount(BaseModel):
    pref: str = Field(..., json_schema_extra={"examples": ["chiba"]})
    count: int = Field(..., json_schema_extra={"examples": [128]})

class CityCount(BaseModel):
    city: str = Field(..., json_schema_extra={"examples": ["funabashi"]})
    count: int = Field(..., json_schema_extra={"examples": [42]})
