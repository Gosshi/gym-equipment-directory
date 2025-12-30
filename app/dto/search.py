"""DTOs for gym search responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GymSummaryDTO(BaseModel):
    """Public summary representation of a gym returned by search endpoints."""

    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    canonical_id: str = Field(description="ジムの canonical UUID")
    name: str = Field(description="名称")
    pref: str = Field(description="都道府県スラッグ")
    city: str = Field(description="市区町村スラッグ")
    official_url: str | None = Field(default=None, description="公式サイトURL（任意）")
    last_verified_at: str | None = Field(
        default=None, description="最終検証日時（ISO8601, nullable）"
    )
    score: float | None = Field(default=None, description="複合スコア（nullable）")
    freshness_score: float | None = Field(default=None, description="鮮度スコア（nullable）")
    richness_score: float | None = Field(default=None, description="充実度スコア（nullable）")
    distance_km: float | None = Field(default=None, description="検索基準点からの距離（km）")
    latitude: float | None = Field(default=None, description="緯度")
    longitude: float | None = Field(default=None, description="経度")
    tags: list[str] = Field(default_factory=list, description="検索用タグ（利用条件など）")
    category: str | None = Field(
        default=None, description="施設カテゴリ（gym, pool, court, hall, etc.）"
    )
    categories: list[str] = Field(
        default_factory=list, description="施設カテゴリ配列 (gym, pool, etc.)"
    )

    model_config = ConfigDict(from_attributes=True)


class GymSearchPageDTO(BaseModel):
    """Search result page for gyms including pagination metadata."""

    items: list[GymSummaryDTO] = Field(description="検索結果")
    total: int = Field(default=0, description="総件数")
    page: int = Field(default=1, description="現在のページ（1始まり）")
    page_size: int = Field(default=20, description="1ページ件数")
    has_more: bool = Field(default=False, description="次ページが存在するか")
    has_prev: bool = Field(default=False, description="前ページが存在するか")
    page_token: str | None = Field(
        default=None, description="継続トークン（Keyset互換用、未使用時はnull）"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": 1,
                            "slug": "dummy-gym",
                            "canonical_id": "11111111-2222-3333-4444-555555555555",
                            "name": "Dummy Gym",
                            "pref": "chiba",
                            "city": "funabashi",
                            "official_url": "https://dummy-gym.example.com",
                            "last_verified_at": "2025-09-01T12:34:56Z",
                            "score": 0.84,
                            "freshness_score": 0.93,
                            "richness_score": 0.68,
                        }
                    ],
                    "total": 10,
                    "page": 1,
                    "page_size": 20,
                    "has_more": True,
                    "has_prev": False,
                }
            ]
        }
    )
