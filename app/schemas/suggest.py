from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["GymSuggestItem"]


class GymSuggestItem(BaseModel):
    slug: str = Field(description="ジムスラッグ")
    name: str = Field(description="ジム名")
    pref: str | None = Field(default=None, description="都道府県スラッグ（nullable）")
    city: str | None = Field(default=None, description="市区町村スラッグ（nullable）")
