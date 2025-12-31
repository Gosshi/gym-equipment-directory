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
    model_config = {"from_attributes": True}  # ★ v2 で必須
    id: int = Field(description="ジムID")
    slug: str = Field(description="ジムスラッグ")
    canonical_id: str = Field(description="ジムの canonical UUID")
    name: str = Field(description="名称")
    city: str = Field(description="市区町村スラッグ")
    pref: str = Field(description="都道府県スラッグ")
    official_url: str | None = Field(default=None, description="公式サイトURL（任意）")
    opening_hours: str | None = Field(default=None, description="営業時間（任意）")
    fees: str | None = Field(default=None, description="料金情報（任意）")

    # Category and category-specific fields
    category: str | None = Field(
        default=None, description="施設カテゴリ (legacy): gym, pool, court, hall, field, etc."
    )
    categories: list[str] = Field(
        default_factory=list, description="施設カテゴリ配列 (複合施設対応)"
    )
    pool_lanes: int | None = Field(default=None, description="プールレーン数")
    pool_length_m: int | None = Field(default=None, description="プール長さ（メートル）")
    pool_heated: bool | None = Field(default=None, description="温水プールか")
    court_type: str | None = Field(default=None, description="コートタイプ")
    facility_meta: dict | None = Field(
        default=None, description="メタデータ（料金・営業時間詳細等）"
    )
    court_count: int | None = Field(default=None, description="コート面数")
    court_surface: str | None = Field(default=None, description="コート表面")
    court_lighting: bool | None = Field(default=None, description="照明設備の有無")
    hall_sports: list[str] = Field(default_factory=list, description="対応スポーツ一覧")
    hall_area_sqm: float | None = Field(default=None, description="面積（平方メートル）")
    field_type: str | None = Field(default=None, description="グラウンドタイプ")
    field_count: int | None = Field(default=None, description="グラウンド面数")
    field_lighting: bool | None = Field(default=None, description="照明設備の有無")

    equipments: list[GymEquipmentLine] = Field(description="設備一覧（JOIN済み）")

    # 追加: 関連する gym_equipments の要約（N+1 回避して取得）
    class GymEquipmentSummary(BaseModel):
        slug: str = Field(description="設備スラッグ")
        name: str = Field(description="設備名")
        availability: str = Field(description="present/absent/unknown")
        verification_status: str = Field(description="検証状況")
        last_verified_at: datetime | None = Field(default=None, description="最終確認時刻")
        source: str | None = Field(default=None, description="情報ソース（URL 等）")

    gym_equipments: list[GymEquipmentSummary] = Field(
        default_factory=list,
        description="設備ごとの在/無・検証状況などの詳細サマリ",
    )

    # 追加: 参照用ジム画像（アップロードは不要、参照のみ）
    class GymImage(BaseModel):
        url: str = Field(description="画像URL")
        source: str | None = Field(default=None, description="出典（任意）")
        verified: bool = Field(default=False, description="検証済みか")
        created_at: datetime | None = Field(default=None, description="登録日時")

    images: list[GymImage] = Field(default_factory=list, description="関連画像の一覧")
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
                    "canonical_id": "11111111-2222-3333-4444-555555555555",
                    "name": "Awesome Gym",
                    "city": "funabashi",
                    "pref": "chiba",
                    "official_url": "https://awesome-gym.example.com",
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
                    "gym_equipments": [
                        {
                            "slug": "squat-rack",
                            "name": "スクワットラック",
                            "availability": "present",
                            "verification_status": "verified",
                            "last_verified_at": "2025-09-01T12:34:56Z",
                            "source": "https://example.com/source",
                        }
                    ],
                    "updated_at": "2025-09-01T12:34:56Z",
                    "images": [
                        {
                            "url": "https://example.com/image.jpg",
                            "source": "instagram",
                            "verified": False,
                            "created_at": "2025-09-01T12:34:56Z",
                        }
                    ],
                }
            ]
        }
    }
