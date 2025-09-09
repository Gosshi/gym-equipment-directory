# app/schemas/gym_search.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["GymSummary", "GymSearchResponse"]


class GymSummary(BaseModel):
    """
    検索結果のジム要約。
    last_verified_at_cached は ISO8601 文字列（例: "2025-09-05T12:34:5600:00"）
    """

    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    name: str = Field(description="名称")
    city: str = Field(description="市区町村スラッグ")
    pref: str = Field(description="都道府県スラッグ")
    last_verified_at: str | None = Field(default=None, description="最終検証日時（UTC, nullable）")
    score: float | None = Field(default=None, description="スコア（nullable）")
    freshness_score: float | None = Field(default=None, description="新鮮さスコア（nullable）")
    richness_score: float | None = Field(default=None, description="充実度スコア（nullable）")


class GymSearchResponse(BaseModel):
    items: list[GymSummary] = Field(description="検索結果")
    total: int = Field(description="総件数")
    has_next: bool = Field(description="次ページ有無")
    page_token: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": 1,
                            "slug": "dummy-funabashi-east",
                            "name": "ダミージム 船橋イースト",
                            "city": "funabashi",
                            "pref": "chiba",
                            "last_verified_at": "2025-09-01T12:34:56Z",
                            "score": 0.84,
                            "freshness_score": 0.93,
                            "richness_score": 0.68,
                        }
                    ],
                    "total": 2,
                    "has_next": False,
                    "page_token": None,
                }
            ]
        }
    )
