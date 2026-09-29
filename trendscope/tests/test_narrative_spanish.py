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


def test_deepseek_system_prompt_follows_requested_language():
    from pathlib import Path

    src = Path("trendscope/narrator/engine.py").read_text(encoding="utf-8")
    assert "Responde SIEMPRE en el idioma" in src


def test_build_prompt_language_follows_payload():
    base = {"top_trends": [], "insights": {}}
    en = _build_prompt({**base, "meta": {"query": {"topic": "ai", "geo": "US"}}}, "executive")
    pt = _build_prompt({**base, "meta": {"query": {"topic": "ai", "geo": "BR"}}}, "executive")
    forced = _build_prompt({**base, "meta": {"lang": "en", "query": {"geo": "CO"}}}, "executive")
    assert "exclusively in English" in en
    assert "exclusivamente em português" in pt
    assert "exclusively in English" in forced
