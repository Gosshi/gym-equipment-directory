from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class GymSummaryDTO(TypedDict, total=False):
    id: int
    slug: str
    name: str
    pref: str
    city: str
    last_verified_at: datetime | None
    score: float


class ServiceResult(TypedDict):
    items: list[GymSummaryDTO]
    total: int
    has_next: bool
    page_token: str | None
