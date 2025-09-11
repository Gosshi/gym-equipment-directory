# app/schemas/common.py
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(description="エラーメッセージ")

    model_config = {"json_schema_extra": {"examples": [{"detail": "Not Found"}]}}


class OkResponse(BaseModel):
    ok: bool = Field(description="成功可否（true 固定）")

    model_config = {"json_schema_extra": {"examples": [{"ok": True}]}}
