# app/schemas/gym_detail.py
from datetime import datetime

from pydantic import BaseModel, Field


class EquipmentRow(BaseModel):
    equipment_slug: str
    equipment_name: str
    category: str | None = None
    availability: str
    count: int | None = None
    max_weight_kg: int | None = None
    verification_status: str
    last_verified_at: datetime | None = None


class SourceRow(BaseModel):
    name: str | None = None
    url: str | None = None


class GymBasic(BaseModel):
    id: int
    name: str
    slug: str
    pref: str | None = None
    city: str | None = None


class GymEquipmentLine(BaseModel):
    equipment_slug: str = Field(description="設備スラッグ")
    equipment_name: str = Field(description="設備名")
    count: int | None = Field(default=None, description="台数（任意）")
    max_weight_kg: int | None = Field(default=None, description="最大重量（任意）")


class GymDetailResponse(BaseModel):
    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    name: str = Field(description="名称")
    city: str = Field(description="市区町村スラッグ")
    pref: str = Field(description="都道府県スラッグ")
    equipments: list[GymEquipmentLine] = Field(description="設備一覧（JOIN済み）")
    updated_at: str | None = Field(
        default=None, description="設備情報の最終更新（= last_verified_at の最大）"
    )
    # include=score のときだけ埋まるオプショナル
    freshness: float | None = Field(default=None, ge=0.0, le=1.0, description="0..1")
    richness: float | None = Field(default=None, ge=0.0, le=1.0, description="0..1")
    score: float | None = Field(default=None, ge=0.0, le=1.0, description="0..1")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "slug": "awesome-gym",
                    "name": "Awesome Gym",
                    "city": "funabashi",
                    "pref": "chiba",
                    "equipments": [
                        {
                            "equipment_slug": "squat-rack",
                            "equipment_name": "スクワットラック",
                            "count": 2,
                            "max_weight_kg": 180,
                        },
                        {
                            "equipment_slug": "dumbbell",
                            "equipment_name": "ダンベル",
                            "count": 1,
                            "max_weight_kg": 50,
                        },
                    ],
                    "updated_at": "2025-09-01T12:34:56Z",
                }
            ]
        }
    }
