"""Normalization helpers for Koto municipal gym candidates."""

from __future__ import annotations

import re
from typing import Any

from .municipal_koto_vocab import match_slug


def _normalize_count(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        digits = re.sub(r"\D", "", value)
        if digits:
            try:
                return int(digits)
            except ValueError:  # pragma: no cover - defensive
                return None
    return None


def _normalize_parsed_entries(entries: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    if not isinstance(entries, list):
        return normalized
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        payload: dict[str, Any] = {"name": name}
        count = _normalize_count(entry.get("count"))
        if count is not None:
            payload["count"] = count
        normalized.append(payload)
    return normalized


def normalize_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return payload with normalized equipment slugs and slots."""

    data: dict[str, Any] = dict(payload or {})
    raw_items = [
        str(item).strip()
        for item in data.get("equipments_raw") or []
        if str(item).strip()
    ]
    parsed_entries = _normalize_parsed_entries(data.get("equipments_parsed"))

    data["equipments_raw"] = []
    seen_raw: set[str] = set()
    for item in raw_items:
        if item in seen_raw:
            continue
        seen_raw.add(item)
        data["equipments_raw"].append(item)

    data["equipments_parsed"] = parsed_entries

    slug_order: list[str] = []
    slug_counts: dict[str, int] = {}

    def _register_slug(name: str, count: int | None) -> None:
        slug = match_slug(name)
        if not slug:
            return
        if slug not in slug_order:
            slug_order.append(slug)
        if isinstance(count, int):
            slug_counts[slug] = max(slug_counts.get(slug, 0), count)

    for entry in parsed_entries:
        _register_slug(entry["name"], entry.get("count"))
    for item in data["equipments_raw"]:
        _register_slug(item, None)

    data["equipments_slugs"] = slug_order
    data["equipments_slotted"] = [
        {"slug": slug, "count": slug_counts[slug]}
        for slug in slug_order
        if slug in slug_counts
    ]
    data["equipments"] = list(slug_order)
    return data


def merge_payloads(primary: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge two parsed payloads, preferring populated values."""

    base = dict(primary or {})
    other = dict(incoming or {})

    base_raw = base.get("equipments_raw") or []
    other_raw = other.get("equipments_raw") or []
    combined_raw: list[str] = []
    seen_raw: set[str] = set()
    for source in (base_raw, other_raw):
        if not isinstance(source, list):
            continue
        for item in source:
            text = str(item).strip()
            if not text or text in seen_raw:
                continue
            seen_raw.add(text)
            combined_raw.append(text)
    base["equipments_raw"] = combined_raw

    primary_entries = _normalize_parsed_entries(base.get("equipments_parsed"))
    incoming_entries = _normalize_parsed_entries(other.get("equipments_parsed"))
    merged_map: dict[str, dict[str, Any]] = {
        entry["name"]: dict(entry) for entry in primary_entries
    }
    for entry in incoming_entries:
        name = entry["name"]
        if name not in merged_map:
            merged_map[name] = dict(entry)
            continue
        existing = merged_map[name]
        existing_count = existing.get("count")
        new_count = entry.get("count")
        if isinstance(new_count, int) and (
            not isinstance(existing_count, int) or new_count > existing_count
        ):
            existing["count"] = new_count
    base["equipments_parsed"] = list(merged_map.values())

    combined_sources: list[dict[str, str]] = []
    seen_sources: set[tuple[str, str]] = set()
    for collection in (base.get("sources"), other.get("sources")):
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label") or "").strip()
            url = str(item.get("url") or "").strip()
            if not label or not url:
                continue
            key = (label, url)
            if key in seen_sources:
                continue
            seen_sources.add(key)
            combined_sources.append({"label": label, "url": url})
    if combined_sources:
        base["sources"] = combined_sources

    if not base.get("center_no") and other.get("center_no"):
        base["center_no"] = other.get("center_no")

    return normalize_payload(base)


__all__ = ["normalize_payload", "merge_payloads"]
