# app/services/gym_search.py
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto import GymSearchPageDTO, GymSummaryDTO
from app.dto.mappers import map_gym_to_summary
from app.models import Equipment, GymEquipment
from app.repositories.gym_repository import GymRepository
from app.utils.paging import build_next_offset_token, parse_offset_token
from app.utils.sort import SortKey, resolve_sort_key


async def search_gyms(
    db: AsyncSession,
    *,
    pref: str | None,
    city: str | None,
    equipments: list[str] | None,
    equipment_match: str,  # "any" | "all"
    sort: str,
    page_token: str | None,
    page: int,
    per_page: int,
) -> GymSearchPageDTO:
    """
    既存挙動に合わせた検索サービス。
      - pref/city: SQL で絞り込み
      - equipments: any/all 判定
      - freshness: Gym.last_verified_at_cached を優先、無ければ Equipment 集約最大
      - page_token: offset 整数互換
      - total: フィルタ後（ソート・ページング前）の総件数
    """
    # 0) sort 正規化
    sort_key: SortKey = resolve_sort_key(sort)

    # 1) 候補ジム取得（Repository 経由）
    repo = GymRepository(db)
    gyms = await repo.list_by_pref_city(pref=pref, city=city)

    items_all: list[dict[str, Any]] = [
        {
            "gym": g,
            "last_verified_at": getattr(g, "last_verified_at_cached", None),
            "score": 0.0,
        }
        for g in gyms
    ]
    gym_ids_all = [int(getattr(it["gym"], "id", 0)) for it in items_all]

    # 2) Equipment 行取得
    ge_rows = []
    if gym_ids_all:
        geq = (
            select(
                GymEquipment.gym_id,
                Equipment.slug.label("equipment_slug"),
                Equipment.name.label("equipment_name"),
                Equipment.category,
                GymEquipment.availability,
                GymEquipment.count,
                GymEquipment.max_weight_kg,
                GymEquipment.verification_status,
                GymEquipment.last_verified_at,
            )
            .join(Equipment, Equipment.id == GymEquipment.equipment_id)
            .where(GymEquipment.gym_id.in_(gym_ids_all))
        )
        if equipments:
            geq = geq.where(Equipment.slug.in_(equipments))
        ge_rows = (await db.execute(geq)).all()

    # 3) 集計
    by_gym: dict[int, list[dict]] = {}
    last_verified_by_gym: dict[int, datetime | None] = {}
    richness_by_gym: dict[int, float] = {}

    for row in ge_rows:
        # 検証日時（最大）
        prev = last_verified_by_gym.get(row.gym_id)
        if prev is None or (row.last_verified_at and row.last_verified_at > prev):
            last_verified_by_gym[row.gym_id] = row.last_verified_at

        # richness
        sc = richness_by_gym.get(row.gym_id, 0.0)
        avail_val = getattr(row.availability, "value", str(row.availability))
        if str(avail_val) == "present":
            sc += 1.0
            cnt = row.count or 0
            sc += (min(int(cnt), 5) * 0.1) if cnt else 0.0
            mw = row.max_weight_kg or 0.0
            sc += (min(float(mw) / 60.0, 1.0) * 0.1) if mw else 0.0
        elif str(avail_val) == "unknown":
            sc += 0.3
        richness_by_gym[row.gym_id] = sc

        by_gym.setdefault(row.gym_id, []).append({"equipment_slug": row.equipment_slug})

    # 4) any/all 判定
    if equipments:
        requested = set(equipments)
        if equipment_match == "all":
            allowed_gym_ids = {
                gid
                for gid, rows in by_gym.items()
                if set(r["equipment_slug"] for r in rows) >= requested
            }
        else:
            allowed_gym_ids = set(by_gym.keys())
    else:
        allowed_gym_ids = set(gym_ids_all)

    # 5) 反映
    filtered: list[GymSummaryDTO] = []
    for it in items_all:
        gid = int(getattr(it["gym"], "id", 0))
        if gid not in allowed_gym_ids:
            continue
        it["last_verified_at"] = it.get("last_verified_at") or last_verified_by_gym.get(gid)
        it["score"] = float(richness_by_gym.get(gid, 0.0))
        filtered.append(it)

    # 6) ソート
    if sort_key == "freshness":
        filtered.sort(
            key=lambda i: (i.get("last_verified_at") is None, i.get("last_verified_at")),
            reverse=True,
        )
    elif sort_key in ("richness", "score"):
        filtered.sort(key=lambda i: i.get("score", 0.0), reverse=True)
    elif sort_key == "gym_name":
        filtered.sort(key=lambda i: getattr(i["gym"], "name", "") or "")
    elif sort_key == "created_at":
        created_map = await _created_at_map(db)
        filtered.sort(key=lambda i: created_map.get(int(getattr(i["gym"], "id", 0))) or 0)

    # 7) ページング
    pagable = (
        [it for it in filtered if it.get("last_verified_at") is not None]
        if sort_key == "freshness"
        else filtered
    )

    total_all = len(filtered)
    if total_all == 0:
        return GymSearchPageDTO(items=[], total=0, has_next=False, page_token=None)

    offset = parse_offset_token(page_token, page=page, per_page=per_page)
    slice_ = pagable[offset : offset + per_page]
    next_token = build_next_offset_token(offset, per_page, len(pagable))

    dto_items = [
        map_gym_to_summary(
            it["gym"],
            last_verified_at=it.get("last_verified_at"),
            score=float(it.get("score", 0.0)),
        )
        for it in slice_
    ]

    return GymSearchPageDTO(
        items=dto_items,
        total=total_all,
        has_next=next_token is not None,
        page_token=next_token,
    )


async def _created_at_map(db: AsyncSession) -> dict[int, datetime | None]:
    repo = GymRepository(db)
    rows = await repo.get_all_ordered_by_id()
    return {g.id: getattr(g, "created_at", None) for g in rows}
