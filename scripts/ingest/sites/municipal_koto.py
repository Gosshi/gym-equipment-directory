"""Helpers for scraping Koto municipal sports facility pages."""

from __future__ import annotations

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
    return unicodedata.normalize("NFKC", value).strip()


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
