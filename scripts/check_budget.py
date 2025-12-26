import argparse
import asyncio
import logging
import os
from datetime import date, timedelta
from typing import TypedDict

from sqlalchemy import func, select

from app.db import SessionLocal, configure_engine
from app.models.api_usage import ApiUsage
from app.services.notification import send_notification

# Pricing (approximate as of late 2024)
# gpt-4o-mini: $0.15 / 1M input tokens, $0.60 / 1M output tokens
PRICE_OPENAI_INPUT = 0.15 / 1_000_000
PRICE_OPENAI_OUTPUT = 0.60 / 1_000_000

# Google Maps Geocoding: $5.00 / 1000 requests (approx $0.005 per request)
PRICE_GOOGLE_MAPS = 0.005

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class UsageStats(TypedDict):
    openai_input: int
    openai_output: int
    google_maps: int


async def get_usage_for_period(days: int = 1) -> UsageStats:
    """Fetch usage stats from the database for the last N days."""
    today = date.today()
    start_date = today - timedelta(
        days=days - 1
    )  # Inclusive of today + (days-1) past days = N days?
    # If days=1, start_date = today. Range [today, today].
    # Wait, usually "past 1 day" means "last 24h" or "today"?
    # For cost *monitoring*, "daily" usually means "today so far" or "yesterday".
    # Implementation Plan says "Daily (nightly check)".
    # If it runs at 3 AM, it's checking yesterday? Or today?
    # Nightly usually means "previous day".
    # If it runs at 3 AM JST, it covers likely the previous day UTC?
    # Let's assume we want "Last N days including today".
    # If days=1, we query usage >= today.

    async with SessionLocal() as session:
        stmt = (
            select(ApiUsage.service, ApiUsage.metric, func.sum(ApiUsage.value))
            .where(ApiUsage.date >= start_date)
            .group_by(ApiUsage.service, ApiUsage.metric)
        )
        result = await session.execute(stmt)
        rows = result.all()

    stats: UsageStats = {"openai_input": 0, "openai_output": 0, "google_maps": 0}

    for service, metric, value in rows:
        val = int(value or 0)
        if service == "openai" and metric == "input_tokens":
            stats["openai_input"] += val
        elif service == "openai" and metric == "output_tokens":
            stats["openai_output"] += val
        elif service == "google_maps" and metric == "requests":
            stats["google_maps"] += val

    return stats


async def get_cost_report(days: int = 1) -> str:
    """Generate a cost report string for notification."""
    stats = await get_usage_for_period(days)
    input_tokens = stats["openai_input"]
    output_tokens = stats["openai_output"]
    maps_calls = stats["google_maps"]

    openai_cost = (input_tokens * PRICE_OPENAI_INPUT) + (output_tokens * PRICE_OPENAI_OUTPUT)
    maps_cost = maps_calls * PRICE_GOOGLE_MAPS
    total_cost = openai_cost + maps_cost

    today = date.today()
    start_date = today - timedelta(days=days - 1)

    date_range_str = f"{start_date} ~ {today}" if days > 1 else f"{today}"

    report_lines = [
        f"**Cost Report ({date_range_str})**",
        f"OpenAI Input: {input_tokens:,} tokens",
        f"OpenAI Output: {output_tokens:,} tokens",
        f"OpenAI Est. Cost: ${openai_cost:.4f}",
        f"Google Maps: {maps_calls:,} requests",
        f"Google Maps Est. Cost: ${maps_cost:.4f}",
        "-----------------------------------",
        f"**Total Est. Cost: ${total_cost:.4f}**",
    ]

    if total_cost > 5.00:
        report_lines.append("\n⚠️ **ALERT: Total cost exceeded $5.00 threshold!**")

    return "\n".join(report_lines)


async def main():
    parser = argparse.ArgumentParser(description="Check API usage and estimated cost")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back")
    args = parser.parse_args()

    configure_engine()

    report_text = await get_cost_report(args.days)
    logger.info(report_text)

    # Send to Discord if CLI env var is set (for testing)
    if os.getenv("DISCORD_WEBHOOK_URL") and os.getenv("SEND_NOTIFICATION"):
        await send_notification(report_text)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
