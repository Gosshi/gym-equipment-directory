"""Vocabulary helpers shared across Koto municipal ingest steps."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Final

from app.ingest.normalizers.equipment_aliases import EQUIPMENT_ALIASES


def _nkfc(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.replace("\x00", "")
    return normalized.strip().lower()


@dataclass(frozen=True, slots=True)
class EquipmentDefinition:
    slug: str
    labels: tuple[str, ...]


_RAW_VOCABULARY: Final[tuple[tuple[str, tuple[str, ...]], ...]] = tuple(
    (slug, tuple(labels)) for slug, labels in sorted(EQUIPMENT_ALIASES.items())
)


VOCABULARY: Final[tuple[EquipmentDefinition, ...]] = tuple(
    EquipmentDefinition(slug=slug, labels=tuple(labels)) for slug, labels in _RAW_VOCABULARY
)

_EXACT_LOOKUP: Final[dict[str, str]] = {
    _nkfc(label): definition.slug for definition in VOCABULARY for label in definition.labels
}


def iter_keyword_tokens() -> tuple[str, ...]:
    """Return normalized keyword tokens for equipment detection."""

    return tuple(sorted(set(_EXACT_LOOKUP)))


def match_slug(value: str | None) -> str | None:
    """Match *value* against known equipment vocabulary."""

    text = _nkfc(value)
    if not text:
        return None
    if text in _EXACT_LOOKUP:
        return _EXACT_LOOKUP[text]
    for definition in VOCABULARY:
        for label in definition.labels:
            normalized_label = _nkfc(label)
            if normalized_label and normalized_label in text:
                return definition.slug
    return None


def keyword_hits(value: str | None) -> bool:
    """Return True if *value* contains any known equipment keyword."""

    text = _nkfc(value)
    if not text:
        return False
    for token in _EXACT_LOOKUP:
        if token and token in text:
            return True
    return False


__all__ = [
    "EquipmentDefinition",
    "VOCABULARY",
    "iter_keyword_tokens",
    "match_slug",
    "keyword_hits",
]
