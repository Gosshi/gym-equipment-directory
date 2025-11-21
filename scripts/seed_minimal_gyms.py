"""Seed minimal gyms and equipment using psycopg.

The script performs idempotent upserts against gyms, equipments, sources, and gym_equipments
from a JSON payload.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import psycopg
from psycopg import Connection, Cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SourcePayload:
    key: str
    source_type: str
    title: str | None
    url: str | None
    captured_at: str | None


@dataclass(slots=True)
class EquipmentPayload:
    slug: str
    name: str
    category: str
    description: str | None


@dataclass(slots=True)
class GymEquipmentPayload:
    slug: str
    availability: str
    count: int | None
    max_weight_kg: int | None
    notes: str | None
    verification_status: str
    source_key: str


@dataclass(slots=True)
class GymPayload:
    slug: str
    canonical_id: str
    name: str
    chain_name: str | None
    address: str | None
    pref: str | None
    city: str | None
    official_url: str | None
    latitude: float | None
    longitude: float | None
    equipments: list[GymEquipmentPayload]


@dataclass(slots=True)
class MinimalSeedPayload:
    sources: list[SourcePayload]
    equipments: list[EquipmentPayload]
    gyms: list[GymPayload]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed minimal gyms with psycopg")
    parser.add_argument(
        "--dsn",
        type=str,
        default=os.getenv("DATABASE_URL"),
        required=False,
        help="PostgreSQL DSN (postgresql://...)",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=Path("scripts/data/seed_minimal_gyms.json"),
        help="Path to JSON payload for seeding",
    )
    args = parser.parse_args()
    if not args.dsn:
        parser.error("--dsn or DATABASE_URL must be provided")
    return args


def normalize_dsn(dsn: str) -> str:
    normalized = dsn.replace("postgres://", "postgresql://", 1)
    for driver in ("+asyncpg", "+psycopg2", "+psycopg"):
        if driver in normalized:
            normalized = normalized.replace(driver, "")
    return normalized


def parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    candidate = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(candidate)


def load_payload(path: Path) -> MinimalSeedPayload:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    sources = [SourcePayload(**item) for item in data.get("sources", [])]
    equipments = [EquipmentPayload(**item) for item in data.get("equipments", [])]
    gyms: list[GymPayload] = []
    for gym in data.get("gyms", []):
        equipments_payload = [GymEquipmentPayload(**item) for item in gym.get("equipments", [])]
        gyms.append(
            GymPayload(
                slug=gym["slug"],
                canonical_id=gym["canonical_id"],
                name=gym["name"],
                chain_name=gym.get("chain_name"),
                address=gym.get("address"),
                pref=gym.get("pref"),
                city=gym.get("city"),
                official_url=gym.get("official_url"),
                latitude=gym.get("latitude"),
                longitude=gym.get("longitude"),
                equipments=equipments_payload,
            )
        )

    return MinimalSeedPayload(sources=sources, equipments=equipments, gyms=gyms)


def upsert_sources(cursor: Cursor[Any], sources: Iterable[SourcePayload]) -> dict[str, int]:
    source_ids: dict[str, int] = {}
    for source in sources:
        captured_at = parse_timestamp(source.captured_at)
        existing = cursor.execute(
            """
            SELECT id
            FROM sources
            WHERE source_type = %s::sourcetype
              AND coalesce(url, '') = coalesce(%s, '')
              AND coalesce(title, '') = coalesce(%s, '')
            LIMIT 1
            """,
            (source.source_type, source.url, source.title),
        ).fetchone()
        if existing:
            source_ids[source.key] = existing[0]
            cursor.execute(
                "UPDATE sources SET captured_at = %s WHERE id = %s",
                (captured_at, existing[0]),
            )
            continue

        inserted = cursor.execute(
            """
            INSERT INTO sources (source_type, title, url, captured_at)
            VALUES (%s::sourcetype, %s, %s, %s)
            RETURNING id
            """,
            (source.source_type, source.title, source.url, captured_at),
        ).fetchone()
        source_ids[source.key] = int(inserted[0])
    logger.info("Upserted %s sources", len(source_ids))
    return source_ids


def upsert_equipments(
    cursor: Cursor[Any], equipments: Iterable[EquipmentPayload]
) -> dict[str, int]:
    equipment_ids: dict[str, int] = {}
    for equipment in equipments:
        inserted = cursor.execute(
            """
            INSERT INTO equipments (name, slug, category, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                description = EXCLUDED.description,
                updated_at = NOW()
            RETURNING id
            """,
            (
                equipment.name,
                equipment.slug,
                equipment.category,
                equipment.description,
            ),
        ).fetchone()
        equipment_ids[equipment.slug] = int(inserted[0])
    logger.info("Upserted %s equipments", len(equipment_ids))
    return equipment_ids


def upsert_gyms(
    cursor: Cursor[Any],
    gyms: Iterable[GymPayload],
    equipment_ids: dict[str, int],
    source_ids: dict[str, int],
) -> None:
    upserted = 0
    for gym in gyms:
        gym_row = cursor.execute(
            """
            INSERT INTO gyms (
                name, chain_name, slug, canonical_id, address, pref, city, official_url,
                affiliate_url, owner_verified, latitude, longitude, last_verified_at_cached
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, false, %s, %s, NULL)
            ON CONFLICT (slug) DO UPDATE SET
                name = EXCLUDED.name,
                chain_name = EXCLUDED.chain_name,
                canonical_id = EXCLUDED.canonical_id,
                address = EXCLUDED.address,
                pref = EXCLUDED.pref,
                city = EXCLUDED.city,
                official_url = EXCLUDED.official_url,
                affiliate_url = EXCLUDED.affiliate_url,
                owner_verified = EXCLUDED.owner_verified,
                latitude = EXCLUDED.latitude,
                longitude = EXCLUDED.longitude,
                updated_at = NOW()
            RETURNING id
            """,
            (
                gym.name,
                gym.chain_name,
                gym.slug,
                gym.canonical_id,
                gym.address,
                gym.pref,
                gym.city,
                gym.official_url,
                gym.latitude,
                gym.longitude,
            ),
        ).fetchone()
        gym_id = int(gym_row[0])
        upsert_gym_equipments(cursor, gym_id, gym.equipments, equipment_ids, source_ids)
        upserted += 1
    logger.info("Upserted %s gyms", upserted)


def upsert_gym_equipments(
    cursor: Cursor[Any],
    gym_id: int,
    equipments: Iterable[GymEquipmentPayload],
    equipment_ids: dict[str, int],
    source_ids: dict[str, int],
) -> None:
    for equipment in equipments:
        if equipment.slug not in equipment_ids:
            msg = f"equipment slug '{equipment.slug}' is not defined in equipments"
            raise ValueError(msg)
        equipment_id = equipment_ids[equipment.slug]
        if equipment.source_key not in source_ids:
            msg = f"source_key '{equipment.source_key}' is not defined in sources"
            raise ValueError(msg)
        source_id = source_ids[equipment.source_key]
        existing = cursor.execute(
            """
            SELECT id
            FROM gym_equipments
            WHERE gym_id = %s AND equipment_id = %s
            LIMIT 1
            """,
            (gym_id, equipment_id),
        ).fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE gym_equipments
                SET availability = %s::availability,
                    count = %s,
                    max_weight_kg = %s,
                    notes = %s,
                    verification_status = %s::verificationstatus,
                    source_id = %s,
                    last_verified_at = NOW(),
                    updated_at = NOW()
                WHERE id = %s
                """,
                (
                    equipment.availability,
                    equipment.count,
                    equipment.max_weight_kg,
                    equipment.notes,
                    equipment.verification_status,
                    source_id,
                    existing[0],
                ),
            )
            continue
        cursor.execute(
            """
            INSERT INTO gym_equipments (
                gym_id, equipment_id, availability, count, max_weight_kg, notes,
                verification_status, source_id, last_verified_at
            )
            VALUES (%s, %s, %s::availability, %s, %s, %s, %s::verificationstatus, %s, NOW())
            """,
            (
                gym_id,
                equipment_id,
                equipment.availability,
                equipment.count,
                equipment.max_weight_kg,
                equipment.notes,
                equipment.verification_status,
                source_id,
            ),
        )


def main() -> None:
    args = parse_args()
    payload = load_payload(args.payload)
    dsn = normalize_dsn(args.dsn)
    logger.info("Connecting to %s", dsn)
    with psycopg.connect(dsn) as conn:  # type: Connection[Any]
        with conn.cursor() as cursor:  # type: Cursor[Any]
            source_ids = upsert_sources(cursor, payload.sources)
            equipment_ids = upsert_equipments(cursor, payload.equipments)
            upsert_gyms(cursor, payload.gyms, equipment_ids, source_ids)
        conn.commit()
    logger.info("Seed completed successfully")


if __name__ == "__main__":
    main()
