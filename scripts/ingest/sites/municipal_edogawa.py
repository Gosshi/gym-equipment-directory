"""Helpers for scraping Edogawa municipal sports facility pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from bs4 import BeautifulSoup

from ._municipal_base import (
    absolutize_url,
    dedupe_urls,
    extract_address,
    extract_links,
    extract_tel,
    normalize_text,
)

SITE_ID: Final[str] = "municipal_edogawa"
BASE_URL: Final[str] = "https://www.city.edogawa.tokyo.jp"
LISTING_PATH: Final[str] = "/e078/sports/trainingroom/index.html"
LISTING_URL: Final[str] = f"{BASE_URL}{LISTING_PATH}"


@dataclass(frozen=True, slots=True)
class MunicipalEdogawaFacilitySeed:
    """Seed data representing a mock Edogawa facility detail page."""

    path: str
    name: str
    postal_code: str
    address: str
    tel: str
    description: str


@dataclass(frozen=True, slots=True)
class MunicipalEdogawaParsedFacility:
    """Parsed fields extracted from an Edogawa facility detail HTML page."""

    name: str
    address: str
    postal_code: str
    tel: str
    detail_url: str


_FACILITY_SEEDS: Final[tuple[MunicipalEdogawaFacilitySeed, ...]] = (
    MunicipalEdogawaFacilitySeed(
        path="/e078/sports/trainingroom/sogo_sports_center.html",
        name="江戸川区総合体育館 トレーニングルーム",
        postal_code="132-0031",
        address="東京都江戸川区松本1-35-1",
        tel="03-3653-7441",
        description="フリーウエイトと有酸素マシンを備えた総合体育館のトレーニングルームです。",
    ),
    MunicipalEdogawaFacilitySeed(
        path="/e078/sports/trainingroom/tobu_health_support.html",
        name="東部健康サポートセンター トレーニング室",
        postal_code="132-0011",
        address="東京都江戸川区瑞江2-5-7",
        tel="03-3679-1305",
        description="初心者講習とヘルスチェックを常設する地域密着型のトレーニング施設です。",
    ),
    MunicipalEdogawaFacilitySeed(
        path="/e078/sports/trainingroom/shinozaki_plaza.html",
        name="篠崎文化プラザ トレーニングルーム",
        postal_code="133-0061",
        address="東京都江戸川区篠崎町7-30-3",
        tel="03-3670-9070",
        description="マシントレーニングとスタジオプログラムを提供する文化プラザ内施設です。",
    ),
)


def _build_listing_html() -> str:
    items = "\n".join(
        f'        <li><a href="{seed.path}">{seed.name}</a></li>' for seed in _FACILITY_SEEDS
    )
    return (
        "<html>\n"
        "  <body>\n"
        '    <section class="facility-listing">\n'
        "      <h1>江戸川区 トレーニングルーム一覧</h1>\n"
        '      <ul class="facilities">\n'
        f"{items}\n"
        "      </ul>\n"
        "    </section>\n"
        "  </body>\n"
        "</html>"
    )


_LISTING_HTML: Final[str] = _build_listing_html()


def _render_detail_html(seed: MunicipalEdogawaFacilitySeed) -> str:
    return (
        "<html>\n"
        "  <head>\n"
        f"    <title>{seed.name}｜江戸川区スポーツ施設</title>\n"
        "  </head>\n"
        "  <body>\n"
        '    <article class="facility-detail">\n'
        f'      <h1 class="facility-name">{seed.name}</h1>\n'
        '      <div class="facility-summary">\n'
        f'        <p class="facility-description">{seed.description}</p>\n'
        "      </div>\n"
        '      <div class="facility-contact">\n'
        f'        <p class="facility-postal">〒{seed.postal_code}</p>\n'
        f'        <p class="facility-address">{seed.address}</p>\n'
        f"        <address>〒{seed.postal_code} {seed.address}</address>\n"
        f'        <p class="facility-tel">TEL：{seed.tel}</p>\n'
        "      </div>\n"
        "    </article>\n"
        "  </body>\n"
        "</html>"
    )


_FACILITY_HTML: Final[dict[str, str]] = {
    absolutize_url(BASE_URL, seed.path): _render_detail_html(seed) for seed in _FACILITY_SEEDS
}


def iter_seed_pages(limit: int | None = None) -> list[tuple[str, str]]:
    """Return mock facility detail pages discovered from the listing page."""

    detail_urls = dedupe_urls(extract_links(_LISTING_HTML, LISTING_URL))
    pages: list[tuple[str, str]] = []
    for url in detail_urls:
        html = _FACILITY_HTML.get(url)
        if not html:
            continue
        pages.append((url, html))
    if limit is not None:
        return pages[: max(0, limit)]
    return pages


def parse(raw_html: str, *, url: str | None = None) -> MunicipalEdogawaParsedFacility:
    """Parse an Edogawa facility detail HTML page."""

    soup = BeautifulSoup(raw_html or "", "html.parser")

    name = ""
    if node := soup.select_one(".facility-name, h1"):
        name = normalize_text(node.get_text(" ", strip=True))
    if not name and soup.title:
        name = normalize_text(soup.title.get_text(" ", strip=True))

    address, postal_code = extract_address(raw_html)
    address = normalize_text(address)
    postal_code = normalize_text(postal_code)

    tel_candidates = extract_tel(raw_html)
    tel = normalize_text(tel_candidates[0]) if tel_candidates else ""

    detail_url = normalize_text(url) if url else ""

    return MunicipalEdogawaParsedFacility(
        name=name,
        address=address,
        postal_code=postal_code,
        tel=tel,
        detail_url=detail_url,
    )


__all__ = [
    "SITE_ID",
    "BASE_URL",
    "LISTING_URL",
    "MunicipalEdogawaFacilitySeed",
    "MunicipalEdogawaParsedFacility",
    "iter_seed_pages",
    "parse",
]
