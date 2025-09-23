# scripts/seed.py
"""
完全ダミーの初期データ(seed)を投入します。
何度実行しても重複しにくいよう、slug/名称でget-or-createします。
"""

import argparse
import asyncio
import logging
import os
import random
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# パス調整（repo 直下から実行する前提）
sys.path.append(os.path.abspath("."))

from app.db import SessionLocal
from app.models import Equipment, Gym, GymEquipment, Source
from app.models.gym_equipment import Availability, VerificationStatus
from app.models.source import SourceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CityAnchor(TypedDict):
    pref: str
    city: str
    addr_template: str
    lat: float
    lng: float
    lat_jitter: float
    lng_jitter: float
    areas: list[str]
    block_range: tuple[int, int]
    banchi_range: tuple[int, int]
    gou_range: tuple[int, int]


CITY_ANCHORS: dict[str, list[CityAnchor]] = {
    "chiba-east": [
        {
            "pref": "chiba",
            "city": "funabashi",
            "addr_template": "千葉県船橋市{area}{block}-{banchi}-{gou}",
            "lat": 35.7000,
            "lng": 139.9850,
            "lat_jitter": 0.010,
            "lng_jitter": 0.012,
            "areas": ["本町", "東町", "宮本", "湊町", "市場"],
            "block_range": (1, 9),
            "banchi_range": (1, 9),
            "gou_range": (1, 9),
        },
        {
            "pref": "chiba",
            "city": "narashino",
            "addr_template": "千葉県習志野市{area}{block}-{banchi}-{gou}",
            "lat": 35.6900,
            "lng": 140.0200,
            "lat_jitter": 0.010,
            "lng_jitter": 0.012,
            "areas": ["津田沼", "谷津", "奏の杜", "藤崎", "茜浜"],
            "block_range": (1, 9),
            "banchi_range": (1, 9),
            "gou_range": (1, 9),
        },
        {
            "pref": "chiba",
            "city": "urayasu",
            "addr_template": "千葉県浦安市{area}{block}-{banchi}-{gou}",
            "lat": 35.6380,
            "lng": 139.9000,
            "lat_jitter": 0.009,
            "lng_jitter": 0.011,
            "areas": ["舞浜", "美浜", "入船", "今川", "北栄"],
            "block_range": (1, 9),
            "banchi_range": (1, 9),
            "gou_range": (1, 9),
        },
        {
            "pref": "chiba",
            "city": "chiba",
            "addr_template": "千葉県千葉市美浜区{area}{block}-{banchi}-{gou}",
            "lat": 35.6400,
            "lng": 140.0500,
            "lat_jitter": 0.010,
            "lng_jitter": 0.012,
            "areas": ["打瀬", "中瀬", "ひび野", "磯辺", "幕張西"],
            "block_range": (1, 9),
            "banchi_range": (1, 9),
            "gou_range": (1, 9),
        },
    ],
    "tokyo-east": [
        {
            "pref": "tokyo",
            "city": "koto",
            "addr_template": "東京都江東区{area}{block}-{banchi}-{gou}",
            "lat": 35.6700,
            "lng": 139.8200,
            "lat_jitter": 0.010,
            "lng_jitter": 0.012,
            "areas": ["豊洲", "有明", "亀戸", "東陽", "森下"],
            "block_range": (1, 9),
            "banchi_range": (1, 9),
            "gou_range": (1, 9),
        },
        {
            "pref": "tokyo",
            "city": "sumida",
            "addr_template": "東京都墨田区{area}{block}-{banchi}-{gou}",
            "lat": 35.7100,
            "lng": 139.8100,
            "lat_jitter": 0.009,
            "lng_jitter": 0.011,
            "areas": ["錦糸", "押上", "太平", "横川", "立花"],
            "block_range": (1, 9),
            "banchi_range": (1, 9),
            "gou_range": (1, 9),
        },
        {
            "pref": "tokyo",
            "city": "taito",
            "addr_template": "東京都台東区{area}{block}-{banchi}-{gou}",
            "lat": 35.7100,
            "lng": 139.7900,
            "lat_jitter": 0.009,
            "lng_jitter": 0.011,
            "areas": ["浅草", "上野", "雷門", "蔵前", "寿"],
            "block_range": (1, 9),
            "banchi_range": (1, 9),
            "gou_range": (1, 9),
        },
    ],
}


@dataclass(slots=True)
class BulkContext:
    source: Source
    slug_to_eq: dict[str, Equipment]
    equipment_categories: dict[str, str]
    overwrite_geo: bool


BULK_CONTEXT: BulkContext | None = None


EQUIPMENT_SEED: list[tuple[str, str, str]] = [
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


GYM_SEED: list[tuple[str, str, str, str, str, str | None, float, float]] = [
    (
        "dummy-funabashi-east",
        "ダミージム 船橋イースト",
        "chiba",
        "funabashi",
        "千葉県船橋市東町1-1-1",
        None,
        35.7013,
        139.9846,
    ),
    (
        "dummy-funabashi-west",
        "ダミージム 船橋ウエスト",
        "chiba",
        "funabashi",
        "千葉県船橋市西町1-2-3",
        None,
        35.6990,
        139.9700,
    ),
    (
        "dummy-tsudanuma-center",
        "ダミージム 津田沼センター",
        "chiba",
        "narashino",
        "千葉県習志野市谷津1-2-3",
        None,
        35.6895,
        140.0203,
    ),
    (
        "dummy-hilton-bay",
        "ダミーホテルジム ベイ",
        "chiba",
        "urayasu",
        "千葉県浦安市舞浜1-1-1",
        None,
        35.6329,
        139.8830,
    ),
    (
        "dummy-makuhari-coast",
        "ダミージム 幕張コースト",
        "chiba",
        "chiba",
        "千葉県千葉市美浜区中瀬1-1-1",
        None,
        35.6486,
        140.0415,
    ),
]


GYM_EQUIPMENT_SEED: list[tuple[str, str, Availability, int | None, int | None]] = [
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
    overwrite_geo: bool = False,
) -> Gym:
    result = await sess.execute(select(Gym).where(Gym.slug == slug))
    g = result.scalar_one_or_none()
    if g:
        # 既存があり、緯度経度が未設定なら補完。上書きしたい場合は overwrite_geo=True で更新。
        if latitude is not None and (getattr(g, "latitude", None) is None or overwrite_geo):
            g.latitude = float(latitude)
        if longitude is not None and (getattr(g, "longitude", None) is None or overwrite_geo):
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


async def bulk_seed_gyms(
    sess: AsyncSession,
    n_gyms: int,
    equip_per_gym: int,
    region: str,
    rng: random.Random,
) -> int:
    if n_gyms <= 0:
        logger.info("Bulk gym count is non-positive; skipping bulk seed.")
        return 0

    if equip_per_gym <= 0:
        raise ValueError("equip_per_gym must be positive.")

    anchors = CITY_ANCHORS.get(region)
    if not anchors:
        raise ValueError(f"Unknown bulk region: {region}")

    ctx = BULK_CONTEXT
    if ctx is None:
        raise RuntimeError("Bulk context is not configured.")

    equipment_slugs = list(ctx.slug_to_eq.keys())
    if equip_per_gym > len(equipment_slugs):
        raise ValueError("equip_per_gym exceeds available equipment seed entries.")

    slugs = [f"bulk-gym-{i + 1:04d}" for i in range(n_gyms)]
    existing_slugs: set[str] = set()
    if slugs:
        result = await sess.execute(select(Gym.slug).where(Gym.slug.in_(slugs)))
        existing_slugs = set(result.scalars().all())

    preview: list[tuple[str, str, float, float]] = []
    now = datetime.utcnow()
    availability_choices = [Availability.present, Availability.absent, Availability.unknown]
    availability_weights = [8, 1, 1]

    for idx, slug in enumerate(slugs, start=1):
        anchor = rng.choice(anchors)
        area = rng.choice(anchor["areas"])
        block = rng.randint(*anchor["block_range"])
        banchi = rng.randint(*anchor["banchi_range"])
        gou = rng.randint(*anchor["gou_range"])
        address = anchor["addr_template"].format(area=area, block=block, banchi=banchi, gou=gou)
        latitude = round(
            anchor["lat"] + rng.uniform(-anchor["lat_jitter"], anchor["lat_jitter"]),
            6,
        )
        longitude = round(
            anchor["lng"] + rng.uniform(-anchor["lng_jitter"], anchor["lng_jitter"]),
            6,
        )
        gym_name = f"ダミージム {area}{block}丁目"
        gym = await get_or_create_gym(
            sess,
            slug=slug,
            name=gym_name,
            pref=anchor["pref"],
            city=anchor["city"],
            address=address,
            official_url=None,
            latitude=latitude,
            longitude=longitude,
            overwrite_geo=ctx.overwrite_geo,
        )
        if len(preview) < 3:
            preview.append((gym_name, address, latitude, longitude))

        selected_equipment = rng.sample(equipment_slugs, equip_per_gym)
        for eq_slug in selected_equipment:
            eq = ctx.slug_to_eq[eq_slug]
            availability = rng.choices(availability_choices, weights=availability_weights, k=1)[0]
            count: int | None = None
            max_weight: int | None = None
            if availability == Availability.present:
                count = rng.randint(1, 5)
                category = ctx.equipment_categories.get(eq_slug, "other")
                if category == "free_weight":
                    max_weight = rng.randint(30, 80)
                elif category == "machine":
                    max_weight = rng.randint(35, 90)
                elif category == "cardio":
                    max_weight = rng.randint(20, 40)
                else:
                    max_weight = rng.randint(20, 50)
            await link_gym_equipment(
                sess,
                gym,
                eq,
                availability=availability,
                count=count,
                max_weight_kg=max_weight,
                verification_status=VerificationStatus.user_verified
                if availability == Availability.present
                else VerificationStatus.unverified,
                source=ctx.source,
                last_verified_at=now,
            )

    for name, address, lat, lng in preview:
        logger.info("Bulk sample: %s | %s (lat=%s, lng=%s)", name, address, lat, lng)

    inserted_count = len(slugs) - len(existing_slugs)
    return inserted_count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed dummy data for gyms and equipment.")
    parser.add_argument(
        "--bulk-gyms",
        type=int,
        default=None,
        metavar="N",
        help="Generate N bulk gyms in addition to the minimal seed.",
    )
    parser.add_argument(
        "--equip-per-gym",
        type=int,
        default=5,
        metavar="M",
        help="Assign M equipment entries to each bulk gym (default: 5).",
    )
    parser.add_argument(
        "--bulk-region",
        choices=sorted(CITY_ANCHORS.keys()),
        default="chiba-east",
        metavar="R",
        help="Bulk generation region (default: chiba-east).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="INT",
        help="Random seed used for deterministic bulk data generation.",
    )
    parser.add_argument(
        "--overwrite-geo",
        action="store_true",
        help="Overwrite existing latitude/longitude during seeding.",
    )
    return parser.parse_args(argv)


async def async_main(args: argparse.Namespace) -> int:
    overwrite_geo_env = os.getenv("SEED_OVERWRITE_GEO", "").lower() in {"1", "true", "yes"}
    overwrite_geo = args.overwrite_geo or overwrite_geo_env

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    async with SessionLocal() as sess:
        src = await get_or_create_source(
            sess,
            stype=SourceType.user_submission,
            title="ダミー投稿（seed）",
            url=None,
            captured_at=datetime.utcnow(),
        )

        slug_to_eq: dict[str, Equipment] = {}
        for slug, name, cat in EQUIPMENT_SEED:
            eq = await get_or_create_equipment(sess, slug=slug, name=name, category=cat)
            slug_to_eq[slug] = eq

        slug_to_gym: dict[str, Gym] = {}
        for slug, name, pref, city, addr, url, lat, lng in GYM_SEED:
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
                overwrite_geo=overwrite_geo,
            )
            slug_to_gym[slug] = g

        await sess.commit()  # ここでIDが確定

        now = datetime.utcnow()
        for gym_slug, eq_slug, avail, count, max_w in GYM_EQUIPMENT_SEED:
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

        bulk_inserted = 0
        if args.bulk_gyms is not None:
            global BULK_CONTEXT
            BULK_CONTEXT = BulkContext(
                source=src,
                slug_to_eq=slug_to_eq,
                equipment_categories={slug: cat for slug, _, cat in EQUIPMENT_SEED},
                overwrite_geo=overwrite_geo,
            )
            try:
                bulk_inserted = await bulk_seed_gyms(
                    sess,
                    args.bulk_gyms,
                    args.equip_per_gym,
                    args.bulk_region,
                    rng,
                )
            finally:
                BULK_CONTEXT = None
            await sess.commit()

    print("✅ Seed completed.")
    if args.bulk_gyms is not None:
        print(
            "Bulk gyms inserted: "
            f"{bulk_inserted} (equip per gym: {args.equip_per_gym}, region: {args.bulk_region})"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    bulk_requested = args.bulk_gyms is not None
    app_env = os.getenv("APP_ENV", "").lower()
    if bulk_requested and app_env == "prod":
        logger.error("Bulk seeding is disabled when APP_ENV=prod.")
        return 1

    if args.bulk_gyms is not None and args.bulk_gyms < 0:
        logger.error("--bulk-gyms must be a non-negative integer.")
        return 1

    if args.equip_per_gym <= 0:
        logger.error("--equip-per-gym must be a positive integer.")
        return 1

    try:
        return asyncio.run(async_main(args))
    except Exception:  # noqa: BLE001
        logger.exception("Seed failed due to an unexpected error.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
