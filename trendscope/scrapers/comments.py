"""Recolector de comentarios de la gente (la materia prima del Índice de Ánimo).

Fuentes, en orden: Reddit (reddit-actions o JSON público) · Hacker News
(Algolia) · respuestas en X (si hay cookies). Nunca lanza excepciones: cada
fuente reporta su estado en ``sources``.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from trendscope.core.query import TrendQuery


def _reddit(topic: str, limit: int, comments_per_post: int, days: float) -> tuple[list, list, str]:
    from trendscope.scrapers import reddit_comments

    posts = reddit_comments.search_public_posts(topic, limit=limit, max_age_days=days)
    comments: list[dict] = []
    # Los hilos con más comentarios primero: ahí está la conversación
    ranked = sorted(posts, key=lambda p: p.get("comments") or 0, reverse=True)
    for p in ranked[:4]:
        pid = p.get("reddit_id") or ""
        if pid and (p.get("comments") or 1) > 0:
            comments.extend(reddit_comments.fetch_comments(pid, limit=comments_per_post))
    return posts, comments, f"posts={len(posts)} comments={len(comments)}"


def _hn(topic: str, limit: int, comments_per_post: int, days: float) -> tuple[list, list, str]:
    from trendscope.scrapers import hn_comments

    posts = hn_comments.fetch_hn_posts(topic, limit=max(3, limit // 2), max_age_days=days)
    comments = hn_comments.fetch_hn_comments(
        topic, limit=comments_per_post * 2, max_age_days=days
    )
    return posts, comments, f"posts={len(posts)} comments={len(comments)}"


def _youtube(query: TrendQuery, comments_per_post: int) -> tuple[list, list, str]:
    from trendscope.scrapers import youtube

    videos, comments = youtube.collect_comments(query, videos=4, per_video=comments_per_post)
    return [], comments, f"videos={len(videos)} comments={len(comments)}"


def _x(query: TrendQuery) -> tuple[list, list, str]:
    from trendscope.scrapers import x_replies

    rows = x_replies.run(query)
    return [], rows, f"signals={len(rows)}"


def collect(topic: str, query: TrendQuery | None = None, limit: int = 8,
            comments_per_post: int = 15) -> dict:
    """Devuelve {"posts", "comments", "sources"} para un tema."""
    query = query or TrendQuery(mode="free", free_topic=topic)
    days = query.max_age_days
    jobs = {
        "reddit": lambda: _reddit(topic, limit, comments_per_post, days),
        "hackernews": lambda: _hn(topic, limit, comments_per_post, days),
        "youtube": lambda: _youtube(query, comments_per_post),
        "x": lambda: _x(query),
    }
    posts: list[dict] = []
    comments: list[dict] = []
    sources: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {name: pool.submit(fn) for name, fn in jobs.items()}
        for name, fut in futures.items():
            try:
                p, c, status = fut.result(timeout=60)
                posts.extend(p)
                comments.extend(c)
                sources[name] = status
            except Exception as e:
                logger.warning(f"Comentarios {name}: {e}")
                sources[name] = f"error: {e}"
    return {"posts": posts, "comments": comments, "sources": sources}
