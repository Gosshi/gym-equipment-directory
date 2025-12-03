"""Utilities for scraping Sumida municipal sports facility pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from bs4 import BeautifulSoup

from ._municipal_base import absolutize_url, extract_links, normalize_text

SITE_ID: Final[str] = "municipal_sumida"
BASE_URL: Final[str] = "https://www.city.sumida.lg.jp"
LISTING_PATH: Final[str] = "/sports/facility/training/index.html"
LISTING_URL: Final[str] = f"{BASE_URL}{LISTING_PATH}"


@dataclass(frozen=True)
class MunicipalSumidaFacilitySeed:
    """Static seed data representing a Sumida facility detail page."""

    path: str
    name: str
    address: str
    official_url: str
    notes: str


@dataclass(frozen=True)
class MunicipalSumidaParsedFacility:
    """Parsed fields extracted from a Sumida facility detail HTML page."""

    name: str
    address: str
    detail_url: str
    official_url: str
    notes: str


_FACILITY_SEEDS: tuple[MunicipalSumidaFacilitySeed, ...] = (
    MunicipalSumidaFacilitySeed(
        path="/sports/facility/training/sports_center.html",
        name="墨田区総合体育館 トレーニングルーム",
        address="東京都墨田区錦糸4-15-1",
        official_url="https://www.sumida-sports.jp/sogotai",
        notes="最新マシンとフリーウエイトを備えたトレーニング施設です。",
    ),
    MunicipalSumidaFacilitySeed(
        path="/sports/facility/training/hikifune_center.html",
        name="ひきふねトレーニングセンター",
        address="東京都墨田区東向島2-38-7",
        official_url="https://www.sumida-sports.jp/hikifune",
        notes="初心者向け講習会と有酸素マシンが充実。",
    ),
    MunicipalSumidaFacilitySeed(
        path="/sports/facility/training/edogawa_gym.html",
        name="江戸川区境スポーツ交流館 トレーニング室",
        address="東京都墨田区八広1-2-3",
        official_url="https://www.sumida-sports.jp/edogawa-border",
        notes="地域連携型のトレーニングスペースで、ダンベルエリアを併設。",
    ),
)


def _build_listing_html() -> str:
    items = "\n".join(
        f"        <li><a href='{seed.path}'>{seed.name}</a></li>" for seed in _FACILITY_SEEDS
    )
    return (
        "<html>\n"
        "  <body>\n"
        "    <h1>墨田区 スポーツ施設一覧</h1>\n"
        "    <ul class='facility-list'>\n"
        f"{items}\n"
        "    </ul>\n"
        "  </body>\n"
        "</html>"
    )


_LISTING_HTML: Final[str] = _build_listing_html()


def _render_detail_html(seed: MunicipalSumidaFacilitySeed) -> str:
    return (
        "<html>\n"
        "  <head>\n"
        f"    <title>{seed.name}｜墨田区スポーツ施設</title>\n"
        "  </head>\n"
        "  <body>\n"
        "    <article class='facility-detail'>\n"
        f"      <h1 class='facility-name'>{seed.name}</h1>\n"
        "      <div class='facility-meta'>\n"
        f"        <p class='facility-address'>{seed.address}</p>\n"
        "        <address>\n"
        f"          {seed.address}\n"
        "        </address>\n"
        "      </div>\n"
        "      <section class='facility-summary'>\n"
        f"        <p class='facility-notes'>{seed.notes}</p>\n"
        "      </section>\n"
        "      <section class='facility-links'>\n"
        f"        <a class='official-link' href='{seed.official_url}'>公式サイト</a>\n"
        "      </section>\n"
        "    </article>\n"
        "  </body>\n"
        "</html>"
    )


_FACILITY_HTML: Final[dict[str, str]] = {
    absolutize_url(BASE_URL, seed.path): _render_detail_html(seed) for seed in _FACILITY_SEEDS
}


def iter_seed_pages(limit: int | None = None) -> list[tuple[str, str]]:
    """Return mock facility detail pages discovered from the listing page."""

    detail_urls = extract_links(_LISTING_HTML, LISTING_URL)
    pages: list[tuple[str, str]] = []
    for url in detail_urls:
        html = _FACILITY_HTML.get(url)
        if not html:
            continue
        pages.append((url, html))
    if limit is not None:
        return pages[: max(0, limit)]
    return pages


def parse(raw_html: str, *, url: str | None = None) -> MunicipalSumidaParsedFacility:
    """Parse a Sumida facility detail HTML page."""

    soup = BeautifulSoup(raw_html or "", "html.parser")

    name = ""
    if node := soup.select_one(".facility-name"):
        name = normalize_text(node.get_text(" ", strip=True))
    if not name and soup.title:
        name = normalize_text(soup.title.get_text(" ", strip=True))

    address = ""
    if node := soup.select_one(".facility-address"):
        address = normalize_text(node.get_text(" ", strip=True))
    if not address and (addr_tag := soup.find("address")):
        address = normalize_text(addr_tag.get_text(" ", strip=True))

    notes = ""
    if node := soup.select_one(".facility-notes"):
        notes = normalize_text(node.get_text(" ", strip=True))
    if not notes:
        paragraph = soup.find("p")
        if paragraph:
            notes = normalize_text(paragraph.get_text(" ", strip=True))

    official_url = ""
    if node := soup.select_one(".facility-links a, a.official-link"):
        official_url = normalize_text(node.get("href"))
        official_url = absolutize_url(BASE_URL, official_url)

    detail_url = normalize_text(url) if url else ""

    return MunicipalSumidaParsedFacility(
        name=name,
        address=address,
        detail_url=detail_url,
        official_url=official_url,
        notes=notes,
    )


__all__ = [
    "SITE_ID",
    "BASE_URL",
    "LISTING_URL",
    "MunicipalSumidaFacilitySeed",
    "MunicipalSumidaParsedFacility",
    "iter_seed_pages",
    "parse",
]
