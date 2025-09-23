"""DTOs for gym search responses."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GymSummaryDTO(BaseModel):
    """Public summary representation of a gym returned by search endpoints."""

    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    name: str = Field(description="名称")
    pref: str = Field(description="都道府県スラッグ")
    city: str = Field(description="市区町村スラッグ")
    last_verified_at: str | None = Field(
        default=None, description="最終検証日時（ISO8601, nullable）"
    )
    score: float | None = Field(default=None, description="複合スコア（nullable）")
    freshness_score: float | None = Field(default=None, description="鮮度スコア（nullable）")
    richness_score: float | None = Field(default=None, description="充実度スコア（nullable）")
    distance_km: float | None = Field(default=None, description="検索基準点からの距離（km）")

    model_config = ConfigDict(from_attributes=True)


class GymSearchPageDTO(BaseModel):
    """Search result page for gyms including pagination metadata."""

    items: list[GymSummaryDTO] = Field(description="検索結果")
    total: int = Field(description="総件数")
    has_next: bool = Field(description="次ページ有無")
    page_token: str | None = Field(default=None, description="Keyset 継続トークン")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": 1,
                            "slug": "dummy-gym",
                            "name": "Dummy Gym",
                            "pref": "chiba",
                            "city": "funabashi",
                            "last_verified_at": "2025-09-01T12:34:56Z",
                            "score": 0.84,
                            "freshness_score": 0.93,
                            "richness_score": 0.68,
                        }
                    ],
                    "total": 10,
                    "has_next": True,
                    "page_token": "v1:freshness:nf=0,ts=1725555555,id=42",
                }
            ]
        }
    )
