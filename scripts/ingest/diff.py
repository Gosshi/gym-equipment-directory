from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.gym import Gym
from app.models.gym_candidate import CandidateStatus, GymCandidate


@dataclass
class DiffSummary:
    new_ids: tuple[int, ...]
    updated_ids: tuple[int, ...]
    duplicate_ids: tuple[int, ...]

    def total(self) -> int:  # 小さな補助関数
        return len(self.new_ids) + len(self.updated_ids) + len(self.duplicate_ids)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


async def classify_candidates(
    session: AsyncSession,
    *,
    source: str,
    candidate_ids: Sequence[int] | None = None,
) -> DiffSummary:
    """候補を分類して `DiffSummary` を返す。

    1. URL完全一致 -> duplicate
    2. 住所一致かつ名前類似度高 -> duplicate
    3. それ以外 -> new
    """
    if not candidate_ids:
        return DiffSummary(new_ids=(), updated_ids=(), duplicate_ids=())

    ids = list(candidate_ids)
    new_ids: list[int] = []
    updated_ids: list[int] = []  # 今回は未使用
    duplicate_ids: list[int] = []

    # Load candidates with source_page to access URL
    stmt = (
        select(GymCandidate)
        .options(joinedload(GymCandidate.source_page))
        .where(GymCandidate.id.in_(ids))
    )
    result = await session.execute(stmt)
    candidates = result.scalars().all()

    for candidate in candidates:
        is_dup = False
        url = candidate.source_page.url

        # 1. URL Match in Gym
        stmt_url = (
            select(Gym.id).where(or_(Gym.official_url == url, Gym.affiliate_url == url)).limit(1)
        )
        if (await session.execute(stmt_url)).scalar():
            duplicate_ids.append(candidate.id)
            candidate.status = CandidateStatus.rejected
            continue

        # 2. Address & Name Match
        if candidate.address_raw:
            # 住所が完全一致するジムを検索
            # Note: 住所の正規化が不十分だとヒットしない可能性があるが、
            # パイプライン側で正規化されていることを期待する。
            stmt_addr = select(Gym).where(Gym.address == candidate.address_raw)
            gyms_with_addr = (await session.execute(stmt_addr)).scalars().all()

            for gym in gyms_with_addr:
                # 名前が類似していれば重複とみなす (閾値 0.8)
                if _similarity(gym.name, candidate.name_raw) > 0.8:
                    duplicate_ids.append(candidate.id)
                    is_dup = True
                    break

        if is_dup:
            candidate.status = CandidateStatus.rejected
            # We use 'rejected' for duplicates as 'duplicate' status is not in DB Enum.
            continue

        new_ids.append(candidate.id)

    await session.commit()

    return DiffSummary(
        new_ids=tuple(new_ids),
        updated_ids=tuple(updated_ids),
        duplicate_ids=tuple(duplicate_ids),
    )


__all__ = ["DiffSummary", "classify_candidates"]
