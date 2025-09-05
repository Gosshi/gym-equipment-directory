# app/schemas/common.py
from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="エラーメッセージ")
