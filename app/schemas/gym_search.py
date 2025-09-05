# app/schemas/gym_search.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

__all__ = ["GymSummary", "GymSearchResponse"]


class GymSummary(BaseModel):
    """
    検索結果のジム要約。
    last_verified_at_cached は ISO8601 文字列（例: "2025-09-05T12:34:56+00:00"）
    """
    id: int = Field(..., description="Gym ID")
    name: str = Field(..., description="ジム名")
    last_verified_at_cached: Optional[str] = Field(
        None,
        description="最終確認日時（ISO8601, null 許容）",
        examples=["2025-09-05T12:34:56+00:00", None],
    )


class GymSearchResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "items": [
                {
                    "id": 101,
                    "name": "Gold Gym Funabashi",
                    "last_verified_at_cached": "2025-09-01T12:34:56Z"
                },
                {
                    "id": 205,
                    "name": "Anytime Chiba",
                    "last_verified_at_cached": None
                }
            ],
            "page": 1,
            "per_page": 20,
            "total": 123,
            "has_next": True
        }
    })
    items: List[GymSummary] = Field(..., description="検索結果（サマリー）")
    page: int = Field(1, ge=1, description="ページ番号（1始まり）")
    per_page: int = Field(20, ge=1, le=50, description="1ページ件数（最大50）")
    total: int = Field(..., description="総件数")
    has_next: bool = Field(..., description="次ページが存在するか")