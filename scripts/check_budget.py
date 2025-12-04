import argparse
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from app.services.notification import send_notification

# Pricing (approximate as of late 2024)
# gpt-4o-mini: $0.15 / 1M input tokens, $0.60 / 1M output tokens
PRICE_OPENAI_INPUT = 0.15 / 1_000_000
PRICE_OPENAI_OUTPUT = 0.60 / 1_000_000

# Google Maps Geocoding: $5.00 / 1000 requests (approx $0.005 per request)
PRICE_GOOGLE_MAPS = 0.005

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def parse_logs(log_dir: Path, days: int = 1):
    cutoff = datetime.now() - timedelta(days=days)

    total_openai_input = 0
    total_openai_output = 0
    total_google_maps = 0

    for root, _, files in os.walk(log_dir):
        for file in files:
            if not file.endswith(".log"):
                continue

            file_path = Path(root) / file
            # Check file modification time first
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime < cutoff:
                continue

            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    timestamp_str = entry.get("timestamp")
                    if not timestamp_str:
                        continue

                    # Simple timestamp check (assuming ISO format)
                    # If parsing fails or is slow, we might skip strict check
                    # if file mtime is close enough
                    # But let's try to parse
                    try:
                        # Handle Z or +00:00
                        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        if ts.replace(tzinfo=None) < cutoff:
                            continue
                    except ValueError:
                        continue

                    event = entry.get("event")
                    if event == "openai_usage":
                        total_openai_input += entry.get("prompt_tokens", 0)
                        total_openai_output += entry.get("completion_tokens", 0)
                    elif event == "google_maps_api_call":
                        total_google_maps += 1

    return total_openai_input, total_openai_output, total_google_maps


async def main():
    parser = argparse.ArgumentParser(description="Check API usage and estimated cost")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back")
    parser.add_argument(
        "--log-dir", type=Path, default=Path("logs"), help="Directory containing logs"
    )
    args = parser.parse_args()

    input_tokens, output_tokens, maps_calls = parse_logs(args.log_dir, args.days)

    openai_cost = (input_tokens * PRICE_OPENAI_INPUT) + (output_tokens * PRICE_OPENAI_OUTPUT)
    maps_cost = maps_calls * PRICE_GOOGLE_MAPS
    total_cost = openai_cost + maps_cost

    report_lines = [
        f"--- Usage Report (Last {args.days} days) ---",
        f"OpenAI Input Tokens:  {input_tokens:,}",
        f"OpenAI Output Tokens: {output_tokens:,}",
        f"OpenAI Est. Cost:     ${openai_cost:.4f}",
        f"Google Maps Calls:    {maps_calls:,}",
        f"Google Maps Est. Cost:${maps_cost:.4f}",
        "-----------------------------------",
        f"Total Est. Cost:      ${total_cost:.4f}",
    ]

    report_text = "\n".join(report_lines)
    logger.info(report_text)

    # Simple alert threshold (e.g., $5.00)
    if total_cost > 5.00:
        logger.warning("ALERT: Total cost exceeded $5.00 threshold!")
        report_text += "\n\n⚠️ **ALERT: Total cost exceeded $5.00 threshold!**"

    # Send to Discord
    if os.getenv("DISCORD_WEBHOOK_URL"):
        await send_notification(f"```\n{report_text}\n```")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
