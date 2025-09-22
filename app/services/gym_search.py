"""Gym search use cases implemented with the repository boundary."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

from app.dto import GymSearchPageDTO
from app.dto.mappers import map_gym_to_summary
from app.infra.unit_of_work import UnitOfWork
from app.repositories.interfaces import GymEquipmentSummaryRow
from app.utils.paging import build_next_offset_token, parse_offset_token
from app.utils.sort import SortKey, resolve_sort_key

EquipmentMatch = Literal["any", "all"]
UnitOfWorkFactory = Callable[[], UnitOfWork]


class GymSearchService:
    """Use case for searching gyms with filtering and paging."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def search(
        self,
        *,
        pref: str | None,
        city: str | None,
        equipments: list[str] | None,
        equipment_match: EquipmentMatch,
        sort: str,
        page_token: str | None,
        page: int,
        per_page: int,
    ) -> GymSearchPageDTO:
        async with self._uow_factory() as uow:
            return await search_gyms(
                uow,
                pref=pref,
                city=city,
                equipments=equipments,
                equipment_match=equipment_match,
                sort=sort,
                page_token=page_token,
                page=page,
                per_page=per_page,
            )


async def search_gyms(
    uow: UnitOfWork,
    *,
    pref: str | None,
    city: str | None,
    equipments: list[str] | None,
    equipment_match: EquipmentMatch,
    sort: str,
    page_token: str | None,
    page: int,
    per_page: int,
) -> GymSearchPageDTO:
    """Legacy-compatible gym search implemented via repositories."""

    sort_key: SortKey = resolve_sort_key(sort)

    gyms = await uow.gyms.list_by_pref_city(pref=pref, city=city)

    items_all: list[dict[str, Any]] = [
        {
            "gym": gym,
            "last_verified_at": getattr(gym, "last_verified_at_cached", None),
            "score": 0.0,
        }
        for gym in gyms
    ]
    gym_ids_all = [int(getattr(item["gym"], "id", 0)) for item in items_all]

    equipment_rows: list[GymEquipmentSummaryRow] = []
    if gym_ids_all:
        equipment_rows = await uow.gyms.fetch_equipment_for_gyms(
            gym_ids=gym_ids_all,
            equipment_slugs=equipments,
        )

    by_gym: dict[int, set[str]] = {}
    last_verified_by_gym: dict[int, datetime | None] = {}
    richness_by_gym: dict[int, float] = {}

    for row in equipment_rows:
        prev = last_verified_by_gym.get(row.gym_id)
        if prev is None or (row.last_verified_at and row.last_verified_at > prev):
            last_verified_by_gym[row.gym_id] = row.last_verified_at

        score = richness_by_gym.get(row.gym_id, 0.0)
        avail = str(row.availability or "")
        if avail == "present":
            score += 1.0
            cnt = row.count or 0
            score += (min(int(cnt), 5) * 0.1) if cnt else 0.0
            mw = row.max_weight_kg or 0.0
            score += (min(float(mw) / 60.0, 1.0) * 0.1) if mw else 0.0
        elif avail == "unknown":
            score += 0.3
        richness_by_gym[row.gym_id] = score

        by_gym.setdefault(row.gym_id, set()).add(row.slug)

    if equipments:
        requested = set(equipments)
        if equipment_match == "all":
            allowed_gym_ids = {gid for gid, slugs in by_gym.items() if slugs >= requested}
        else:
            allowed_gym_ids = set(by_gym.keys())
    else:
        allowed_gym_ids = set(gym_ids_all)

    filtered: list[dict[str, Any]] = []
    for item in items_all:
        gid = int(getattr(item["gym"], "id", 0))
        if gid not in allowed_gym_ids:
            continue
        item["last_verified_at"] = item.get("last_verified_at") or last_verified_by_gym.get(gid)
        item["score"] = float(richness_by_gym.get(gid, 0.0))
        filtered.append(item)

    if sort_key == "freshness":
        filtered.sort(
            key=lambda i: (i.get("last_verified_at") is None, i.get("last_verified_at")),
            reverse=True,
        )
    elif sort_key in {"richness", "score"}:
        filtered.sort(key=lambda i: i.get("score", 0.0), reverse=True)
    elif sort_key == "gym_name":
        filtered.sort(key=lambda i: getattr(i["gym"], "name", "") or "")
    elif sort_key == "created_at":
        created_map = await uow.gyms.created_at_map(gym_ids_all)
        filtered.sort(key=lambda i: created_map.get(int(getattr(i["gym"], "id", 0))) or 0)

    pagable = (
        [item for item in filtered if item.get("last_verified_at") is not None]
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
            item["gym"],
            last_verified_at=item.get("last_verified_at"),
            score=float(item.get("score", 0.0)),
        )
        for item in slice_
    ]

    return GymSearchPageDTO(
        items=dto_items,
        total=total_all,
        has_next=next_token is not None,
        page_token=next_token,
    )
