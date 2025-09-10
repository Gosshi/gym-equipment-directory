# app/services/gym_detail.py
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import gyms as repo
from app.services.score import ScoreBundle, compute_bundle


async def search_gyms(
    db: AsyncSession,
    pref: str | None = None,
    city: str | None = None,
    equipments: Sequence[str] | None = None,
    equipment_match: str = "any",
) -> tuple[list[dict], int]:
    """
    Return (items, total). items はページング前のジム要約 dict 配列。
    last_verified_at は datetime (or None) のまま返す（トークン化は呼び出し側）。
    """
    gyms_all = await repo.list_candidate_gyms(db, pref=pref, city=city)
    gym_ids_all = [g.id for g in gyms_all]

    # optional equipment filter
    equip_filter = list(equipments) if equipments else None

    # fetch gym-equipment rows (optionally filtered by equipment slugs)
    ge_rows = []
    if gym_ids_all:
        ge_rows = await repo.list_gym_equipments(db, gym_ids_all, equip_filter)

    # aggregate per-gym
    by_gym: dict[int, list[dict]] = {}
    last_verified_by_gym: dict[int, datetime | None] = {}
    richness_by_gym: dict[int, float] = {}

    for row in ge_rows:
        hi = {
            "equipment_slug": row.equipment_slug,
            "availability": row.availability.value
            if hasattr(row.availability, "value")
            else str(row.availability),
            "count": row.count,
            "max_weight_kg": row.max_weight_kg,
            "verification_status": row.verification_status.value
            if hasattr(row.verification_status, "value")
            else str(row.verification_status),
            "last_verified_at": row.last_verified_at,
        }
        by_gym.setdefault(row.gym_id, []).append(hi)

        # max(last_verified_at) per gym
        lv = last_verified_by_gym.get(row.gym_id)
        if lv is None or (row.last_verified_at and row.last_verified_at > lv):
            last_verified_by_gym[row.gym_id] = row.last_verified_at

        # richness scoring (router と同一ロジック)
        sc = richness_by_gym.get(row.gym_id, 0.0)
        avail = hi.get("availability")
        if str(avail) == "present":
            sc += 1.0
            cnt = hi.get("count") or 0
            sc += min(int(cnt), 5) * 0.1 if cnt else 0.0
            mw = hi.get("max_weight_kg") or 0
            sc += min(float(mw) / 60.0, 1.0) * 0.1 if mw else 0.0
        elif str(avail) == "unknown":
            sc += 0.3
        richness_by_gym[row.gym_id] = sc

    # determine allowed gyms for equipments filter (any/all)
    if equip_filter:
        requested = set(equip_filter)
        if equipment_match == "all":
            allowed_gym_ids = {
                gid
                for gid, rows in by_gym.items()
                if set(r["equipment_slug"] for r in rows) >= requested
            }
        else:
            # any
            allowed_gym_ids = set(by_gym.keys())
    else:
        allowed_gym_ids = set(gym_ids_all)

    # keep original order from gyms_all
    gyms = [g for g in gyms_all if g.id in allowed_gym_ids]

    # build items
    items: list[dict] = []
    for g in gyms:
        gym_lv = last_verified_by_gym.get(g.id) or getattr(g, "last_verified_at_cached", None)
        items.append(
            {
                "id": g.id,
                "slug": g.slug,
                "name": g.name,
                "city": g.city,
                "pref": g.pref,
                "last_verified_at": gym_lv,  # datetime のまま
                "score": richness_by_gym.get(g.id, 0.0),
                "freshness_score": None,  # 互換のため残す
                "richness_score": richness_by_gym.get(g.id, 0.0),
            }
        )

    return items, len(items)


async def get_gym_detail(db: AsyncSession, slug: str, include_score: bool = False) -> dict | None:
    """詳細 + 装備一覧。include_score=True で freshness/richness/score を付与。"""
    gym = await repo.get_gym_by_slug(db, slug)
    if not gym:
        return None

    ge_rows = await repo.list_gym_equipments(db, [gym.id])

    equipments = [
        {
            "equipment_slug": r.equipment_slug,
            "equipment_name": r.equipment_name,
            "category": r.category,
            "count": r.count,
            "max_weight_kg": r.max_weight_kg,
        }
        for r in ge_rows
    ]

    # updated_at: 装備の last_verified_at の最大値
    updated_at: datetime | None = None
    for r in ge_rows:
        if r.last_verified_at and (updated_at is None or r.last_verified_at > updated_at):
            updated_at = r.last_verified_at

    freshness_val: float | None = None
    richness_val: float | None = None
    score_val: float | None = None

    if include_score:
        num_equips = len(ge_rows)
        max_cnt = await repo.count_equips_grouped(db)
        gym_lv = getattr(gym, "last_verified_at_cached", None)
        bundle: ScoreBundle = compute_bundle(gym_lv, num_equips, int(max_cnt))
        freshness_val = float(bundle.freshness)
        richness_val = float(bundle.richness)
        score_val = float(bundle.score)

    return {
        "id": gym.id,
        "slug": gym.slug,
        "name": gym.name,
        "city": gym.city,
        "pref": gym.pref,
        "equipments": equipments,
        "updated_at": updated_at,  # ルーター側で dt_to_token 変換
        "freshness": freshness_val,
        "richness": richness_val,
        "score": score_val,
    }
