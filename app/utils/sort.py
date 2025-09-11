# app/utils/sort.py
from __future__ import annotations

from typing import Literal

__all__ = ["SortKey", "resolve_sort_key"]

SortKey = Literal["freshness", "richness", "score", "gym_name", "created_at"]


def resolve_sort_key(s: str | None) -> SortKey:
    """
    受け取った文字列を内部ソートキーに正規化する。
    未知値や None は 'freshness' にフォールバック。
    """
    if not s:
        return "freshness"
    k = s.lower()

    if k in ("freshness", "recent", "updated"):
        return "freshness"
    if k in ("richness", "score", "rank"):
        # 内部では 'richness' と 'score' を同義で扱う
        return "richness"
    if k in ("gym_name", "name", "alpha"):
        return "gym_name"
    if k in ("created_at", "created"):
        return "created_at"

    return "freshness"
