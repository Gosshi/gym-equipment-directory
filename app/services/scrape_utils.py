"""Scraping utilities for on-demand URL fetching during candidate approval."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.services.http_utils import fetch_url_checked

logger = logging.getLogger(__name__)


@dataclass
class ScrapeOutcome:
    merged_data: dict[str, Any] | None
    failure_reason: str | None = None


def _merge_structured_array(
    existing: list[dict[str, Any]],
    new_items: list[dict[str, Any]],
    key_field: str,
) -> list[dict[str, Any]]:
    """Merge structured arrays by key field, preserving existing and updating with new.

    - Items are matched by key_field (e.g., 'court_type', 'slug')
    - Existing items are preserved
    - New items update existing with additional non-null fields
    - Items only in new data are added
    """
    # Index existing items by key
    result_map: dict[str, dict[str, Any]] = {}
    for item in existing:
        if isinstance(item, dict):
            key = item.get(key_field)
            if key:
                result_map[key] = item.copy()

    # Merge new items
    for item in new_items:
        if not isinstance(item, dict):
            continue
        key = item.get(key_field)
        if key:
            if key in result_map:
                # Update existing with new non-null fields
                for field, value in item.items():
                    if value is not None and value != "":
                        result_map[key][field] = value
            else:
                # Add new item
                result_map[key] = item.copy()

    return list(result_map.values())


# Mapping of array keys to their unique identifier field
_ARRAY_KEY_FIELDS: dict[str, str] = {
    "courts": "court_type",
    "equipments": "slug",
    "pools": "length_m",  # Use length as identifier for pools
    "sports": None,  # Simple string array, uses dedup
}


def merge_parsed_json(
    existing: dict[str, Any] | None,
    new_data: dict[str, Any],
) -> dict[str, Any]:
    """Merge new parsed data into existing parsed_json.

    - New non-empty values overwrite existing values
    - Structured arrays (courts, equipments) are smart-merged by key field
    - Simple tag-like arrays are concatenated and deduplicated
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
            # Check if this is a structured array with a known key field
            key_field = _ARRAY_KEY_FIELDS.get(key)
            if key_field and all(isinstance(item, dict) for item in new_value):
                # Smart merge by key field
                result[key] = _merge_structured_array(existing_value, new_value, key_field)
            else:
                # For simple arrays (tags, categories), concatenate and deduplicate
                combined = existing_value + new_value
                try:
                    seen: set[Any] = set()
                    deduped = []
                    for item in combined:
                        if item not in seen:
                            seen.add(item)
                            deduped.append(item)
                    result[key] = deduped
                except TypeError:
                    # Items not hashable (unknown dicts), prefer new data
                    result[key] = new_value
        else:
            # Overwrite with new value
            result[key] = new_value

    return result


async def try_scrape_official_url(
    official_url: str | None,
    scraped_page_url: str | None,
    existing_parsed_json: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Try to scrape the official URL and merge with existing parsed_json.

    Returns the merged parsed_json if scraping was successful, or None if:
    - official_url is None or empty
    - official_url is the same as the scraped page URL
    - robots.txt blocks scraping
    - HTTP fetch fails
    """
    outcome = await scrape_official_url_with_reason(
        official_url=official_url,
        scraped_page_url=scraped_page_url,
        existing_parsed_json=existing_parsed_json,
    )
    return outcome.merged_data


async def scrape_official_url_with_reason(
    official_url: str | None,
    scraped_page_url: str | None,
    existing_parsed_json: dict[str, Any] | None,
) -> ScrapeOutcome:
    """Scrape the official URL and return merged data with a failure reason."""
    if not official_url:
        return ScrapeOutcome(None, "missing_official_url")

    # Normalize URLs for comparison
    official_normalized = official_url.rstrip("/").lower()
    scraped_normalized = (scraped_page_url or "").rstrip("/").lower()

    if official_normalized == scraped_normalized:
        logger.debug("Official URL same as scraped URL, skipping: %s", official_url)
        return ScrapeOutcome(None, "same_url")

    logger.info(
        "Attempting to scrape official URL: %s (different from scraped: %s)",
        official_url,
        scraped_page_url,
    )

    try:
        html, status, failure_reason = await fetch_url_checked(official_url)
        if html is None:
            logger.warning("Failed to fetch official URL: %s", official_url)
            return ScrapeOutcome(None, failure_reason or "fetch_failed")

        logger.info(
            "Successfully fetched official URL: %s (status=%s, %d bytes)",
            official_url,
            status,
            len(html),
        )

        # Basic metadata
        new_data: dict[str, Any] = {
            "official_url_scraped": True,
            "official_url_status": status,
            "official_url": official_url,
        }

        # Extract text and use LLM
        try:
            from bs4 import BeautifulSoup

            from app.ingest.normalizers.equipment_aliases import EQUIPMENT_ALIASES
            from app.ingest.parsers.municipal._base import _extract_facility_with_llm

            soup = BeautifulSoup(html, "html.parser")
            # Remove scripts and styles
            for script in soup(["script", "style", "noscript", "iframe"]):
                script.decompose()

            text_content = soup.get_text(separator="\n", strip=True)

            logger.info("Extracting facility info with LLM for %s", official_url)
            llm_result = await _extract_facility_with_llm(text_content, EQUIPMENT_ALIASES)

            if llm_result:
                logger.info("LLM extraction successful for %s", official_url)
                new_data.update(llm_result)
            else:
                logger.warning("LLM extraction returned None for %s", official_url)

        except Exception as e:
            logger.error("Error during LLM extraction for %s: %s", official_url, e)
            # Proceed with just metadata if LLM fails

        # Merge with existing parsed_json
        return ScrapeOutcome(merge_parsed_json(existing_parsed_json, new_data))

    except Exception as exc:
        logger.exception("Error scraping official URL %s: %s", official_url, exc)
        return ScrapeOutcome(None, "unexpected_error")
