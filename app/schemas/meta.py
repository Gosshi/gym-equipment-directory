# app/schemas/meta.py
from pydantic import BaseModel

class PrefCount(BaseModel):
    pref: str
    count: int

class CityCount(BaseModel):
    city: str
    count: int
