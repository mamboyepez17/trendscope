"""
XActions-PY — Local notifications / webhooks for watch & pipeline.

Default: log. Optional HTTP POST webhook (JSON body, no fancy signing yet).
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

import httpx

_log = logging.getLogger(__name__)

WEBHOOK_ENV = "XACTIONS_WEBHOOK_URL"


def webhook_url() -> str | None:
    return os.getenv(WEBHOOK_ENV) or None


def make_notifier(
    url: str | None = None,
    *,
    extra: dict[str, Any] | None = None,
    http: httpx.AsyncClient | None = None,
) -> Callable[[str], None]:
    """
    Returns a sync callable(message) that logs and, if url set, best-effort POSTs.
    (Fire-and-forget style for pipeline notify_fn.)
    """
    url = url or webhook_url()
    extra = extra or {}

    def _notify(message: str) -> None:
        _log.info("notify: %s", message)
        if not url:
            return
        payload = {"text": message, "message": message, **extra}
        try:
            # short timeout; notify should never hang the pipeline
            httpx.post(url, json=payload, timeout=5.0)
        except httpx.HTTPError as e:
            _log.warning("webhook failed: %s", e)

    return _notify


def format_tweet_alert(tweets: list[dict[str, Any]], query: str | None = None) -> str:
    if not tweets:
        return "No new tweets"
    head = f"{len(tweets)} new tweet(s)"
    if query:
        head += f" for “{query}”"
    lines = [head]
    for t in tweets[:5]:
        author = (t.get("author") or {}).get("username") or "?"
        text = (t.get("text") or "").replace("\n", " ")[:80]
        lines.append(f"  @{author}: {text}")
    if len(tweets) > 5:
        lines.append(f"  … +{len(tweets) - 5} more")
    return "\n".join(lines)


async def post_webhook(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Explicit async POST for callers that want the response."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        return {"status_code": resp.status_code, "ok": resp.is_success}
