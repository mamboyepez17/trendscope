"""Org isolation: each API key/org only sees its own watchlist/history/jobs."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from trendscope.watchlist.models import WatchItem
from trendscope.watchlist.store import WatchlistStore


def test_store_list_filtered_by_org(tmp_path):
    store = WatchlistStore(db_path=tmp_path / "w.db")
    store.add(
        WatchItem(
            id=None,
            topic="a-topic",
            category=None,
            geo="CO",
            sentiment_engine="local",
            interval_minutes=60,
            org_id="orgA",
        )
    )
    store.add(
        WatchItem(
            id=None,
            topic="b-topic",
            category=None,
            geo="CO",
            sentiment_engine="local",
            interval_minutes=60,
            org_id="orgB",
        )
    )
    a = store.list_all(org_id="orgA")
    b = store.list_all(org_id="orgB")
    assert [i.topic for i in a] == ["a-topic"]
    assert [i.topic for i in b] == ["b-topic"]


def test_store_get_org_checked(tmp_path):
    store = WatchlistStore(db_path=tmp_path / "w.db")
    item = store.add(
        WatchItem(
            id=None,
            topic="x",
            category=None,
            geo="CO",
            sentiment_engine="local",
            interval_minutes=60,
            org_id="orgA",
        )
    )
    assert store.get(item.id, org_id="orgA") is not None
    assert store.get(item.id, org_id="orgB") is None


def test_history_org_filter(tmp_path):
    store = WatchlistStore(db_path=tmp_path / "h.db")
    payload = {
        "meta": {
            "query": {"topic": "ai", "geo": "CO"},
            "total_analyzed": 1,
            "sentiment_summary": {"positive": 1},
        },
        "top_trends": [{"trend_score": 80, "title": "t"}],
    }
    store.save_history(payload, org_id="orgA")
    store.save_history(payload, org_id="orgB")
    a = store.get_history(topic="ai", org_id="orgA")
    b = store.get_history(topic="ai", org_id="orgB")
    assert len(a) == 1
    assert len(b) == 1
    assert a[0].org_id == "orgA"
    assert b[0].org_id == "orgB"


def test_api_watchlist_isolated_between_orgs(isolated_app):
    client = TestClient(isolated_app)
    keys = "keyA|orgA|trends:read+watchlist:write,keyB|orgB|trends:read+watchlist:write"

    with patch("trendscope.api.middleware.settings.api_key_required", True):
        with patch("trendscope.api.middleware.settings.api_keys", keys):
            r1 = client.post(
                "/watchlist",
                params={"topic": "fromA"},
                headers={"X-API-Key": "keyA"},
            )
            assert r1.status_code == 200
            r2 = client.post(
                "/watchlist",
                params={"topic": "fromB"},
                headers={"X-API-Key": "keyB"},
            )
            assert r2.status_code == 200

            list_a = client.get("/watchlist", headers={"X-API-Key": "keyA"}).json()
            list_b = client.get("/watchlist", headers={"X-API-Key": "keyB"}).json()

    topics_a = {i["topic"] for i in list_a["items"]}
    topics_b = {i["topic"] for i in list_b["items"]}
    assert topics_a == {"fromA"}
    assert topics_b == {"fromB"}


def test_api_cannot_get_other_org_item(isolated_app):
    client = TestClient(isolated_app)
    keys = "keyA|orgA|watchlist:write,keyB|orgB|watchlist:write"
    with patch("trendscope.api.middleware.settings.api_key_required", True):
        with patch("trendscope.api.middleware.settings.api_keys", keys):
            created = client.post(
                "/watchlist",
                params={"topic": "secret"},
                headers={"X-API-Key": "keyA"},
            ).json()
            item_id = created["id"]
            ok = client.get(f"/watchlist/{item_id}", headers={"X-API-Key": "keyA"})
            deny = client.get(f"/watchlist/{item_id}", headers={"X-API-Key": "keyB"})
    assert ok.status_code == 200
    assert deny.status_code == 404


def test_default_org_without_auth(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        client.post("/watchlist", params={"topic": "anon"})
        items = client.get("/watchlist").json()["items"]
    assert any(i["topic"] == "anon" and i["org_id"] == "default" for i in items)
