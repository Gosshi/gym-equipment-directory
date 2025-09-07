# app/schemas/gym_detail.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class EquipmentRow(BaseModel):
    equipment_slug: str
    equipment_name: str
    category: Optional[str] = None
    availability: str
    count: Optional[int] = None
    max_weight_kg: Optional[int] = None
    verification_status: str
    last_verified_at: Optional[datetime] = None


class SourceRow(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None


class GymBasic(BaseModel):
    id: int
    name: str
    slug: str
    pref: Optional[str] = None
    city: Optional[str] = None


class GymEquipmentLine(BaseModel):
    equipment_slug: str = Field(description="設備スラッグ")
    equipment_name: str = Field(description="設備名")
    count: Optional[int] = Field(default=None, description="台数（任意）")
    max_weight_kg: Optional[int] = Field(default=None, description="最大重量（任意）")


class GymDetailResponse(BaseModel):
    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    name: str = Field(description="名称")
    city: str = Field(description="市区町村スラッグ")
    pref: str = Field(description="都道府県スラッグ")
    equipments: List[GymEquipmentLine] = Field(description="設備一覧（JOIN済み）")
    updated_at: Optional[str] = Field(
        default=None, description="設備情報の最終更新（= last_verified_at の最大）"
    )

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
