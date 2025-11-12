"""Parser entrypoint for Minato ward pages."""

from __future__ import annotations

from .parse_municipal_common import parse_common_municipal_page
from .parse_municipal_generic import MunicipalParseResult


def parse_municipal_minato_page(
    html: str,
    url: str,
    *,
    page_type: str | None = None,
) -> MunicipalParseResult:
    return parse_common_municipal_page(
        html,
        url,
        source_key="municipal_minato",
        page_type=page_type,
    )


__all__ = ["parse_municipal_minato_page"]
