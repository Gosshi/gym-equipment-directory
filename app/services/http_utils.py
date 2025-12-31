"""Shared HTTP utilities for robots.txt parsing and URL fetching."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import NamedTuple
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
    """Result of robots.txt check."""

    rules: RobotsRules | None
    proceed: bool


def parse_robots(txt: str, *, user_agent: str) -> RobotsRules:
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
    respect_robots: bool = True,
) -> RobotsDecision:
    """Load and parse robots.txt for the given base URL.

    Args:
        client: HTTP client to use for fetching
        base_url: Base URL to fetch robots.txt from
        user_agent: User agent string for robots.txt parsing
        timeout: Request timeout in seconds
        respect_robots: If True, return proceed=False on errors; if False, proceed anyway

    Returns:
        RobotsDecision with rules and whether to proceed.
    """
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        response = await client.get(robots_url, timeout=timeout)
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch robots.txt from %s: %s", robots_url, exc)
        if respect_robots:
            logger.warning("Aborting fetch because robots.txt could not be loaded")
            return RobotsDecision(None, False)
        logger.warning("Continuing because respect_robots=False")
        return RobotsDecision(None, True)

    status = response.status_code
    if status == 200:
        rules = parse_robots(response.text or "", user_agent=user_agent)
        return RobotsDecision(rules, True)
    if status == 404:
        # No robots.txt means everything is allowed
        logger.debug("robots.txt returned 404 for %s; proceeding", robots_url)
        return RobotsDecision(None, True)
    if status >= 400:
        if respect_robots:
            logger.warning(
                "robots.txt returned status %s from %s; aborting",
                status,
                robots_url,
            )
            return RobotsDecision(None, False)
        logger.warning(
            "robots.txt status %s from %s; continuing because respect_robots=False",
            status,
            robots_url,
        )
        return RobotsDecision(None, True)

    rules = parse_robots(response.text or "", user_agent=user_agent)
    return RobotsDecision(rules, True)


async def request_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = RETRY_ATTEMPTS,
) -> httpx.Response:
    """Execute an HTTP GET with retry logic.

    Args:
        client: HTTP client to use
        url: URL to fetch
        headers: Optional headers to include
        timeout: Request timeout in seconds
        retries: Number of retry attempts

    Returns:
        HTTP response

    Raises:
        httpx.HTTPError: If all retry attempts fail
    """
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return await client.get(url, headers=headers, timeout=timeout)
        except httpx.HTTPError as exc:
            last_error = exc
            logger.warning(
                "HTTP request failed (attempt %s/%s) for %s: %s",
                attempt,
                retries,
                url,
                exc,
            )
            await asyncio.sleep(0.5 * attempt)
    assert last_error is not None
    raise last_error


def is_path_allowed(url: str, robots: RobotsRules | None) -> bool:
    """Check if a URL path is allowed by robots.txt rules."""
    if robots is None:
        return True
    parsed = urlparse(url)
    return robots.allows(parsed.path)


async def fetch_url_checked(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = DEFAULT_TIMEOUT,
    respect_robots: bool = True,
) -> tuple[str | None, int | None, str | None]:
    """Fetch a URL with robots.txt checking.

    Args:
        url: URL to fetch
        user_agent: User agent string
        timeout: Request timeout in seconds
        respect_robots: Whether to respect robots.txt

    Returns:
        Tuple of (html_content, status_code, failure_reason) on failure
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
            respect_robots=respect_robots,
        )
        if not decision.proceed:
            logger.info("Scraping blocked by robots.txt policy for %s", url)
            return None, None, "robots_blocked"

        if not is_path_allowed(url, decision.rules):
            logger.info("URL path blocked by robots.txt: %s", url)
            return None, None, "robots_blocked"

        try:
            response = await request_with_retries(client, url, timeout=timeout)
        except httpx.HTTPError:
            return None, None, "request_failed"

        if response.status_code != 200:
            logger.warning("URL %s returned status %s", url, response.status_code)
            return None, response.status_code, "http_status"

        return response.text, response.status_code, None
