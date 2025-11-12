"""Common helpers for municipal ward parsers."""

from __future__ import annotations

from app.ingest.parsers.municipal._base import sanitize_text

from .parse_municipal_generic import MunicipalParseResult, parse_municipal_page
from .sources_registry import SOURCES


def parse_common_municipal_page(
    html: str,
    url: str,
    *,
    source_key: str,
    page_type: str | None = None,
) -> MunicipalParseResult:
    source = SOURCES[source_key]
    parsed = parse_municipal_page(html, url, source=source, page_type=page_type)
    meta = dict(parsed.meta or {})
    canonical_hint = sanitize_text(parsed.facility_name or parsed.page_title)
    if canonical_hint:
        meta.setdefault("canonical_hint", canonical_hint)
    if page_type == "facility":
        meta["create_gym"] = True
    elif page_type in {"index", "category"}:
        meta["create_gym"] = False
    elif page_type == "article":
        meta.setdefault("create_gym", False)
    parsed.meta = meta
    parsed.page_type = page_type
    return parsed


__all__ = ["parse_common_municipal_page"]
