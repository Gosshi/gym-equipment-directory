"""Helpers for scraping Koto municipal sports facility pages."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Final

from bs4 import BeautifulSoup

SITE_ID: Final[str] = "municipal_koto"
ALLOWED_HOSTS: Final[tuple[str, ...]] = ("www.koto-hsc.or.jp",)
BASE_URL: Final[str] = "https://www.koto-hsc.or.jp"
SUPPORTED_AREAS: Final[set[tuple[str, str]]] = {("tokyo", "koto")}

# Known facility detail paths (江東区スポーツセンター群)
_DETAIL_PATHS: Final[tuple[str, ...]] = (
    "/sports_center2/",  # 深川北
    "/sports_center3/",  # 亀戸
    "/sports_center4/",  # 有明
    "/sports_center5/",  # 東砂
    "/sports_center2/introduction/",
    "/sports_center3/introduction/",
    "/sports_center4/introduction/",
    "/sports_center5/introduction/",
)


def iter_listing_urls(pref: str, city: str, *, limit: int | None = None) -> Iterable[str]:
    """Return a slice of known detail paths for the supported area."""

    _ = pref, city  # unused but keeps signature consistent
    paths = list(_DETAIL_PATHS)
    if limit is not None:
        clamped = max(0, min(limit, len(paths)))
        paths = paths[:clamped]
    return paths


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return unicodedata.normalize("NFKC", value).replace("\x00", "").strip()


_ADDRESS_LABELS: Final[tuple[str, ...]] = ("所在地", "住所")
_ADDRESS_TAGS: Final[tuple[str, ...]] = ("dt", "dd", "th", "td", "p", "li", "span", "div")
_BREADCRUMB_TAGS: Final[tuple[str, ...]] = ("nav", "ol", "ul", "h2", "h3", "h4", "h5")
_ADDRESS_REGEX: Final[re.Pattern[str]] = re.compile(
    r"(東京都[^\n]+?区[^\n]+?\d[\d\-－ー丁目番地号]*|江東区[^\n]+?\d[\d\-－ー丁目番地号]*)"
)


def parse_detail(html: str) -> dict[str, str | list[str] | None]:
    """Extract name, address, and equipment strings from a detail HTML page."""

    soup = BeautifulSoup(html or "", "html.parser")

    name = ""
    if h1 := soup.find("h1"):
        text = h1.get_text(" ", strip=True)
        if text:
            name = _norm(text)
    if not name and soup.title:
        title_text = soup.title.get_text(" ", strip=True)
        name = _norm(title_text)

    address = ""
    if address_tag := soup.find("address"):
        text = address_tag.get_text(" ", strip=True)
        address = _norm(text)
    if not address:
        # Labels such as 所在地 / 住所 that accompany a nearby value.
        for tag in soup.find_all(_ADDRESS_TAGS):
            raw_text = _norm(tag.get_text(" ", strip=True))
            if not raw_text:
                continue
            for label in _ADDRESS_LABELS:
                if label not in raw_text:
                    continue
                # Try to extract the value embedded in the same element.
                candidate = re.sub(rf"^{re.escape(label)}\s*[:：\-－\|｜]*", "", raw_text)
                candidate = _norm(candidate)
                if _looks_like_address(candidate):
                    address = candidate
                    break
                # Otherwise inspect adjacent siblings (dt/dd, th/td etc.).
                if sibling := _extract_sibling_value(tag):
                    address = sibling
                    break
            if address:
                break
    if not address:
        # Regex based extraction from the whole text content.
        text_blob = soup.get_text("\n", strip=True)
        if match := _ADDRESS_REGEX.search(text_blob):
            address = _norm(match.group(0))
    if not address:
        # Breadcrumb or heading that at least indicates the ward.
        for crumb in soup.find_all(_BREADCRUMB_TAGS):
            crumb_text = _norm(crumb.get_text(" ", strip=True))
            if "江東区" in crumb_text:
                address = crumb_text
                break
    if not address:
        text = soup.get_text("\n", strip=True)
        for line in text.splitlines():
            if "〒" in line or "東京都" in line:
                address = _norm(line)
                if address:
                    break

    equipments_raw: list[str] = []
    keywords = ("トレーニング", "マシン", "ダンベル", "スミス", "ベンチ", "ラット")
    for li in soup.select("ul li"):
        value = _norm(li.get_text(" ", strip=True))
        if value and any(keyword in value for keyword in keywords):
            equipments_raw.append(value)
    if not equipments_raw:
        for paragraph in soup.select("p"):
            value = _norm(paragraph.get_text(" ", strip=True))
            if value and any(keyword in value for keyword in keywords):
                equipments_raw.append(value)

    if name:
        name = re.sub(r"^(施設案内\s*[\|｜]\s*)", "", name)
        name = re.sub(r"[\|｜]\s*江東区$", "", name)
        name = name.strip()

    return {
        "name": name,
        "address": address or None,
        "equipments_raw": equipments_raw,
    }


__all__ = [
    "SITE_ID",
    "ALLOWED_HOSTS",
    "BASE_URL",
    "SUPPORTED_AREAS",
    "iter_listing_urls",
    "parse_detail",
]


def _extract_sibling_value(tag: object) -> str:
    if not hasattr(tag, "name"):
        return ""
    sibling_tags = {
        "dt": ("dd",),
        "th": ("td",),
        "li": (),
        "p": (),
        "span": (),
        "div": (),
    }
    tag_name = getattr(tag, "name", "")
    for sibling_name in sibling_tags.get(tag_name, ("dd", "td")):
        sibling = tag.find_next_sibling(sibling_name) if sibling_name else None
        if sibling:
            candidate = _norm(sibling.get_text(" ", strip=True))
            if _looks_like_address(candidate):
                return candidate
            if candidate:
                return candidate
    return ""


def _looks_like_address(value: str) -> bool:
    if not value:
        return False
    if "東京都" in value or "江東区" in value:
        return True
    if re.search(r"\d", value):
        return True
    return False
