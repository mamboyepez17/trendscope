"""Repository interface contract tests."""

from pathlib import Path

from trendscope.watchlist.models import WatchItem
from trendscope.watchlist.repository import SqliteWatchlistRepository, WatchlistRepository
from trendscope.watchlist.store import WatchlistStore


def _repo(tmp_path) -> SqliteWatchlistRepository:
    return SqliteWatchlistRepository(WatchlistStore(db_path=tmp_path / "r.db"))


def test_sqlite_repo_is_watchlist_repository(tmp_path):
    assert isinstance(_repo(tmp_path), WatchlistRepository)


def test_repo_crud_roundtrip(tmp_path):
    repo = _repo(tmp_path)
    item = repo.add(
        WatchItem(
            id=None,
            topic="ai",
            category=None,
            geo="CO",
            sentiment_engine="local",
            interval_minutes=60,
            org_id="orgA",
        )
    )
    assert repo.get(item.id, org_id="orgA") is not None
    assert repo.get(item.id, org_id="orgB") is None
    listed = repo.list_all(org_id="orgA")
    assert [i.topic for i in listed] == ["ai"]
    assert repo.delete(item.id, org_id="orgA")
    assert repo.get(item.id, org_id="orgA") is None


def test_repo_history_and_stats(tmp_path):
    repo = _repo(tmp_path)
    repo.save_history(
        {
            "meta": {
                "query": {"topic": "x", "geo": "CO"},
                "total_analyzed": 1,
                "sentiment_summary": {"positive": 1},
            },
            "top_trends": [{"trend_score": 50, "title": "t"}],
        },
        org_id="orgA",
    )
    hist = repo.get_history(topic="x", org_id="orgA")
    assert len(hist) == 1
    stats = repo.get_stats()
    assert stats["total_history_records"] >= 1
    pruned = repo.prune_history(keep_days=365)
    assert "deleted_rows" in pruned
