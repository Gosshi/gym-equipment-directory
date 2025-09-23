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
    total: int = Field(default=0, description="総件数")
    page: int = Field(default=1, description="現在のページ（1始まり）")
    page_size: int = Field(default=20, description="1ページ件数")
    has_more: bool = Field(default=False, description="次ページが存在するか")
    has_prev: bool = Field(default=False, description="前ページが存在するか")
    page_token: str | None = Field(
        default=None, description="継続トークン（Keyset互換用、未使用時はnull）"
    )
