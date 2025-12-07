from __future__ import annotations

import base64
import json
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, constr


class ReportType(str, Enum):
    wrong_info = "wrong_info"
    closed = "closed"
    duplicate = "duplicate"
    abuse = "abuse"
    other = "other"


class ReportCreateRequest(BaseModel):
    type: ReportType = Field(description="報告種別")
    message: constr(min_length=5) = Field(description="詳細メッセージ（5文字以上）")
    email: EmailStr | None = Field(default=None, description="連絡先メール（任意）")
    source_url: str | None = Field(default=None, description="参考URL（任意）")


class ReportAdminItem(BaseModel):
    id: int
    gym_id: int
    gym_slug: str
    type: ReportType
    message: str
    email: str | None
    source_url: str | None
    status: str
    created_at: str


class ReportAdminListResponse(BaseModel):
    items: list[ReportAdminItem]
    next_cursor: str | None = None


def encode_cursor(dt: datetime, rid: int) -> str:
    payload: dict[str, Any] = {"k": [dt.isoformat(), int(rid)]}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(token: str) -> tuple[datetime, int]:
    try:
        data = json.loads(base64.urlsafe_b64decode(token.encode()).decode())
        k = data.get("k")
        assert isinstance(k, list) and len(k) == 2
        return (datetime.fromisoformat(k[0]), int(k[1]))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid cursor") from exc
