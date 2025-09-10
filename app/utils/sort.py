# app/utils/sort.py
from __future__ import annotations

from typing import Literal

SortKey = Literal["freshness", "richness", "score", "gym_name", "created_at"]


def resolve_sort_key(s: str | None) -> SortKey:
    if not s:
        return "freshness"
    s = s.lower()
    if s in ("freshness", "recent", "updated"):
        return "freshness"
    if s in ("richness", "score", "rank"):
        return "richness"
    if s in ("gym_name", "name", "alpha"):
        return "gym_name"
    if s in ("created_at", "created"):
        return "created_at"
    return "freshness"
