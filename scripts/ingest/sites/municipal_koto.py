"""Helpers for scraping Koto municipal sports facility pages."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from typing import Any, Final
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ._municipal_base import extract_address, normalize_text

logger = logging.getLogger(__name__)

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

_SEED_FACILITIES: Final[tuple[dict[str, Any], ...]] = (
    {
        "path": "/sports_center2/",
        "name": "深川北スポーツセンター",
        "address": "東京都江東区北砂1-2-3",
        "equipments": (
            "トレーニング室（マシン・ダンベル・スミスマシン）",
            "フリーウエイトゾーン（ベンチプレス・ラットプルダウン）",
            "有酸素エリア（エアロバイク）",
        ),
    },
    {
        "path": "/sports_center3/",
        "name": "亀戸スポーツセンター",
        "address": "東京都江東区亀戸2-4-6",
        "equipments": (
            "トレーニング室（マシン・ベンチプレス・スミスマシン）",
            "ダンベルセット完備",
            "ラットプルマシンとレッグプレス",
        ),
    },
    {
        "path": "/sports_center4/",
        "name": "有明スポーツセンター",
        "address": "東京都江東区有明2-3-5",
        "equipments": (
            "最新マシンとダンベルのトレーニング室",
            "ラットプルダウンステーション",
            "レッグプレスマシン",
            "有酸素マシン（エアロバイク）",
        ),
    },
    {
        "path": "/sports_center5/",
        "name": "東砂スポーツセンター",
        "address": "東京都江東区東砂4-24-1",
        "equipments": (
            "スミスマシンとベンチプレス台",
            "ダンベル・ラットプルダウン完備",
            "レッグプレスのある筋力トレーニング室",
        ),
    },
    {
        "path": "/sports_center2/introduction/",
        "name": "深川北スポーツセンター",
        "address": "東京都江東区北砂1-2-3",
        "equipments": (
            "スミスマシンやベンチプレスのトレーニング室",
            "有酸素マシンとしてエアロバイクを配置",
        ),
        "title_suffix": "施設案内",
    },
    {
        "path": "/sports_center3/introduction/",
        "name": "亀戸スポーツセンター",
        "address": "東京都江東区亀戸2-4-6",
        "equipments": (
            "ベンチプレスとスミスマシンを備えるトレーニングエリア",
            "ダンベルとラットプルダウンを用意",
        ),
        "title_suffix": "施設案内",
    },
    {
        "path": "/sports_center4/introduction/",
        "name": "有明スポーツセンター",
        "address": "東京都江東区有明2-3-5",
        "equipments": (
            "ダンベルとラットプルダウンの強化スペース",
            "レッグプレスとエアロバイクのトレーニング設備",
        ),
        "title_suffix": "施設案内",
    },
    {
        "path": "/sports_center5/introduction/",
        "name": "東砂スポーツセンター",
        "address": "東京都江東区東砂4-24-1",
        "equipments": (
            "スミスマシン中心のトレーニング室",
            "ベンチプレス・ダンベル・ラットプルダウンを完備",
        ),
        "title_suffix": "施設案内",
    },
)


def _build_directory_paths() -> tuple[str, ...]:
    directories: set[str] = set()
    for facility in _SEED_FACILITIES:
        path = str(facility.get("path", ""))
        if not path:
            continue
        if not path.endswith("/"):
            path = f"{path}/"
        if path.endswith("/introduction//"):
            path = path.rstrip("/")
        if path.endswith("/introduction/"):
            directories.add(path)
            continue
        directories.add(f"{path}introduction/")
    return tuple(sorted(directories))


_FACILITY_DIRECTORY_PATHS: Final[tuple[str, ...]] = _build_directory_paths()

_ALLOWED_PATH_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"/sports_center\d+/introduction/?$"),
    re.compile(r"/sports_center\d+/introduction/tr_detail\.html$"),
    re.compile(r"/sports_center\d+/introduction/trainingmachine\.html$"),
    re.compile(r"/sports_center\d+/introduction/post_\d+\.html$"),
    re.compile(r"/sports_center\d+/introduction/[a-z0-9_-]+\.html$"),
)


def iter_listing_urls(pref: str, city: str, *, limit: int | None = None) -> Iterable[str]:
    """Return a slice of known detail paths for the supported area."""

    _ = pref, city  # unused but keeps signature consistent
    paths = list(_FACILITY_DIRECTORY_PATHS)
    if limit is not None:
        clamped = max(0, min(limit, len(paths)))
        paths = paths[:clamped]
    return paths


def _render_seed_html(seed: dict[str, Any]) -> str:
    equipments_html = "\n".join(f"          <li>{item}</li>" for item in seed.get("equipments", ()))
    title_suffix = seed.get("title_suffix", "")
    if title_suffix:
        page_title = f"{seed['name']}｜{title_suffix}｜江東区"
    else:
        page_title = f"{seed['name']}｜江東区"
    description = seed.get("description", "")
    description_html = f"      <p>{description}</p>" if description else ""
    address = seed.get("address", "")
    address_html = f"      <address>{address}</address>" if address else ""
    return (
        "<html>\n"
        f"  <head><title>{page_title}</title></head>\n"
        "  <body>\n"
        f'    <div class="breadcrumb">江東区 / {seed["name"]}</div>\n'
        f"    <h1>{seed['name']}</h1>\n"
        f"{address_html}\n"
        '    <section class="facility-detail">\n'
        "      <h2>トレーニング設備</h2>\n"
        '      <ul class="equipments">\n'
        f"{equipments_html}\n"
        "      </ul>\n"
        f"{description_html}\n"
        "    </section>\n"
        "  </body>\n"
        "</html>"
    )


def seed_pages(limit: int | None = None) -> list[tuple[str, str]]:
    """Return a static catalogue of seed pages for municipal Koto."""

    items = list(_SEED_FACILITIES)
    if limit is not None:
        clamped = max(0, min(limit, len(items)))
        items = items[:clamped]
    pages: list[tuple[str, str]] = []
    for seed in items:
        url = f"{BASE_URL}{seed['path']}" if seed["path"].startswith("/") else seed["path"]
        html = _render_seed_html(seed)
        pages.append((url, html))
    return pages


_ADDRESS_LABELS: Final[tuple[str, ...]] = ("所在地", "住所")
_ADDRESS_TAGS: Final[tuple[str, ...]] = ("dt", "dd", "th", "td", "p", "li", "span", "div")
_BREADCRUMB_TAGS: Final[tuple[str, ...]] = ("nav", "ol", "ul", "h2", "h3", "h4", "h5")


def _path_matches(path: str) -> bool:
    return any(pattern.match(path) for pattern in _ALLOWED_PATH_PATTERNS)


def _same_directory(directory_path: str, candidate_path: str) -> bool:
    normalized_directory = directory_path if directory_path.endswith("/") else f"{directory_path}/"
    return candidate_path.startswith(normalized_directory)


def _normalize_url(url: str, base_url: str) -> str:
    cleaned = url.split("#", 1)[0]
    return urljoin(base_url, cleaned)


async def collect_detail_urls(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    allowed_hosts: Iterable[str],
    pref: str,
    city: str,
    limit: int,
    respect_robots: bool,
    robots_allows: Callable[[str], bool] | None,
    timeout: float,
) -> list[str]:
    """Collect introduction subpages for municipal Koto facilities."""

    _ = pref, city
    detail_urls: list[str] = []
    seen: set[str] = set()
    for directory_path in _FACILITY_DIRECTORY_PATHS:
        if limit and len(detail_urls) >= limit:
            break
        directory_url = urljoin(base_url, directory_path)
        parsed_directory = urlparse(directory_url)
        if parsed_directory.netloc not in allowed_hosts:
            continue
        if respect_robots and robots_allows and not robots_allows(parsed_directory.path):
            logger.debug("Skipping directory due to robots: %s", directory_url)
            continue
        try:
            response = await client.get(directory_url, timeout=timeout)
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch municipal Koto directory %s: %s", directory_url, exc)
            continue
        if response.status_code != 200:
            logger.warning(
                "Directory request returned status %s for %s",
                response.status_code,
                directory_url,
            )
            continue

        candidates = [directory_url]
        soup = BeautifulSoup(response.text or "", "html.parser")
        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            if not href:
                continue
            absolute = _normalize_url(href, directory_url)
            parsed_absolute = urlparse(absolute)
            if parsed_absolute.netloc not in allowed_hosts:
                continue
            if respect_robots and robots_allows and not robots_allows(parsed_absolute.path):
                logger.debug("Skipping link due to robots: %s", absolute)
                continue
            if not _path_matches(parsed_absolute.path):
                continue
            if not _same_directory(parsed_directory.path, parsed_absolute.path):
                continue
            candidates.append(absolute)

        for candidate in candidates:
            if limit and len(detail_urls) >= limit:
                break
            parsed_candidate = urlparse(candidate)
            if parsed_candidate.netloc not in allowed_hosts:
                continue
            if not _path_matches(parsed_candidate.path):
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            detail_urls.append(candidate)
    return detail_urls


def parse_detail(html: str) -> dict[str, str | list[str] | None]:
    """Extract name, address, and equipment strings from a detail HTML page."""

    soup = BeautifulSoup(html or "", "html.parser")

    name = ""
    if h1 := soup.find("h1"):
        text = h1.get_text(" ", strip=True)
        if text:
            name = normalize_text(text)
    if not name and soup.title:
        title_text = soup.title.get_text(" ", strip=True)
        name = normalize_text(title_text)

    address = ""
    if address_tag := soup.find("address"):
        text = address_tag.get_text(" ", strip=True)
        address = normalize_text(text)
    if not address:
        # Labels such as 所在地 / 住所 that accompany a nearby value.
        for tag in soup.find_all(_ADDRESS_TAGS):
            raw_text = normalize_text(tag.get_text(" ", strip=True))
            if not raw_text:
                continue
            for label in _ADDRESS_LABELS:
                if label not in raw_text:
                    continue
                # Try to extract the value embedded in the same element.
                candidate = re.sub(rf"^{re.escape(label)}\s*[:：\-－\|｜]*", "", raw_text)
                candidate = normalize_text(candidate)
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
        extracted_address, _postal = extract_address(html)
        if extracted_address:
            address = normalize_text(extracted_address)
    if not address:
        # Breadcrumb or heading that at least indicates the ward.
        for crumb in soup.find_all(_BREADCRUMB_TAGS):
            crumb_text = normalize_text(crumb.get_text(" ", strip=True))
            if "江東区" in crumb_text:
                address = crumb_text
                break
    if not address:
        text = soup.get_text("\n", strip=True)
        for line in text.splitlines():
            if "〒" in line or "東京都" in line:
                address = normalize_text(line)
                if address:
                    break

    equipments_raw: list[str] = []
    keywords = ("トレーニング", "マシン", "ダンベル", "スミス", "ベンチ", "ラット")
    for li in soup.select("ul li"):
        value = normalize_text(li.get_text(" ", strip=True))
        if value and any(keyword in value for keyword in keywords):
            equipments_raw.append(value)
    if not equipments_raw:
        for paragraph in soup.select("p"):
            value = normalize_text(paragraph.get_text(" ", strip=True))
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
    "collect_detail_urls",
    "seed_pages",
    "iter_seed_pages",
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
            candidate = normalize_text(sibling.get_text(" ", strip=True))
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


def iter_seed_pages(limit: int | None = None):
    g = globals()
    for name in ("seed_pages", "iter_pages"):
        fn = g.get(name)
        if callable(fn):
            return fn(limit)
    for name in ("iter_seed_urls", "seed_urls", "iter_urls", "urls"):
        fn = g.get(name)
        if callable(fn):
            urls = list(fn(limit))
            return [{"url": u} for u in urls]
    raise NotImplementedError(
        "municipal_koto: no seed iterator found "
        "(expected one of seed_pages/iter_pages/iter_seed_urls/seed_urls)"
    )
