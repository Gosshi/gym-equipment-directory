"""Ingest helpers for the Koto municipal sports facility site."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Final
from urllib.parse import urljoin
import unicodedata

from bs4 import BeautifulSoup

SITE_ID: Final[str] = "municipal_koto"
BASE_URL: Final[str] = "https://www.koto-hsc.or.jp"
ALLOWED_HOSTS: Final[tuple[str, ...]] = ("www.koto-hsc.or.jp",)
SUPPORTED_AREAS: Final[set[tuple[str, str]]] = {("tokyo", "koto")}

_DETAIL_PATHS: dict[tuple[str, str], tuple[str, ...]] = {
    ("tokyo", "koto"): (
        "/facility/koto-sc/",  # 江東区スポーツ会館
        "/facility/kameido-sc/",  # 亀戸スポーツセンター
        "/facility/sunamachi-sc/",  # 砂町スポーツセンター
    ),
}


def _normalize_area(pref: str, city: str) -> tuple[str, str]:
    pref_slug = pref.strip().lower()
    city_slug = city.strip().lower()
    key = (pref_slug, city_slug)
    if key not in SUPPORTED_AREAS:
        msg = f"Unsupported area for municipal_koto: pref={pref}, city={city}"
        raise ValueError(msg)
    return key


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    return normalized.strip()


def iter_listing_urls(pref: str, city: str) -> Iterator[str]:
    """Yield absolute URLs for detail pages within the supported area."""

    key = _normalize_area(pref, city)
    for path in _DETAIL_PATHS.get(key, ()):  # pragma: no cover - defensive
        yield urljoin(BASE_URL, path)


@dataclass(slots=True)
class MunicipalKotoDetail:
    """Structured data parsed from a municipal facility detail page."""

    name: str
    address: str
    equipments_raw: list[str]


def _extract_name(soup: BeautifulSoup) -> str:
    for selector in ("h1", ".page-title", ".facility-title"):
        node = soup.select_one(selector)
        if not node:
            continue
        text = node.get_text(strip=True)
        if text:
            return _normalize_text(text)
    return ""


def _extract_address(soup: BeautifulSoup) -> str:
    if node := soup.select_one("address"):
        text = node.get_text(strip=True)
        if text:
            return _normalize_text(text)
    for selector in (".facility-address", ".detail-address", "p.address"):
        node = soup.select_one(selector)
        if not node:
            continue
        text = node.get_text(strip=True)
        if text:
            return _normalize_text(text)
    return ""


def _extract_equipments(soup: BeautifulSoup) -> list[str]:
    equipments: list[str] = []
    for selector in ("ul.equipments li", "ul.facility-equipments li", "ul#equipments li"):
        for node in soup.select(selector):
            text = node.get_text(strip=True)
            normalized = _normalize_text(text)
            if normalized:
                equipments.append(normalized)
        if equipments:
            break
    return equipments


def parse_detail(html: str) -> MunicipalKotoDetail:
    """Parse a municipal facility detail page and return structured data."""

    soup = BeautifulSoup(html or "", "html.parser")
    name = _extract_name(soup)
    address = _extract_address(soup)
    equipments = _extract_equipments(soup)
    return MunicipalKotoDetail(name=name, address=address, equipments_raw=equipments)


def normalize_equipments(equipments: Iterable[str]) -> list[str]:
    """Normalize raw equipment strings (NFKC conversion)."""

    normalized: list[str] = []
    for equipment in equipments:
        text = _normalize_text(equipment)
        if text:
            normalized.append(text)
    return normalized
