from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Equipment, Gym, GymEquipment
from app.utils.paging import build_next_offset_token, parse_offset_token
from app.utils.sort import SortKey, resolve_sort_key


class GymSummaryDTO(TypedDict, total=False):
    id: int
    slug: str
    name: str
    pref: str
    city: str
    last_verified_at: datetime | None  # router側でdt_to_tokenへ
    score: float  # richness/score 用


class ServiceResult(TypedDict):
    items: list[GymSummaryDTO]
    total: int
    has_next: bool
    page_token: str | None


async def search_gyms(
    db: AsyncSession,
    *,
    pref: str | None,
    city: str | None,
    equipments: list[str] | None,
    equipment_match: str,  # "any" | "all"
    sort: str,  # 互換のため文字列で受け取り resolve_sort_key で正規化
    page_token: str | None,
    page: int,
    per_page: int,
) -> ServiceResult:
    """
    既存の router 実装と等価の挙動を service にまとめる。
    - pref/city は SQL 側で絞り込み
    - 設備は対象 gym_id 群を求めた上で GymEquipment を取得し、any/all 判定
    - freshness: last_verified_at が None のものはページング対象から除外
    - page_token は offset 整数互換
    """
    # 0) sort 正規化（早期）
    sort_key: SortKey = resolve_sort_key(sort)

    # 1) Pref/City 絞り込みで候補ジム取得
    gq = select(Gym)
    if pref:
        gq = gq.where(func.lower(Gym.pref) == func.lower(pref))
    if city:
        gq = gq.where(func.lower(Gym.city) == func.lower(city))
    gyms = (await db.scalars(gq)).all()

    items_all: list[GymSummaryDTO] = []
    for g in gyms:
        items_all.append(
            {
                "id": g.id,
                "slug": str(g.slug),
                "name": str(g.name),
                "pref": str(g.pref),
                "city": str(g.city),
                # ★ Gym のキャッシュ列をそのまま freshness 判定に使う
                "last_verified_at": getattr(g, "last_verified_at_cached", None),
                "score": 0.0,
            }
        )
    gym_ids_all = [g["id"] for g in items_all]

    # 2) 設備行取得（必要なら slug でさらに絞る）
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

    # 3) last_verified / richness スコア集計
    by_gym: dict[int, list[dict]] = {}
    last_verified_by_gym: dict[int, datetime | None] = {}
    richness_by_gym: dict[int, float] = {}

    for row in ge_rows:
        # 最終検証日時集約（最大）
        lv_prev = last_verified_by_gym.get(row.gym_id)
        if lv_prev is None or (row.last_verified_at and row.last_verified_at > lv_prev):
            last_verified_by_gym[row.gym_id] = row.last_verified_at

        # richness スコア
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

        by_gym.setdefault(row.gym_id, []).append(
            {
                "equipment_slug": row.equipment_slug,
                # ここでの by_gym は後続の any/all 判定にのみ使用
            }
        )

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

    # 5) allowed を反映し、last_verified/score を items へ投影
    filtered: list[GymSummaryDTO] = []
    for it in items_all:
        if it["id"] not in allowed_gym_ids:
            continue
        gid = it["id"]
        it["last_verified_at"] = it.get("last_verified_at") or last_verified_by_gym.get(gid)
        it["score"] = float(richness_by_gym.get(gid, 0.0))
        filtered.append(it)

    # 6) ソート
    key = sort_key
    if key == "freshness":
        filtered.sort(
            key=lambda i: (i.get("last_verified_at") is None, i.get("last_verified_at")),
            reverse=True,
        )
    elif key in ("richness", "score"):
        filtered.sort(key=lambda i: i.get("score", 0.0), reverse=True)
    elif key == "gym_name":
        filtered.sort(key=lambda i: i.get("name") or "")
    elif key == "created_at":
        # id -> created_at マップを取得して比較
        # gym_rows = (await db.scalars(select(Gym).order_by(Gym.id))).all()
        created_map = await _created_at_map(db)
        filtered.sort(key=lambda i: created_map.get(i.get("id")) or 0)

    # 7) ページング（freshness のみ last_verified_at is not None を対象）
    if key == "freshness":
        pagable = [it for it in filtered if it.get("last_verified_at") is not None]
    else:
        pagable = filtered

    total_all = len(filtered)
    if total_all == 0:
        return {"items": [], "total": 0, "has_next": False, "page_token": None}

    try:
        offset = parse_offset_token(page_token, page=page, per_page=per_page)
    except Exception:
        # router で 400 へ変換する場合は例外を上位に投げてもよいが、
        # service 内で握って total=0 にしてしまうのは避ける。
        raise

    slice_ = pagable[offset : offset + per_page]
    next_token = build_next_offset_token(offset, per_page, len(pagable))

    return {
        "items": slice_,
        "total": total_all,
        "has_next": next_token is not None,
        "page_token": next_token,
    }


# --- internal helpers ---------------------------------------------------------
async def _created_at_map(db: AsyncSession) -> dict[int, datetime | None]:
    rows = (await db.scalars(select(Gym).order_by(Gym.id))).all()
    return {int(g.id): getattr(g, "created_at", None) for g in rows}
