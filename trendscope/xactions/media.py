"""
XActions-PY — Media download + follower snapshots (unfollower detection).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import httpx

_log = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^\w\-.]+")


def safe_filename(name: str, max_len: int = 80) -> str:
    name = _SAFE_NAME.sub("_", name).strip("_")
    return name[:max_len] or "file"


def collect_media_urls(tweets: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Flatten media entries from parsed tweets to {url, type, tweet_id}."""
    out: list[dict[str, str]] = []
    for t in tweets:
        tid = t.get("id") or "unknown"
        for m in t.get("media") or []:
            if not isinstance(m, dict):
                continue
            url = m.get("video_url") or m.get("url")
            if not url:
                continue
            out.append(
                {
                    "url": url,
                    "type": m.get("type") or "unknown",
                    "tweet_id": str(tid),
                }
            )
    return out


async def download_media(
    urls: list[dict[str, str]],
    dest_dir: str | Path,
    *,
    client: httpx.AsyncClient | None = None,
    max_files: int = 50,
) -> dict[str, Any]:
    """
    Download media URLs to dest_dir. Returns {downloaded, skipped, failed, paths}.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    owns = client is None
    if owns:
        client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
    downloaded: list[str] = []
    failed: list[dict[str, str]] = []
    skipped: list[str] = []
    try:
        for item in urls[:max_files]:
            url = item["url"]
            ext = ".mp4" if "video" in (item.get("type") or "") else Path(url.split("?")[0]).suffix or ".jpg"
            if not ext.startswith("."):
                ext = "." + ext
            name = safe_filename(f"{item.get('tweet_id', 'media')}{ext}")
            path = dest / name
            if path.exists():
                skipped.append(str(path))
                continue
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                path.write_bytes(resp.content)
                downloaded.append(str(path))
            except (httpx.HTTPError, OSError) as e:
                failed.append({"url": url, "error": str(e)})
                _log.warning("download failed %s: %s", url, e)
    finally:
        if owns:
            await client.aclose()
    return {
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "dest": str(dest),
    }


# ─── Follower snapshots ───────────────────────────────────────────────────────

def save_follower_snapshot(
    username: str,
    follower_ids: list[str],
    path: Path | str | None = None,
) -> Path:
    """Save current follower id set under ~/.xactions/state/followers_<user>.json."""
    from .watch import save_state

    key = f"followers_snap:{username.lower()}"
    return save_state(key, {"follower_ids": list(follower_ids)}, path=path)


def load_follower_snapshot(
    username: str,
    path: Path | str | None = None,
) -> list[str] | None:
    from .watch import load_state

    state = load_state(f"followers_snap:{username.lower()}", path)
    ids = state.get("follower_ids")
    return list(ids) if ids is not None else None


def diff_followers(
    previous: list[str],
    current: list[str],
) -> dict[str, list[str]]:
    """Who unfollowed (in previous, not current) and who is new."""
    prev_set = set(previous)
    cur_set = set(current)
    return {
        "unfollowed": sorted(prev_set - cur_set),
        "new_followers": sorted(cur_set - prev_set),
    }
