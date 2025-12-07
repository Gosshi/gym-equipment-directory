"""Utilities for handling the ingest pipeline of ``site_a``."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

SITE_ID = "site_a"
BASE_URL = "https://site-a.example.com"
ALLOWED_HOSTS = ("site-a.example.com",)
SUPPORTED_HTTP_AREAS = {("tokyo", "koto"), ("chiba", "funabashi")}
_LISTING_PAGE_RANGE = range(1, 4)


@dataclass(frozen=True)
class SiteAGymSeed:
    """Static seed data representing a gym page on site A."""

    slug: str
    name: str
    address: str
    equipments: Sequence[str]
    tags: Sequence[str] = ()


@dataclass(frozen=True)
class SiteAParsedGym:
    """Parsed payload extracted from a ``site_a`` HTML page."""

    name_raw: str
    address_raw: str
    equipments: list[str]
    equipments_raw: list[str]
    tags: list[str]


_GYM_SEEDS: tuple[SiteAGymSeed, ...] = (
    SiteAGymSeed(
        slug="toyosu",
        name="ダミージム豊洲",
        address="東京都江東区豊洲1-2-3",
        equipments=("スミスマシン", "ラットプルダウン", "ダンベル 40kg"),
        tags=("駐車場あり", "Wi-Fi", "シャワー"),
    ),
    SiteAGymSeed(
        slug="kiba",
        name="ダミージム木場",
        address="東京都江東区木場2-1-1",
        equipments=("ラットプル", "チェストプレス", "エアロバイク"),
        tags=("24時間営業", "レンタルウェア"),
    ),
    SiteAGymSeed(
        slug="monzen-nakacho",
        name="ダミージム門前仲町",
        address="東京都江東区門前仲町1-2-8",
        equipments=("スミス", "シーテッドロー", "バイク"),
        tags=("サウナ", "パウダールーム"),
    ),
    SiteAGymSeed(
        slug="kinshicho",
        name="ダミージム錦糸町",
        address="東京都墨田区錦糸4-5-6",
        equipments=("ダンベルセット", "ショルダープレス", "トレッドミル"),
        tags=("駐車場あり", "レンタルシューズ"),
    ),
    SiteAGymSeed(
        slug="funabashi",
        name="ダミージム船橋",
        address="千葉県船橋市本町1-1-1",
        equipments=("レッグプレス", "チェストプレスマシン", "ランニングマシン"),
        tags=("24時間営業", "Wi-Fi", "レンタルタオル"),
    ),
    SiteAGymSeed(
        slug="narashino",
        name="ダミージム習志野",
        address="千葉県習志野市津田沼2-3-4",
        equipments=("バトルロープ", "クロストレーナー", "スミスマシン"),
        tags=("駐車場あり",),
    ),
    SiteAGymSeed(
        slug="urayasu",
        name="ダミージム浦安",
        address="千葉県浦安市舞浜1-2-1",
        equipments=("エアバイク", "ダンベル", "ラットプルダウン"),
        tags=("シャワー", "サウナ"),
    ),
    SiteAGymSeed(
        slug="makuhari",
        name="ダミージム幕張",
        address="千葉県千葉市美浜区中瀬1-4-2",
        equipments=("ヒップアブダクター", "チェストプレス", "ダンベル40kg"),
        tags=("駐車場あり", "Wi-Fi", "パウダールーム"),
    ),
    SiteAGymSeed(
        slug="tokyo-east",
        name="ダミージム東京イースト",
        address="東京都江戸川区東葛西1-2-3",
        equipments=("レッグプレスマシン", "スミスマシン", "クロストレーナー"),
        tags=("24時間営業",),
    ),
    SiteAGymSeed(
        slug="tokyo-south",
        name="ダミージム東京サウス",
        address="東京都品川区東品川3-4-5",
        equipments=("チェストプレス", "ショルダープレスマシン", "エリプティカル"),
        tags=("レンタルウェア", "レンタルシューズ", "レンタルタオル"),
    ),
)

_EQUIPMENT_VARIANTS: dict[str, tuple[str, ...]] = {
    "smith-machine": ("スミスマシン", "スミス", "smith machine"),
    "lat-pulldown": ("ラットプルダウン", "ラットプル", "ラットプルマシン"),
    "dumbbell": ("ダンベル", "ダンベルセット", "ダンベル 40kg", "ダンベル40kg"),
    "chest-press": ("チェストプレス", "チェストプレスマシン"),
    "leg-press": ("レッグプレス", "レッグプレスマシン"),
    "bike": ("エアロバイク", "バイク", "バイクマシン"),
    "treadmill": ("トレッドミル", "ランニングマシン"),
    "elliptical": ("クロストレーナー", "エリプティカル"),
    "shoulder-press": ("ショルダープレス", "ショルダープレスマシン"),
    "seated-row": ("シーテッドロー", "ローイングマシン"),
    "battle-rope": ("バトルロープ",),
    "hip-abductor": ("ヒップアブダクター",),
    "air-bike": ("エアバイク",),
    "rowing": ("ローイング", "ロウイング"),
}

_TAG_VARIANTS: dict[str, tuple[str, ...]] = {
    "parking": ("駐車場あり", "駐車場"),
    "24h": ("24時間営業", "24h"),
    "shower": ("シャワー", "シャワールーム"),
    "sauna": ("サウナ",),
    "wifi": ("wi-fi", "wifi", "ワイファイ"),
    "powder_room": ("パウダールーム", "化粧室"),
    "rental_wear": ("レンタルウェア", "ウェアレンタル"),
    "rental_shoes": ("レンタルシューズ", "シューズレンタル"),
    "rental_towel": ("レンタルタオル", "タオルレンタル"),
}


def _normalize_key(name: str) -> str:
    if not isinstance(name, str):
        return ""
    return "".join(ch for ch in name.strip().lower() if ch not in {" ", "\u3000", "-"})


_EQUIPMENT_LOOKUP: dict[str, str] = {}
for slug, variants in _EQUIPMENT_VARIANTS.items():
    for variant in variants:
        _EQUIPMENT_LOOKUP[_normalize_key(variant)] = slug

_TAG_LOOKUP: dict[str, str] = {}
for slug, variants in _TAG_VARIANTS.items():
    for variant in variants:
        _TAG_LOOKUP[_normalize_key(variant)] = slug


def _render_html(seed: SiteAGymSeed) -> str:
    equipments = "\n".join(f"           <li>{item}</li>" for item in seed.equipments)
    tags = "\n".join(f"           <li>{item}</li>" for item in seed.tags)
    template = """<html>
  <head><title>サイトA | {name}</title></head>
  <body>
    <div class="gym-detail">
      <h1 class="gym-name">{name}</h1>
      <div class="address">{address}</div>
      <ul class="equipments">
{equipments}
      </ul>
      <ul class="tags">
{tags}
      </ul>
    </div>
  </body>
</html>
"""
    return template.format(name=seed.name, address=seed.address, equipments=equipments, tags=tags)


def iter_seed_pages(limit: int | None) -> list[tuple[str, str]]:
    """Return the static list of seed pages for ``site_a``."""

    max_items = len(_GYM_SEEDS)
    count = max_items if limit is None else min(limit, max_items)
    selected = _GYM_SEEDS[:count]
    pages: list[tuple[str, str]] = []
    for seed in selected:
        url = f"https://site-a.local/gyms/{seed.slug}"
        pages.append((url, _render_html(seed)))
    return pages


def _extract_name(soup: BeautifulSoup) -> str:
    if (node := soup.select_one(".gym-name")) and (text := node.get_text(strip=True)):
        return text
    title = soup.title.string if soup.title and soup.title.string else ""
    if "|" in title:
        return title.split("|")[-1].strip()
    if "｜" in title:
        return title.split("｜")[-1].strip()
    return title.strip()


def _extract_address(soup: BeautifulSoup) -> str:
    if node := soup.select_one(".address"):
        return node.get_text(strip=True)
    return ""


def _extract_equipments(soup: BeautifulSoup) -> list[str]:
    return [
        node.get_text(strip=True)
        for node in soup.select(".equipments li")
        if node.get_text(strip=True)
    ]


def _extract_tags(soup: BeautifulSoup) -> list[str]:
    # Tags are rendered in <ul class="tags">...</ul> by _render_html
    return [
        node.get_text(strip=True) for node in soup.select(".tags li") if node.get_text(strip=True)
    ]


def map_equipments(equipments: Iterable[str]) -> list[str]:
    """Map raw equipment names to known ``EQUIPMENT_SEED`` slugs."""

    slugs: list[str] = []
    seen: set[str] = set()
    for name in equipments:
        key = _normalize_key(name)
        slug = _EQUIPMENT_LOOKUP.get(key)
        if slug is None or slug in seen:
            continue
        slugs.append(slug)
        seen.add(slug)
    return slugs


def map_tags(tags: Iterable[str]) -> list[str]:
    """Map raw tag names to known slugs."""

    slugs: list[str] = []
    seen: set[str] = set()
    for name in tags:
        key = _normalize_key(name)
        slug = _TAG_LOOKUP.get(key)
        if slug is None or slug in seen:
            continue
        slugs.append(slug)
        seen.add(slug)
    return slugs


def parse_gym_html(raw_html: str) -> SiteAParsedGym:
    """Parse ``site_a`` HTML into structured data."""

    soup = BeautifulSoup(raw_html or "", "html.parser")
    equipments_raw = _extract_equipments(soup)
    tags_raw = _extract_tags(soup)
    return SiteAParsedGym(
        name_raw=_extract_name(soup),
        address_raw=_extract_address(soup),
        equipments=map_equipments(equipments_raw),
        equipments_raw=equipments_raw,
        tags=map_tags(tags_raw),
    )


def render_seed_html(seed: SiteAGymSeed) -> str:
    """Expose HTML rendering for tests."""

    return _render_html(seed)


def seed_data() -> Sequence[SiteAGymSeed]:
    """Return the immutable seed dataset."""

    return _GYM_SEEDS


def _normalize_area(pref: str, city: str) -> tuple[str, str]:
    pref_slug = pref.strip().lower()
    city_slug = city.strip().lower()
    if (pref_slug, city_slug) not in SUPPORTED_HTTP_AREAS:
        msg = f"Unsupported area for site_a HTTP fetch: pref={pref}, city={city}"
        raise ValueError(msg)
    return pref_slug, city_slug


def build_listing_url(pref: str, city: str, page: int) -> str:
    """Return the listing URL for the provided area and page index."""

    pref_slug, city_slug = _normalize_area(pref, city)
    if page < 1:
        msg = "Listing page index must be >= 1"
        raise ValueError(msg)
    return f"{BASE_URL}/gyms/{pref_slug}/{city_slug}?page={page}"


def build_detail_url(pref: str, city: str, slug: str) -> str:
    """Return the absolute detail URL for a gym slug."""

    pref_slug, city_slug = _normalize_area(pref, city)
    if not slug:
        msg = "Gym slug must be provided"
        raise ValueError(msg)
    return f"{BASE_URL}/gyms/{pref_slug}/{city_slug}/{slug}"


def iter_listing_urls(pref: str, city: str) -> Iterator[str]:
    """Yield listing URLs for supported prefecture/city pairs."""

    pref_slug, city_slug = _normalize_area(pref, city)
    for page in _LISTING_PAGE_RANGE:
        yield build_listing_url(pref_slug, city_slug, page)


def iter_detail_urls_from_listing(html: str) -> list[str]:
    """Extract absolute detail URLs from a listing HTML page."""

    soup = BeautifulSoup(html or "", "html.parser")
    urls: list[str] = []
    for link in soup.select("a.gym-link"):
        href = (link.get("href") or "").strip()
        if not href:
            continue
        urls.append(urljoin(BASE_URL, href))
    return urls
