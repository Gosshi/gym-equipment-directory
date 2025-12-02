"""Discovery script to find gym facility URLs using Google Custom Search API."""

from __future__ import annotations

import argparse
import logging
import os
import time
from typing import Any

from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# List of Tokyo 23 wards (most commented out for initial verification)
WARDS = [
    # "chiyoda",
    # "chuo",
    # "minato",
    # "shinjuku",
    # "bunkyo",
    # "taito",
    "sumida",
    # "koto",
    # "shinagawa",
    # "meguro",
    # "ota",
    # "setagaya",
    # "shibuya",
    # "nakano",
    # "suginami",
    # "toshima",
    # "kita",
    # "arakawa",
    # "itabashi",
    # "nerima",
    # "adachi",
    # "katsushika",
    # "edogawa",
]

WARD_JP_NAMES = {
    "sumida": "墨田",
    "koto": "江東",
    "edogawa": "江戸川",
    # Add others as needed
}


def search_gyms(query: str, api_key: str, cx: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for gym facilities using Google Custom Search API."""
    service = build("customsearch", "v1", developerKey=api_key)
    results = []

    # API returns max 10 results per page
    num_pages = (limit + 9) // 10

    for i in range(num_pages):
        start_index = i * 10 + 1
        try:
            res = (
                service.cse()
                .list(q=query, cx=cx, start=start_index, num=min(10, limit - len(results)))
                .execute()
            )

            items = res.get("items", [])
            if not items:
                break

            for item in items:
                results.append(
                    {
                        "title": item.get("title"),
                        "link": item.get("link"),
                        "snippet": item.get("snippet"),
                    }
                )

            if len(results) >= limit:
                break

            time.sleep(1)  # Respect rate limits

        except Exception as e:
            logger.error(f"Search failed: {e}")
            break

    return results


def discover_urls_for_ward(
    ward: str, api_key: str, cx: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Discover URLs for a specific ward."""
    ward_jp = WARD_JP_NAMES.get(ward, ward)
    query = f"{ward_jp}区 トレーニング室 公営ジム"
    logger.info(f"Searching for: {query}")
    return search_gyms(query, api_key, cx, limit)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover gym URLs")
    parser.add_argument("--ward", help="Specific ward to search (optional)")
    parser.add_argument("--limit", type=int, default=10, help="Max results per ward")
    args = parser.parse_args(argv)

    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key or not cx:
        logger.error("GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID must be set")
        return 1

    target_wards = [args.ward] if args.ward else WARDS

    for ward in target_wards:
        results = discover_urls_for_ward(ward, api_key, cx, args.limit)
        print(f"\n--- Results for {ward} ({len(results)}) ---")
        for item in results:
            print(f"Title: {item['title']}")
            print(f"URL:   {item['link']}")
            print(f"Desc:  {item['snippet']}")
            print("-" * 40)

    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    raise SystemExit(main())
