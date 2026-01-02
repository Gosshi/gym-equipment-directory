"""Generic parser for Tokyo municipal training room pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.ingest.normalizers.equipment_aliases import EQUIPMENT_ALIASES
from app.ingest.normalizers.tag_aliases import TAG_ALIASES
from app.ingest.parsers.municipal._base import (
    _extract_facility_with_llm,
    classify_categories,
    classify_category,
    detect_create_gym,
    extract_address_one_line,
    extract_equipments,
    sanitize_text,
    validate_facility_name,
)
from app.ingest.parsers.municipal.config_loader import load_config

from .sources_registry import MunicipalSource


@dataclass
class MunicipalParseResult:
    facility_name: str
    address: str | None
    equipments_raw: list[str]
    equipments: list[dict[str, Any]]
    tags: list[str]
    center_no: str | None
    page_type: str | None
    page_title: str
    meta: dict[str, Any]
    categories: list[str]  # gym, pool, court, hall, field, martial_arts, archery


def _ensure_iterable(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value if item]


def _collect_nodes(soup: BeautifulSoup, selectors: Any) -> list[Tag]:
    nodes: list[Tag] = []
    for selector in _ensure_iterable(selectors):
        nodes.extend(node for node in soup.select(selector) if isinstance(node, Tag))
    if not nodes and soup.body:
        nodes = [soup.body]
    return nodes


def _extract_primary_title(soup: BeautifulSoup, selectors: Any) -> str:
    for selector in _ensure_iterable(selectors):
        node = soup.select_one(selector)
        if isinstance(node, Tag):
            text = sanitize_text(node.get_text(" ", strip=True))
            if text:
                return text
    return ""


def _extract_center_no(url: str, hints: dict[str, str] | None) -> str | None:
    if not hints:
        return None
    pattern = hints.get("center_no_from_url")
    if not pattern:
        return None
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return None


def _aggregate_raw_lines(entries: list[dict[str, Any]]) -> list[str]:
    pairs: list[tuple[int, str]] = []
    for entry in entries:
        for order, line in entry.get("raw_pairs", []):
            pairs.append((int(order), line))
    pairs.sort(key=lambda item: item[0])
    seen: set[str] = set()
    ordered: list[str] = []
    for _, line in pairs:
        if line in seen:
            continue
        seen.add(line)
        ordered.append(line)
    return ordered


def _strip_internal_fields(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for entry in entries:
        cleaned.append(
            {
                "slug": entry.get("slug", ""),
                "count": int(entry.get("count", 0)),
                "raw": list(entry.get("raw", [])),
            }
        )
    return cleaned


async def parse_municipal_page(
    html: str,
    url: str,
    *,
    source: MunicipalSource,
    page_type: str | None = None,
) -> MunicipalParseResult:
    # Normalize URL: remove fragment and query
    normalized_url = url.split("#")[0].split("?")[0]
    if normalized_url.endswith("/index.html"):
        normalized_url = normalized_url[:-11]  # Remove /index.html

    clean_html = (html or "").replace("\x00", "")

    # Global fix for unicode escapes (e.g. Shibuya)
    # We use regex to avoid corrupting existing non-ASCII characters
    try:

        def replace_escape(match):
            return chr(int(match.group(1), 16))

        if "\\u" in clean_html:
            clean_html = re.sub(r"\\u([0-9a-fA-F]{4})", replace_escape, clean_html)

            # Extract hidden HTML tables (e.g. inside JSON in scripts) and append to body
            # This allows BeautifulSoup to parse them as elements
            hidden_tables = re.findall(
                r"<table.*?>.*?</table>",
                clean_html,
                re.DOTALL | re.IGNORECASE,
            )
            if hidden_tables:
                # print(f"DEBUG: Found {len(hidden_tables)} hidden tables, appending to HTML")
                clean_html += "\n".join(hidden_tables)

    except Exception as e:
        print(f"DEBUG: Global unicode escape fix failed: {e}")

    soup = BeautifulSoup(clean_html, "html.parser")
    config = load_config(source.title)
    selectors = config.get("selectors", {})

    # Check if URL matches detail_article pattern
    detail_pattern = config.get("url_patterns", {}).get("detail_article")
    if detail_pattern and not re.search(detail_pattern, url):
        # Not a detail page, skip
        return MunicipalParseResult(
            facility_name="",
            address=None,
            equipments_raw=[],
            equipments=[],
            tags=[],
            center_no=None,
            page_type=page_type,
            page_title="",
            meta={"create_gym": False, "page_url": normalized_url},
            categories=[],
        )

    title_text = _extract_primary_title(soup, selectors.get("title"))
    page_title = sanitize_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    facility_name = title_text or page_title

    # Remove earlier Keyword Checks (User requested LLM check instead)

    # 1. Try LLM Facility Extraction
    # Combine text from body nodes
    nodes = _collect_nodes(soup, selectors.get("body"))

    # Combine text from body nodes
    body_text = " ".join(node.get_text(" ", strip=True) for node in nodes if node.get_text())

    # Sanitize first (safe for real Japanese)
    body_text = sanitize_text(body_text)

    # Use full page text (or body text) for LLM
    llm_text = body_text if len(body_text) > 50 else soup.get_text(" ", strip=True)

    llm_data = await _extract_facility_with_llm(llm_text, EQUIPMENT_ALIASES)

    # LLM Filtering Logic - Only reject if this is NOT a facility page at all
    # (e.g., index page, announcement, etc.)
    # We now accept non-gym facilities like pools, courts, halls.
    # The LLM's is_gym flag originally meant "is a gym", but we repurpose it as "is a facility"
    # For now, we'll trust the LLM rejection for truly irrelevant pages.
    if llm_data and llm_data.get("is_gym") is False:
        # Check if it's at least a recognizable facility by keywords
        detected_category = classify_category(body_text)
        if detected_category == "hall":  # Fallback means no specific category found
            # Double-check: if no specific category, trust LLM rejection
            return MunicipalParseResult(
                facility_name=facility_name,
                address=None,
                equipments_raw=[],
                equipments=[],
                tags=[],
                center_no=None,
                page_type=page_type,
                page_title=page_title,
                meta={"create_gym": False, "page_url": normalized_url, "reason": "llm_rejection"},
                categories=[],
            )
        # Otherwise, continue processing as a non-gym facility

    # Extract llm_categories and llm_structured_data from LLM response (regardless of is_gym flag)
    # This ensures hours/fee are captured for pools, halls, courts, etc.
    llm_categories: list[str] | None = None
    llm_structured_data = {}

    if llm_data:
        # Support both new 'categories' array and legacy 'category' string
        raw_categories = llm_data.get("categories")
        if isinstance(raw_categories, list):
            llm_categories = [c for c in raw_categories if isinstance(c, str)]
        elif llm_data.get("category"):
            # Fallback to legacy single category
            llm_categories = [llm_data["category"]]

        # Store structured data from LLM
        if llm_data.get("hours"):
            llm_structured_data["hours"] = llm_data["hours"]
        if llm_data.get("fee") is not None:
            llm_structured_data["fee"] = llm_data["fee"]
        # Multi-facility flag
        if llm_data.get("is_multi_facility") is not None:
            llm_structured_data["is_multi_facility"] = llm_data["is_multi_facility"]
        # Category-specific fields
        for field in [
            "lanes",
            "length_m",
            "heated",
            "court_type",
            "courts",
            "surface",
            "lighting",
            "sports",
            "area_sqm",
            "field_type",
            "fields",
        ]:
            if llm_data.get(field) is not None:
                llm_structured_data[field] = llm_data[field]

    if llm_data and llm_data.get("is_gym") is True:
        # LLM found a facility
        facility_name = llm_data.get("name") or facility_name
        address = llm_data.get("address")

        # Process equipments from LLM (for gym category)
        equipments_structured = []
        raw_eq_items = llm_data.get("equipments", [])
        if isinstance(raw_eq_items, list):
            for i, item in enumerate(raw_eq_items):
                slug = item.get("slug")
                count = item.get("count")
                if slug:
                    equipments_structured.append(
                        {
                            "slug": str(slug),
                            "count": int(count) if count is not None else 1,
                            "raw": [],
                            "order": i,
                            "raw_pairs": [],
                        }
                    )

        equipments_raw = [f"{e['slug']} x{e['count']}" for e in equipments_structured]
        create_gym = True

    else:
        # 2. Fallback to Legacy Logic (Only if LLM failed completely/errored, NOT if it said false)
        # Note: _extract... returns None on Exception.
        # Ideally we trust LLM. If None, it might be API error.
        # We can still try heuristic, but risk noise.
        # User implies "Use LLM".
        # If LLM returned None (API error), we might skip or fallback.
        # Let's fallback for robustness, but prioritize LLM rejection.

        address = await extract_address_one_line(
            clean_html,
            selectors=selectors,
            patterns={"address": config.get("address_patterns")},
        )

        equipments_extracted = extract_equipments(
            clean_html,
            selectors=selectors,
            aliases=EQUIPMENT_ALIASES,
        )
        equipments_raw = _aggregate_raw_lines(equipments_extracted)
        equipments_raw = _aggregate_raw_lines(equipments_extracted)
        equipments_structured = _strip_internal_fields(equipments_extracted)
        equipment_count = sum(max(int(entry.get("count", 0)), 0) for entry in equipments_structured)

        create_gym = detect_create_gym(
            normalized_url,
            title=facility_name or page_title,
            body=body_text,
            patterns={"url": config.get("url_patterns")},
            keywords=config.get("keywords"),
            eq_count=equipment_count,
            address=address,
        )
        if create_gym:
            # Post-LLM Validation
            if not validate_facility_name(facility_name):
                print(f"DEBUG: Rejected Generic Name: {facility_name}")
                create_gym = False

            # Address validation is done inside _clean_address called by extract_address_one_line
            # BUT for LLM result, we just took it. ensure it's valid too.
            from app.ingest.parsers.municipal._base import _clean_address

            # Re-clean/validate address if it came from LLM
            if address:
                cleaned_addr = await _clean_address(address)
                if not cleaned_addr:
                    print(f"DEBUG: Rejected Invalid Address: {address}")
                    address = None  # Clear invalid address
                    create_gym = False  # Recommend rejecting if no address? Or keep checking?
                    # If address is invalid, likely scraping failed.

            # If no address after validation, reject?
            if not address:
                create_gym = False

    # Determine facility categories (prefer LLM, fallback to keyword-based)
    if llm_categories:
        categories = llm_categories
    else:
        categories = classify_categories(body_text)

    # Primary category for backward compatibility
    category = categories[0] if categories else "hall"

    # For non-gym categories, we still create facilities if we have an address
    # This allows pools, courts, etc. to be saved
    should_create = create_gym or (address and category != "hall")

    meta = {
        "create_gym": should_create,
        "page_url": normalized_url,
        "categories": categories,  # New: array of all categories
    }

    # Add structured data from LLM if available
    if llm_structured_data:
        meta.update(llm_structured_data)

    center_no = _extract_center_no(normalized_url, source.parse_hints)

    # Extract tags from body text
    tags: list[str] = []
    if should_create:
        for slug, keywords in TAG_ALIASES.items():
            for keyword in keywords:
                if keyword in body_text:
                    tags.append(slug)
                    break

    return MunicipalParseResult(
        facility_name=facility_name,
        address=address,
        equipments_raw=equipments_raw,
        equipments=equipments_structured,
        tags=tags,
        center_no=center_no,
        page_type=page_type,
        page_title=page_title,
        meta=meta,
        categories=categories if should_create else [],
    )


__all__ = ["MunicipalParseResult", "parse_municipal_page"]
