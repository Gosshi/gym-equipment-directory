"""Normalization entrypoint for Minato ward candidates."""

from __future__ import annotations

from typing import Any

from .normalize_municipal_common import normalize_common_municipal_payload
from .normalize_municipal_generic import MunicipalNormalizationResult


def normalize_municipal_minato_payload(
    parsed_json: dict[str, Any] | None,
    *,
    page_url: str,
) -> MunicipalNormalizationResult:
    return normalize_common_municipal_payload(
        parsed_json,
        source_key="municipal_minato",
        page_url=page_url,
    )


__all__ = ["normalize_municipal_minato_payload", "MunicipalNormalizationResult"]
