"""DTOs for gym detail responses and related nested resources."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class GymBasicDTO(BaseModel):
    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    canonical_id: str = Field(description="ジムの canonical UUID")
    name: str = Field(description="ジム名")
    pref: str | None = Field(default=None, description="都道府県スラッグ")
    city: str | None = Field(default=None, description="市区町村スラッグ")

    model_config = ConfigDict(from_attributes=True)


class GymEquipmentLineDTO(BaseModel):
    equipment_slug: str = Field(description="設備スラッグ")
    equipment_name: str = Field(description="設備名")
    category: str | None = Field(default=None, description="設備カテゴリ（任意）")
    count: int | None = Field(default=None, description="台数（任意）")
    max_weight_kg: int | None = Field(default=None, description="最大重量（任意）")

    @computed_field(return_type=str)
    def name(self) -> str:
        """旧API互換用の name フィールド。"""

        return self.equipment_name

    @computed_field(return_type=str)
    def slug(self) -> str:
        """旧API互換用の slug フィールド。"""

        return self.equipment_slug

    @computed_field(return_type=str | None)
    def description(self) -> str | None:
        """台数や最大重量をまとめた説明文を生成する。"""

        parts: list[str] = []
        if self.count is not None:
            parts.append(f"{self.count}台")
        if self.max_weight_kg is not None:
            parts.append(f"最大{self.max_weight_kg}kg")
        return " / ".join(parts) if parts else None


class GymEquipmentSummaryDTO(BaseModel):
    slug: str = Field(description="設備スラッグ")
    name: str = Field(description="設備名")
    category: str | None = Field(default=None, description="設備カテゴリ（任意）")
    count: int | None = Field(default=None, description="台数（任意）")
    max_weight_kg: int | None = Field(default=None, description="最大重量（任意）")
    availability: str = Field(description="present/absent/unknown")
    verification_status: str = Field(description="検証状況")
    last_verified_at: datetime | None = Field(default=None, description="最終確認時刻")
    source: str | None = Field(default=None, description="情報ソース（URL 等）")


class GymImageDTO(BaseModel):
    url: str = Field(description="画像URL")
    source: str | None = Field(default=None, description="出典（任意）")
    verified: bool = Field(default=False, description="検証済みか")
    created_at: datetime | None = Field(default=None, description="登録日時")


class GymDetailDTO(BaseModel):
    """Full detail payload for a gym."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    canonical_id: str = Field(description="ジムの canonical UUID")
    name: str = Field(description="名称")
    city: str = Field(description="市区町村スラッグ")
    pref: str = Field(description="都道府県スラッグ")
    equipments: list[GymEquipmentLineDTO] = Field(description="設備一覧（JOIN済み）")
    gym_equipments: list[GymEquipmentSummaryDTO] = Field(
        default_factory=list, description="設備ごとの在/無・検証状況などの詳細サマリ"
    )
    images: list[GymImageDTO] = Field(default_factory=list, description="関連画像の一覧")
    updated_at: str | None = Field(
        default=None, description="設備情報の最終更新（= last_verified_at の最大）"
    )
    freshness: float | None = Field(default=None, ge=0.0, le=1.0, description="0..1")
    richness: float | None = Field(default=None, ge=0.0, le=1.0, description="0..1")
    score: float | None = Field(default=None, ge=0.0, le=1.0, description="0..1")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "slug": "awesome-gym",
                    "canonical_id": "11111111-2222-3333-4444-555555555555",
                    "name": "Awesome Gym",
                    "city": "funabashi",
                    "pref": "chiba",
                    "equipments": [
                        {
                            "equipment_slug": "squat-rack",
                            "equipment_name": "スクワットラック",
                            "category": "strength",
                            "count": 2,
                            "max_weight_kg": 180,
                        }
                    ],
                    "gym_equipments": [
                        {
                            "slug": "squat-rack",
                            "name": "スクワットラック",
                            "category": "strength",
                            "count": 2,
                            "max_weight_kg": 180,
                            "availability": "present",
                            "verification_status": "verified",
                            "last_verified_at": "2025-09-01T12:34:56Z",
                            "source": "https://example.com/source",
                        }
                    ],
                    "images": [
                        {
                            "url": "https://example.com/image.jpg",
                            "source": "instagram",
                            "verified": False,
                            "created_at": "2025-09-01T12:34:56Z",
                        }
                    ],
                    "updated_at": "2025-09-01T12:34:56Z",
                    "freshness": 0.9,
                    "richness": 0.7,
                    "score": 0.82,
                }
            ]
        }
    )

    @computed_field(return_type=list[GymEquipmentLineDTO])
    def equipment_details(self) -> list[GymEquipmentLineDTO]:
        """旧API互換のため equipment_details を提供する。"""

        return self.equipments
