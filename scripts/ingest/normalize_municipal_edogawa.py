"""Wrapper normalizer for Edogawa municipal candidates."""

from __future__ import annotations

from typing import Any

from .normalize_municipal_generic import (
    MunicipalNormalizationResult,
    normalize_municipal_payload,
)
from .sources_registry import SOURCES


def normalize_municipal_edogawa_payload(
    parsed_json: dict[str, Any] | None,
    *,
    page_url: str,
) -> MunicipalNormalizationResult:
    source = SOURCES["municipal_edogawa"]
    return normalize_municipal_payload(parsed_json, source=source, page_url=page_url)


__all__ = ["normalize_municipal_edogawa_payload", "MunicipalNormalizationResult"]
