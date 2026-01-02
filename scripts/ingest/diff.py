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
    reviewing_ids: tuple[int, ...]  # 既存Gymと一致し手動レビューが必要な候補

    def total(self) -> int:  # 小さな補助関数
        return (
            len(self.new_ids)
            + len(self.updated_ids)
            + len(self.duplicate_ids)
            + len(self.reviewing_ids)
        )


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


async def classify_candidates(
    session: AsyncSession,
    *,
    source: str,
    candidate_ids: Sequence[int] | None = None,
) -> DiffSummary:
    """候補を分類して `DiffSummary` を返す。

    1. URL完全一致 -> reviewing (既存Gymとの差分レビュー用)
    2. 住所一致かつ名前類似度高 -> reviewing
    3. それ以外 -> new
    """
    if not candidate_ids:
        return DiffSummary(new_ids=(), updated_ids=(), duplicate_ids=(), reviewing_ids=())

    ids = list(candidate_ids)
    new_ids: list[int] = []
    updated_ids: list[int] = []  # parsed_json backfill用
    duplicate_ids: list[int] = []  # 将来の完全重複検出用（現在未使用）
    reviewing_ids: list[int] = []  # 既存Gymと一致し手動レビューが必要

    # Load candidates with source_page to access URL
    stmt = (
        select(GymCandidate)
        .options(joinedload(GymCandidate.source_page))
        .where(GymCandidate.id.in_(ids))
    )
    result = await session.execute(stmt)
    candidates = result.scalars().all()

    for candidate in candidates:
        matched_gym: Gym | None = None
        url = candidate.source_page.url

        # 1. URL Match in Gym
        stmt_url = (
            select(Gym).where(or_(Gym.official_url == url, Gym.affiliate_url == url)).limit(1)
        )
        existing_gym = (await session.execute(stmt_url)).scalar_one_or_none()
        if existing_gym:
            matched_gym = existing_gym

        # 2. Address & Name Match (if no URL match)
        if not matched_gym and candidate.address_raw:
            stmt_addr = select(Gym).where(Gym.address == candidate.address_raw)
            gyms_with_addr = (await session.execute(stmt_addr)).scalars().all()

            for gym in gyms_with_addr:
                if _similarity(gym.name, candidate.name_raw) > 0.8:
                    matched_gym = gym
                    break

        # 3. Classify based on match result
        if matched_gym:
            # Mark as reviewing and record linked_gym_id
            reviewing_ids.append(candidate.id)
            candidate.status = CandidateStatus.reviewing

            # Add linked_gym_id to parsed_json for admin UI
            if candidate.parsed_json is None:
                candidate.parsed_json = {}
            # Create a new dict to trigger SQLAlchemy change detection
            updated_json = dict(candidate.parsed_json)
            updated_json["linked_gym_id"] = matched_gym.id
            updated_json["linked_gym_slug"] = matched_gym.slug
            candidate.parsed_json = updated_json
        else:
            new_ids.append(candidate.id)

    await session.commit()

    return DiffSummary(
        new_ids=tuple(new_ids),
        updated_ids=tuple(updated_ids),
        duplicate_ids=tuple(duplicate_ids),
        reviewing_ids=tuple(reviewing_ids),
    )


__all__ = ["DiffSummary", "classify_candidates"]
