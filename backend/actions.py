"""Outbound n8n webhook requests with bounded timeouts."""
import logging
import httpx

logger = logging.getLogger("cockpit.actions")


async def post_webhook(url: str, payload: dict, method: str = "POST", timeout: float = 5.0):
    if not url:
        return False, "No webhook configured"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method.upper(), url, json=payload)
            response.raise_for_status()
            return True, None
    except httpx.TimeoutException:
        return False, "Request timed out"
    except httpx.HTTPError as exc:
        logger.warning("webhook request failed: %s", exc)
        return False, "Webhook request failed"
