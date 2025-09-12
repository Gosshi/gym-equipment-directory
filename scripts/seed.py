# scripts/seed.py
"""
完全ダミーの初期データ(seed)を投入します。
何度実行しても重複しにくいよう、slug/名称でget-or-createします。
"""

import asyncio
import os
import sys
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# パス調整（repo 直下から実行する前提）
sys.path.append(os.path.abspath("."))

from app.db import SessionLocal
from app.models import Equipment, Gym, GymEquipment, Source
from app.models.gym_equipment import Availability, VerificationStatus
from app.models.source import SourceType

# ---------- get-or-create helpers (ALL ASYNC) ----------


async def get_or_create_equipment(
    sess: AsyncSession, slug: str, name: str, category: str, desc: str | None = None
) -> Equipment:
    result = await sess.execute(select(Equipment).where(Equipment.slug == slug))
    eq = result.scalar_one_or_none()
    if eq:
        return eq
    eq = Equipment(slug=slug, name=name, category=category, description=desc)
    sess.add(eq)
    await sess.flush()
    return eq


async def get_or_create_gym(
    sess: AsyncSession,
    slug: str,
    name: str,
    pref: str,
    city: str,
    address: str,
    official_url: str | None = None,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> Gym:
    result = await sess.execute(select(Gym).where(Gym.slug == slug))
    g = result.scalar_one_or_none()
    if g:
        # 既存があり、緯度経度が未設定なら補完（上書きしたい場合は直接UPDATEしてください）
        if getattr(g, "latitude", None) is None and latitude is not None:
            g.latitude = float(latitude)
        if getattr(g, "longitude", None) is None and longitude is not None:
            g.longitude = float(longitude)
        return g
    g = Gym(
        slug=slug,
        name=name,
        pref=pref,
        city=city,
        address=address,
        official_url=official_url,
        latitude=latitude,
        longitude=longitude,
    )
    sess.add(g)
    await sess.flush()
    return g


async def link_gym_equipment(
    sess: AsyncSession,
    gym: Gym,
    eq: Equipment,
    availability: Availability,
    count: int | None = None,
    max_weight_kg: int | None = None,
    verification_status: VerificationStatus = VerificationStatus.unverified,
    source: Source | None = None,
    last_verified_at: datetime | None = None,
    notes: str | None = None,
) -> GymEquipment:
    result = await sess.execute(
        select(GymEquipment).where(
            (GymEquipment.gym_id == gym.id) & (GymEquipment.equipment_id == eq.id)
        )
    )
    ge = result.scalar_one_or_none()
    if ge:
        # 既存は軽く更新（初回seedなら基本通らない）
        ge.availability = availability
        ge.count = count
        ge.max_weight_kg = max_weight_kg
        ge.verification_status = verification_status
        ge.source_id = source.id if source else None
        ge.last_verified_at = last_verified_at
        ge.notes = notes
        return ge

    ge = GymEquipment(
        gym_id=gym.id,
        equipment_id=eq.id,
        availability=availability,
        count=count,
        max_weight_kg=max_weight_kg,
        verification_status=verification_status,
        source_id=source.id if source else None,
        last_verified_at=last_verified_at,
        notes=notes,
    )
    sess.add(ge)
    await sess.flush()
    return ge


async def get_or_create_source(
    sess: AsyncSession,
    stype: SourceType,
    title: str | None = None,
    url: str | None = None,
    captured_at: datetime | None = None,
) -> Source:
    # ダミーなので厳密一意までは見ないが、同一title/urlなら再利用
    q = select(Source).where(Source.source_type == stype)
    if title:
        q = q.where(Source.title == title)
    if url:
        q = q.where(Source.url == url)
    result = await sess.execute(q)
    src = result.scalar_one_or_none()
    if src:
        return src
    src = Source(source_type=stype, title=title, url=url, captured_at=captured_at)
    sess.add(src)
    await sess.flush()
    return src


# ---------- main ----------


async def main() -> int:
    # ---- 1) ダミーの設備マスター
    equipment_seed = [
        ("squat-rack", "スクワットラック", "free_weight"),
        ("bench-press", "ベンチプレス", "free_weight"),
        ("dumbbell", "ダンベル", "free_weight"),
        ("smith-machine", "スミスマシン", "free_weight"),
        ("power-rack", "パワーラック", "free_weight"),
        ("lat-pulldown", "ラットプルダウン", "machine"),
        ("chest-press", "チェストプレス", "machine"),
        ("leg-press", "レッグプレス", "machine"),
        ("leg-curl", "レッグカール", "machine"),
        ("leg-extension", "レッグエクステンション", "machine"),
        ("pec-deck", "ペックデック", "machine"),
        ("treadmill", "トレッドミル", "cardio"),
        ("bike", "エアロバイク", "cardio"),
        ("elliptical", "クロストレーナー", "cardio"),
        ("rowing", "ローイングマシン", "cardio"),
        ("stretch-area", "ストレッチエリア", "other"),
        ("cable-machine", "ケーブルマシン", "machine"),
        ("hack-squat", "ハックスクワット", "machine"),
        ("dip-bar", "ディップバー", "free_weight"),
        ("pullup-bar", "懸垂バー", "free_weight"),
    ]

    # ---- 2) ダミーのジム
    gym_seed = [
        (
            "dummy-funabashi-east",
            "ダミージム 船橋イースト",
            "chiba",
            "funabashi",
            "千葉県船橋市東町1-1-1",
            None,
            35.0000,
            139.0000,
        ),
        (
            "dummy-funabashi-west",
            "ダミージム 船橋ウエスト",
            "chiba",
            "funabashi",
            "千葉県船橋市西町1-2-3",
            None,
            35.0100,
            139.0000,
        ),
        (
            "dummy-tsudanuma-center",
            "ダミージム 津田沼センター",
            "chiba",
            "narashino",
            "千葉県習志野市谷津1-2-3",
            None,
            35.0500,
            139.0000,
        ),
        (
            "dummy-hilton-bay",
            "ダミーホテルジム ベイ",
            "chiba",
            "urayasu",
            "千葉県浦安市舞浜1-1-1",
            None,
            35.0200,
            139.0000,
        ),
        (
            "dummy-makuhari-coast",
            "ダミージム 幕張コースト",
            "chiba",
            "chiba",
            "千葉県千葉市美浜区中瀬1-1-1",
            None,
            35.0300,
            139.0000,
        ),
    ]

    # ---- 3) 設備 × ジム
    ge_seed = [
        ("dummy-funabashi-east", "squat-rack", Availability.present, 2, None),
        ("dummy-funabashi-east", "bench-press", Availability.present, 3, None),
        ("dummy-funabashi-east", "dumbbell", Availability.present, None, 40),
        ("dummy-funabashi-east", "treadmill", Availability.present, 6, None),
        ("dummy-funabashi-east", "bike", Availability.unknown, None, None),
        ("dummy-funabashi-west", "squat-rack", Availability.absent, None, None),
        ("dummy-funabashi-west", "smith-machine", Availability.present, 1, None),
        ("dummy-funabashi-west", "treadmill", Availability.present, 4, None),
        ("dummy-funabashi-west", "dumbbell", Availability.present, None, 30),
        ("dummy-tsudanuma-center", "power-rack", Availability.present, 1, None),
        ("dummy-tsudanuma-center", "bench-press", Availability.present, 2, None),
        ("dummy-tsudanuma-center", "elliptical", Availability.present, 2, None),
        ("dummy-hilton-bay", "dumbbell", Availability.present, None, 20),
        ("dummy-hilton-bay", "treadmill", Availability.present, 3, None),
        ("dummy-hilton-bay", "squat-rack", Availability.absent, None, None),
        ("dummy-makuhari-coast", "lat-pulldown", Availability.present, 1, None),
        ("dummy-makuhari-coast", "leg-press", Availability.present, 1, None),
        ("dummy-makuhari-coast", "rowing", Availability.unknown, None, None),
    ]

    async with SessionLocal() as sess:
        # 出典ダミー
        src = await get_or_create_source(
            sess,
            stype=SourceType.user_submission,
            title="ダミー投稿（seed）",
            url=None,
            captured_at=datetime.utcnow(),
        )

        # equipments
        slug_to_eq: dict[str, Equipment] = {}
        for slug, name, cat in equipment_seed:
            eq = await get_or_create_equipment(sess, slug=slug, name=name, category=cat)
            slug_to_eq[slug] = eq

        # gyms
        slug_to_gym: dict[str, Gym] = {}
        for slug, name, pref, city, addr, url, lat, lng in gym_seed:
            g = await get_or_create_gym(
                sess,
                slug=slug,
                name=name,
                pref=pref,
                city=city,
                address=addr,
                official_url=url,
                latitude=lat,
                longitude=lng,
            )
            slug_to_gym[slug] = g

        await sess.commit()  # ここでIDが確定

        # gym_equipments
        now = datetime.utcnow()
        for gym_slug, eq_slug, avail, count, max_w in ge_seed:
            g = slug_to_gym[gym_slug]
            e = slug_to_eq[eq_slug]
            await link_gym_equipment(
                sess,
                g,
                e,
                availability=avail,
                count=count,
                max_weight_kg=max_w,
                verification_status=VerificationStatus.user_verified
                if avail == Availability.present
                else VerificationStatus.unverified,
                source=src,
                last_verified_at=now,
            )

        await sess.commit()

    print("✅ Seed completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
