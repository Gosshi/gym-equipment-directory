"""HTTP fetcher implementation for ingest pipeline sources."""

from __future__ import annotations

import asyncio
import logging
import os
import random
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select

from app.db import SessionLocal
from app.models.scraped_page import ScrapedPage

from .sites import municipal_koto, site_a
from .utils import get_or_create_source

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "GymDirectoryBot/0.1 (+contact-url)"
DEFAULT_TIMEOUT = 15.0
DEFAULT_LIMIT = 20
MAX_LIMIT = 30
PROD_MAX_LIMIT = 20
DEFAULT_MIN_DELAY = 2.0
DEFAULT_MAX_DELAY = 5.0
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
    municipal_koto.SITE_ID: HttpSiteConfig(
        module=municipal_koto,
        base_url=municipal_koto.BASE_URL,
        allowed_hosts=municipal_koto.ALLOWED_HOSTS,
        supported_areas=set(municipal_koto.SUPPORTED_AREAS),
        uses_listing_pages=False,
    ),
}


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


async def _load_robots(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    user_agent: str,
    timeout: float,
) -> RobotsRules | None:
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        response = await client.get(robots_url, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch robots.txt from %s: %s", robots_url, exc)
        return None
    if response.status_code >= 400:
        logger.warning(
            "robots.txt returned unexpected status %s from %s",
            response.status_code,
            robots_url,
        )
        return None
    return _parse_robots(response.text or "", user_agent=user_agent)


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
    listing_urls = list(config.module.iter_listing_urls(pref, city))
    detail_urls: list[str] = []
    seen: set[str] = set()
    if config.uses_listing_pages:
        for listing_url in listing_urls:
            _ensure_allowed_domain(listing_url, config.allowed_hosts)
            parsed_listing = urlparse(listing_url)
            if respect_robots and robots and not robots.allows(parsed_listing.path):
                logger.warning("Skipping listing due to robots.txt: %s", listing_url)
                continue
            try:
                response = await client.get(listing_url, timeout=timeout)
            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch listing %s: %s", listing_url, exc)
                continue
            if response.status_code != 200:
                logger.warning(
                    "Listing request returned status %s for %s",
                    response.status_code,
                    listing_url,
                )
                continue
            for url in config.module.iter_detail_urls_from_listing(response.text):
                absolute = _ensure_allowed_domain(url, config.allowed_hosts)
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
            absolute = _ensure_allowed_domain(detail_url, config.allowed_hosts)
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
) -> tuple[bool, bool]:
    now = datetime.now(UTC)
    status = response.status_code
    meta = _extract_response_meta(response)
    if status == 200:
        html = response.text
        content_hash = sha256(html.encode("utf-8")).hexdigest()
        merged_meta = _merge_meta(existing.response_meta if existing else None, meta)
        if existing is None:
            page = ScrapedPage(
                source_id=source_id,
                url=url,
                fetched_at=now,
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
        existing.response_meta = merged_meta
        return False, True
    logger.warning("Detail request returned status %s for %s", status, url)
    return False, False


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
    config = SITE_CONFIGS.get(source)
    if config is None:
        msg = f"Unsupported source for HTTP fetch: {source}"
        raise ValueError(msg)

    pref = pref.strip().lower()
    city = city.strip().lower()
    if (pref, city) not in config.supported_areas:
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
        robots: RobotsRules | None = None
        if respect_robots:
            robots = await _load_robots(
                client,
                base_url=config.base_url,
                user_agent=user_agent,
                timeout=timeout,
            )
            if robots is None:
                logger.warning("Aborting fetch because robots.txt could not be loaded")
                return 1

        detail_urls = await _collect_detail_urls(
            client,
            config=config,
            pref=pref,
            city=city,
            limit=effective_limit,
            respect_robots=respect_robots,
            robots=robots,
            timeout=timeout,
        )

        if not detail_urls:
            logger.info(
                "No detail URLs discovered for %s/%s (limit=%s)",
                pref,
                city,
                effective_limit,
            )
            return 0

        if dry_run:
            for url in detail_urls:
                print(url)
            logger.info("Dry-run listed %s detail URLs for %s/%s", len(detail_urls), pref, city)
            return 0

        async with SessionLocal() as session:
            source_obj = await get_or_create_source(session, title=source)
            success = 0
            not_modified = 0
            failures = 0
            for index, url in enumerate(detail_urls):
                _ensure_allowed_domain(url, config.allowed_hosts)
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

                ok, cached = await _upsert_detail_page(
                    session,
                    source_id=source_obj.id,
                    url=url,
                    response=response,
                    existing=existing_page,
                )
                if ok:
                    success += 1
                elif cached:
                    not_modified += 1
                else:
                    failures += 1

                if index < len(detail_urls) - 1:
                    delay = random.uniform(min_delay, max_delay)
                    await asyncio.sleep(delay)

            await session.commit()

        sample = ", ".join(detail_urls[:2])
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
