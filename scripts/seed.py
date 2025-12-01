# scripts/seed.py
"""
完全ダミーの初期データ(seed)を投入します。
何度実行しても重複しにくいよう、slug/名称でget-or-createします。
"""

import argparse
import asyncio
import hashlib
import logging
import os
import random
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypedDict

from sqlalchemy import func, select
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


DEFAULT_MIX_SPEC = "fw=4,m=4,c=2,o=1"
CATEGORY_ALIAS_MAP: dict[str, str] = {
    "fw": "free_weight",
    "m": "machine",
    "c": "cardio",
    "o": "other",
}
DEFAULT_CATEGORY_WEIGHTS: dict[str, int] = {
    "free_weight": 4,
    "machine": 4,
    "cardio": 2,
    "other": 1,
}
MAX_WEIGHT_RANGES: dict[str, tuple[int, int]] = {
    "free_weight": (30, 80),
    "machine": (35, 90),
    "cardio": (20, 40),
    "other": (20, 50),
}


@dataclass(slots=True)
class LinkSummary:
    gym_count: int
    equipment_count: int
    inserted_count: int
    updated_count: int
    samples: list[tuple[str, int]]


EQUIPMENT_SEED: list[tuple[str, str, str, str | None]] = [
    ("power-rack", "パワーラック", "free_weight", "フリーウェイトの基幹ラック。"),
    ("squat-rack", "スクワットラック", "free_weight", "スクワット専用ラック。"),
    ("half-rack", "ハーフラック", "free_weight", "省スペースのラック。"),
    ("bench-press", "ベンチプレス台", "free_weight", "王道のプレス台。"),
    ("incline-bench", "インクラインベンチ", "free_weight", "角度調整可能なベンチ。"),
    ("decline-bench", "デクラインベンチ", "free_weight", "下部狙いのプレスベンチ。"),
    ("adjustable-bench", "アジャスタブルベンチ", "free_weight", None),
    ("smith-machine", "スミスマシン", "free_weight", "軌道が固定されたバー。"),
    ("deadlift-platform", "デッドリフトプラットフォーム", "free_weight", "床を保護する専用台。"),
    ("barbell-set", "バーベルセット", "free_weight", "20kgバーとプレート一式。"),
    ("dumbbell", "ダンベルセット", "free_weight", "可変ダンベル一式。"),
    ("kettlebell-set", "ケトルベルセット", "free_weight", "重量違いのケトルベル。"),
    ("ez-curl-bar", "EZカールバー", "free_weight", "肘に優しい湾曲バー。"),
    ("preacher-bench", "プリーチャーベンチ", "free_weight", "アームカール用ベンチ。"),
    ("dip-bar", "ディップスタンド", "free_weight", None),
    ("pullup-bar", "懸垂バー", "free_weight", None),
    ("lat-pulldown", "ラットプルダウン", "machine", "背中の牽引系マシン。"),
    ("seated-row", "シーテッドロー", "machine", "水平ローイング。"),
    ("cable-crossover", "ケーブルクロスオーバー", "machine", "ケーブルの多用途マシン。"),
    ("chest-press", "チェストプレス", "machine", None),
    ("shoulder-press", "ショルダープレス", "machine", "肩周りを鍛えるマシン。"),
    ("pec-deck", "ペックデック", "machine", "胸を絞り込むマシン。"),
    ("leg-press", "レッグプレス", "machine", "下半身全体を鍛える。"),
    ("leg-extension", "レッグエクステンション", "machine", "大腿四頭筋を孤立。"),
    ("leg-curl", "レッグカール", "machine", "ハムストリングを刺激。"),
    ("hack-squat", "ハックスクワット", "machine", "軌道固定のスクワット。"),
    ("calf-raise-machine", "カーフレイズマシン", "machine", "ふくらはぎ強化。"),
    ("glute-drive", "グルートドライブ", "machine", "ヒップスラスト補助。"),
    ("hip-abductor", "ヒップアブダクター", "machine", "股関節外転を鍛える。"),
    ("hip-adductor", "ヒップアダクター", "machine", "股関節内転を鍛える。"),
    ("ab-crunch-machine", "アブクランチマシン", "machine", None),
    ("assisted-dip-chin", "アシストディップ＆チン", "machine", "自重補助マシン。"),
    ("functional-trainer", "ファンクショナルトレーナー", "machine", "多関節のケーブル装置。"),
    ("treadmill", "トレッドミル", "cardio", "定番のランニングマシン。"),
    ("bike", "エアロバイク", "cardio", "定番の有酸素バイク。"),
    ("air-bike", "エアバイク", "cardio", "全身連動のファンバイク。"),
    ("recumbent-bike", "リカンベントバイク", "cardio", "背もたれ付きバイク。"),
    ("elliptical", "クロストレーナー", "cardio", "関節に優しい全身運動。"),
    ("stair-climber", "ステアクライマー", "cardio", "階段昇降マシン。"),
    ("upright-bike", "アップライトバイク", "cardio", "直立姿勢のエアロバイク。"),
    ("rowing", "ローイングマシン", "cardio", "ボート漕ぎ運動。"),
    ("ski-erg", "スキーエルゴ", "cardio", "クロカンスキー動作。"),
    ("overhead-press", "オーバーヘッドプレス", "machine", "肩を鍛えるマシン。"),
    ("torso-rotation", "トーソローテーション", "machine", "腹斜筋を鍛えるマシン。"),
    ("ab-back-combo", "アブ・バックコンボ", "machine", "腹筋と背筋の複合マシン。"),
    ("back-extension", "バックエクステンション", "machine", "背筋を鍛えるマシン。"),
    ("bicep-curl", "バイセップカール", "machine", "上腕二頭筋を鍛えるマシン。"),
    ("flat-bench", "フラットベンチ", "free_weight", "平らなベンチ。"),
    ("body-composition-analyzer", "体組成計", "other", "筋肉量や体脂肪率を測定。"),
    ("weight-scale", "体重計", "other", "体重測定器。"),
    ("blood-pressure-monitor", "血圧計", "other", "血圧測定器。"),
    ("battle-rope", "バトルロープ", "other", "全身を使うロープ運動。"),
    ("plyo-box", "プライオボックス", "other", "ジャンプ系トレーニング用。"),
    ("medicine-ball", "メディシンボール", "other", "投げて鍛えるボール。"),
    ("agility-ladder", "アジリティラダー", "other", "フットワーク向上用。"),
    ("resistance-band", "トレーニングバンド", "other", "多用途のチューブ。"),
    ("foam-roller", "フォームローラー", "other", "セルフケア用ローラー。"),
    ("yoga-block", "ヨガブロック", "other", "柔軟をサポート。"),
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


async def migrate_legacy_equipments(sess: AsyncSession) -> None:
    """Migrate legacy equipment slugs to new ones."""
    from sqlalchemy import delete

    # back-extension-machine -> back-extension
    # Delete the old one so the new one can be created without name conflict.
    result = await sess.execute(delete(Equipment).where(Equipment.slug == "back-extension-machine"))
    if result.rowcount > 0:
        logger.info("Deleted legacy equipment: back-extension-machine")
        await sess.commit()


async def get_or_create_equipment(
    sess: AsyncSession,
    slug: str,
    name: str,
    category: str,
    desc: str | None = None,
) -> Equipment:
    result = await sess.execute(select(Equipment).where(Equipment.slug == slug))
    eq = result.scalar_one_or_none()
    if eq:
        if desc and not getattr(eq, "description", None):
            eq.description = desc
            await sess.flush()
        return eq
    eq = Equipment(slug=slug, name=name, category=category, description=desc)
    sess.add(eq)
    await sess.flush()
    return eq


async def ensure_equipment_master(sess: AsyncSession) -> dict[str, Equipment]:
    slug_to_eq: dict[str, Equipment] = {}
    for slug, name, category, desc in EQUIPMENT_SEED:
        eq = await get_or_create_equipment(sess, slug=slug, name=name, category=category, desc=desc)
        slug_to_eq[slug] = eq
    return slug_to_eq


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


def parse_mix_weights(value: str | None) -> dict[str, int]:
    weights = DEFAULT_CATEGORY_WEIGHTS.copy()
    if not value:
        return weights

    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        return weights

    for part in parts:
        if "=" not in part:
            raise ValueError(f"Missing '=' in mix specification: '{part}'")
        alias, weight_str = part.split("=", 1)
        alias = alias.strip().lower()
        category = CATEGORY_ALIAS_MAP.get(alias)
        if not category:
            raise ValueError(f"Unknown mix alias: '{alias}'")
        try:
            weight = int(weight_str)
        except ValueError as exc:  # noqa: B904 - include context in error message
            raise ValueError(f"Invalid weight for '{alias}': '{weight_str}'") from exc
        if weight < 0:
            raise ValueError(f"Weight for '{alias}' must be non-negative.")
        weights[category] = weight

    if all(weight == 0 for weight in weights.values()):
        raise ValueError("At least one equipment category weight must be positive.")

    return weights


def parse_csv_tokens(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    tokens = [token.strip().lower() for token in value.split(",") if token.strip()]
    return tuple(dict.fromkeys(tokens))


def derive_seed(master_seed: int, *parts: str) -> int:
    payload = ":".join((str(master_seed), *parts)).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def choose_category(
    rng: random.Random,
    available_by_cat: dict[str, list[str]],
    weights: dict[str, int],
) -> str | None:
    candidates = [cat for cat, slugs in available_by_cat.items() if slugs]
    if not candidates:
        return None

    weighted_candidates = [cat for cat in candidates if weights.get(cat, 0) > 0]
    if weighted_candidates:
        candidate_weights = [weights.get(cat, 0) for cat in weighted_candidates]
        return rng.choices(weighted_candidates, weights=candidate_weights, k=1)[0]

    return rng.choice(candidates)


def create_eq_rng(
    base_rng: random.Random,
    deterministic_seed: int | None,
    gym_slug: str,
    equipment_slug: str,
) -> random.Random:
    if deterministic_seed is not None:
        eq_seed = derive_seed(deterministic_seed, "equipment", gym_slug, equipment_slug)
        return random.Random(eq_seed)
    # Use a fresh RNG seeded from the base RNG to avoid cross-talk between equipments.
    return random.Random(base_rng.random())


def ensure_category_lists(slug_to_eq: dict[str, Equipment]) -> dict[str, list[str]]:
    category_to_slugs: dict[str, list[str]] = defaultdict(list)
    for slug, eq in slug_to_eq.items():
        category = getattr(eq, "category", None) or "other"
        category_to_slugs[category].append(slug)
    for slugs in category_to_slugs.values():
        slugs.sort()
    return category_to_slugs


async def link_existing_gyms(
    sess: AsyncSession,
    slug_to_eq: dict[str, Equipment],
    *,
    source: Source,
    base_rng: random.Random,
    deterministic_seed: int | None,
    target_mode: str,
    min_equip: int,
    max_equip: int,
    mix_weights: dict[str, int],
    pref_filters: Iterable[str],
    city_filters: Iterable[str],
    now_anchor: datetime,
) -> LinkSummary:
    category_to_slugs = ensure_category_lists(slug_to_eq)
    if not category_to_slugs:
        logger.info("Equipment master is empty; skipping equipment linking.")
        return LinkSummary(0, 0, 0, 0, [])

    gym_query = select(Gym).order_by(Gym.id)
    pref_filters = tuple(pref_filters)
    city_filters = tuple(city_filters)
    if pref_filters:
        gym_query = gym_query.where(func.lower(Gym.pref).in_(pref_filters))
    if city_filters:
        gym_query = gym_query.where(func.lower(Gym.city).in_(city_filters))

    gyms = (await sess.execute(gym_query)).scalars().all()
    if not gyms:
        logger.info("No gyms matched the --link-existing filters; skipping equipment linking.")
        return LinkSummary(0, 0, 0, 0, [])

    gym_ids = [gym.id for gym in gyms]
    existing_total: dict[int, int] = defaultdict(int)
    existing_known: dict[int, set[str]] = defaultdict(set)
    if gym_ids:
        result = await sess.execute(
            select(GymEquipment.gym_id, GymEquipment.equipment_id).where(
                GymEquipment.gym_id.in_(gym_ids)
            )
        )
        eq_id_to_slug = {eq.id: slug for slug, eq in slug_to_eq.items()}
        for gym_id, equipment_id in result.all():
            existing_total[gym_id] += 1
            slug = eq_id_to_slug.get(equipment_id)
            if slug:
                existing_known[gym_id].add(slug)

    if target_mode == "empty-only":
        gyms = [gym for gym in gyms if existing_total.get(gym.id, 0) == 0]
        if not gyms:
            logger.info(
                "No empty gyms matched the --link-existing filters; skipping equipment linking."
            )
            return LinkSummary(0, 0, 0, 0, [])

    total_assignments = 0
    inserted = 0
    updated = 0
    samples: list[tuple[str, int]] = []

    for gym in gyms:
        if deterministic_seed is not None:
            gym_rng = random.Random(derive_seed(deterministic_seed, "gym", gym.slug, "selection"))
        else:
            gym_rng = base_rng

        existing_slugs = existing_known.get(gym.id, set())
        selected_set = set(existing_slugs)
        target_count = gym_rng.randint(min_equip, max_equip)
        if len(selected_set) > target_count:
            target_count = len(selected_set)

        available_by_cat = {
            category: [slug for slug in slugs if slug not in selected_set]
            for category, slugs in category_to_slugs.items()
        }

        while len(selected_set) < target_count:
            category = choose_category(gym_rng, available_by_cat, mix_weights)
            if category is None:
                break
            choices = available_by_cat[category]
            if not choices:
                break
            idx = gym_rng.randrange(len(choices))
            slug = choices.pop(idx)
            selected_set.add(slug)

        if not selected_set:
            continue

        selected_slugs = sorted(selected_set)
        assignment_count = len(selected_slugs)
        total_assignments += assignment_count

        gym_max_verified = gym.last_verified_at_cached

        for slug in selected_slugs:
            eq = slug_to_eq.get(slug)
            if not eq:
                continue
            eq_rng = create_eq_rng(base_rng, deterministic_seed, gym.slug, slug)
            roll = eq_rng.random()
            if roll < 0.8:
                availability = Availability.present
            elif roll < 0.9:
                availability = Availability.unknown
            else:
                availability = Availability.absent

            count: int | None = None
            max_weight: int | None = None
            if availability is Availability.present:
                count = eq_rng.randint(1, 6)
                weight_min, weight_max = MAX_WEIGHT_RANGES.get(eq.category or "other", (20, 60))
                max_weight = eq_rng.randint(weight_min, weight_max)
            else:
                count = None
                max_weight = None

            days_ago = eq_rng.randint(0, 270)
            seconds_offset = eq_rng.randint(0, 86_399)
            last_verified_at = now_anchor - timedelta(days=days_ago, seconds=seconds_offset)

            verification_status = (
                VerificationStatus.user_verified
                if availability is Availability.present
                else VerificationStatus.unverified
            )

            await link_gym_equipment(
                sess,
                gym,
                eq,
                availability=availability,
                count=count,
                max_weight_kg=max_weight,
                verification_status=verification_status,
                source=source,
                last_verified_at=last_verified_at,
            )

            if slug in existing_slugs:
                updated += 1
            else:
                inserted += 1

            if gym_max_verified is None or (
                last_verified_at is not None and last_verified_at > gym_max_verified
            ):
                gym_max_verified = last_verified_at

        if gym_max_verified is not None:
            gym.last_verified_at_cached = gym_max_verified

        if len(samples) < 5:
            samples.append((gym.name, assignment_count))

    summary = LinkSummary(
        gym_count=len(gyms),
        equipment_count=total_assignments,
        inserted_count=inserted,
        updated_count=updated,
        samples=samples,
    )

    if summary.equipment_count == 0:
        logger.info("No equipment assignments were generated for the selected gyms.")
        return summary

    logger.info(
        "Linked equipment for %s gyms (assignments=%s, new=%s, updated=%s).",
        summary.gym_count,
        summary.equipment_count,
        summary.inserted_count,
        summary.updated_count,
    )
    for name, count in summary.samples:
        logger.info("Sample gym: %s -> %s equipments", name, count)

    return summary


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
        "--equip-only",
        action="store_true",
        help="Seed only the equipment master and exit.",
    )
    parser.add_argument(
        "--link-existing",
        action="store_true",
        help="Link equipment to existing gyms based on EQUIPMENT_SEED.",
    )
    parser.add_argument(
        "--target",
        choices=["all", "empty-only"],
        default="empty-only",
        help="Target gyms for --link-existing (default: empty-only).",
    )
    parser.add_argument(
        "--min-equip",
        type=int,
        default=4,
        metavar="N",
        help="Minimum equipment count per gym for --link-existing (default: 4).",
    )
    parser.add_argument(
        "--max-equip",
        type=int,
        default=7,
        metavar="N",
        help="Maximum equipment count per gym for --link-existing (default: 7).",
    )
    parser.add_argument(
        "--mix",
        type=str,
        default=DEFAULT_MIX_SPEC,
        help="Category mix for --link-existing (default: fw=4,m=4,c=2,o=1).",
    )
    parser.add_argument(
        "--pref",
        type=str,
        default=None,
        help="Comma-separated prefecture filter for --link-existing.",
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Comma-separated city filter for --link-existing.",
    )
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
    if getattr(args, "equip_only", False):
        async with SessionLocal() as sess:
            await ensure_equipment_master(sess)
            await sess.commit()
        logger.info("Equipment master seeded successfully.")
        return 0

    overwrite_geo_env = os.getenv("SEED_OVERWRITE_GEO", "").lower() in {"1", "true", "yes"}
    overwrite_geo = args.overwrite_geo or overwrite_geo_env

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    async with SessionLocal() as sess:
        slug_to_eq = await ensure_equipment_master(sess)

        src = await get_or_create_source(
            sess,
            stype=SourceType.user_submission,
            title="ダミー投稿（seed）",
            url=None,
            captured_at=datetime.utcnow(),
        )

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
                equipment_categories={slug: cat for slug, _, cat, _ in EQUIPMENT_SEED},
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

        if getattr(args, "link_existing", False):
            mix_weights = getattr(args, "mix_weights", DEFAULT_CATEGORY_WEIGHTS)
            pref_filters = getattr(args, "pref_filters", ())
            city_filters = getattr(args, "city_filters", ())
            now_anchor = datetime.utcnow()
            await link_existing_gyms(
                sess,
                slug_to_eq,
                source=src,
                base_rng=rng,
                deterministic_seed=args.seed,
                target_mode=args.target,
                min_equip=args.min_equip,
                max_equip=args.max_equip,
                mix_weights=mix_weights,
                pref_filters=pref_filters,
                city_filters=city_filters,
                now_anchor=now_anchor,
            )
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

    if args.link_existing:
        if args.min_equip <= 0 or args.max_equip <= 0:
            logger.error("--min-equip and --max-equip must be positive integers.")
            return 1
        if args.min_equip > args.max_equip:
            logger.error("--min-equip must be less than or equal to --max-equip.")
            return 1

    try:
        args.mix_weights = parse_mix_weights(args.mix)
    except ValueError as exc:
        logger.error("Invalid --mix value: %s", exc)
        return 1

    args.pref_filters = parse_csv_tokens(args.pref)
    args.city_filters = parse_csv_tokens(args.city)

    try:
        return asyncio.run(async_main(args))
    except Exception:  # noqa: BLE001
        logger.exception("Seed failed due to an unexpected error.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
