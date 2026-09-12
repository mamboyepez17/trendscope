"""Narrative must be in Spanish; Twitter query helpers."""

from unittest.mock import patch

from trendscope.narrator.engine import _build_prompt
from trendscope.scrapers.twitter import _twitter_query


def test_build_prompt_forces_spanish():
    payload = {
        "meta": {
            "query": {"topic": "ai", "geo": "CO"},
            "total_analyzed": 1,
            "sentiment_summary": {"positive": 1, "negative": 0, "neutral": 0},
        },
        "top_trends": [],
        "insights": {},
    }
    p = _build_prompt(payload, "executive")
    assert "español" in p.lower() or "exclusivamente en español" in p.lower()


def test_twitter_query_still_quoted():
    assert _twitter_query("Abelardo de la Espriella").startswith('"')


def test_deepseek_system_prompt_spanish():
    from pathlib import Path

    src = Path("trendscope/narrator/engine.py").read_text(encoding="utf-8")
    assert "Responde SIEMPRE en español" in src or "exclusivamente en español" in src
