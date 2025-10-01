from __future__ import annotations

import re
import unicodedata
import uuid

NAMESPACE_GYM = uuid.UUID("11111111-2222-3333-4444-555555555555")

_CLEAN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\s*施設案内\s*[\|｜]\s*"), ""),
    (re.compile(r"[\|｜]\s*江東区\s*$"), ""),
]
_WS_RE = re.compile(r"\s+")


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    sanitized = normalized.replace("\x00", "")
    collapsed = _WS_RE.sub(" ", sanitized).strip()
    return collapsed


def normalize_name(name: str) -> str:
    cleaned = _normalize_text(name)
    for pattern, replacement in _CLEAN_PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned.strip(" -|")


def make_canonical_id(pref_slug: str | None, city_slug: str | None, name: str) -> str:
    pref_part = (pref_slug or "").strip().lower()
    city_part = (city_slug or "").strip().lower()
    name_part = normalize_name(name).lower()
    key = "|".join([pref_part, city_part, name_part])
    return str(uuid.uuid5(NAMESPACE_GYM, key))
