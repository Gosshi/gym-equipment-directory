# app/schemas.py
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime

# --- 共通 ---

class GymBasic(BaseModel):
    id: int = Field(..., description="ジムID")
    slug: str = Field(..., description="ジムのスラッグ（URL識別子）")
    name: str = Field(..., description="ジム名")
    chain_name: Optional[str] = Field(None, description="チェーン名スラッグ")
    address: Optional[str] = Field(None, description="住所スラッグ")
    pref: Optional[str] = Field(None, description="都道府県スラッグ")
    city: Optional[str] = Field(None, description="市区町村スラッグ")

    model_config = {"from_attributes": True}

class EquipmentHighlight(BaseModel):
    equipment_slug: str = Field(..., description="設備スラッグ（例: squat-rack）")
    availability: str = Field(..., description="present/absent/unknown")
    count: Optional[int] = Field(None, description="台数などの数量")
    max_weight_kg: Optional[int] = Field(None, description="最大重量(kg) 例: ダンベル最大重量")
    verification_status: str = Field(..., description="verified/unverified など")
    last_verified_at: Optional[datetime] = Field(None, description="設備情報の最終確認時刻")

class SearchItem(BaseModel):
    gym: GymBasic = Field(..., description="ジム基本情報")
    highlights: List[EquipmentHighlight] = Field(default_factory=list, description="設備ハイライト")
    last_verified_at: Optional[datetime] = Field(None, description="ジムに紐づく設備の最終確認（最大）")
    score: float = Field(0.0, description="設備充実度の簡易スコア")

class SearchResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
         "example": {
             "items": [
                 {
                     "gym": {
                         "id": 101,
                         "slug": "gold-gym-funabashi",
                         "name": "Gold Gym Funabashi",
                         "pref": "chiba",
                         "city": "funabashi"
                     },
                     "highlights": [
                         {
                             "equipment_slug": "squat-rack",
                             "availability": "present",
                             "count": 3,
                             "max_weight_kg": 180,
                             "verification_status": "verified",
                             "last_verified_at": "2025-09-01T12:34:56Z"
                         }
                     ],
                     "last_verified_at": "2025-09-01T12:34:56Z",
                     "score": 1.3
                 }
             ],
             "page": 1,
             "per_page": 20,
             "total": 123
         }
     })
    items: List[SearchItem] = Field(..., description="検索結果")
    page: int = Field(1, ge=1, le=50, description="ページ番号（1始まり）")
    per_page: int = Field(20, ge=1, le=50, description="1ページ件数")
    total: int = Field(..., description="総件数")

class EquipmentRow(BaseModel):
    equipment_slug: str
    equipment_name: str
    category: str
    availability: str
    count: Optional[int] = None
    max_weight_kg: Optional[int] = None
    verification_status: str
    last_verified_at: Optional[datetime] = None

class SourceRow(BaseModel):
    type: str
    title: Optional[str] = None
    url: Optional[str] = None
    captured_at: Optional[datetime] = None

class GymDetailResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "gym": {"id": 101, "slug": "gold-gym-funabashi", "name": "Gold Gym Funabashi", "pref": "chiba", "city": "funabashi"},
            "equipments": [
                {"equipment_slug": "dumbbell", "equipment_name": "Dumbbell", "category": "free-weights",
                 "availability": "present", "count": 20, "max_weight_kg": 50,
                 "verification_status": "verified", "last_verified_at": "2025-09-01T12:34:56Z"}
            ],
            "sources": [],
            "updated_at": "2025-09-01T12:34:56Z"
        }
    })
    gym: GymBasic
    equipments: List[EquipmentRow]
    sources: List[SourceRow]
    updated_at: Optional[datetime] = None

# app/schemas.py に追加（任意）
class ErrorResponse(BaseModel):
    detail: str = Field(..., description="エラーメッセージ")
