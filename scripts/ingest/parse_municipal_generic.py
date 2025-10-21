"""Generic parser for Tokyo municipal training room pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.ingest.normalizers.equipment_aliases import EQUIPMENT_ALIASES
from app.ingest.parsers.municipal._base import (
    detect_create_gym,
    extract_address_one_line,
    extract_equipments,
    sanitize_text,
)
from app.ingest.parsers.municipal.config_loader import load_config

from .sources_registry import MunicipalSource


@dataclass(slots=True)
class MunicipalParseResult:
    facility_name: str
    address: str | None
    equipments_raw: list[str]
    equipments: list[dict[str, Any]]
    center_no: str | None
    page_type: str | None
    page_title: str
    meta: dict[str, Any]


def _ensure_iterable(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item]


def _collect_nodes(soup: BeautifulSoup, selectors: Any) -> list[Tag]:
    nodes: list[Tag] = []
    for selector in _ensure_iterable(selectors):
        nodes.extend(node for node in soup.select(selector) if isinstance(node, Tag))
    if not nodes and soup.body:
        nodes = [soup.body]
    return nodes


def _extract_primary_title(soup: BeautifulSoup, selectors: Any) -> str:
    for selector in _ensure_iterable(selectors):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            text = sanitize_text(node.get_text(" ", strip=True))
            if text:
                return text
    return ""


def _extract_center_no(url: str, hints: dict[str, str] | None) -> str | None:
    if not hints:
        return None
    pattern = hints.get("center_no_from_url")
    if not pattern:
        return None
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def _aggregate_raw_lines(entries: list[dict[str, Any]]) -> list[str]:
    pairs: list[tuple[int, str]] = []
    for entry in entries:
        for order, line in entry.get("raw_pairs", []):
            pairs.append((int(order), line))
    pairs.sort(key=lambda item: item[0])
    seen: set[str] = set()
    ordered: list[str] = []
    for _, line in pairs:
        if line in seen:
            continue
        seen.add(line)
        ordered.append(line)
    return ordered


def _strip_internal_fields(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for entry in entries:
        cleaned.append(
            {
                "slug": entry.get("slug", ""),
                "count": int(entry.get("count", 0)),
                "raw": list(entry.get("raw", [])),
            }
        )
    return cleaned


def parse_municipal_page(
    html: str,
    url: str,
    *,
    source: MunicipalSource,
    page_type: str | None = None,
) -> MunicipalParseResult:
    clean_html = (html or "").replace("\x00", "")
    soup = BeautifulSoup(clean_html, "html.parser")
    config = load_config(source.title)
    selectors = config.get("selectors", {})

    title_text = _extract_primary_title(soup, selectors.get("title"))
    page_title = sanitize_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    facility_name = title_text or page_title

    nodes = _collect_nodes(soup, selectors.get("body"))
    body_text = " ".join(
        sanitize_text(node.get_text(" ", strip=True)) for node in nodes if node.get_text()
    )

    address = extract_address_one_line(
        clean_html,
        selectors=selectors,
        patterns={"address": config.get("address_patterns")},
    )

    equipments_extracted = extract_equipments(
        clean_html,
        selectors=selectors,
        aliases=EQUIPMENT_ALIASES,
    )
    equipments_raw = _aggregate_raw_lines(equipments_extracted)
    equipments_structured = _strip_internal_fields(equipments_extracted)
    equipment_count = sum(max(int(entry.get("count", 0)), 0) for entry in equipments_structured)

    create_gym = detect_create_gym(
        url,
        title=facility_name or page_title,
        body=body_text,
        patterns={"url": config.get("url_patterns")},
        keywords=config.get("keywords"),
        eq_count=equipment_count,
        address=address,
    )

    meta = {"create_gym": create_gym}
    center_no = _extract_center_no(url, source.parse_hints)

    return MunicipalParseResult(
        facility_name=facility_name,
        address=address,
        equipments_raw=equipments_raw,
        equipments=equipments_structured,
        center_no=center_no,
        page_type=page_type,
        page_title=page_title,
        meta=meta,
    )


__all__ = ["MunicipalParseResult", "parse_municipal_page"]
