"""Parsing helpers for Koto municipal facility detail pages."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Final

from bs4 import BeautifulSoup, NavigableString, Tag

from .municipal_koto_vocab import keyword_hits
from .sites._municipal_base import extract_address

_MAIN_SELECTORS: Final[tuple[str, ...]] = (
    "#main",
    ".entry-content",
    "main",
    "#contents",
    ".post",
    ".article",
    "#content",
)
_HEADING_KEYWORDS: Final[tuple[str, ...]] = ("設備", "トレーニング", "マシン", "機器")
_CONTROL_RE: Final[re.Pattern[str]] = re.compile(r"[\x00-\x1F\x7F\u200B\u200C\u200D\uFEFF]")
_TEL_RE: Final[re.Pattern[str]] = re.compile(r"TEL[:：]\s*[^\s　、。,，・\n]+")
_FOOTNOTE_RE: Final[re.Pattern[str]] = re.compile(r"※[^\n]*")
_SPACES_RE: Final[re.Pattern[str]] = re.compile(r"\s+")
_COUNT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"×\s*([０-９0-9]+)"),
    re.compile(r"([０-９0-9]+)\s*台"),
)
_CENTER_RE: Final[re.Pattern[str]] = re.compile(r"sports_center(\d+)")


@dataclass(slots=True)
class EquipmentRecord:
    """Structured equipment entry."""

    name: str
    count: int | None


@dataclass(slots=True)
class MunicipalKotoParseResult:
    name: str
    address: str | None
    equipments_raw: list[str]
    equipments_parsed: list[EquipmentRecord]
    sources: list[dict[str, str]]
    center_no: str | None

    def to_payload(self) -> dict[str, object]:
        parsed_items: list[dict[str, object]] = []
        for record in self.equipments_parsed:
            item: dict[str, object] = {"name": record.name}
            if record.count is not None:
                item["count"] = record.count
            parsed_items.append(item)
        return {
            "equipments_raw": self.equipments_raw,
            "equipments_parsed": parsed_items,
            "sources": self.sources,
            "center_no": self.center_no,
        }


def parse_municipal_koto_page(html: str, url: str) -> MunicipalKotoParseResult:
    """Parse ``municipal_koto`` detail HTML and return structured data."""

    soup = BeautifulSoup(html or "", "html.parser")
    main = _select_main_node(soup)
    name = _extract_name(soup, main)
    address = _extract_address(soup, main)
    equipments_raw, equipments_parsed = _extract_equipments(main)
    center_no = _extract_center_no(url)
    sources: list[dict[str, str]] = []
    if url:
        sources.append({"label": "official", "url": url})
    return MunicipalKotoParseResult(
        name=name,
        address=address,
        equipments_raw=equipments_raw,
        equipments_parsed=equipments_parsed,
        sources=sources,
        center_no=center_no,
    )


def _select_main_node(soup: BeautifulSoup) -> Tag:
    for selector in _MAIN_SELECTORS:
        node = soup.select_one(selector)
        if node:
            return node
    if soup.body:
        return soup.body
    return soup


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    text = _CONTROL_RE.sub(" ", text)
    text = _TEL_RE.sub(" ", text)
    text = _FOOTNOTE_RE.sub(" ", text)
    text = text.replace("\u3000", " ")
    text = _SPACES_RE.sub(" ", text)
    return text.strip()


def _extract_name(soup: BeautifulSoup, main: Tag | None) -> str:
    name = ""
    if main:
        candidate = main.find("h1")
        if candidate:
            name = _clean_text(candidate.get_text(" ", strip=True))
    if not name and (h1 := soup.find("h1")):
        name = _clean_text(h1.get_text(" ", strip=True))
    if not name and soup.title:
        name = _clean_text(soup.title.get_text(" ", strip=True))
    if name:
        name = re.sub(r"^(施設案内\s*[\|｜]\s*)", "", name)
        name = re.sub(r"[\|｜]\s*江東区$", "", name)
    return name.strip()


def _extract_address(soup: BeautifulSoup, main: Tag | None) -> str | None:
    if main and (addr_tag := main.find("address")):
        text = _clean_text(addr_tag.get_text(" ", strip=True))
        if text:
            return text
    if main:
        for tag in main.find_all(["p", "li", "dd", "dt", "span", "div", "th", "td"]):
            raw_text = _clean_text(tag.get_text(" ", strip=True))
            if not raw_text:
                continue
            for label in ("所在地", "住所"):
                if label not in raw_text:
                    continue
                candidate = re.sub(rf"^{label}\s*[:：\-－\|｜]*", "", raw_text).strip()
                if candidate:
                    return candidate
    extracted_address, _postal = extract_address(str(main) if main else soup.prettify())
    if extracted_address:
        return _clean_text(extracted_address)
    return None


def _extract_center_no(url: str) -> str | None:
    if not url:
        return None
    match = _CENTER_RE.search(url)
    if match:
        return match.group(1)
    return None


def _extract_equipments(main: Tag) -> tuple[list[str], list[EquipmentRecord]]:
    raw_results: list[str] = []
    parsed_results: list[EquipmentRecord] = []
    seen: set[str] = set()

    def _add_entry(text: str, *, prefer_count_text: str | None = None) -> None:
        cleaned = _clean_text(text)
        if not cleaned:
            return
        if cleaned in seen:
            return
        seen.add(cleaned)
        raw_results.append(cleaned)
        count_source = prefer_count_text if prefer_count_text else cleaned
        count = _extract_count(count_source)
        name = _remove_count_suffix(cleaned)
        if name:
            parsed_results.append(EquipmentRecord(name=name, count=count))

    for block in _iter_heading_sections(main):
        if block.name == "table":
            for name_text, count_text, row_text in _extract_table_entries(block):
                _add_entry(row_text or name_text, prefer_count_text=count_text)
        elif block.name in {"ul", "ol"}:
            for li in block.find_all("li"):
                _add_entry(li.get_text(" ", strip=True))
        else:
            for ul in block.find_all("ul"):
                for li in ul.find_all("li"):
                    _add_entry(li.get_text(" ", strip=True))
            for table in block.find_all("table"):
                for name_text, count_text, row_text in _extract_table_entries(table):
                    _add_entry(row_text or name_text, prefer_count_text=count_text)

    if not raw_results:
        for table in main.find_all("table"):
            for name_text, count_text, row_text in _extract_table_entries(table):
                _add_entry(row_text or name_text, prefer_count_text=count_text)

    if len(raw_results) < 3:
        for li in main.find_all("li"):
            value = li.get_text(" ", strip=True)
            if keyword_hits(value):
                _add_entry(value)

    if len(raw_results) < 3:
        fragments: list[str] = []
        for paragraph in main.find_all("p"):
            text = _clean_text(paragraph.get_text(" ", strip=True))
            if text:
                fragments.append(text)
        combined = "\n".join(fragments)
        for piece in re.split(r"[\n、,，・／/|｜]", combined):
            if keyword_hits(piece):
                _add_entry(piece)

    return raw_results, parsed_results


def _iter_heading_sections(main: Tag) -> list[Tag]:
    sections: list[Tag] = []
    for heading in main.find_all(["h2", "h3"]):
        heading_text = _clean_text(heading.get_text(" ", strip=True))
        if not heading_text:
            continue
        if not any(keyword in heading_text for keyword in _HEADING_KEYWORDS):
            continue
        sibling = heading.next_sibling
        while sibling and isinstance(sibling, NavigableString):
            if str(sibling).strip():
                break
            sibling = sibling.next_sibling
        if not isinstance(sibling, Tag):
            continue
        if sibling.name in {"h2", "h3"}:
            continue
        sections.append(sibling)
    return sections


def _extract_table_entries(table: Tag) -> list[tuple[str, str, str]]:
    entries: list[tuple[str, str, str]] = []
    rows = table.find_all("tr")
    if not rows:
        return entries
    header_cells = rows[0].find_all(["th", "td"])
    name_col = 0
    count_col: int | None = None
    if header_cells and any(cell.name == "th" for cell in header_cells):
        headers = [_clean_text(cell.get_text(" ", strip=True)).lower() for cell in header_cells]
        for index, header in enumerate(headers):
            if any(keyword in header for keyword in ("名称", "機器", "設備", "種目", "機種")):
                name_col = index
                break
        for index, header in enumerate(headers):
            if any(keyword in header for keyword in ("台数", "数量", "台")):
                count_col = index
                break
        data_rows = rows[1:]
    else:
        data_rows = rows
    for row in data_rows:
        cells = row.find_all(["td", "th"])
        values = [_clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        if not any(values):
            continue
        row_text = " ".join(value for value in values if value)
        name_text = values[name_col] if name_col < len(values) else values[0]
        count_text = (
            values[count_col]
            if count_col is not None and count_col < len(values)
            else row_text
        )
        if keyword_hits(row_text) or keyword_hits(name_text):
            entries.append((name_text, count_text, row_text))
    return entries


def _extract_count(text: str | None) -> int | None:
    cleaned = _clean_text(text)
    if not cleaned:
        return None
    for pattern in _COUNT_PATTERNS:
        match = pattern.search(cleaned)
        if not match:
            continue
        digits = unicodedata.normalize("NFKC", match.group(1))
        digits = re.sub(r"\D", "", digits)
        if digits:
            try:
                return int(digits)
            except ValueError:  # pragma: no cover - defensive
                continue
    return None


def _remove_count_suffix(text: str) -> str:
    cleaned = re.sub(r"×\s*[０-９0-9]+", "", text)
    cleaned = re.sub(r"（\s*\d+\s*台\s*）", "", cleaned)
    cleaned = re.sub(r"\s*台$", "", cleaned)
    return cleaned.strip(" ・、，,：:")


__all__ = [
    "EquipmentRecord",
    "MunicipalKotoParseResult",
    "parse_municipal_koto_page",
]
