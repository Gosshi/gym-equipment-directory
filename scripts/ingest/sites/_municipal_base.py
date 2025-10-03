"""Common helpers for municipal facility scrapers."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Final
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

_FULLWIDTH_HYPHENS: Final[tuple[str, ...]] = (
    "−",
    "‐",
    "―",
    "ー",
    "ｰ",
    "–",
    "—",
    "─",
)

_POSTAL_CODE_RE: Final[re.Pattern[str]] = re.compile(r"〒?\s*(\d{3})[\-‐‑‒–—―−ーｰ－‐]?(\d{4})")
_ADDRESS_RE: Final[re.Pattern[str]] = re.compile(
    r"((?:東京都|北海道|(?:京都|大阪)府|[\wぁ-んァ-ヶ一-龯]{2,3}県)?[^\n]{0,30}(?:市|区|郡|町|村)[^\n]*?\d[^\n]*)"
)
_TEL_RE: Final[re.Pattern[str]] = re.compile(r"0\d{1,4}[\-\(（]??\d{1,4}[\-\)）]?\d{3,4}")
_IGNORE_URLS: Final[set[str]] = {"", "#", "#top", "javascript:void(0)", "javascript:;"}
_IGNORE_PREFIXES: Final[tuple[str, ...]] = ("javascript:",)


def normalize_text(value: str | None) -> str:
    """Return text normalized to NFC, without NULs, and compacted whitespace."""

    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value).replace("\x00", "")
    normalized = normalized.replace("\u3000", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def absolutize_url(base: str | None, href: str | None) -> str:
    """Convert *href* to an absolute URL using *base* when available."""

    if not href:
        return ""
    href = href.strip()
    if not href or href in _IGNORE_URLS:
        return ""
    if href.startswith(("mailto:", "tel:")):
        return href
    if href.startswith(_IGNORE_PREFIXES):
        return ""
    return urljoin(base or "", href)


def extract_links(html: str | None, base_url: str | None = None) -> list[str]:
    """Return unique non-anchor links from *html*, resolved from *base_url*."""

    soup = BeautifulSoup(html or "", "html.parser")
    results: list[str] = []
    seen: set[str] = set()
    for tag in soup.find_all("a"):
        href = tag.get("href")
        url = absolutize_url(base_url, href)
        if not url:
            continue
        canonical = _canonicalize_url(url)
        if canonical in seen:
            continue
        seen.add(canonical)
        results.append(canonical)
    return results


def extract_address(source: str | None) -> tuple[str | None, str | None]:
    """Extract an address and postal code tuple from HTML or plain text."""

    if not source:
        return None, None
    soup = BeautifulSoup(source, "html.parser")

    candidates: list[str] = []
    for tag in soup.find_all(["address", "p", "li", "dd", "dt", "td", "span", "div"]):
        text = normalize_text(tag.get_text(" ", strip=True))
        if text:
            candidates.append(text)
    full_text = normalize_text(soup.get_text("\n", strip=True))
    if full_text:
        candidates.append(full_text)
    raw_text = normalize_text(source)
    if raw_text:
        candidates.append(raw_text)

    postal_code = None
    address = None
    for text in candidates:
        if not postal_code and (match := _POSTAL_CODE_RE.search(text)):
            postal_code = f"{match.group(1)}-{match.group(2)}"
        if not address and (match := _ADDRESS_RE.search(text)):
            address = match.group(1)
        if address and postal_code:
            break
    return address, postal_code


def extract_tel(source: str | None) -> list[str]:
    """Extract telephone numbers from *source* text or HTML."""

    if not source:
        return []
    soup = BeautifulSoup(source, "html.parser")
    text = normalize_text(soup.get_text(" ", strip=True))
    matches = _TEL_RE.findall(text)
    results: list[str] = []
    seen: set[str] = set()
    for match in matches:
        tel = _normalize_tel(match)
        if tel and tel not in seen:
            seen.add(tel)
            results.append(tel)
    return results


def dedupe_urls(urls: Iterable[str | None]) -> list[str]:
    """Remove duplicates and boilerplate placeholders from *urls*."""

    results: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if not url:
            continue
        cleaned = normalize_text(url)
        if not cleaned or cleaned in _IGNORE_URLS:
            continue
        if cleaned.startswith(_IGNORE_PREFIXES):
            continue
        canonical = _canonicalize_url(cleaned)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        results.append(canonical)
    return results


def _canonicalize_url(url: str) -> str:
    split = urlsplit(url)
    fragment = split.fragment.lower()
    if fragment in {"", "top", "header", "main"}:
        split = split._replace(fragment="")
    canonical = urlunsplit(split)
    if canonical.endswith("/") and split.path not in {"/", ""}:
        canonical = canonical.rstrip("/")
    return canonical


def _normalize_tel(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        if digits.startswith(("03", "06")):
            return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    if len(digits) == 9:
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    normalized = value
    for hyphen in _FULLWIDTH_HYPHENS:
        normalized = normalized.replace(hyphen, "-")
    normalized = normalized.replace("(", "").replace(")", "")
    normalized = re.sub(r"-+", "-", normalized)
    return normalized.strip("-")


__all__ = [
    "normalize_text",
    "absolutize_url",
    "extract_links",
    "extract_address",
    "extract_tel",
    "dedupe_urls",
]
