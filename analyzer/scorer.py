# analyzer/scorer.py
import math
import re
from datetime import datetime, timezone

from loguru import logger

from core.query import TrendQuery


def _score_by_source(item: dict) -> float:
    """Puntuacion base segun la fuente del item."""
    source = item.get("source", "")

    if source == "reddit":
        upvotes = min(item.get("score", 0), 50000)
        ratio = item.get("upvote_ratio", 0.5)
        comments = min(item.get("comments", 0), 5000)
        # Bonus por recencia
        created = item.get("created_utc", 0)
        hours_old = (datetime.now(timezone.utc).timestamp() - created) / 3600 if created else 999
        recency = 15 if hours_old < 6 else (8 if hours_old < 24 else 0)
        return (upvotes / 50000 * 35) + (ratio * 25) + (comments / 5000 * 25) + recency

    elif source == "google_trends_rss":
        t = item.get("approx_traffic", "0").replace("+", "").replace(",", "")
        # Manejar sufijos K y M
        t_upper = t.upper().strip()
        try:
            if "M" in t_upper:
                traffic = int(re.sub(r"[^0-9]", "", t_upper) or "0") * 1000000
            elif "K" in t_upper:
                traffic = int(re.sub(r"[^0-9]", "", t_upper) or "0") * 1000
            else:
                traffic = int(re.sub(r"[^0-9]", "", t) or "0")
            # Escala logaritmica: 100 -> 40, 1000 -> 55, 10000 -> 70, 100000 -> 85
            if traffic > 0:
                return min(85, 30 + math.log10(traffic) * 11)
            return 35.0
        except Exception:
            return 50.0

    elif source == "google_trends_pytrends":
        return min(80, item.get("avg_interest_7d", 0) * 0.8)

    elif source == "twitter":
        likes = min(item.get("likes", 0), 10000)
        retweets = min(item.get("retweets", 0), 5000)
        followers = min(item.get("user_followers", 0), 1000000)
        return (likes / 10000 * 40) + (retweets / 5000 * 35) + (followers / 1000000 * 25)

    elif source == "amazon_bestsellers":
        rank_str = item.get("rank", "#99")
        rank_num = int(re.sub(r"[^0-9]", "", rank_str) or "99")
        return max(0, 100 - rank_num * 1.5)

    elif source == "tiktok_trending":
        # Si tiene video_count, usar eso como proxy de popularidad
        video_count = item.get("video_count", 0)
        if video_count > 0:
            return min(85, 50 + (video_count / 1000000) * 35)
        return 65.0

    return 0.0


def score_item(item: dict, query: TrendQuery) -> float:
    """Calcula trend_score para un item individual."""
    score = _score_by_source(item)
    kws = [k.lower() for k in query.keywords]

    # Bonus por relevancia con las keywords de la query
    text = (item.get("title") or item.get("keyword") or item.get("text") or "").lower()
    if kws:
        matches = sum(1 for k in kws if k in text)
        score = min(100, score + matches * 8)

    # Bonus/penalizacion por sentimiento
    sentiment = item.get("sentiment_label", "neutral")
    if sentiment == "positive":
        score = min(100, score + 5)
    elif sentiment == "negative":
        score = max(0, score - 3)

    return round(score, 2)


def enrich_and_score(items: list[dict], query: TrendQuery) -> list[dict]:
    """Enriquece items con trend_score y los ordena de mayor a menor."""
    for item in items:
        item["trend_score"] = score_item(item, query)
        item["scored_at"] = datetime.now(timezone.utc).isoformat()

    scored = sorted(items, key=lambda x: x["trend_score"], reverse=True)
    if scored:
        logger.success(
            f"Scoring: {len(scored)} items | "
            f"Top score: {scored[0]['trend_score']} | "
            f"'{(scored[0].get('title') or scored[0].get('keyword', ''))[:50]}'"
        )
    return scored
