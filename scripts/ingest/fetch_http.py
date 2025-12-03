"""HTTP fetcher implementation for ingest pipeline sources."""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, NamedTuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.db import SessionLocal
from app.models.scraped_page import ScrapedPage

from .sites import site_a
from .sources_registry import SOURCES, MunicipalSource
from .utils import get_or_create_source

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "GymDirectoryBot/0.1 (+contact-url)"
DEFAULT_TIMEOUT = 15.0
DEFAULT_LIMIT = 20
MAX_LIMIT = 30
PROD_MAX_LIMIT = 120
DEFAULT_MIN_DELAY = 2.0
DEFAULT_MAX_DELAY = 5.0
BATCH_SIZE = 20
RETRY_ATTEMPTS = 3


@dataclass(frozen=True)
class HttpSiteConfig:
    module: Any
    base_url: str
    allowed_hosts: tuple[str, ...]
    supported_areas: set[tuple[str, str]]
    uses_listing_pages: bool


SITE_CONFIGS: dict[str, HttpSiteConfig] = {
    site_a.SITE_ID: HttpSiteConfig(
        module=site_a,
        base_url=site_a.BASE_URL,
        allowed_hosts=site_a.ALLOWED_HOSTS,
        supported_areas=set(site_a.SUPPORTED_HTTP_AREAS),
        uses_listing_pages=True,
    ),
}

MUNICIPAL_PAGE_TYPE_META_KEY = "municipal_page_type"
MUNICIPAL_MAX_DEPTH = 2


@dataclass(frozen=True)
class MunicipalDiscoveredPage:
    url: str
    page_type: str | None


class RobotsRules:
    """Simple representation of robots.txt disallow rules."""

    def __init__(self, disallow_rules: Iterable[str]):
        cleaned = []
        for rule in disallow_rules:
            rule = rule.strip()
            if not rule:
                continue
            cleaned.append(rule)
        self._rules = tuple(cleaned)

    def allows(self, path: str) -> bool:
        """Return whether ``path`` is allowed."""

        if not self._rules:
            return True
        for rule in self._rules:
            if rule == "/":
                return False
            normalized = rule.rstrip("*")
            if normalized and path.startswith(normalized):
                return False
        return True


def _resolve_limit(raw_limit: int | None, app_env: str) -> int:
    max_limit = PROD_MAX_LIMIT if app_env == "prod" else MAX_LIMIT
    default_limit = min(DEFAULT_LIMIT, max_limit)
    if raw_limit is None:
        return default_limit
    if raw_limit < 1:
        msg = "limit must be >= 1"
        raise ValueError(msg)
    if raw_limit > max_limit:
        msg = f"limit must be <= {max_limit} for environment '{app_env or 'dev'}'"
        raise ValueError(msg)
    return raw_limit


def _ensure_allowed_domain(url: str, allowed_hosts: Iterable[str]) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        msg = f"Unsupported URL scheme for '{url}'"
        raise ValueError(msg)
    hosts = set(allowed_hosts)
    if parsed.netloc not in hosts:
        msg = f"URL '{url}' is not part of the allowed domains"
        raise ValueError(msg)
    return url


def _resolve_absolute_url(url_or_path: str, base_url: str) -> str:
    parsed = urlparse(url_or_path)
    if parsed.scheme in {"http", "https"}:
        return url_or_path
    return urljoin(base_url, url_or_path)


def _normalize_path(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") + "/"
    return path


def _classify_municipal_url(
    url: str,
    *,
    source: MunicipalSource,
    intro_patterns: list[re.Pattern[str]],
    article_patterns: list[re.Pattern[str]],
    intro_seed_paths: set[str],
) -> str | None:
    path = _normalize_path(url)
    if path in intro_seed_paths:
        return "intro"
    for pattern in intro_patterns:
        if pattern.search(path):
            return "intro"
    for pattern in article_patterns:
        if pattern.search(path):
            return "article"
    return None


def _iter_links(html: str) -> Iterable[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if not href:
            continue
        yield href


async def _discover_municipal_pages(
    client: httpx.AsyncClient,
    *,
    source: MunicipalSource,
    limit: int,
    respect_robots: bool,
    robots: RobotsRules | None,
    timeout: float,
) -> list[MunicipalDiscoveredPage]:
    parsed_base = urlparse(source.base_url)
    allowed_hosts = set(source.allowed_hosts) if source.allowed_hosts else {parsed_base.netloc}
    intro_patterns = source.compile_intro_patterns()
    article_patterns = source.compile_article_patterns()
    intro_seed_paths = {
        _normalize_path(_resolve_absolute_url(seed, source.base_url)) for seed in source.list_seeds
    }
    queue: deque[tuple[str, int]] = deque()
    seen: set[str] = set()
    results: list[MunicipalDiscoveredPage] = []

    for seed in source.list_seeds:
        absolute = _resolve_absolute_url(seed, source.base_url)
        queue.append((absolute, 0))

    while queue and len(results) < limit:
        current_url, depth = queue.popleft()
        parsed = urlparse(current_url)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc not in allowed_hosts:
            continue
        if current_url in seen:
            continue
        if respect_robots and robots and not robots.allows(parsed.path):
            logger.debug("Skipping %s due to robots.txt", current_url)
            continue
        seen.add(current_url)
        try:
            response = await client.get(current_url, timeout=timeout)
        except httpx.HTTPError as exc:
            logger.warning("Failed to crawl %s: %s", current_url, exc)
            continue
        if response.status_code != 200:
            logger.debug("Crawl for %s returned status %s", current_url, response.status_code)
            continue

        classification = _classify_municipal_url(
            current_url,
            source=source,
            intro_patterns=intro_patterns,
            article_patterns=article_patterns,
            intro_seed_paths=intro_seed_paths,
        )
        if classification or current_url in intro_seed_paths:
            results.append(MunicipalDiscoveredPage(url=current_url, page_type=classification))
            if len(results) >= limit:
                break

        if depth >= MUNICIPAL_MAX_DEPTH:
            continue

        for href in _iter_links(response.text or ""):
            resolved = _resolve_absolute_url(href, current_url)
            parsed_resolved = urlparse(resolved)
            if parsed_resolved.netloc not in allowed_hosts:
                continue
            if respect_robots and robots and not robots.allows(parsed_resolved.path):
                continue
            if resolved in seen:
                continue
            queue.append((resolved, depth + 1))

    return results


def _parse_robots(txt: str, *, user_agent: str) -> RobotsRules:
    disallow: list[str] = []
    active = False
    agent_lower = user_agent.lower()
    for line in txt.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lower().startswith("user-agent:"):
            value = stripped.split(":", 1)[1].strip()
            value_lower = value.lower()
            active = value_lower in {"*", agent_lower}
            continue
        if not active:
            continue
        if stripped.lower().startswith("disallow:"):
            value = stripped.split(":", 1)[1].strip()
            disallow.append(value)
    return RobotsRules(disallow)


async def _request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return await client.get(url, headers=headers)
        except httpx.HTTPError as exc:  # pragma: no cover - retried path
            last_error = exc
            logger.warning(
                "HTTP request failed (attempt %s/%s) for %s: %s",
                attempt,
                RETRY_ATTEMPTS,
                url,
                exc,
            )
            await asyncio.sleep(0.5 * attempt)
    assert last_error is not None  # for type checkers
    raise last_error


class RobotsDecision(NamedTuple):
    rules: RobotsRules | None
    proceed: bool


async def _load_robots(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    user_agent: str,
    timeout: float,
    respect_robots: bool,
) -> RobotsDecision:
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        response = await client.get(robots_url, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch robots.txt from %s: %s", robots_url, exc)
        if respect_robots:
            logger.warning("Aborting fetch because robots.txt could not be loaded")
            return RobotsDecision(None, False)
        logger.warning("Continuing because --respect-robots=false")
        return RobotsDecision(None, True)

    status = response.status_code
    if status == 200:
        rules = _parse_robots(response.text or "", user_agent=user_agent)
        return RobotsDecision(rules, True)
    if status == 404:
        logger.warning(
            "robots.txt returned 404; proceeding as 'no robots' for %s",
            robots_url,
        )
        return RobotsDecision(None, True)
    if status >= 400:
        if respect_robots:
            logger.warning(
                "robots.txt returned status %s from %s; aborting due to respect_robots",
                status,
                robots_url,
            )
            return RobotsDecision(None, False)
        logger.warning(
            "robots.txt status %s from %s; continuing because --respect-robots=false",
            status,
            robots_url,
        )
        return RobotsDecision(None, True)

    rules = _parse_robots(response.text or "", user_agent=user_agent)
    return RobotsDecision(rules, True)


async def _collect_detail_urls(
    client: httpx.AsyncClient,
    *,
    config: HttpSiteConfig,
    pref: str,
    city: str,
    limit: int,
    respect_robots: bool,
    robots: RobotsRules | None,
    timeout: float,
) -> list[str]:
    try:
        listing_iterable = config.module.iter_listing_urls(pref, city, limit=limit)
    except TypeError:
        listing_iterable = config.module.iter_listing_urls(pref, city)
    listing_urls = list(listing_iterable)
    detail_urls: list[str] = []
    seen: set[str] = set()
    if config.uses_listing_pages:
        for listing_url in listing_urls:
            absolute_listing = _resolve_absolute_url(listing_url, config.base_url)
            _ensure_allowed_domain(absolute_listing, config.allowed_hosts)
            parsed_listing = urlparse(absolute_listing)
            if respect_robots and robots and not robots.allows(parsed_listing.path):
                logger.warning("Skipping listing due to robots.txt: %s", absolute_listing)
                continue
            try:
                response = await client.get(absolute_listing, timeout=timeout)
            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch listing %s: %s", absolute_listing, exc)
                continue
            if response.status_code != 200:
                logger.warning(
                    "Listing request returned status %s for %s",
                    response.status_code,
                    absolute_listing,
                )
                continue
            for url in config.module.iter_detail_urls_from_listing(response.text):
                resolved = _resolve_absolute_url(url, config.base_url)
                absolute = _ensure_allowed_domain(resolved, config.allowed_hosts)
                parsed = urlparse(absolute)
                if respect_robots and robots and not robots.allows(parsed.path):
                    logger.warning("Skipping detail due to robots.txt: %s", absolute)
                    continue
                if absolute in seen:
                    continue
                seen.add(absolute)
                detail_urls.append(absolute)
                if len(detail_urls) >= limit:
                    return detail_urls
    else:
        for detail_url in listing_urls:
            resolved = _resolve_absolute_url(detail_url, config.base_url)
            absolute = _ensure_allowed_domain(resolved, config.allowed_hosts)
            parsed = urlparse(absolute)
            if respect_robots and robots and not robots.allows(parsed.path):
                logger.warning("Skipping detail due to robots.txt: %s", absolute)
                continue
            if absolute in seen:
                continue
            seen.add(absolute)
            detail_urls.append(absolute)
            if len(detail_urls) >= limit:
                break
    return detail_urls


def _extract_response_meta(response: httpx.Response) -> dict[str, str]:
    meta: dict[str, str] = {}
    etag = response.headers.get("ETag")
    if etag:
        meta["etag"] = etag
    last_modified = response.headers.get("Last-Modified")
    if last_modified:
        meta["last_modified"] = last_modified
    content_type = response.headers.get("Content-Type")
    if content_type:
        parts = [part.strip() for part in content_type.split(";") if part.strip()]
        if parts:
            meta["content_type"] = parts[0]
        for part in parts[1:]:
            if part.lower().startswith("charset="):
                meta["charset"] = part.split("=", 1)[1].strip()
                break
    if "charset" not in meta and response.encoding:
        meta["charset"] = response.encoding
    content_language = response.headers.get("Content-Language")
    if content_language:
        meta["lang"] = content_language.split(",")[0].strip()
    return meta


def _merge_meta(existing: dict[str, Any] | None, new_meta: dict[str, str]) -> dict[str, Any] | None:
    if not new_meta:
        return existing
    merged = dict(existing or {})
    merged.update(new_meta)
    return merged


async def _upsert_detail_page(
    session,
    *,
    source_id: int,
    url: str,
    response: httpx.Response,
    existing: ScrapedPage | None,
    extra_meta: dict[str, Any] | None = None,
) -> tuple[bool, bool]:
    now = datetime.now(UTC)
    status = response.status_code
    meta = _extract_response_meta(response)
    if status == 200:
        html = response.text
        content_hash = sha256(html.encode("utf-8")).hexdigest()
        merged_meta = _merge_meta(existing.response_meta if existing else None, meta)
        merged_meta = _merge_extra_meta(merged_meta, extra_meta)
        if existing is None:
            page = ScrapedPage(
                source_id=source_id,
                url=url,
                fetched_at=datetime.now(UTC),
                http_status=status,
                raw_html=html,
                content_hash=content_hash,
                response_meta=merged_meta,
            )
            session.add(page)
        else:
            existing.raw_html = html
            existing.http_status = status
            existing.fetched_at = now
            existing.content_hash = content_hash
            existing.response_meta = merged_meta
        return True, False
    if status == 304:
        if existing is None:
            logger.warning("Received 304 for %s but no cached page exists", url)
            return False, False
        existing.fetched_at = now
        existing.http_status = status
        merged_meta = _merge_meta(existing.response_meta, meta)
        merged_meta = _merge_extra_meta(merged_meta, extra_meta)
        existing.response_meta = merged_meta
        return False, True
    logger.warning("Detail request returned status %s for %s", status, url)
    return False, False


def _merge_extra_meta(
    meta: dict[str, Any] | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not extra:
        return meta
    merged = dict(meta or {})
    merged.update(extra)
    return merged


async def fetch_http_pages(
    source: str,
    *,
    pref: str,
    city: str,
    limit: int | None,
    min_delay: float,
    max_delay: float,
    respect_robots: bool,
    user_agent: str,
    timeout: float,
    dry_run: bool,
    force: bool,
) -> int:
    source = source.strip()
    municipal_source = SOURCES.get(source)
    config = SITE_CONFIGS.get(source)
    if municipal_source is None and config is None:
        msg = f"Unsupported source for HTTP fetch: {source}"
        raise ValueError(msg)

    pref = pref.strip().lower()
    city = city.strip().lower()
    if municipal_source is not None:
        if pref != municipal_source.pref_slug or city != municipal_source.city_slug:
            msg = f"Unsupported area combination: pref={pref}, city={city}"
            raise ValueError(msg)
    elif config is not None and (pref, city) not in config.supported_areas:
        msg = f"Unsupported area combination: pref={pref}, city={city}"
        raise ValueError(msg)

    if min_delay <= 0 or max_delay <= 0:
        msg = "Delays must be positive values"
        raise ValueError(msg)
    if min_delay > max_delay:
        msg = "min-delay cannot be greater than max-delay"
        raise ValueError(msg)

    app_env = os.getenv("APP_ENV", "").lower()
    effective_limit = _resolve_limit(limit, app_env)
    if app_env == "prod":
        respect_robots = True

    headers = {"User-Agent": user_agent}

    async with httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        base_url = municipal_source.base_url if municipal_source else config.base_url
        decision = await _load_robots(
            client,
            base_url=base_url,
            user_agent=user_agent,
            timeout=timeout,
            respect_robots=respect_robots,
        )
        if respect_robots and not decision.proceed:
            return 1
        robots = decision.rules if respect_robots else None

        if municipal_source is not None:
            detail_pages = await _discover_municipal_pages(
                client,
                source=municipal_source,
                limit=effective_limit,
                respect_robots=respect_robots,
                robots=robots,
                timeout=timeout,
            )
            detail_urls = detail_pages
        else:
            collector = getattr(config.module, "collect_detail_urls", None)
            if callable(collector):
                collected = await collector(
                    client,
                    base_url=config.base_url,
                    allowed_hosts=config.allowed_hosts,
                    pref=pref,
                    city=city,
                    limit=effective_limit,
                    respect_robots=respect_robots,
                    robots_allows=robots.allows if (respect_robots and robots) else None,
                    timeout=timeout,
                )
                detail_urls = [
                    MunicipalDiscoveredPage(url=item, page_type=None) for item in collected
                ]
            else:
                collected_urls = await _collect_detail_urls(
                    client,
                    config=config,
                    pref=pref,
                    city=city,
                    limit=effective_limit,
                    respect_robots=respect_robots,
                    robots=robots,
                    timeout=timeout,
                )
                detail_urls = [
                    MunicipalDiscoveredPage(url=item, page_type=None) for item in collected_urls
                ]

        if not detail_urls:
            logger.info(
                "No detail URLs discovered for %s/%s (limit=%s)",
                pref,
                city,
                effective_limit,
            )
            return 0

        if dry_run:
            for page in detail_urls:
                print(page.url)
            logger.info("Dry-run listed %s detail URLs for %s/%s", len(detail_urls), pref, city)
            return 0

        async with SessionLocal() as session:
            source_obj = await get_or_create_source(session, title=source)
            success = 0
            not_modified = 0
            failures = 0
            processed_in_batch = 0
            for index, page in enumerate(detail_urls):
                url = page.url
                allowed_hosts = (
                    tuple(municipal_source.allowed_hosts)
                    if municipal_source and municipal_source.allowed_hosts
                    else (urlparse(municipal_source.base_url).netloc,)
                    if municipal_source
                    else config.allowed_hosts
                )
                _ensure_allowed_domain(url, allowed_hosts)
                headers = {"User-Agent": user_agent}
                existing_result = await session.execute(
                    select(ScrapedPage).where(
                        ScrapedPage.source_id == source_obj.id,
                        ScrapedPage.url == url,
                    )
                )
                existing_page = existing_result.scalar_one_or_none()
                if not force and existing_page and existing_page.response_meta:
                    conditional_headers: dict[str, str] = {}
                    etag = existing_page.response_meta.get("etag")
                    if isinstance(etag, str) and etag:
                        conditional_headers["If-None-Match"] = etag
                    last_modified = existing_page.response_meta.get("last_modified")
                    if isinstance(last_modified, str) and last_modified:
                        conditional_headers["If-Modified-Since"] = last_modified
                    headers.update(conditional_headers)
                try:
                    response = await _request_with_retries(client, url, headers=headers)
                except httpx.HTTPError as exc:
                    logger.warning("Failed to fetch detail %s: %s", url, exc)
                    failures += 1
                    continue

                extra_meta = {}
                if page.page_type:
                    extra_meta[MUNICIPAL_PAGE_TYPE_META_KEY] = page.page_type

                ok, cached = await _upsert_detail_page(
                    session,
                    source_id=source_obj.id,
                    url=url,
                    response=response,
                    existing=existing_page,
                    extra_meta=extra_meta or None,
                )
                if ok:
                    success += 1
                elif cached:
                    not_modified += 1
                else:
                    failures += 1

                processed_in_batch += 1
                if processed_in_batch % BATCH_SIZE == 0:
                    await session.commit()
                    session.expunge_all()

                if index < len(detail_urls) - 1:
                    delay = random.uniform(min_delay, max_delay)
                    await asyncio.sleep(delay)

            await session.commit()
            session.expunge_all()

        sample = ", ".join(page.url for page in detail_urls[:2])
        logger.info(
            "Fetch summary for %s/%s: success=%s, not_modified=%s, failures=%s",
            pref,
            city,
            success,
            not_modified,
            failures,
        )
        if sample:
            logger.info("Sample detail URLs: %s%s", sample, "..." if len(detail_urls) > 2 else "")

    return 0
