import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def send_notification(message: str, embed: dict | None = None) -> None:
    """Send a message to the configured Discord Webhook."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL is not set. Notification skipped.")
        return

    payload = {"content": message}
    if embed:
        payload["embeds"] = [embed]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(webhook_url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Notification sent successfully.")
        except httpx.HTTPError as exc:
            logger.error(f"Failed to send notification: {exc}")
