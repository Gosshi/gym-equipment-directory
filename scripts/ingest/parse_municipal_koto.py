"""Wrapper parser for Koto municipal pages using the generic parser."""

from __future__ import annotations

from .parse_municipal_generic import MunicipalParseResult, parse_municipal_page
from .sources_registry import SOURCES


async def parse_municipal_koto_page(
    html: str,
    url: str,
    *,
    page_type: str | None = None,
) -> MunicipalParseResult:
    source = SOURCES["municipal_koto"]
    return await parse_municipal_page(html, url, source=source, page_type=page_type)


__all__ = ["parse_municipal_koto_page"]
