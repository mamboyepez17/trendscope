"""
XActions-PY — Analytics
Análisis de engagement sobre tweets scrapeados. Puro stdlib, sin dependencias.

Métricas calculadas:
  - Promedios de likes, retweets, replies, quotes, views por tweet
  - Engagement rate (por followers y por views)
  - Top tweets por engagement
  - Mejores horas y días de la semana para publicar
  - Ratios de contenido (con media, replies, quotes)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

TWEET_DATE_FORMAT = "%a %b %d %H:%M:%S %z %Y"


def parse_tweet_date(created_at: str | None) -> datetime | None:
    """Parsea el formato de fecha de Twitter: 'Mon Jun 21 12:00:00 +0000 2026'."""
    if not created_at:
        return None
    try:
        return datetime.strptime(created_at, TWEET_DATE_FORMAT)
    except (ValueError, TypeError):
        return None


def _engagement_score(tweet: dict[str, Any]) -> int:
    """Score de engagement ponderado: replies y quotes pesan más que likes."""
    return (
        (tweet.get("likes") or 0)
        + (tweet.get("retweets") or 0) * 2
        + (tweet.get("replies") or 0) * 3
        + (tweet.get("quotes") or 0) * 3
        + (tweet.get("bookmarks") or 0) * 2
    )


def _avg(values: list[int]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def analyze_tweets(
    tweets: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
    top_n: int = 5,
) -> dict[str, Any]:
    """
    Analiza una lista de tweets y devuelve un reporte de engagement.

    tweets: lista de tweets en formato XActions (ver parse_tweet).
    profile: perfil del autor (opcional, mejora el engagement rate).
    top_n: cuántos top tweets incluir.
    """
    if not tweets:
        return {
            "total_tweets": 0,
            "averages": {},
            "engagement_rate_followers": None,
            "engagement_rate_views": None,
            "top_tweets": [],
            "best_hours": [],
            "best_days": [],
            "content": {},
        }

    likes = [t.get("likes") or 0 for t in tweets]
    retweets = [t.get("retweets") or 0 for t in tweets]
    replies = [t.get("replies") or 0 for t in tweets]
    quotes = [t.get("quotes") or 0 for t in tweets]
    views = [t.get("views") or 0 for t in tweets]
    bookmarks = [t.get("bookmarks") or 0 for t in tweets]

    averages = {
        "likes": _avg(likes),
        "retweets": _avg(retweets),
        "replies": _avg(replies),
        "quotes": _avg(quotes),
        "views": _avg(views),
        "bookmarks": _avg(bookmarks),
    }

    # Engagement rate = engagement promedio por tweet / alcance.
    per_tweet_engagement = [
        lk + rt + rp + qt for lk, rt, rp, qt in zip(likes, retweets, replies, quotes)
    ]
    avg_engagement = _avg(per_tweet_engagement)

    engagement_rate_followers: float | None = None
    if profile and profile.get("followers"):
        engagement_rate_followers = round(avg_engagement / profile["followers"] * 100, 4)

    engagement_rate_views: float | None = None
    total_views = sum(views)
    if total_views > 0:
        engagement_rate_views = round(
            (sum(likes) + sum(retweets) + sum(replies) + sum(quotes)) / total_views * 100, 4
        )

    # Top tweets por engagement score
    scored = sorted(tweets, key=_engagement_score, reverse=True)
    top_tweets = [
        {
            "id": t.get("id"),
            "url": t.get("url"),
            "text": (t.get("text") or "")[:120],
            "likes": t.get("likes"),
            "retweets": t.get("retweets"),
            "replies": t.get("replies"),
            "views": t.get("views"),
            "score": _engagement_score(t),
        }
        for t in scored[:top_n]
    ]

    # Mejores horas / días (por engagement acumulado)
    hour_engagement: dict[int, int] = {}
    day_engagement: dict[str, int] = {}
    dated = 0
    for t in tweets:
        dt = parse_tweet_date(t.get("created_at"))
        if not dt:
            continue
        dated += 1
        score = _engagement_score(t)
        hour_engagement[dt.hour] = hour_engagement.get(dt.hour, 0) + score
        day = dt.strftime("%A")
        day_engagement[day] = day_engagement.get(day, 0) + score

    best_hours = sorted(hour_engagement.items(), key=lambda kv: kv[1], reverse=True)[:3]
    best_days = sorted(day_engagement.items(), key=lambda kv: kv[1], reverse=True)[:3]

    with_media = sum(1 for t in tweets if t.get("media"))
    content = {
        "with_media_pct": round(with_media / len(tweets) * 100, 1),
        "replies_pct": round(sum(1 for t in tweets if t.get("is_reply")) / len(tweets) * 100, 1),
        "retweets_pct": round(sum(1 for t in tweets if t.get("is_retweet")) / len(tweets) * 100, 1),
        "quotes_pct": round(sum(1 for t in tweets if t.get("is_quote")) / len(tweets) * 100, 1),
        "tweets_with_date": dated,
    }

    return {
        "total_tweets": len(tweets),
        "averages": averages,
        "engagement_rate_followers": engagement_rate_followers,
        "engagement_rate_views": engagement_rate_views,
        "top_tweets": top_tweets,
        "best_hours": [{"hour": h, "engagement": e} for h, e in best_hours],
        "best_days": [{"day": d, "engagement": e} for d, e in best_days],
        "content": content,
    }


def compare_accounts(
    profile_a: dict[str, Any],
    tweets_a: list[dict[str, Any]],
    profile_b: dict[str, Any],
    tweets_b: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compara dos cuentas lado a lado (perfil + engagement de tweets recientes).
    """
    report_a = analyze_tweets(tweets_a, profile=profile_a)
    report_b = analyze_tweets(tweets_b, profile=profile_b)

    def _side(profile: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
        return {
            "username": profile.get("username"),
            "name": profile.get("name"),
            "followers": profile.get("followers"),
            "following": profile.get("following"),
            "tweets_count": profile.get("tweets_count"),
            "verified": profile.get("verified"),
            "analyzed_tweets": report.get("total_tweets"),
            "averages": report.get("averages"),
            "engagement_rate_followers": report.get("engagement_rate_followers"),
            "engagement_rate_views": report.get("engagement_rate_views"),
        }

    a = _side(profile_a, report_a)
    b = _side(profile_b, report_b)

    def _winner(key: str, higher_is_better: bool = True) -> str | None:
        va = a.get(key)
        vb = b.get(key)
        if va is None or vb is None:
            return None
        try:
            if va == vb:
                return "tie"
            if higher_is_better:
                return a["username"] if va > vb else b["username"]
            return a["username"] if va < vb else b["username"]
        except TypeError:
            return None

    avg_a = (report_a.get("averages") or {}).get("likes") or 0
    avg_b = (report_b.get("averages") or {}).get("likes") or 0

    return {
        "a": a,
        "b": b,
        "winner": {
            "followers": _winner("followers"),
            "engagement_rate_followers": _winner("engagement_rate_followers"),
            "avg_likes": (
                a["username"] if avg_a > avg_b else b["username"] if avg_b > avg_a else "tie"
            ),
        },
        "reports": {"a": report_a, "b": report_b},
    }
