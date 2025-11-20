"""Diff classification for normalized gym candidates.

目的:
    正規化済みの候補レコードを既存の Gym / GymCandidate と比較し、
    新規 / 更新 / 重複(duplicate) を分類する。初期版ではスタブ実装。

将来拡張:
    - Gym テーブルとの類似度 (名前 + 住所 + 設備セット) による重複検知
    - fuzzy マッチ (Levenshtein) や geohash 距離
    - 住所正規化による差分吸収

返却ポリシー:
    - new_ids: 承認対象 (status=new)
    - updated_ids: 承認対象 (既存候補との差分あり)
    - duplicate_ids: 承認除外 (duplicate_of_id 付与予定)

注意:
    DB I/O を伴うロジックは後続 PR で実装。現段階では空集合を返す。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: I001


@dataclass(slots=True)
class DiffSummary:
    new_ids: tuple[int, ...]
    updated_ids: tuple[int, ...]
    duplicate_ids: tuple[int, ...]

    def total(self) -> int:  # 小さな補助関数
        return len(self.new_ids) + len(self.updated_ids) + len(self.duplicate_ids)


async def classify_candidates(
    session: AsyncSession,
    *,
    source: str,
    candidate_ids: Sequence[int] | None = None,
) -> DiffSummary:
    """候補を分類して `DiffSummary` を返す (スタブ)。

    今は単純に渡された candidate_ids を new とみなす。
    将来的に Gym テーブル・他候補との比較をここに実装する。
    """
    ids = list(candidate_ids or [])
    return DiffSummary(new_ids=tuple(ids), updated_ids=tuple(), duplicate_ids=tuple())


__all__ = ["DiffSummary", "classify_candidates"]
