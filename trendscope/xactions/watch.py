"""
XActions-PY — Watch deltas + scrape cursor checkpoints.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

DEFAULT_STATE_DIR = Path(os.getenv("XACTIONS_HOME", str(Path.home() / ".xactions"))) / "state"


def _state_path(key: str, path: Path | str | None = None) -> Path:
    d = Path(path) if path else DEFAULT_STATE_DIR
    d.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:80]
    return d / f"{safe}.json"


def load_state(key: str, path: Path | str | None = None) -> dict[str, Any]:
    p = _state_path(key, path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(key: str, data: dict[str, Any], path: Path | str | None = None) -> Path:
    p = _state_path(key, path)
    data = dict(data)
    data["updated_at"] = time.time()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def save_cursor(key: str, cursor: str | None, path: Path | str | None = None) -> None:
    state = load_state(key, path)
    if cursor is None:
        state.pop("cursor", None)
    else:
        state["cursor"] = cursor
    save_state(key, state, path)


def load_cursor(key: str, path: Path | str | None = None) -> str | None:
    return load_state(key, path).get("cursor")


def mark_scrape_complete(key: str, path: Path | str | None = None) -> None:
    state = load_state(key, path)
    state["cursor"] = None
    state["completed_at"] = time.time()
    save_state(key, state, path)


def filter_new_ids(
    key: str,
    tweet_ids: list[str],
    path: Path | str | None = None,
    max_seen: int = 5000,
) -> list[str]:
    """Return ids not previously seen; record them as seen."""
    state = load_state(key, path)
    seen = list(state.get("seen_ids") or [])
    seen_set = set(seen)
    new_ids = [i for i in tweet_ids if i not in seen_set]
    if new_ids:
        seen.extend(new_ids)
        if len(seen) > max_seen:
            seen = seen[-max_seen:]
        state["seen_ids"] = seen
        save_state(key, state, path)
    return new_ids


async def watch_search_once(
    client: Any,
    query: str,
    *,
    key: str | None = None,
    limit: int = 20,
    mode: str = "Latest",
    state_dir: Path | str | None = None,
) -> dict[str, Any]:
    """
    One poll: search tweets, return only ids not seen before for this key.
    """
    from .scrapers import search_tweets

    key = key or f"watch:{query}"
    tweets = await search_tweets(client, query, limit=limit, mode=mode)
    ids = [t["id"] for t in tweets if t.get("id")]
    new_ids = filter_new_ids(key, ids, path=state_dir)
    new_set = set(new_ids)
    new_tweets = [t for t in tweets if t.get("id") in new_set]
    return {
        "query": query,
        "fetched": len(tweets),
        "new_count": len(new_tweets),
        "new_tweets": new_tweets,
    }
