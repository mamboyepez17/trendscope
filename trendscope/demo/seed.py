"""Offline demo payload — realistic sample for dashboard / API without scraping."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_demo_payload(topic: str = "AI in Colombia") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    trends = [
        {
            "rank": 1,
            "title": "Startups colombianas adoptan IA generativa en atención al cliente",
            "source": "reddit",
            "trend_score": 92.0,
            "url": "https://example.com/reddit/ai-startups",
            "category": "tecnologia",
            "sentiment": {"label": "positive", "score": 0.88, "emotions": {"joy": 0.4}},
            "signals": {"reddit_score": 420, "comments": 87},
        },
        {
            "rank": 2,
            "title": "Google Trends: interés en machine learning sube 40% en la región",
            "source": "google_trends",
            "trend_score": 85.5,
            "url": "https://example.com/gtrends/ml",
            "category": "tecnologia",
            "sentiment": {"label": "positive", "score": 0.75, "emotions": {}},
            "signals": {"google_traffic": "50000+"},
        },
        {
            "rank": 3,
            "title": "Debate: ¿la IA reemplazará puestos en soporte técnico?",
            "source": "twitter",
            "trend_score": 78.2,
            "url": "https://example.com/x/ai-jobs",
            "category": "economia",
            "sentiment": {"label": "negative", "score": 0.42, "emotions": {"fear": 0.3}},
            "signals": {"likes": 1200, "retweets": 340},
        },
        {
            "rank": 4,
            "title": "Hacker News: open-source LLMs for Spanish get traction",
            "source": "hackernews",
            "trend_score": 74.0,
            "url": "https://news.ycombinator.com/",
            "category": "tecnologia",
            "sentiment": {"label": "positive", "score": 0.7, "emotions": {}},
            "signals": {"hn_points": 210},
        },
        {
            "rank": 5,
            "title": "GDELT: LatAm news coverage of AI regulation increases",
            "source": "gdelt",
            "trend_score": 68.0,
            "url": "https://example.com/gdelt/regulation",
            "category": "politica",
            "sentiment": {"label": "neutral", "score": 0.5, "emotions": {}},
            "signals": {},
        },
        {
            "rank": 6,
            "title": "YouTube: cursos de prompt engineering en español",
            "source": "youtube",
            "trend_score": 61.5,
            "url": "https://youtube.com/",
            "category": "educacion",
            "sentiment": {"label": "positive", "score": 0.8, "emotions": {}},
            "signals": {"youtube_views": 150000},
        },
    ]

    return {
        "meta": {
            "tool": "TrendScope",
            "version": "demo",
            "generated_at": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "query": {
                "mode": "free",
                "topic": topic,
                "geo": "CO",
                "keywords_used": [topic, f"{topic} CO", f"tendencias {topic}"],
            },
            "total_analyzed": len(trends),
            "top_n_exported": len(trends),
            "sources_used": sorted({t["source"] for t in trends}),
            "sentiment_summary": {
                "positive": 4,
                "negative": 1,
                "neutral": 1,
                "engine": "demo",
                "overall": "positive",
            },
            "source_errors": {},
            "source_health": {
                "reddit": {"score": 1.0},
                "google_trends": {"score": 1.0},
                "twitter": {"score": 0.8},
                "hackernews": {"score": 1.0},
                "gdelt": {"score": 1.0},
                "youtube": {"score": 1.0},
            },
        },
        "top_trends": trends,
        "insights": {
            "summary": (
                f"Demo offline: strong positive momentum around '{topic}' "
                "with debate on labor impact."
            ),
            "emerging": [trends[2]],
            "established": [trends[0], trends[1]],
        },
        "agent_prompt": f"Analyze demo trends for '{topic}' (offline sample data).",
    }
