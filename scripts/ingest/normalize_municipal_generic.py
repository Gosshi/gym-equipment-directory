"""Generic normalizer for municipal ingest sources."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from .municipal_koto_vocab import match_slug
from .sources_registry import MunicipalSource

_CONTROL_RE = re.compile(r"[\x00\u200B-\u200D\uFEFF]")
_WHITESPACE_RE = re.compile(r"\s+")
_COUNT_PATTERNS = (
    re.compile(r"×\s*([０-９0-9]+)"),
    re.compile(r"([０-９0-9]+)\s*台"),
    re.compile(r"([０-９0-9]+)\s*基"),
)
_GENERIC_TITLES = {"トレーニングルーム", "トレーニングマシンの紹介", "利用上の注意"}


def _sanitize_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    text = _CONTROL_RE.sub("", text)
    text = text.replace("\u3000", " ")
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _sanitize_list(items: list[Any] | tuple[Any, ...] | None) -> list[str]:
    results: list[str] = []
    if not items:
        return results
    seen: set[str] = set()
    for item in items:
        cleaned = _sanitize_text(str(item) if item is not None else "")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        results.append(cleaned)
    return results


def _parse_count(text: str | None) -> int | None:
    if not text:
        return None
    for pattern in _COUNT_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        raw = match.group(1)
        digits = unicodedata.normalize("NFKC", raw)
        digits = re.sub(r"\D", "", digits)
        if digits:
            try:
                return int(digits)
            except ValueError:  # pragma: no cover - defensive
                return None
    return None


def _build_equipment_slots(items: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    slugs: list[str] = []
    counts: dict[str, int] = {}
    for item in items:
        slug = match_slug(item)
        if not slug:
            continue
        if slug not in slugs:
            slugs.append(slug)
        count = _parse_count(item)
        if isinstance(count, int):
            counts[slug] = max(counts.get(slug, 0), count)
    slotted = [{"slug": slug, "count": counts[slug]} for slug in slugs if slug in counts]
    return slugs, slotted


@dataclass(slots=True)
class MunicipalNormalizationResult:
    name_raw: str
    address_raw: str | None
    pref_slug: str
    city_slug: str
    parsed_json: dict[str, Any]


def normalize_municipal_payload(
    parsed_json: dict[str, Any] | None,
    *,
    source: MunicipalSource,
    page_url: str,
) -> MunicipalNormalizationResult:
    data = dict(parsed_json or {})
    facility_name = _sanitize_text(data.get("facility_name"))
    address = _sanitize_text(data.get("address")) or None
    equipments_raw = _sanitize_list(data.get("equipments_raw"))
    center_no = _sanitize_text(data.get("center_no")) or None
    page_type = _sanitize_text(data.get("page_type")) or None

    slugs, slotted = _build_equipment_slots(equipments_raw)

    payload: dict[str, Any] = {
        "facility_name": facility_name,
        "address": address,
        "equipments_raw": equipments_raw,
        "equipments_slugs": slugs,
        "equipments_slotted": slotted,
        "equipments": list(slugs),
        "center_no": center_no,
        "page_type": page_type,
        "page_url": page_url,
    }

    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    meta = dict(meta)
    should_create = True
    if page_type == "article" and not address:
        title = facility_name or _sanitize_text(data.get("page_title"))
        if title in _GENERIC_TITLES:
            should_create = False
    meta["create_gym"] = should_create
    payload["meta"] = meta

    return MunicipalNormalizationResult(
        name_raw=facility_name or _sanitize_text(data.get("page_title")) or "",
        address_raw=address,
        pref_slug=source.pref_slug,
        city_slug=source.city_slug,
        parsed_json=payload,
    )


__all__ = ["MunicipalNormalizationResult", "normalize_municipal_payload"]
