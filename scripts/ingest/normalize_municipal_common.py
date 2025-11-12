"""Common normalization helpers for municipal ward ingest."""

from __future__ import annotations

from typing import Any

from .normalize_municipal_generic import (
    MunicipalNormalizationResult,
    normalize_municipal_payload,
)
from .sources_registry import SOURCES


def normalize_common_municipal_payload(
    parsed_json: dict[str, Any] | None,
    *,
    source_key: str,
    page_url: str,
) -> MunicipalNormalizationResult:
    source = SOURCES[source_key]
    base = normalize_municipal_payload(parsed_json, source=source, page_url=page_url)
    payload = dict(base.parsed_json)
    meta = dict(payload.get("meta") or {})
    page_type = payload.get("page_type")
    if page_type == "facility":
        meta["create_gym"] = True
    elif page_type in {"index", "category"}:
        meta["create_gym"] = False
    elif page_type == "article":
        meta["create_gym"] = bool(meta.get("create_gym"))
    else:
        meta.setdefault("create_gym", True)
    payload["meta"] = meta
    return MunicipalNormalizationResult(
        name_raw=base.name_raw,
        address_raw=base.address_raw,
        pref_slug=base.pref_slug,
        city_slug=base.city_slug,
        parsed_json=payload,
    )


__all__ = ["normalize_common_municipal_payload"]
