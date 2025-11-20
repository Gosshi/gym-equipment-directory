# app/utils/sort.py
from __future__ import annotations

from typing import Literal

__all__ = ["SortKey", "resolve_sort_key"]

SortKey = Literal["freshness", "richness", "score", "gym_name", "created_at", "distance"]


def resolve_sort_key(s: str | None) -> SortKey:
    """ユーザー入力のソートキー文字列を内部的な正規化キーへ変換する。

    振る舞い:
    - 未指定 / 空文字 / 未知値 → `freshness` にフォールバック。
    - `richness` と `score` を区別（score は将来: freshness/richness の重み付き合算に使用）。
    - 距離ソート: `distance` / `nearby` → `distance` に正規化（未実装時は fallback か 422）。

    将来拡張:
    - `score` 実装時に重み（例: freshness=0.6, richness=0.4）を service 層へ追加。
    - `distance` Keyset ページング対応時は複合キー（distance,id）を token 化。
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
