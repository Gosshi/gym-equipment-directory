"""Wrapper parser for Sumida ward municipal pages."""

from __future__ import annotations

from .parse_municipal_generic import MunicipalParseResult, parse_municipal_page
from .sources_registry import SOURCES


def parse_municipal_sumida_page(
    html: str,
    url: str,
    *,
    page_type: str | None = None,
) -> MunicipalParseResult:
    source = SOURCES["municipal_sumida"]
    return parse_municipal_page(html, url, source=source, page_type=page_type)


__all__ = ["parse_municipal_sumida_page"]
