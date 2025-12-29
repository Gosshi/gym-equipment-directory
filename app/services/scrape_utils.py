"""Scraping utilities for on-demand URL fetching during candidate approval."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any, NamedTuple
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "GymDirectoryBot/0.1 (+contact-url)"
DEFAULT_TIMEOUT = 15.0
RETRY_ATTEMPTS = 3


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


class RobotsDecision(NamedTuple):
    rules: RobotsRules | None
    proceed: bool


def _parse_robots(txt: str, *, user_agent: str) -> RobotsRules:
    """Parse robots.txt content and return RobotsRules for the given user agent."""
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


async def load_robots(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = DEFAULT_TIMEOUT,
) -> RobotsDecision:
    """Load and parse robots.txt for the given base URL.

    Returns a RobotsDecision with rules and whether to proceed.
    """
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        response = await client.get(robots_url, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch robots.txt from %s: %s", robots_url, exc)
        return RobotsDecision(None, False)

    status = response.status_code
    if status == 200:
        rules = _parse_robots(response.text or "", user_agent=user_agent)
        return RobotsDecision(rules, True)
    if status == 404:
        # No robots.txt means everything is allowed
        return RobotsDecision(None, True)
    if status >= 400:
        logger.warning(
            "robots.txt returned status %s from %s; blocking scrape",
            status,
            robots_url,
        )
        return RobotsDecision(None, False)

    rules = _parse_robots(response.text or "", user_agent=user_agent)
    return RobotsDecision(rules, True)


async def fetch_url_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> httpx.Response | None:
    """Fetch a URL with retry logic. Returns None on failure."""
    last_error: Exception | None = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            return await client.get(url, timeout=timeout)
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning(
                "HTTP request failed (attempt %s/%s) for %s: %s",
                attempt,
                RETRY_ATTEMPTS,
                url,
                exc,
            )
            await asyncio.sleep(0.5 * attempt)
    logger.error("All retry attempts failed for %s: %s", url, last_error)
    return None


def is_url_allowed_by_robots(
    url: str,
    robots: RobotsRules | None,
) -> bool:
    """Check if a URL path is allowed by robots.txt rules."""
    if robots is None:
        return True
    parsed = urlparse(url)
    return robots.allows(parsed.path)


async def check_url_scrapable(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = DEFAULT_TIMEOUT,
) -> bool:
    """Check if a URL is scrapable (not blocked by robots.txt).

    Returns True if the URL can be scraped, False otherwise.
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(
        headers={"User-Agent": user_agent},
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        decision = await load_robots(
            client,
            base_url=base_url,
            user_agent=user_agent,
            timeout=timeout,
        )
        if not decision.proceed:
            return False
        return is_url_allowed_by_robots(url, decision.rules)


async def fetch_and_parse_url(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[str | None, int | None]:
    """Fetch a URL and return its HTML content and status code.

    Returns (html_content, status_code) or (None, None) on failure.
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient(
        headers={"User-Agent": user_agent},
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        # Check robots.txt first
        decision = await load_robots(
            client,
            base_url=base_url,
            user_agent=user_agent,
            timeout=timeout,
        )
        if not decision.proceed:
            logger.info("Scraping blocked by robots.txt policy for %s", url)
            return None, None

        if not is_url_allowed_by_robots(url, decision.rules):
            logger.info("URL path blocked by robots.txt: %s", url)
            return None, None

        # Fetch the URL
        response = await fetch_url_with_retries(client, url, timeout=timeout)
        if response is None:
            return None, None

        if response.status_code != 200:
            logger.warning(
                "URL %s returned status %s",
                url,
                response.status_code,
            )
            return None, response.status_code

        return response.text, response.status_code


def merge_parsed_json(
    existing: dict[str, Any] | None,
    new_data: dict[str, Any],
) -> dict[str, Any]:
    """Merge new parsed data into existing parsed_json.

    - New non-empty values overwrite existing values
    - Arrays are concatenated and deduplicated
    - Nested dicts are recursively merged
    """
    if existing is None:
        return new_data.copy()

    result = existing.copy()

    for key, new_value in new_data.items():
        if new_value is None or new_value == "" or new_value == []:
            continue

        existing_value = result.get(key)

        if isinstance(new_value, dict) and isinstance(existing_value, dict):
            result[key] = merge_parsed_json(existing_value, new_value)
        elif isinstance(new_value, list) and isinstance(existing_value, list):
            # Concatenate and deduplicate
            combined = existing_value + new_value
            # Try to deduplicate if items are hashable
            try:
                seen: set[Any] = set()
                deduped = []
                for item in combined:
                    if item not in seen:
                        seen.add(item)
                        deduped.append(item)
                result[key] = deduped
            except TypeError:
                # Items not hashable, just concatenate
                result[key] = combined
        else:
            # Overwrite with new value
            result[key] = new_value

    return result
