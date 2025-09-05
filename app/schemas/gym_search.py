# app/schemas/gym_search.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

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
    """
    /gyms/search のレスポンス本体。
    items は GymSummary の配列、ページング情報と合計件数を含む。
    """
    items: List[GymSummary] = Field(..., description="検索結果リスト")
    page: int = Field(..., ge=1, description="現在ページ（1始まり）", examples=[1])
    per_page: int = Field(..., ge=1, le=100, description="1ページ件数（最大100）", examples=[20])
    total: int = Field(..., ge=0, description="総件数", examples=[123])
    has_next: bool = Field(..., description="次ページが存在するか", examples=[True])
