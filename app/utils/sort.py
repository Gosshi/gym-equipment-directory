# app/utils/sort.py
from __future__ import annotations

from typing import Literal

__all__ = ["SortKey", "resolve_sort_key"]

SortKey = Literal["freshness", "richness", "score", "gym_name", "created_at", "distance"]


def resolve_sort_key(s: str | None) -> SortKey:
    """Normalize a user-provided sort key.

    Unknown / None fall back to ``freshness``. Preserve ``score`` distinctly so
    later we can implement weighted freshness/richness without ambiguity.
    """
    if not s:
        return "freshness"
    k = s.lower().strip()
    if k in {"freshness", "recent", "updated"}:
        return "freshness"
    if k in {"richness", "rank"}:
        return "richness"
    if k in {"score"}:
        return "score"
    if k in {"gym_name", "name", "alpha"}:
        return "gym_name"
    if k in {"created_at", "created"}:
        return "created_at"
    if k in {"distance", "nearby"}:
        return "distance"
    return "freshness"
