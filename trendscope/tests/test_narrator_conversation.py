"""Narrator for conversation mood — Spanish, answer only."""

from unittest.mock import patch

from trendscope.narrator.engine import generate_summary


def test_conversation_narrative_prompt_spanish_no_thinking():
    payload = {
        "meta": {
            "query": {"topic": "Abelardo", "geo": "CO"},
            "total_analyzed": 20,
            "sentiment_summary": {"positive": 8, "negative": 10, "neutral": 2},
        },
        "top_trends": [],
        "insights": {
            "conversation": {
                "mood": "hot",
                "emoji": "😠",
                "acceptance_score": -0.2,
                "support": 6,
                "against": 12,
                "toxic": 3,
            }
        },
    }
    with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
        with patch("trendscope.narrator.engine.settings.narrator_provider", "deepseek"):
            with patch("trendscope.narrator.engine.settings.deepseek_model", "deepseek-flash"):
                with patch(
                    "trendscope.narrator.engine._call_deepseek",
                    return_value="La conversación está caliente: más rechazo que apoyo.",
                ) as mock_ds:
                    result = generate_summary(payload, style="alert")
    assert result["provider"] == "deepseek"
    prompt = mock_ds.call_args[0][0]
    assert "español" in prompt.lower() or "espanol" in prompt.lower() or "COMPLETO" in prompt
    assert "chain of thought" not in prompt.lower()
    assert "reasoning" not in prompt.lower()
