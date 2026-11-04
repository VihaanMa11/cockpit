"""Outbound n8n webhook requests with bounded timeouts."""
import logging
import httpx

logger = logging.getLogger("cockpit.actions")


async def post_webhook(url: str, payload: dict, method: str = "POST", timeout: float = 10.0):
    if not url:
        logger.warning("post_webhook called with empty URL")
        return False, "No webhook configured"
    logger.info("Sending outbound webhook -> %s %s with payload %s", method.upper(), url, payload)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method.upper(), url, json=payload)
            response.raise_for_status()
            logger.info("Webhook success: %s %s -> HTTP %d", method.upper(), url, response.status_code)
            return True, None
    except httpx.TimeoutException:
        logger.warning("Webhook timeout after %.1fs: %s %s", timeout, method.upper(), url)
        return False, "Request timed out"
    except httpx.HTTPStatusError as exc:
        logger.warning("Webhook HTTP error %d: %s %s", exc.response.status_code, method.upper(), url)
        return False, f"HTTP {exc.response.status_code}"
    except httpx.RequestError as exc:
        logger.warning("Webhook connection error: %s (%s)", url, exc)
        return False, f"Connection error: {exc}"
    except Exception as exc:
        logger.warning("Webhook unexpected error: %s", exc)
        return False, str(exc)
