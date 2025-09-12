from __future__ import annotations

from pydantic import BaseModel, Field


class FavoriteCreateRequest(BaseModel):
    device_id: str = Field(
        description="匿名デバイスID",
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    gym_id: int = Field(description="ジムID")


class FavoriteItem(BaseModel):
    gym_id: int
    slug: str
    name: str
    pref: str | None = None
    city: str | None = None
    last_verified_at: str | None = None
