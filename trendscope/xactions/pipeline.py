"""
XActions-PY — Declarative pipeline engine.

Example pipeline JSON:
{
  "name": "crypto-monitor",
  "steps": [
    {"type": "search", "query": "crypto", "limit": 20, "mode": "Latest"},
    {"type": "filter", "min_likes": 5, "exclude_retweets": true},
    {"type": "notify", "message": "New hits: {count}"},
    {"type": "report", "format": "md"}
  ]
}

Steps:
  search | profile_tweets | filter | notify | report | print | like (writes)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

VALID_TYPES = {
    "search",
    "profile_tweets",
    "filter",
    "notify",
    "report",
    "print",
    "like",
}


def load_pipeline(source: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        data = source
    else:
        p = Path(source)
        data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "steps" not in data:
        raise ValueError("Pipeline must be an object with a 'steps' array")
    steps = data["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError("Pipeline 'steps' must be a non-empty array")
    for i, s in enumerate(steps):
        if not isinstance(s, dict) or s.get("type") not in VALID_TYPES:
            raise ValueError(f"Invalid step {i}: {s!r}")
    data.setdefault("name", "pipeline")
    return data


def apply_filter(tweets: list[dict[str, Any]], step: dict[str, Any]) -> list[dict[str, Any]]:
    min_likes = step.get("min_likes")
    min_retweets = step.get("min_retweets")
    min_views = step.get("min_views")
    exclude_rts = bool(step.get("exclude_retweets"))
    exclude_replies = bool(step.get("exclude_replies"))
    lang = step.get("lang")
    contains = step.get("contains")

    out = []
    for t in tweets:
        if exclude_rts and t.get("is_retweet"):
            continue
        if exclude_replies and t.get("is_reply"):
            continue
        if min_likes is not None and (t.get("likes") or 0) < min_likes:
            continue
        if min_retweets is not None and (t.get("retweets") or 0) < min_retweets:
            continue
        if min_views is not None and (t.get("views") or 0) < min_views:
            continue
        if lang and (t.get("lang") or "").lower() != str(lang).lower():
            continue
        if contains and contains.lower() not in (t.get("text") or "").lower():
            continue
        out.append(t)
    return out


async def run_pipeline(
    client: Any,
    pipeline: dict[str, Any] | str | Path,
    *,
    dry_run: bool = True,
    notify_fn=None,
) -> dict[str, Any]:
    """
    Execute pipeline steps. `like` steps are skipped unless dry_run is False.
    notify_fn(message: str) optional; default logs.
    """
    from .actions import like_tweet
    from .notify import make_notifier
    from .report import render_account_report_md
    from .scrapers import scrape_profile, scrape_tweets, search_tweets

    if notify_fn is None:
        notify_fn = make_notifier()

    pipe = load_pipeline(pipeline)
    tweets: list[dict[str, Any]] = []
    profile: dict[str, Any] | None = None
    log: list[dict[str, Any]] = []
    artifacts: list[str] = []

    for i, step in enumerate(pipe["steps"]):
        stype = step["type"]
        if stype == "search":
            tweets = await search_tweets(
                client,
                step.get("query", ""),
                limit=int(step.get("limit", 20)),
                mode=step.get("mode", "Latest"),
            )
            log.append({"step": i, "type": stype, "count": len(tweets), "query": step.get("query")})
        elif stype == "profile_tweets":
            username = step.get("username") or step.get("target")
            if not username:
                raise ValueError(f"step {i}: profile_tweets requires username")
            profile = await scrape_profile(client, username)
            tweets = await scrape_tweets(
                client, username, limit=int(step.get("limit", 30))
            )
            log.append({"step": i, "type": stype, "count": len(tweets), "username": username})
        elif stype == "filter":
            before = len(tweets)
            tweets = apply_filter(tweets, step)
            log.append(
                {"step": i, "type": stype, "before": before, "after": len(tweets)}
            )
        elif stype == "notify":
            msg_t = step.get("message", "{count} new items")
            msg = msg_t.format(count=len(tweets), name=pipe.get("name"))
            if notify_fn:
                notify_fn(msg)
            else:
                _log.info("notify: %s", msg)
            log.append({"step": i, "type": stype, "message": msg})
        elif stype == "report":
            if profile is None:
                profile = {"username": step.get("username") or "search"}
            md = render_account_report_md(profile, tweets)
            fmt = step.get("format", "md")
            out = step.get("out")
            if out:
                if fmt == "html":
                    from .report import render_account_report_html

                    content = render_account_report_html(profile, tweets)
                else:
                    content = md
                Path(out).write_text(content, encoding="utf-8")
                artifacts.append(out)
            else:
                artifacts.append(md)
            log.append({"step": i, "type": stype, "format": fmt, "out": out})
        elif stype == "print":
            limit = int(step.get("limit", 5))
            for t in tweets[:limit]:
                _log.info(
                    "print @%s ❤%s %s",
                    (t.get("author") or {}).get("username"),
                    t.get("likes"),
                    (t.get("text") or "")[:60],
                )
            log.append({"step": i, "type": stype, "shown": min(limit, len(tweets))})
        elif stype == "like":
            if dry_run:
                log.append({"step": i, "type": stype, "dry_run": True, "would_like": len(tweets)})
                continue
            liked = 0
            max_like = int(step.get("max", len(tweets)))
            for t in tweets[:max_like]:
                tid = t.get("id")
                if not tid:
                    continue
                result = await like_tweet(client, str(tid))
                if result.get("success"):
                    liked += 1
            log.append({"step": i, "type": stype, "liked": liked})
        else:  # pragma: no cover — validated in load_pipeline
            raise ValueError(f"Unknown step type: {stype}")

    return {
        "name": pipe.get("name"),
        "steps_run": len(pipe["steps"]),
        "final_count": len(tweets),
        "log": log,
        "artifacts": artifacts,
        "tweets": tweets,
        "dry_run": dry_run,
    }
