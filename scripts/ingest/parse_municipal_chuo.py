"""Parser entrypoint for Chuo ward pages."""

from __future__ import annotations

from .parse_municipal_common import parse_common_municipal_page
from .parse_municipal_generic import MunicipalParseResult


def parse_municipal_chuo_page(
    html: str,
    url: str,
    *,
    page_type: str | None = None,
) -> MunicipalParseResult:
    return parse_common_municipal_page(
        html,
        url,
        source_key="municipal_chuo",
        page_type=page_type,
    )


__all__ = ["parse_municipal_chuo_page"]
