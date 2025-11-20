# app/schemas/meta.py
from pydantic import BaseModel, Field, computed_field


class MetaOption(BaseModel):
    """共通メタオプション。

    後方互換ポリシー:
    - 旧フロントは `pref` / `city` / `category` / `slug` / `name` などのフィールド名を参照していた。
    - 新スキーマでは `key` / `label` を正規化し、computed_field で旧名称をミラーリング。
    - API レスポンスで余分なフィールドを残すコストは軽微（文字列複製のみ）かつ移行容易性を優先。
    - 完全移行後（十分な周知後）に computed_field の削除を検討できるようコメントを残す。
    """

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
    """設備オプション。

    後方互換:
    - 旧: slug/name
    - 新: key/label
    - 利用側が段階的に切り替え可能なよう両方 exposed。
    """

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
