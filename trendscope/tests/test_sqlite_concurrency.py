"""SQLite concurrency: WAL, busy_timeout, lazy cache."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from trendscope.core.persistent_cache import PersistentCache, get_cache, reset_cache_for_tests
from trendscope.watchlist.store import WatchlistStore


def test_cache_wal_mode(tmp_path: Path):
    c = PersistentCache(db_path=tmp_path / "c.db")
    with sqlite3.connect(c.path) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert str(mode).lower() == "wal"


def test_watchlist_wal_mode(tmp_path: Path):
    s = WatchlistStore(db_path=tmp_path / "w.db")
    with sqlite3.connect(s.path) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert str(mode).lower() == "wal"


def test_cache_concurrent_read_write(tmp_path: Path):
    c = PersistentCache(db_path=tmp_path / "c2.db", ttl=60)

    def worker(i: int) -> None:
        c.set(f"k{i}", {"i": i})
        c.get(f"k{i}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, range(40)))


def test_watchlist_concurrent_history_and_list(tmp_path: Path):
    s = WatchlistStore(db_path=tmp_path / "w2.db")

    def write_hist(i: int) -> None:
        s.save_history(
            {
                "meta": {
                    "query": {"topic": f"t{i}", "geo": "CO"},
                    "total_analyzed": 1,
                    "sentiment_summary": {"positive": 1, "negative": 0, "neutral": 0},
                },
                "top_trends": [{"trend_score": 50.0}],
            }
        )

    def list_all(_: int) -> None:
        s.list_active()

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(write_hist, i) for i in range(20)]
        futs += [pool.submit(list_all, i) for i in range(20)]
        for f in futs:
            f.result()


def test_lazy_cache_singleton(tmp_path: Path, monkeypatch):
    # get_cache creates on first use; reset injects tmp path
    c = reset_cache_for_tests(tmp_path / "lazy.db")
    assert c.path.exists()
    assert get_cache() is c
