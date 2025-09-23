# app/schemas/gym_search.py
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

__all__ = ["GymSummary", "GymSearchResponse", "GymSearchQuery"]


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
    distance_km: float | None = Field(default=None, description="検索基準点からの距離（km）")


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
                            "distance_km": 1.23,
                        }
                    ],
                    "total": 2,
                    "has_next": False,
                    "page_token": None,
                }
            ]
        }
    )


class GymSearchQuery(BaseModel):
    """/gyms/search のクエリDTO（厳格バリデーション）。

    - 空文字は 400 扱い（HTTPException を発生）
    - 範囲外（per_page など）は 400 扱い
    - 許容値外（sort/equipment_match など）も 400 扱い
    """

    pref: str | None = Field(default=None, description="都道府県スラッグ（lower）")
    city: str | None = Field(default=None, description="市区町村スラッグ（lower）")
    lat: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="検索基準点の緯度（度）",
    )
    lng: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="検索基準点の経度（度）",
    )
    radius_km: float | None = Field(
        default=None,
        ge=0.0,
        description="検索半径（km）",
    )
    equipments: str | None = Field(
        default=None, description="設備スラッグのCSV（例: squat-rack,dumbbell）"
    )
    equipment_match: Literal["all", "any"] = Field(
        default="all", description="equipments の一致条件"
    )
    sort: Literal["freshness", "richness", "gym_name", "created_at", "score", "distance"] = Field(
        default="score", description="並び順"
    )
    per_page: int = Field(default=20, description="1ページ件数（1..50）")
    page_token: str | None = Field(default=None, description="Keyset 継続トークン")

    @field_validator("pref", "city")
    @classmethod
    def _check_slugish_optional(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            # 400で返したいのでHTTPExceptionを直接投げる
            raise HTTPException(status_code=400, detail="empty string is not allowed")
        # 許容されるスラッグ: 英小/数値/ハイフン
        for ch in s:
            if not (ch.islower() or ch.isdigit() or ch == "-"):
                raise HTTPException(status_code=400, detail="invalid slug")
        return s

    @field_validator("equipments")
    @classmethod
    def _check_equipments_csv(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v.strip():
            raise HTTPException(status_code=400, detail="equipments must not be empty")
        return v

    @field_validator("per_page")
    @classmethod
    def _check_per_page(cls, v: int) -> int:
        if not (1 <= int(v) <= 50):
            raise HTTPException(status_code=400, detail="per_page must be between 1 and 50")
        return int(v)

    # FastAPI で BaseModel をそのまま Query から受け取ると 422 になるため、
    # DTO生成時の ValidationError を 400 に変換する依存関数を提供する。
    @classmethod
    def as_query(
        cls,
        pref: Annotated[str | None, Query(description="都道府県スラッグ（lower）例: chiba")] = None,
        city: Annotated[
            str | None, Query(description="市区町村スラッグ（lower）例: funabashi")
        ] = None,
        lat: Annotated[
            float | None,
            Query(description="検索基準点の緯度（度）", ge=-90.0, le=90.0),
        ] = None,
        lng: Annotated[
            float | None,
            Query(description="検索基準点の経度（度）", ge=-180.0, le=180.0),
        ] = None,
        radius_km: Annotated[
            float | None,
            Query(description="検索半径（km）", ge=0.0),
        ] = None,
        equipments: Annotated[
            str | None,
            Query(description="設備スラッグCSV（例: squat-rack,dumbbell）"),
        ] = None,
        equipment_match: Annotated[
            Literal["all", "any"], Query(description="equipments の一致条件")
        ] = "all",
        sort: Annotated[
            Literal["freshness", "richness", "gym_name", "created_at", "score", "distance"],
            Query(description="並び順"),
        ] = "score",
        per_page: Annotated[int, Query(description="1ページ件数（1..50）", examples=[10])] = 20,
        page_token: Annotated[str | None, Query(description="Keyset 継続トークン")] = None,
    ) -> GymSearchQuery:
        try:
            return cls.model_validate(
                {
                    "pref": pref,
                    "city": city,
                    "lat": lat,
                    "lng": lng,
                    "radius_km": radius_km,
                    "equipments": equipments,
                    "equipment_match": equipment_match,
                    "sort": sort,
                    "per_page": per_page,
                    "page_token": page_token,
                }
            )
        except ValidationError as e:  # noqa: F841 - 具体内容は隠蔽
            # 仕様として 400 を返す
            raise HTTPException(status_code=400, detail="invalid parameter")
