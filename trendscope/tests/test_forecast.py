"""Forecasting: EMA, velocity, breakout."""

from pathlib import Path

from trendscope.analyzer.forecast import (
    classify_trend,
    ema_series,
    forecast_from_scores,
    forecast_topic,
    is_breakout,
    velocity,
)
from trendscope.watchlist.store import WatchlistStore


def test_ema_series_basic():
    out = ema_series([10, 20, 30], alpha=0.5)
    assert out[0] == 10
    assert out[1] == 15
    assert out[2] == 22.5


def test_velocity_rising():
    assert velocity([10, 20, 30]) > 0


def test_velocity_falling():
    assert velocity([30, 20, 10]) < 0


def test_breakout_spike():
    values = [40, 41, 39, 40, 42, 40, 95]
    assert is_breakout(values)


def test_no_breakout_flat():
    values = [40, 41, 39, 40, 41, 40]
    assert not is_breakout(values)


def test_classify_trend():
    assert classify_trend(2.0) == "rising"
    assert classify_trend(-2.0) == "falling"
    assert classify_trend(0.0) == "stable"


def test_forecast_from_scores():
    fc = forecast_from_scores("ai", [10, 20, 30, 40, 80])
    assert fc.topic == "ai"
    assert fc.trend == "rising"
    assert fc.points == 5


def test_forecast_topic_from_store(tmp_path):
    from datetime import datetime, timezone

    store = WatchlistStore(db_path=Path(tmp_path) / "f.db")
    for score in [30, 35, 40, 50, 90]:
        store.save_history(
            {
                "meta": {
                    "query": {"topic": "crypto", "geo": "CO"},
                    "total_analyzed": 5,
                    "sentiment_summary": {
                        "positive": 3,
                        "negative": 1,
                        "neutral": 1,
                        "overall": "positive",
                        "engine": "local",
                    },
                },
                "top_trends": [{"trend_score": score, "title": "btc"}],
            }
        )

    result = forecast_topic(store, "crypto", days=30)
    assert result is not None
    assert result["topic"] == "crypto"
    assert result["points"] >= 5
    assert result["trend"] in {"rising", "falling", "stable"}
    assert "ema" in result
    assert "velocity" in result
    assert "breakout" in result


def test_forecast_endpoint(tmp_path, isolated_app):
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from trendscope.api.factory import get_app_state

    store = get_app_state(isolated_app).store
    store.save_history(
        {
            "meta": {
                "query": {"topic": "ai", "geo": "CO"},
                "total_analyzed": 3,
                "sentiment_summary": {"positive": 2, "negative": 0, "neutral": 1},
            },
            "top_trends": [{"trend_score": 70, "title": "t"}],
        }
    )
    store.save_history(
        {
            "meta": {
                "query": {"topic": "ai", "geo": "CO"},
                "total_analyzed": 3,
                "sentiment_summary": {"positive": 2, "negative": 0, "neutral": 1},
            },
            "top_trends": [{"trend_score": 85, "title": "t"}],
        }
    )

    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/forecast", params={"topic": "ai"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic"] == "ai"
