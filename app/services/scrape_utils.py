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
_ARRAY_KEY_FIELDS: dict[str, str | None] = {
    "courts": "court_type",
    "equipments": "slug",
    "pools": "length_m",  # Use length as identifier for pools
    "fields": "field_type",  # Field arrays keyed by type
    "sports": None,  # Simple string array, uses dedup
    "source_urls": None,  # Simple URL array, uses dedup
}

# Fields that should be MERGED (recursively) rather than overwritten during scrape
# These are category-specific nested objects that contain detailed facility data
_CATEGORY_FIELDS_TO_MERGE: frozenset[str] = frozenset(
    {
        "pool",  # Pool data object: {lanes, length_m, heated}
        "court",  # Court data object: {courts: [...]}
        "hall",  # Hall data object: {sports, area_sqm}
        "field",  # Field data object: {fields: [...]}
        "archery",  # Archery data object: {archery_type, rooms}
    }
)

# Legacy scalar fields that should be preserved if they already exist
# These are typically manually curated values from detail pages
_PROTECTED_SCRAPE_FIELDS: frozenset[str] = frozenset(
    {
        # Scalar values that should not be overwritten if already set
        "hours",  # Operating hours
        "fee",  # Usage fee
        "official_url",  # Manually entered official URL (scrape uses source_urls)
    }
)


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

        # Category fields (pool, court, hall, field, archery) should be recursively merged
        if key in _CATEGORY_FIELDS_TO_MERGE:
            if isinstance(new_value, dict) and isinstance(existing_value, dict):
                # Recursively merge category objects
                result[key] = merge_parsed_json(existing_value, new_value)
            elif new_value and not existing_value:
                # No existing data, use new value
                result[key] = new_value
            # else: existing_value is set and new_value is not a dict - keep existing
        elif isinstance(new_value, dict) and isinstance(existing_value, dict):
            # Generic dict merge
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
        elif key in _PROTECTED_SCRAPE_FIELDS and existing_value is not None:
            # Protected field already has a value - don't overwrite
            pass
        else:
            # Overwrite with new value
            result[key] = new_value

    return result


async def try_scrape_official_url(
    official_url: str | None,
    scraped_page_url: str | None,
    existing_parsed_json: dict[str, Any] | None,
    scrape_subpages: bool = False,
) -> dict[str, Any] | None:
    """Try to scrape the official URL and merge with existing parsed_json.

    Args:
        official_url: The URL to scrape
        scraped_page_url: The URL that was originally scraped (to avoid duplicates)
        existing_parsed_json: Existing data to merge with
        scrape_subpages: If True, detect and scrape facility subpages (max 5)

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
        scrape_subpages=scrape_subpages,
    )
    return outcome.merged_data


async def scrape_official_url_with_reason(
    official_url: str | None,
    scraped_page_url: str | None,
    existing_parsed_json: dict[str, Any] | None,
    scrape_subpages: bool = False,
) -> ScrapeOutcome:
    """Scrape the official URL and return merged data with a failure reason.

    Args:
        official_url: The URL to scrape
        scraped_page_url: The URL that was originally scraped
        existing_parsed_json: Existing data to merge with
        scrape_subpages: If True, detect and scrape facility subpages (max 5)
    """
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
        # Note: We don't set "official_url" here to preserve manually entered URLs
        # Instead, we add the scraped URL to source_urls array
        new_data: dict[str, Any] = {
            "official_url_scraped": True,
            "official_url_status": status,
            "scraped_url": official_url,  # Track what was scraped
        }

        # Add to source_urls array (will be merged with existing)
        existing_source_urls = (existing_parsed_json or {}).get("source_urls", [])
        if official_url not in existing_source_urls:
            new_data["source_urls"] = existing_source_urls + [official_url]

        # Extract text and use LLM
        try:
            from bs4 import BeautifulSoup

            from app.ingest.normalizers.equipment_aliases import EQUIPMENT_ALIASES
            from app.ingest.parsers.municipal._base import (
                _extract_facility_with_llm,
                extract_facility_links,
            )

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

            # If scrape_subpages is enabled, detect and scrape facility links
            if scrape_subpages:
                logger.info("Detecting facility subpages for %s", official_url)
                subpage_urls = await extract_facility_links(html, official_url)

                if subpage_urls:
                    logger.info(
                        "Found %d facility subpages, scraping (max 5)...", len(subpage_urls)
                    )
                    # Limit to 5 subpages to avoid excessive scraping
                    for subpage_url in subpage_urls[:5]:
                        logger.info("Scraping subpage: %s", subpage_url)
                        try:
                            subpage_html, subpage_status, _ = await fetch_url_checked(subpage_url)
                            if subpage_html:
                                # Extract text from subpage
                                subpage_soup = BeautifulSoup(subpage_html, "html.parser")
                                for script in subpage_soup(
                                    ["script", "style", "noscript", "iframe"]
                                ):
                                    script.decompose()
                                subpage_text = subpage_soup.get_text(separator="\n", strip=True)

                                # Extract data with LLM
                                subpage_result = await _extract_facility_with_llm(
                                    subpage_text, EQUIPMENT_ALIASES
                                )
                                if subpage_result:
                                    logger.info("Subpage extraction successful: %s", subpage_url)
                                    # Merge subpage data into new_data
                                    new_data = merge_parsed_json(new_data, subpage_result)
                        except Exception as e:
                            logger.warning("Failed to scrape subpage %s: %s", subpage_url, e)
                            # Continue with other subpages

        except Exception as e:
            logger.error("Error during LLM extraction for %s: %s", official_url, e)
            # Proceed with just metadata if LLM fails

        # Merge with existing parsed_json
        return ScrapeOutcome(merge_parsed_json(existing_parsed_json, new_data))

    except Exception as exc:
        logger.exception("Error scraping official URL %s: %s", official_url, exc)
        return ScrapeOutcome(None, "unexpected_error")
