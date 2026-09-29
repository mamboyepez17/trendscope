# scrapers/youtube.py
# YouTube Trends — gratis, sin auth, via API publica de search
# Usa el endpoint publico de YouTube que devuelve videos trending
import re
import time
import json

import requests
from loguru import logger

from trendscope.core.query import TrendQuery


def _parse_published_utc(published: str) -> float | None:
    """Convierte 'Hace 2 días' / '2 days ago' / 'Streamed 3 hours ago' a unix ts."""
    import re
    import time

    if not published:
        return None
    s = published.lower()
    m = re.search(
        r"(\d+)\s*(second|minute|hour|day|week|month|year|segundo|minuto|hora|d[ií]a|semana|mes|a[nñ]o)s?",
        s,
    )
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    # Normalizar español → inglés
    unit = {
        "segundo": "second",
        "minuto": "minute",
        "hora": "hour",
        "día": "day",
        "dia": "day",
        "semana": "week",
        "mes": "month",
        "año": "year",
        "ano": "year",
    }.get(unit, unit)
    mult = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
        "week": 604800,
        "month": 2592000,
        "year": 31536000,
    }.get(unit, 0)
    if not mult:
        return None
    return time.time() - n * mult


# Filtro "fecha de subida" + tipo video: hoy / esta semana / este mes / este año
_YT_UPLOAD_FILTER = {1: "EgQIAhAB", 7: "EgQIAxAB", 31: "EgQIBBAB", 366: "EgQIBRAB"}


def _yt_filter(days: float) -> str:
    for limit_days, code in sorted(_YT_UPLOAD_FILTER.items()):
        if days <= limit_days:
            return code
    return "EgIQAQ=="


def _context(geo: str | None) -> dict:
    from trendscope.core.locale import youtube_client

    return {"client": {"clientName": "WEB", "clientVersion": "2.20240601.00.00", **youtube_client(geo)}}


def _search_youtube(
    keyword: str, limit: int = 20, max_age_days: float = 7, geo: str | None = None
) -> list[dict]:
    """
    Busca videos en YouTube usando el endpoint interno publico.
    No requiere API key — usa el mismo endpoint que usa la pagina de busqueda.
    """
    url = "https://www.youtube.com/youtubei/v1/search"
    payload = {
        "context": _context(geo),
        "query": keyword,
        "params": _yt_filter(max_age_days),  # solo videos recientes
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        # Navegar la estructura JSON de YouTube (es compleja y anidada)
        contents = (
            data.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )

        for section in contents:
            items = (
                section.get("itemSectionRenderer", {})
                .get("contents", [])
            )
            for item in items:
                video = item.get("videoRenderer", {})
                if not video or not video.get("videoId"):
                    continue

                title = (
                    video.get("title", {})
                    .get("runs", [{}])[0]
                    .get("text", "")
                )

                channel = (
                    video.get("ownerText", {})
                    .get("runs", [{}])[0]
                    .get("text", "")
                )

                # Views: "1.2M views" -> extraer numero
                view_text = (
                    video.get("viewCount", {})
                    .get("simpleText", "")
                )
                views = _parse_views(view_text)

                # Tiempo: "Hace 2 dias"
                published = (
                    video.get("publishedTimeText", {})
                    .get("simpleText", "")
                )

                video_id = video.get("videoId", "")
                created = _parse_published_utc(published)
                results.append({
                    "source": "youtube",
                    "keyword": keyword,
                    "title": title,
                    "channel": channel,
                    "views": views,
                    "published": published,
                    "created_utc": created,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "video_id": video_id,
                })

                if len(results) >= limit:
                    break

        logger.info(f"YouTube search '{keyword}': {len(results)} videos")
        return results

    except Exception as e:
        logger.warning(f"YouTube search '{keyword}': {e}")
        return []


def _parse_views(view_text: str) -> int:
    """Convierte '1.2M views' o '15K views' a entero."""
    if not view_text:
        return 0
    # Extraer numero
    match = re.search(r"([\d.]+)\s*([KM]?)", view_text, re.I)
    if not match:
        return 0
    num = float(match.group(1))
    suffix = match.group(2).upper()
    if suffix == "M":
        return int(num * 1_000_000)
    elif suffix == "K":
        return int(num * 1_000)
    return int(num)


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de YouTube."""
    all_videos: list[dict] = []

    for kw in query.keywords[:3]:
        videos = _search_youtube(kw, limit=20, max_age_days=query.max_age_days, geo=query.geo)
        all_videos.extend(videos)
        time.sleep(0.5)

    logger.info(f"YouTube: {len(all_videos)} videos para '{query.display_name}'")
    return all_videos


# ── Comentarios ──────────────────────────────────────────────────────────────
# /youtubei/v1/next con el videoId trae un token de continuación de la sección
# de comentarios; con ese token /next devuelve los comentarios. YouTube usa dos
# formatos: el viejo `commentRenderer` y el nuevo `commentEntityPayload`
# (en frameworkUpdates). Se soportan ambos.

_NEXT_URL = "https://www.youtube.com/youtubei/v1/next"


def _walk(obj, key: str):
    """Todos los valores de `key` en un JSON anidado."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if k == key:
                    yield v
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)


def _text(node) -> str:
    if not isinstance(node, dict):
        return str(node or "")
    if "simpleText" in node:
        return node["simpleText"]
    if "content" in node and isinstance(node["content"], str):
        return node["content"]
    return "".join(r.get("text", "") for r in node.get("runs", []) if isinstance(r, dict))


def _parse_count(text: str) -> int:
    """'1,2 mil' / '1.2K' / '15' → entero (likes de comentarios)."""
    if not text:
        return 0
    t = str(text).lower().replace("\xa0", " ")
    m = re.search(r"([\d]+(?:[.,]\d+)?)\s*(millones|mill|mil|k|m)?\b", t)
    if not m:
        return 0
    num = float(m.group(1).replace(",", "."))
    suf = m.group(2) or ""
    if suf in ("k", "mil"):
        num *= 1_000
    elif suf in ("m", "mill", "millones"):
        num *= 1_000_000
    return int(num)


def _comments_token(watch: dict) -> str | None:
    for section in _walk(watch, "itemSectionRenderer"):
        if isinstance(section, dict) and section.get("sectionIdentifier") == "comment-item-section":
            for cmd in _walk(section, "continuationCommand"):
                if isinstance(cmd, dict) and cmd.get("token"):
                    return cmd["token"]
    for panel in _walk(watch, "engagementPanelSectionListRenderer"):
        if isinstance(panel, dict) and "comment" in str(panel.get("panelIdentifier", "")):
            for cmd in _walk(panel, "continuationCommand"):
                if isinstance(cmd, dict) and cmd.get("token"):
                    return cmd["token"]
    return None


def parse_comments_payload(data: dict, video: dict | None = None) -> list[dict]:
    """Extrae comentarios de una respuesta de /next (ambos formatos)."""
    video = video or {}
    out: list[dict] = []
    seen: set[str] = set()

    def add(cid, text, author, likes, published):
        text = (text or "").strip()
        if not text or cid in seen:
            return
        seen.add(cid)
        out.append({
            "source": "youtube_comment",
            "reddit_id": cid,
            "post_id": video.get("video_id", ""),
            "title": text[:200],
            "text": text[:500],
            "author": (author or "").lstrip("@"),
            "score": likes,
            "likes": likes,
            "created_utc": _parse_published_utc(published),
            "published": published,
            "permalink": f"{video.get('url', '')}&lc={cid}" if video.get("url") and cid else video.get("url", ""),
            "kind": "comment",
        })

    for p in _walk(data, "commentEntityPayload"):
        if not isinstance(p, dict):
            continue
        props = p.get("properties") or {}
        add(
            props.get("commentId") or p.get("key", ""),
            _text(props.get("content") or {}),
            (p.get("author") or {}).get("displayName", ""),
            _parse_count((p.get("toolbar") or {}).get("likeCountNotliked", "")),
            props.get("publishedTime", ""),
        )
    for r in _walk(data, "commentRenderer"):
        if not isinstance(r, dict):
            continue
        add(
            r.get("commentId", ""),
            _text(r.get("contentText") or {}),
            _text(r.get("authorText") or {}),
            _parse_count(_text(r.get("voteCount") or {})),
            _text(r.get("publishedTimeText") or {}),
        )
    return out


def fetch_video_comments(video: dict, limit: int = 20, geo: str | None = None) -> list[dict]:
    """Comentarios principales de un video (sin API key)."""
    vid = video.get("video_id")
    if not vid:
        return []
    ctx = _context(geo)
    try:
        watch = requests.post(_NEXT_URL, json={"context": ctx, "videoId": vid}, timeout=15)
        watch.raise_for_status()
        token = _comments_token(watch.json())
        if not token:
            logger.info(f"YouTube {vid}: comentarios desactivados o sin token")
            return []
        resp = requests.post(_NEXT_URL, json={"context": ctx, "continuation": token}, timeout=15)
        resp.raise_for_status()
        comments = parse_comments_payload(resp.json(), video)[:limit]
        logger.info(f"YouTube comments {vid}: {len(comments)}")
        return comments
    except Exception as e:
        logger.warning(f"YouTube comments {vid}: {e}")
        return []


def collect_comments(query: TrendQuery, videos: int = 4, per_video: int = 20) -> tuple[list, list]:
    """Busca videos recientes del tema y trae sus comentarios.

    Devuelve (videos, comentarios). Prioriza los videos con más vistas.
    """
    keyword = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not keyword:
        return [], []
    found = _search_youtube(keyword, limit=12, max_age_days=query.max_age_days, geo=query.geo)
    from trendscope.core.text import mentions_count, topic_tokens

    tokens = topic_tokens(keyword)
    need = len(tokens) if len(tokens) <= 3 else -(-2 * len(tokens) // 3)
    relevant = [v for v in found if not tokens or mentions_count(v.get("title", ""), tokens) >= need]
    relevant.sort(key=lambda v: v.get("views") or 0, reverse=True)
    comments: list[dict] = []
    for v in relevant[:videos]:
        comments.extend(fetch_video_comments(v, limit=per_video, geo=query.geo))
        time.sleep(0.3)
    return relevant, comments
