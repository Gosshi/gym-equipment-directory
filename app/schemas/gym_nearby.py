from __future__ import annotations

from pydantic import BaseModel, Field


class GymNearbyItem(BaseModel):
    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    name: str = Field(description="名称")
    pref: str = Field(description="都道府県スラッグ")
    city: str = Field(description="市区町村スラッグ")
    latitude: float = Field(description="ジムの緯度")
    longitude: float = Field(description="ジムの経度")
    distance_km: float = Field(description="指定座標からの距離（km）")
    last_verified_at: str | None = Field(
        default=None, description="最終検証日時（ISO8601, nullable）"
    )


class GymNearbyResponse(BaseModel):
    items: list[GymNearbyItem] = Field(description="検索結果")
    has_next: bool = Field(description="次ページ有無")
    page_token: str | None = Field(default=None, description="Keyset 継続トークン")
