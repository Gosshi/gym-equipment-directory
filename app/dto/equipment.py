"""DTOs for equipment resources exposed via the public API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EquipmentMasterDTO(BaseModel):
    id: int = Field(description="設備ID")
    slug: str = Field(description="スラッグ（lower-case, kebab）")
    name: str = Field(description="表示名")
    category: str | None = Field(default=None, description="カテゴリ（任意）")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 12,
                "slug": "squat-rack",
                "name": "スクワットラック",
                "category": "free-weights",
            }
        },
    )
