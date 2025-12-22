"""Shared helpers for municipal training room parsers."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from app.utils.openai_client import OpenAIClientWrapper

# Regex that removes NULL, zero width and control characters.
_CONTROL_RE = re.compile(
    r"[\x00-\x1F\x7F]|\u200B|\u200C|\u200D|\uFEFF",
)
_WHITESPACE_RE = re.compile(r"\s+")
_JP_DIGIT_TRANSLATION = str.maketrans(
    {
        "０": "0",
        "１": "1",
        "２": "2",
        "３": "3",
        "４": "4",
        "５": "5",
        "６": "6",
        "７": "7",
        "８": "8",
        "９": "9",
    }
)
_JP_NUMERAL_MAP: dict[str, int] = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_JP_NUMERAL_UNITS: dict[str, int] = {
    "十": 10,
    "百": 100,
    "千": 1000,
}
_DEFAULT_ADDRESS_PATTERNS: tuple[str, ...] = (
    r"〒\s*\d{3}[-‐−―ーｰ－]\d{4}[^。．\n\r]*",
    r"東京都[^。．\n\r]*?区[^。．\n\r]*",
)
_SEGMENT_RE = re.compile(r"[。．、，,\n\r]+")
_MULTIPLY_RE = re.compile(r"×\s*([0-9０-９]+)")
_JP_COUNT_RE = re.compile(r"([零〇一二三四五六七八九十百千]+)\s*(?:台|基)")
_TEL_TRAIL_RE = re.compile(
    r"\s*(?:TEL|ＴＥＬ|電話|電話番号)(?:\s*[:：])?\s*[0-9０-９]{2,4}-[0-9０-９]{2,4}-[0-9０-９]{3,4}.*$",
    flags=re.IGNORECASE,
)
_ADDRESS_NOISE_KEYWORDS = (
    "バリアフリー",
    "連絡先",
    "地図",
    "アクセス",
    "(外部サイト)",
    "（外部サイト）",
)


@dataclass
class EquipmentEntry:
    """Structured representation of a detected equipment entry."""

    slug: str
    count: int
    raw: list[str]
    orders: list[int]


def sanitize_text(text: str) -> str:
    """Return *text* normalized to a single trimmed line.

    The function removes NULL, zero-width and ASCII control characters, converts the
    string using NFKC normalization, collapses whitespace and trims leading/trailing
    spaces.
    """

    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\u3000", " ")
    normalized = _CONTROL_RE.sub(" ", normalized)
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def _ensure_iterable(value: Any) -> Iterable[str]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set)):  # noqa: UP038
        return tuple(str(item) for item in value if item)
    return (str(value),)


def _iter_candidate_nodes(soup: BeautifulSoup, selectors: dict[str, Any], key: str) -> list[Tag]:
    results: list[Tag] = []
    for selector in _ensure_iterable(selectors.get(key)):
        results.extend(node for node in soup.select(selector) if isinstance(node, Tag))
    return results


def _iter_text_segments(text: str) -> Iterable[str]:
    for segment in _SEGMENT_RE.split(text):
        cleaned = sanitize_text(segment)
        if cleaned:
            yield cleaned


def _clean_address_with_llm(candidate: str) -> str:
    """Clean address using LLM to remove complex noise."""
    try:
        client = OpenAIClientWrapper()
        response = client.chat_completion(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that extracts the postal address "
                        "from a noisy string. "
                        "Return ONLY the full address part (e.g., '東京都墨田区...'). "
                        "Ensure the output includes the Prefecture and Municipality "
                        "if they are present in the text. "
                        "Do not abbreviate or output partial addresses like '錦糸4-1' "
                        "if the full version is available. "
                        "Do not include any other text, notes, or explanations. "
                        "If the input contains '移転しました' or similar relocation notes, "
                        "extract the *new* address if present, "
                        "otherwise extract the address described as the current location. "
                        "If no valid address is found, return the input as is."
                    ),
                },
                {"role": "user", "content": candidate},
            ],
            temperature=0.0,
            max_tokens=100,
        )
        cleaned = response.choices[0].message.content.strip()
        return cleaned
    except Exception:
        # Fallback to original if LLM fails
        return candidate


def _clean_address(candidate: str) -> str:
    cleaned = sanitize_text(candidate)
    # Remove phone number trail
    cleaned = _TEL_TRAIL_RE.sub("", cleaned).strip()

    # Truncate at noise keywords
    for keyword in _ADDRESS_NOISE_KEYWORDS:
        index = cleaned.find(keyword)
        if index != -1:
            cleaned = cleaned[:index].strip()

    for delimiter in ("、", "，", "・"):
        if delimiter in cleaned:
            cleaned = cleaned.split(delimiter)[0]

    # Use LLM for further cleaning if the address still looks noisy or long
    # For now, we apply it to all addresses to ensure high quality as requested,
    # but we could optimize to only apply if len(cleaned) > 20 or contains specific chars.
    # Given the low cost of gpt-4o-mini, we'll apply it if the length is suspicious (> 15 chars)
    # or contains "※" which indicates notes.
    if len(cleaned) > 15 or "※" in cleaned:
        cleaned = _clean_address_with_llm(cleaned)

    return cleaned


def extract_address_one_line(
    html: str,
    *,
    selectors: dict[str, Any],
    patterns: dict[str, Any],
) -> str | None:
    """Extract a postal address as a single line from *html*.

    The function searches candidate nodes defined in *selectors* (``address_hint`` and
    ``body``) and applies the configured regular expressions to locate addresses. The
    shortest matching string is returned.
    """

    soup = BeautifulSoup(html or "", "html.parser")
    pattern_dict = patterns or {}
    address_patterns = list(_ensure_iterable(pattern_dict.get("address"))) or list(
        _DEFAULT_ADDRESS_PATTERNS
    )
    compiled = [re.compile(pattern) for pattern in address_patterns]

    candidates: list[str] = []
    nodes = _iter_candidate_nodes(soup, selectors, "address_hint")
    if not nodes:
        nodes = _iter_candidate_nodes(soup, selectors, "body")
    if not nodes and soup.body:
        nodes = [soup.body]

    seen_segments: set[str] = set()
    for node in nodes:
        text = sanitize_text(node.get_text(" ", strip=True))
        if not text:
            continue
        for segment in _iter_text_segments(text):
            if segment in seen_segments:
                continue
            seen_segments.add(segment)
            for pattern in compiled:
                match = pattern.search(segment)
                if match:
                    candidates.append(match.group().strip())

    if not candidates:
        # Fallback: If we searched specific nodes but found nothing, try the entire body
        # This handles cases where the address is in a footer/header outside the
        # main content selector
        if nodes and nodes != [soup.body] and soup.body:
            text = sanitize_text(soup.body.get_text(" ", strip=True))
            if text:
                for segment in _iter_text_segments(text):
                    if segment in seen_segments:
                        continue
                    seen_segments.add(segment)
                    for pattern in compiled:
                        match = pattern.search(segment)
                        if match:
                            candidates.append(match.group().strip())

    if not candidates:
        return None
    candidate = min(candidates, key=len)
    return _clean_address(candidate)


def _parse_digit(text: str | None) -> int | None:
    if not text:
        return None
    digits = text.translate(_JP_DIGIT_TRANSLATION)
    digits = re.sub(r"\D", "", digits)
    if digits:
        try:
            return int(digits)
        except ValueError:  # pragma: no cover - defensive
            return None
    kanji_match = _JP_COUNT_RE.search(text)
    if kanji_match:
        kanji = kanji_match.group(1)
        return _parse_kanji_number(kanji)
    return None


def _parse_kanji_number(value: str) -> int | None:
    total = 0
    current = 0
    for char in value:
        if char in _JP_NUMERAL_UNITS:
            unit = _JP_NUMERAL_UNITS[char]
            current = max(current, 1)
            total += current * unit
            current = 0
        elif char in _JP_NUMERAL_MAP:
            current = _JP_NUMERAL_MAP[char]
        else:
            return None
    return total + current if total or current else None


def _match_alias(text: str, aliases: Mapping[str, Iterable[str]]) -> str | None:
    normalized = sanitize_text(text).lower()
    for slug, candidates in aliases.items():
        for candidate in candidates:
            token = sanitize_text(candidate).lower()
            if not token:
                continue
            if token in normalized:
                return slug
    return None


def _iter_equipment_lines(block: Tag) -> Iterable[str]:
    for li in block.find_all("li"):
        yield li.get_text(" ", strip=True)
    for row in block.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        text = " ".join(cell for cell in cells if cell)
        if text:
            yield text
    for paragraph in block.find_all("p"):
        text = paragraph.get_text(" ", strip=True)
        if text:
            yield text
    for child in block.children:
        if isinstance(child, NavigableString):
            text = sanitize_text(str(child))
            if text:
                yield text
        elif isinstance(child, Tag):
            text = child.get_text(" ", strip=True)
            if text:
                yield text


def _extract_facility_with_llm(
    text: str,
    aliases: Mapping[str, Iterable[str]],
) -> dict[str, Any] | None:
    """Extract facility info (name, address, equipments) using LLM.

    Returns None if the text does not describe a gym/training room.
    """
    # Create a simplified list of standard equipment names for the prompt
    standard_names = []
    for slug, alias_list in aliases.items():
        first_alias = next(iter(alias_list), slug)
        standard_names.append(f"{first_alias} ({slug})")

    prompt_content = (
        "Analyze the text and determine if it describes a physical public gym "
        "or training room facility that represents a valid candidate for a gym directory. "
        "Return a JSON object with the following fields:\n"
        "- is_gym: Boolean. Set to true ONLY if this page describes a facility's "
        "details (equipment, usage). Set to false if it is an announcement "
        "(e.g., 'Notice of Closure', 'Recruitment'), a generic list of facilities, "
        "or irrelevant content.\n"
        "- name: The specific name of the facility (e.g., '墨田区総合体育館'). "
        "Remove generic headers like 'Facility Guide', 'Training Room', 'Access'. "
        "If the title is generic (e.g., 'Training Room'), look for the parent "
        "facility name in the text/title. Do NOT translate the name; "
        "keep it in Japanese. Return null if is_gym is false.\n"
        "- address: The full postal address of the PHYSICAL facility. "
        "Return null if is_gym is false. "
        "CRITICAL: Do NOT extract the address of the City Hall (区役所), "
        "Administration Office, or Contact Information typically found in the footer "
        "unless it is explicitly stated as the facility's location. "
        "Look for keywords like '所在地' (Location), 'アクセス' (Access), or '場所'. "
        "If multiple addresses are found, look for the one associated with the "
        "Gym/Sports Center name or map.\n"
        "- equipments: A list of training equipment available. "
        "Objects with 'slug' and 'count'. Return empty list if is_gym is false "
        "or no equipment found.\n"
        "  Map equipment to these standard slugs if possible:\n"
        f"  {', '.join(standard_names)}\n"
        "  IMPORTANT: Use the English ID inside the parentheses (e.g., 'treadmill') "
        "as the 'slug', NOT the Japanese name.\n"
        "  If count is unknown but present, set to 1. If explicitly 'none', exclude it.\n"
        "Return ONLY the JSON object."
    )

    try:
        client = OpenAIClientWrapper()
        response = client.chat_completion(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": prompt_content,
                },
                {
                    "role": "user",
                    "content": text[:15000],
                },  # Truncate to avoid token limits
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        if not data:
            return None

        # Return the data as is (containing is_gym)
        return data

    except Exception:
        return None

    except Exception:
        return None


def extract_equipments(
    html: str,
    *,
    selectors: dict[str, Any],
    aliases: Mapping[str, Iterable[str]],
) -> list[dict[str, Any]]:
    """Return structured equipment list extracted from *html*.

    The function uses LLM (gpt-4o-mini) to extract equipment data from the text content
    of the matched blocks. It falls back to the legacy regex-based method if LLM fails
    or returns no results (though empty results might be valid, we'll trust LLM for now).
    """
    soup = BeautifulSoup(html or "", "html.parser")
    blocks = _iter_candidate_nodes(soup, selectors, "equipment_blocks")
    if not blocks and soup.body:
        blocks = [soup.body]

    # Fallback to legacy regex method
    seen_lines: set[str] = set()
    pending_slugs: list[str] = []
    aggregated: dict[str, EquipmentEntry] = {}
    line_order: dict[str, int] = {}
    line_index = 0

    for block in blocks:
        for raw_line in _iter_equipment_lines(block):
            line = sanitize_text(raw_line)
            if not line or line in seen_lines:
                continue
            seen_lines.add(line)
            line_order[line] = line_index
            line_index += 1

            slug = _match_alias(line, aliases)
            digit_count = _parse_digit(line)
            if slug:
                entry = aggregated.get(slug)
                if entry is None:
                    entry = EquipmentEntry(slug=slug, count=0, raw=[], orders=[])
                    aggregated[slug] = entry
                entry.raw.append(line)
                entry.orders.append(line_order[line])
                if digit_count is not None:
                    entry.count += digit_count
                    if slug in pending_slugs:
                        pending_slugs = [pending for pending in pending_slugs if pending != slug]
                else:
                    if slug not in pending_slugs:
                        pending_slugs.append(slug)
                continue

            multiply_match = _MULTIPLY_RE.search(line)
            if multiply_match:
                digit_count = _parse_digit(multiply_match.group(1))
            if digit_count is not None and pending_slugs:
                for pending_slug in pending_slugs:
                    entry = aggregated.setdefault(
                        pending_slug,
                        EquipmentEntry(slug=pending_slug, count=0, raw=[], orders=[]),
                    )
                    entry.count += digit_count
                    entry.raw.append(line)
                    entry.orders.append(line_order[line])
                pending_slugs = []

    results: list[dict[str, Any]] = []
    for entry in aggregated.values():
        if entry.count <= 0:
            entry.count = 1
        order = min(entry.orders) if entry.orders else 0
        results.append(
            {
                "slug": entry.slug,
                "count": entry.count,
                "raw": list(entry.raw),
                "order": order,
                "raw_pairs": list(zip(entry.orders, entry.raw)),
            }
        )
    return sorted(results, key=lambda item: item["order"])


def detect_create_gym(
    url: str,
    title: str,
    body: str,
    *,
    patterns: dict[str, Any],
    keywords: Mapping[str, Iterable[str]],
    eq_count: int,
    address: str | None,
) -> bool:
    """Return ``True`` when the parsed page should create a gym candidate."""

    if not address:
        return False

    pattern_dict = patterns or {}
    url_patterns = pattern_dict.get("url") or pattern_dict.get("url_patterns") or pattern_dict
    skip_patterns = (
        list(_ensure_iterable(url_patterns.get("skip"))) if isinstance(url_patterns, dict) else []
    )

    for pattern in skip_patterns:
        if re.search(pattern, url):
            return False

    intro_pattern = None
    detail_pattern = None
    if isinstance(url_patterns, dict):
        intro_pattern = url_patterns.get("intro_top")
        detail_pattern = url_patterns.get("detail_article")
    intro_match = bool(intro_pattern and re.search(intro_pattern, url))
    detail_match = bool(detail_pattern and re.search(detail_pattern, url))
    if not intro_match and not detail_match:
        return False

    keyword_dict = keywords or {}
    searchable = f"{sanitize_text(title)} {sanitize_text(body)}".lower()
    required_keywords = list(_ensure_iterable(keyword_dict.get("training")))

    keyword_hit = False
    if required_keywords:
        for token in required_keywords:
            normalized_token = sanitize_text(token).lower()
            if normalized_token and normalized_token in searchable:
                keyword_hit = True
                break
        if not keyword_hit:
            return False

    facility_keywords = list(_ensure_iterable(keyword_dict.get("facility")))
    if facility_keywords:
        for token in facility_keywords:
            normalized_token = sanitize_text(token).lower()
            if normalized_token and normalized_token in searchable:
                return True

    # If we have equipment, we can be more confident even if facility keywords didn't match
    # (but required keywords must have matched if present)
    if eq_count >= 3:
        return True

    return False


__all__ = [
    "EquipmentEntry",
    "detect_create_gym",
    "extract_address_one_line",
    "extract_equipments",
    "sanitize_text",
    "_extract_facility_with_llm",
]
