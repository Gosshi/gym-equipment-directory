# app/schemas/meta.py
from pydantic import BaseModel, Field, computed_field


class MetaOption(BaseModel):
    key: str = Field(..., description="安定キー", json_schema_extra={"example": "chiba"})
    label: str = Field(..., description="表示ラベル", json_schema_extra={"example": "千葉"})
    count: int | None = Field(
        default=None, description="関連件数（pref/city のみ）", json_schema_extra={"example": 128}
    )


class PrefOption(MetaOption):
    @computed_field(return_type=str)
    def pref(self) -> str:
        """旧互換の pref キーを残す。"""

        return self.key


class CityOption(MetaOption):
    @computed_field(return_type=str)
    def city(self) -> str:
        """旧互換の city キーを残す。"""

        return self.key


class CategoryOption(MetaOption):
    @computed_field(return_type=str)
    def category(self) -> str:
        """旧互換の category キーを残す。"""

        return self.key


class EquipmentOption(BaseModel):
    key: str = Field(
        ..., description="設備スラッグ", json_schema_extra={"example": "smith-machine"}
    )
    label: str = Field(..., description="表示名", json_schema_extra={"example": "スミスマシン"})
    category: str | None = Field(
        default=None, description="設備カテゴリ", json_schema_extra={"example": "strength"}
    )

    @computed_field(return_type=str)
    def slug(self) -> str:
        """旧互換 slug を返す。"""

        return self.key

    @computed_field(return_type=str)
    def name(self) -> str:
        """旧互換 name を返す。"""

        return self.label
