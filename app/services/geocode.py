"""Geocoding utilities with local caching."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import unicodedata
from collections.abc import Iterable
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geocode_cache import GeocodeCache

logger = logging.getLogger(__name__)

_USER_AGENT = "GymDir/0.1 (admin@gym.example)"
_RATE_LIMIT_SECONDS = 1.0
_LAST_REQUEST_AT = 0.0
_MAX_BACKOFF_SECONDS = 2.0

_OPENCAGE_API_KEY = os.getenv("OPENCAGE_API_KEY")

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_OPENCAGE_URL = "https://api.opencagedata.com/geocode/v1/json"

_KANTO_BOUNDS = (34.5, 138.5, 36.2, 140.3)
_OPENCAGE_BOUNDS = ",".join(str(value) for value in _KANTO_BOUNDS)
_NOMINATIM_VIEWBOX = "138.5,34.5,140.3,36.2"

_PREFECTURES = [
    "北海道",
    "青森県",
    "岩手県",
    "宮城県",
    "秋田県",
    "山形県",
    "福島県",
    "茨城県",
    "栃木県",
    "群馬県",
    "埼玉県",
    "千葉県",
    "東京都",
    "神奈川県",
    "新潟県",
    "富山県",
    "石川県",
    "福井県",
    "山梨県",
    "長野県",
    "岐阜県",
    "静岡県",
    "愛知県",
    "三重県",
    "滋賀県",
    "京都府",
    "大阪府",
    "兵庫県",
    "奈良県",
    "和歌山県",
    "鳥取県",
    "島根県",
    "岡山県",
    "広島県",
    "山口県",
    "徳島県",
    "香川県",
    "愛媛県",
    "高知県",
    "福岡県",
    "佐賀県",
    "長崎県",
    "熊本県",
    "大分県",
    "宮崎県",
    "鹿児島県",
    "沖縄県",
]


def sanitize_address(address: str) -> str:
    """Normalize addresses for consistent caching and lookup."""

    normalized = unicodedata.normalize("NFKC", address or "")
    cleaned = normalized.replace("\x00", "").strip()
    return " ".join(cleaned.split())


async def get_cached(session: AsyncSession, address: str) -> tuple[float, float] | None:
    """Return cached latitude/longitude for an address if available."""

    sanitized = sanitize_address(address)
    if not sanitized:
        return None

    result = await session.execute(
        select(GeocodeCache.latitude, GeocodeCache.longitude).where(
            GeocodeCache.address == sanitized
        )
    )
    row = result.one_or_none()
    if row is None:
        return None
    latitude, longitude = row
    if latitude is None or longitude is None:
        return None
    return float(latitude), float(longitude)


async def put_cache(
    session: AsyncSession,
    address: str,
    latitude: float | None,
    longitude: float | None,
    provider: str,
    raw: Any,
) -> None:
    """Persist a geocode result in the cache table."""

    sanitized = sanitize_address(address)
    if not sanitized:
        return

    result = await session.execute(select(GeocodeCache).where(GeocodeCache.address == sanitized))
    cache = result.scalar_one_or_none()
    if cache is None:
        cache = GeocodeCache(address=sanitized, provider=provider)
        session.add(cache)

    cache.latitude = latitude
    cache.longitude = longitude
    cache.provider = provider
    if isinstance(raw, dict | list):
        cache.raw = raw
    else:
        try:
            cache.raw = json.loads(json.dumps(raw))
        except (TypeError, ValueError):
            cache.raw = None
    await session.flush()


def _enforce_rate_limit() -> None:
    global _LAST_REQUEST_AT

    now = time.monotonic()
    wait = _RATE_LIMIT_SECONDS - (now - _LAST_REQUEST_AT)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_AT = time.monotonic()


def _request_json(url: str, params: dict[str, Any], provider: str) -> Any:
    """Execute an HTTP GET with rate limiting and exponential backoff."""

    backoff = 0.1
    attempts = 0
    while True:
        attempts += 1
        _enforce_rate_limit()
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": _USER_AGENT, "Referer": "https://gym.example/"},
                timeout=10,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failures
            logger.warning("%s request failed: %s", provider, exc)
            return None

        if response.status_code == 429 and backoff <= _MAX_BACKOFF_SECONDS and attempts <= 3:
            time.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
            continue

        if response.status_code == 429:
            logger.warning("%s rate limited (429)", provider)
            return None

        if not response.ok:
            logger.warning("%s request failed with status %s", provider, response.status_code)
            return None

        try:
            return response.json()
        except ValueError:  # pragma: no cover - unexpected response
            logger.warning("Failed to decode %s response as JSON", provider)
            return None


def opencage_geocode(address: str) -> tuple[float, float, str, Any] | None:
    """Lookup coordinates via the OpenCage endpoint when available."""

    if not _OPENCAGE_API_KEY:
        return None

    sanitized = sanitize_address(address)
    if not sanitized:
        return None

    payload = _request_json(
        _OPENCAGE_URL,
        {
            "key": _OPENCAGE_API_KEY,
            "q": sanitized,
            "countrycode": "jp",
            "language": "ja",
            "no_annotations": 1,
            "limit": 1,
            "bounds": _OPENCAGE_BOUNDS,
        },
        "opencage",
    )

    if not payload:
        return None

    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not results:
        return None

    first = results[0]
    geometry = first.get("geometry", {}) if isinstance(first, dict) else {}
    latitude = geometry.get("lat")
    longitude = geometry.get("lng")
    if latitude is None or longitude is None:
        logger.warning("Invalid OpenCage payload: %s", first)
        return None

    try:
        return float(latitude), float(longitude), "opencage", first
    except (TypeError, ValueError):
        logger.warning("Invalid OpenCage coordinates: %s", geometry)
        return None


def nominatim_geocode(address: str) -> tuple[float, float, str, Any] | None:
    """Lookup coordinates via the public Nominatim endpoint."""

    sanitized = sanitize_address(address)
    if not sanitized:
        return None

    payload = _request_json(
        _NOMINATIM_URL,
        {
            "format": "jsonv2",
            "q": sanitized,
            "limit": 1,
            "addressdetails": 0,
            "accept-language": "ja",
            "countrycodes": "jp",
            "bounded": 1,
            "viewbox": _NOMINATIM_VIEWBOX,
        },
        "nominatim",
    )

    if not payload:
        return None

    first = payload[0] if isinstance(payload, list) and payload else None
    if not isinstance(first, dict):
        return None

    try:
        latitude = float(first["lat"])
        longitude = float(first["lon"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Invalid Nominatim payload: %s", first)
        return None

    return latitude, longitude, "nominatim", first


def _strip_facility_name(address: str) -> str:
    """Remove leading facility names before the prefecture segment."""

    for prefecture in _PREFECTURES:
        index = address.find(prefecture)
        if index != -1:
            return address[index:]
    return address


def _unique(values: Iterable[str]) -> list[str]:
    """Return a list with duplicates removed while preserving order."""

    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _build_queries(address: str) -> list[str]:
    """Compose prioritized geocoding queries from a clean address."""

    base = sanitize_address(address)
    if not base:
        return []

    stripped = _strip_facility_name(base)
    queries = [base, f"{base} 日本"]
    if stripped and stripped != base:
        queries.append(f"{stripped} 日本")
    return _unique(queries)


def _geocode_with_providers(address: str) -> tuple[float, float, str, Any] | None:
    """Try configured providers sequentially until one succeeds."""

    for query in _build_queries(address):
        if _OPENCAGE_API_KEY:
            result = opencage_geocode(query)
            if result is not None:
                return result
            logger.info("miss %s provider=%s addr=%r", "-", "opencage", query)

        result = nominatim_geocode(query)
        if result is not None:
            return result
        logger.info("miss %s provider=%s addr=%r", "-", "nominatim", query)

    return None


async def geocode(session: AsyncSession, address: str) -> tuple[float, float] | None:
    """Geocode an address with caching and provider lookup."""

    sanitized = sanitize_address(address)
    if len(sanitized) < 5:
        logger.info("skip: insufficient address (%s)", address)
        return None

    cached = await get_cached(session, sanitized)
    if cached is not None:
        return cached

    try:
        result = await asyncio.to_thread(_geocode_with_providers, sanitized)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Geocoding thread execution failed")
        return None

    if result is None:
        return None

    latitude, longitude, provider, raw = result
    await put_cache(session, sanitized, latitude, longitude, provider, raw)
    return latitude, longitude
