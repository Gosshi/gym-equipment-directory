"""Generic parser for Tokyo municipal training room pages."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from bs4 import BeautifulSoup, NavigableString, Tag

from .sites._municipal_base import extract_address
from .sources_registry import MunicipalSource

_DEFAULT_MAIN_SELECTORS: tuple[str, ...] = (
    "main",
    "#main",
    "#contents",
    ".entry-content",
    ".article",
    ".post",
    "#content",
)
_EQUIPMENT_KEYWORDS: tuple[str, ...] = ("設備", "機器", "器具", "トレーニング", "マシン")
_CONTROL_RE = re.compile(r"[\x00\u200B-\u200D\uFEFF]")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(slots=True)
class MunicipalParseResult:
    facility_name: str
    address: str | None
    equipments_raw: list[str]
    center_no: str | None
    page_type: str | None
    page_title: str


def _sanitize_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    text = _CONTROL_RE.sub("", text)
    text = text.replace("\u3000", " ")
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _select_main_node(soup: BeautifulSoup, hints: dict[str, str] | None) -> Tag:
    selectors: list[str] = []
    if hints and (custom := hints.get("main_selectors")):
        selectors.extend([segment.strip() for segment in custom.split(",") if segment.strip()])
    selectors.extend(_DEFAULT_MAIN_SELECTORS)
    for selector in selectors:
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            return node
    return soup.body or soup


def _extract_name(soup: BeautifulSoup, main: Tag | None) -> str:
    candidates: list[str] = []
    if main and (heading := main.find("h1")):
        candidates.append(heading.get_text(" ", strip=True))
    if soup.find("h1"):
        candidates.append(soup.find("h1").get_text(" ", strip=True))
    if soup.title:
        candidates.append(soup.title.get_text(" ", strip=True))
    for candidate in candidates:
        cleaned = _sanitize_text(candidate)
        if cleaned:
            cleaned = re.sub(r"^(施設案内\s*[\|｜]\s*)", "", cleaned)
            cleaned = re.sub(r"[\|｜]\s*江東区$", "", cleaned)
            return cleaned
    return ""


def _extract_address(main: Tag | None, soup: BeautifulSoup) -> str | None:
    nodes: Iterable[Tag] = []
    if main:
        nodes = main.find_all(["address", "p", "li", "dd", "dt", "td", "span", "div"])
    for node in nodes:
        raw = _sanitize_text(node.get_text(" ", strip=True))
        if not raw:
            continue
        for label in ("所在地", "住所"):
            if label not in raw:
                continue
            candidate = re.sub(rf"^{label}\s*[:：\-－\|｜]*", "", raw).strip()
            if candidate:
                return candidate
    html_source = str(main) if main else soup.prettify()
    extracted, _postal = extract_address(html_source)
    if extracted:
        return _sanitize_text(extracted)
    return None


def _iter_equipment_sections(main: Tag) -> Iterable[Tag]:
    for heading in main.find_all(["h2", "h3", "h4", "h5", "h6"]):
        heading_text = _sanitize_text(heading.get_text(" ", strip=True))
        if not heading_text:
            continue
        if not any(keyword in heading_text for keyword in _EQUIPMENT_KEYWORDS):
            continue
        for sibling in heading.next_siblings:
            if isinstance(sibling, NavigableString):
                continue
            if isinstance(sibling, Tag) and sibling.name and sibling.name.startswith("h"):
                break
            if isinstance(sibling, Tag):
                yield sibling


def _extract_table_entries(table: Tag) -> list[str]:
    rows: list[str] = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        text = _sanitize_text(" ".join(cell for cell in cells if cell))
        if text:
            rows.append(text)
    return rows


def _collect_equipment_texts(main: Tag | None) -> list[str]:
    if main is None:
        return []
    results: list[str] = []
    seen: set[str] = set()

    def _add(text: str) -> None:
        cleaned = _sanitize_text(text)
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        results.append(cleaned)

    sections = list(_iter_equipment_sections(main))
    for section in sections:
        for li in section.find_all("li"):
            _add(li.get_text(" ", strip=True))
        for table in section.find_all("table"):
            for entry in _extract_table_entries(table):
                _add(entry)

    if not results:
        for table in main.find_all("table"):
            for entry in _extract_table_entries(table):
                _add(entry)
        if len(results) < 3:
            for li in main.find_all("li"):
                _add(li.get_text(" ", strip=True))

    return results


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


def parse_municipal_page(
    html: str,
    url: str,
    *,
    source: MunicipalSource,
    page_type: str | None = None,
) -> MunicipalParseResult:
    soup = BeautifulSoup(html or "", "html.parser")
    main = _select_main_node(soup, source.parse_hints)
    name = _extract_name(soup, main)
    address = _extract_address(main, soup)
    equipments_raw = _collect_equipment_texts(main)
    center_no = _extract_center_no(url, source.parse_hints)
    page_title = _sanitize_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    return MunicipalParseResult(
        facility_name=name,
        address=address,
        equipments_raw=equipments_raw,
        center_no=center_no,
        page_type=page_type,
        page_title=page_title,
    )


__all__ = ["MunicipalParseResult", "parse_municipal_page"]
