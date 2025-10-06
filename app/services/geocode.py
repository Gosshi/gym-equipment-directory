"""Geocoding utilities with local caching."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import unicodedata
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geocode_cache import GeocodeCache

logger = logging.getLogger(__name__)

_USER_AGENT = "gym-directory/0.1 (contact@example.com)"
_RATE_LIMIT_SECONDS = 1.0
_LAST_REQUEST_AT = 0.0
_PROVIDER = "nominatim"


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


def nominatim_geocode(address: str) -> tuple[float, float, Any] | None:
    """Lookup coordinates via the public Nominatim endpoint."""

    sanitized = sanitize_address(address)
    if not sanitized:
        logger.info("skip: insufficient address (empty after sanitize)")
        return None

    _enforce_rate_limit()
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"format": "json", "q": sanitized},
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
    except requests.RequestException as exc:  # pragma: no cover - network failures
        logger.warning("Geocoding request failed: %s", exc)
        return None

    if response.status_code == 429:
        logger.warning("Geocoding rate limited by provider (429)")
        return None
    if not response.ok:
        logger.warning("Geocoding request failed with status %s", response.status_code)
        return None

    try:
        payload = response.json()
    except ValueError:  # pragma: no cover - unexpected response
        logger.warning("Failed to decode geocoding response as JSON")
        return None

    if not payload:
        return None

    first = payload[0]
    try:
        latitude = float(first["lat"])
        longitude = float(first["lon"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Invalid geocoding payload: %s", first)
        return None

    return latitude, longitude, first


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
        result = await asyncio.to_thread(nominatim_geocode, sanitized)
    except Exception:  # pragma: no cover - defensive logging
        logger.exception("Geocoding thread execution failed")
        return None

    if result is None:
        return None

    latitude, longitude, raw = result
    await put_cache(session, sanitized, latitude, longitude, _PROVIDER, raw)
    return latitude, longitude
