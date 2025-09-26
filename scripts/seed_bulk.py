"""Bulk dummy gym data generator for development/testing.

This script adds hundreds of gyms centred around Chiba, Tokyo, and Ibaraki with
plausible looking addresses and coordinates. The generated data is intended for
manual QA of the search UI (pagination, filters, map interactions, etc.).

Usage example::

    python -m scripts.seed_bulk --count 500

The script is idempotent-ish: it always creates gyms with unique bulk-prefixed
slugs, so rerunning it simply appends more gyms instead of crashing.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import random
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select

# Allow "python -m scripts.seed_bulk" from the repo root.
sys.path.append(os.path.abspath("."))

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models import Equipment, Gym
from app.models.gym_equipment import Availability, VerificationStatus
from app.models.source import SourceType
from scripts.seed import (
    EQUIPMENT_SEED,
    get_or_create_equipment,
    get_or_create_gym,
    get_or_create_source,
    link_gym_equipment,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CityConfig:
    pref_slug: str
    city_slug: str
    prefecture_label: str
    city_label: str
    neighborhoods: tuple[str, ...]
    lat_range: tuple[float, float]
    lng_range: tuple[float, float]


CITY_CONFIGS: tuple[CityConfig, ...] = (
    # Chiba prefecture
    CityConfig(
        pref_slug="chiba",
        city_slug="chiba",
        prefecture_label="千葉県",
        city_label="千葉市中央区",
        neighborhoods=("富士見", "本千葉町", "中央", "栄町", "新田町", "新宿"),
        lat_range=(35.6000, 35.6250),
        lng_range=(140.1000, 140.1400),
    ),
    CityConfig(
        pref_slug="chiba",
        city_slug="funabashi",
        prefecture_label="千葉県",
        city_label="船橋市",
        neighborhoods=("本町", "湊町", "市場", "宮本", "前原西", "海神"),
        lat_range=(35.6800, 35.7500),
        lng_range=(139.9500, 140.0800),
    ),
    CityConfig(
        pref_slug="chiba",
        city_slug="ichikawa",
        prefecture_label="千葉県",
        city_label="市川市",
        neighborhoods=("八幡", "南八幡", "真間", "新田", "行徳駅前", "妙典"),
        lat_range=(35.6800, 35.7400),
        lng_range=(139.9000, 139.9600),
    ),
    CityConfig(
        pref_slug="chiba",
        city_slug="kashiwa",
        prefecture_label="千葉県",
        city_label="柏市",
        neighborhoods=("柏", "末広町", "中央", "豊四季", "若柴", "南柏"),
        lat_range=(35.8200, 35.9000),
        lng_range=(139.9200, 140.0300),
    ),
    # Tokyo 23 wards
    CityConfig(
        pref_slug="tokyo",
        city_slug="minato",
        prefecture_label="東京都",
        city_label="港区",
        neighborhoods=("芝", "芝公園", "三田", "南青山", "北青山", "虎ノ門"),
        lat_range=(35.6300, 35.6800),
        lng_range=(139.7300, 139.7800),
    ),
    CityConfig(
        pref_slug="tokyo",
        city_slug="shibuya",
        prefecture_label="東京都",
        city_label="渋谷区",
        neighborhoods=("渋谷", "恵比寿南", "広尾", "神宮前", "松濤", "代官山町"),
        lat_range=(35.6400, 35.6800),
        lng_range=(139.6700, 139.7400),
    ),
    CityConfig(
        pref_slug="tokyo",
        city_slug="shinjuku",
        prefecture_label="東京都",
        city_label="新宿区",
        neighborhoods=("西新宿", "歌舞伎町", "神楽坂", "四谷", "戸山", "高田馬場"),
        lat_range=(35.6800, 35.7100),
        lng_range=(139.6800, 139.7300),
    ),
    CityConfig(
        pref_slug="tokyo",
        city_slug="taito",
        prefecture_label="東京都",
        city_label="台東区",
        neighborhoods=("浅草", "上野", "雷門", "蔵前", "鳥越", "谷中"),
        lat_range=(35.7000, 35.7300),
        lng_range=(139.7700, 139.8200),
    ),
    # Ibaraki prefecture
    CityConfig(
        pref_slug="ibaraki",
        city_slug="mito",
        prefecture_label="茨城県",
        city_label="水戸市",
        neighborhoods=("南町", "泉町", "千波町", "笠原町", "見和", "大工町"),
        lat_range=(36.3300, 36.3900),
        lng_range=(140.4300, 140.4900),
    ),
    CityConfig(
        pref_slug="ibaraki",
        city_slug="tsukuba",
        prefecture_label="茨城県",
        city_label="つくば市",
        neighborhoods=("吾妻", "研究学園", "竹園", "二の宮", "花室", "天久保"),
        lat_range=(36.0000, 36.1100),
        lng_range=(140.0500, 140.1600),
    ),
    CityConfig(
        pref_slug="ibaraki",
        city_slug="tsuchiura",
        prefecture_label="茨城県",
        city_label="土浦市",
        neighborhoods=("大和町", "桜町", "真鍋新町", "港町", "荒川沖東", "神立中央"),
        lat_range=(36.0500, 36.1200),
        lng_range=(140.1800, 140.2600),
    ),
)


_pref_map: dict[str, list[CityConfig]] = {}
for cfg in CITY_CONFIGS:
    _pref_map.setdefault(cfg.pref_slug, []).append(cfg)
PREF_TO_CONFIGS: dict[str, tuple[CityConfig, ...]] = {
    pref: tuple(configs) for pref, configs in _pref_map.items()
}

PREF_WEIGHTS: dict[str, float] = {
    "tokyo": 0.4,
    "chiba": 0.35,
    "ibaraki": 0.25,
}

EQUIPMENT_SLUGS: tuple[str, ...] = tuple(slug for slug, *_ in EQUIPMENT_SEED)
EQUIPMENT_CATEGORY: dict[str, str] = {slug: category for slug, _, category in EQUIPMENT_SEED}

AVAILABILITY_CHOICES: tuple[Availability, ...] = (
    Availability.present,
    Availability.unknown,
    Availability.absent,
)
AVAILABILITY_WEIGHTS: tuple[int, ...] = (8, 1, 1)

MAX_SLUG_ATTEMPTS = 25
SAMPLE_PREVIEW_LIMIT = 5


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk-generate dummy gyms for QA.")
    parser.add_argument(
        "--count",
        type=int,
        default=500,
        help="Number of gyms to generate (default: 500).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for deterministic output.",
    )
    parser.add_argument(
        "--min-equip",
        type=int,
        default=4,
        help="Minimum number of equipment entries per gym (default: 4).",
    )
    parser.add_argument(
        "--max-equip",
        type=int,
        default=7,
        help="Maximum number of equipment entries per gym (default: 7).",
    )
    parser.add_argument(
        "--overwrite-geo",
        action="store_true",
        help="Overwrite latitude/longitude if a generated slug somehow already exists.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _choices_with_weights(rng: random.Random, choices: list[str], weights: list[float]) -> str:
    return rng.choices(choices, weights=weights, k=1)[0]


def pick_city_config(rng: random.Random) -> CityConfig:
    prefs = list(PREF_TO_CONFIGS.keys())
    weights = [PREF_WEIGHTS.get(pref, 1.0) for pref in prefs]
    pref_slug = _choices_with_weights(rng, prefs, weights)
    configs = PREF_TO_CONFIGS[pref_slug]
    return rng.choice(configs)


def generate_slug(
    rng: random.Random,
    config: CityConfig,
    existing: set[str],
) -> str:
    for _ in range(MAX_SLUG_ATTEMPTS):
        suffix = rng.randint(0, 999_999)
        slug = f"bulk-{config.pref_slug}-{config.city_slug}-{suffix:06d}"
        if slug not in existing:
            existing.add(slug)
            return slug
    raise RuntimeError("Could not generate a unique slug after multiple attempts.")


def random_coordinate(rng: random.Random, bounds: tuple[float, float]) -> float:
    low, high = bounds
    if low > high:
        low, high = high, low
    return round(rng.uniform(low, high), 6)


def build_address(rng: random.Random, config: CityConfig) -> tuple[str, str, int, int, int]:
    neighborhood = rng.choice(config.neighborhoods)
    chome = rng.randint(1, 6)
    ban = rng.randint(1, 20)
    gou = rng.randint(1, 20)
    address = f"{config.prefecture_label}{config.city_label}{neighborhood}{chome}丁目{ban}-{gou}"
    return neighborhood, address, chome, ban, gou


def build_gym_name(config: CityConfig, neighborhood: str, chome: int, slug: str) -> str:
    token = slug.split("-")[-1]
    return f"{config.city_label}{neighborhood}{chome}丁目フィットネス {token.upper()}"


def decide_equipment_count(rng: random.Random, minimum: int, maximum: int) -> int:
    return rng.randint(minimum, maximum)


def to_last_verified_timestamp(rng: random.Random) -> datetime:
    days_ago = rng.randint(0, 270)
    hours = rng.randint(0, 23)
    minutes = rng.randint(0, 59)
    return datetime.utcnow() - timedelta(days=days_ago, hours=hours, minutes=minutes)


async def ensure_equipment_master(sess: AsyncSession) -> dict[str, Equipment]:
    slug_to_equipment: dict[str, Equipment] = {}
    for slug, name, category in EQUIPMENT_SEED:
        eq = await get_or_create_equipment(sess, slug=slug, name=name, category=category)
        slug_to_equipment[slug] = eq
    await sess.flush()
    return slug_to_equipment


async def async_main(args: argparse.Namespace) -> int:
    if args.count <= 0:
        logger.info("No gyms requested (count=%s). Nothing to do.", args.count)
        return 0

    if args.min_equip <= 0:
        raise ValueError("--min-equip must be greater than zero.")

    if args.max_equip < args.min_equip:
        raise ValueError("--max-equip must be greater than or equal to --min-equip.")

    if args.max_equip > len(EQUIPMENT_SLUGS):
        raise ValueError("Requested equipment count exceeds equipment seed size.")

    rng = random.Random(args.seed)

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    overwrite_geo_env = os.getenv("SEED_OVERWRITE_GEO", "").lower() in {"1", "true", "yes"}
    overwrite_geo = args.overwrite_geo or overwrite_geo_env

    async with SessionLocal() as sess:
        slug_to_equipment = await ensure_equipment_master(sess)
        source = await get_or_create_source(
            sess,
            stype=SourceType.user_submission,
            title="ダミーデータ生成 (bulk)",
            url=None,
            captured_at=datetime.utcnow(),
        )
        await sess.commit()

        existing_slugs = set((await sess.scalars(select(Gym.slug))).all())
        counters = Counter()
        samples: list[tuple[str, str, float, float]] = []
        inserted = 0

        for _ in range(args.count):
            config = pick_city_config(rng)
            slug = generate_slug(rng, config, existing_slugs)
            neighborhood, address, chome, _, _ = build_address(rng, config)
            latitude = random_coordinate(rng, config.lat_range)
            longitude = random_coordinate(rng, config.lng_range)
            gym_name = build_gym_name(config, neighborhood, chome, slug)

            gym = await get_or_create_gym(
                sess,
                slug=slug,
                name=gym_name,
                pref=config.pref_slug,
                city=config.city_slug,
                address=address,
                official_url=None,
                latitude=latitude,
                longitude=longitude,
                overwrite_geo=overwrite_geo,
            )
            gym.owner_verified = rng.random() < 0.2

            equipment_count = decide_equipment_count(rng, args.min_equip, args.max_equip)
            selected_equipment = rng.sample(EQUIPMENT_SLUGS, equipment_count)
            latest_verified: datetime | None = None

            for eq_slug in selected_equipment:
                eq = slug_to_equipment[eq_slug]
                availability = rng.choices(
                    AVAILABILITY_CHOICES,
                    weights=AVAILABILITY_WEIGHTS,
                    k=1,
                )[0]
                count: int | None = None
                max_weight: int | None = None
                category = EQUIPMENT_CATEGORY.get(eq_slug, "other")
                if availability == Availability.present:
                    count = rng.randint(1, 6)
                    if category == "free_weight":
                        max_weight = rng.randint(30, 90)
                    elif category == "machine":
                        max_weight = rng.randint(35, 110)
                    elif category == "cardio":
                        max_weight = None
                    else:
                        max_weight = rng.randint(20, 60)
                verified_at = to_last_verified_timestamp(rng)
                latest_verified = (
                    verified_at if latest_verified is None else max(latest_verified, verified_at)
                )
                await link_gym_equipment(
                    sess,
                    gym,
                    eq,
                    availability=availability,
                    count=count,
                    max_weight_kg=max_weight,
                    verification_status=(
                        VerificationStatus.user_verified
                        if availability == Availability.present
                        else VerificationStatus.unverified
                    ),
                    source=source,
                    last_verified_at=verified_at,
                )

            if latest_verified:
                gym.last_verified_at_cached = latest_verified

            counters[config.pref_slug] += 1
            inserted += 1

            if len(samples) < SAMPLE_PREVIEW_LIMIT:
                samples.append((gym.name, address, latitude, longitude))

        await sess.commit()

    for name, address, lat, lng in samples:
        logger.info("Sample gym: %s | %s (lat=%.6f, lng=%.6f)", name, address, lat, lng)

    logger.info("Inserted gyms: %s", inserted)
    for pref_slug, count in counters.items():
        logger.info("  %s: %s", pref_slug, count)

    return inserted


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return asyncio.run(async_main(args))
    except Exception:  # noqa: BLE001
        logger.exception("Bulk seeding failed.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
