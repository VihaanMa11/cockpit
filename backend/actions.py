"""Outbound webhook calls (n8n / agent endpoints)."""

import logging

import httpx

logger = logging.getLogger("cockpit.actions")

WEBHOOK_TIMEOUT_SECONDS = 3.0


async def post_webhook(url: str, payload: dict) -> bool:
    """POST a JSON payload to url. Returns True on a 2xx response, False on
    any timeout, connection error, or non-2xx status. Never raises."""
    if not url:
        logger.warning("post_webhook: no URL configured, skipping")
        return False
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except httpx.HTTPError as exc:
        logger.warning("post_webhook: %s failed: %s", url, exc)
        return False
