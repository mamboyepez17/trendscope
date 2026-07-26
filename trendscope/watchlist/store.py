"""SQLite persistence for watchlist and analysis history."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from trendscope.settings import settings
from trendscope.watchlist.models import AnalysisRecord, WatchItem


class WatchlistStore:
    """SQLite store for watchlist and historical analysis records."""

    def __init__(self, db_path: str | Path | None = None):
        self.path = Path(db_path or f"{settings.data_dir}/watchlist.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    category TEXT,
                    geo TEXT NOT NULL DEFAULT 'CO',
                    interval_minutes INTEGER NOT NULL DEFAULT 60,
                    sentiment_engine TEXT NOT NULL DEFAULT 'local',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    geo TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    total_signals INTEGER,
                    top_score REAL,
                    positive INTEGER,
                    negative INTEGER,
                    neutral INTEGER,
                    payload_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_topic_at ON history(topic, analyzed_at)"
            )

    def add(self, item: WatchItem) -> WatchItem:
        """Add a watch item."""
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                """
                INSERT INTO watchlist (topic, category, geo, interval_minutes, sentiment_engine, active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    item.topic,
                    item.category,
                    item.geo,
                    item.interval_minutes,
                    item.sentiment_engine,
                    int(item.active),
                ),
            )
            item.id = cur.lastrowid
            item.created_at = datetime.now(timezone.utc)
        return item

    def list_all(self) -> list[WatchItem]:
        """Return all watch items."""
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM watchlist ORDER BY created_at DESC").fetchall()
        return [self._row_to_watchitem(r) for r in rows]

    def list_active(self) -> list[WatchItem]:
        """Return active watch items."""
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM watchlist WHERE active = 1 ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_watchitem(r) for r in rows]

    def get(self, item_id: int) -> Optional[WatchItem]:
        """Return a single watch item by id."""
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM watchlist WHERE id = ?", (item_id,)).fetchone()
        return self._row_to_watchitem(row) if row else None

    def update(self, item: WatchItem) -> WatchItem:
        """Update an existing watch item."""
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                UPDATE watchlist
                SET topic = ?, category = ?, geo = ?, interval_minutes = ?,
                    sentiment_engine = ?, active = ?
                WHERE id = ?
                """,
                (
                    item.topic,
                    item.category,
                    item.geo,
                    item.interval_minutes,
                    item.sentiment_engine,
                    int(item.active),
                    item.id,
                ),
            )
        return item

    def delete(self, item_id: int) -> bool:
        """Delete a watch item."""
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
            return cur.rowcount > 0

    def save_history(self, payload: dict) -> AnalysisRecord:
        """Persist a snapshot from a pipeline payload."""
        meta = payload.get("meta", {})
        query = meta.get("query", {})
        sentiment = meta.get("sentiment_summary", {})
        top = payload.get("top_trends", [])
        topic = query.get("topic", "unknown")
        record = AnalysisRecord(
            id=None,
            topic=topic,
            geo=query.get("geo", "CO"),
            analyzed_at=datetime.now(timezone.utc),
            total_signals=meta.get("total_analyzed", 0) or 0,
            top_score=top[0]["trend_score"] if top else 0.0,
            positive=sentiment.get("positive", 0) or 0,
            negative=sentiment.get("negative", 0) or 0,
            neutral=sentiment.get("neutral", 0) or 0,
            payload_json=json.dumps(payload, ensure_ascii=False),
        )
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                """
                INSERT INTO history
                (topic, geo, analyzed_at, total_signals, top_score, positive, negative, neutral, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.topic,
                    record.geo,
                    record.analyzed_at.isoformat(),
                    record.total_signals,
                    record.top_score,
                    record.positive,
                    record.negative,
                    record.neutral,
                    record.payload_json,
                ),
            )
            record.id = cur.lastrowid
        return record

    def get_history(
        self, topic: Optional[str] = None, days: int = 7, limit: int = 100
    ) -> list[AnalysisRecord]:
        """Return historical analysis records."""
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            if topic:
                rows = conn.execute(
                    """
                    SELECT * FROM history
                    WHERE topic = ? AND analyzed_at >= datetime('now', '-' || ? || ' days')
                    ORDER BY analyzed_at DESC
                    LIMIT ?
                    """,
                    (topic, days, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM history
                    WHERE analyzed_at >= datetime('now', '-' || ? || ' days')
                    ORDER BY analyzed_at DESC
                    LIMIT ?
                    """,
                    (days, limit),
                ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def _row_to_watchitem(self, row: sqlite3.Row) -> WatchItem:
        return WatchItem(
            id=row["id"],
            topic=row["topic"],
            category=row["category"],
            geo=row["geo"],
            interval_minutes=row["interval_minutes"],
            sentiment_engine=row["sentiment_engine"],
            active=bool(row["active"]),
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
        )

    def _row_to_record(self, row: sqlite3.Row) -> AnalysisRecord:
        return AnalysisRecord(
            id=row["id"],
            topic=row["topic"],
            geo=row["geo"],
            analyzed_at=datetime.fromisoformat(row["analyzed_at"]),
            total_signals=row["total_signals"],
            top_score=row["top_score"],
            positive=row["positive"],
            negative=row["negative"],
            neutral=row["neutral"],
            payload_json=row["payload_json"],
        )

    def get_stats(self) -> dict:
        """Return aggregate stats for the dashboard."""
        with sqlite3.connect(self.path) as conn:
            total_watch = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
            active_watch = conn.execute(
                "SELECT COUNT(*) FROM watchlist WHERE active = 1"
            ).fetchone()[0]
            total_history = conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
            unique_topics = conn.execute(
                "SELECT COUNT(DISTINCT topic) FROM history"
            ).fetchone()[0]
        return {
            "total_watchlist": total_watch,
            "active_watchlist": active_watch,
            "total_history_records": total_history,
            "unique_topics_analyzed": unique_topics,
        }


def get_store() -> WatchlistStore:
    """Factory for the default watchlist store."""
    return WatchlistStore()
