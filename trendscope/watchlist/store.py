"""SQLite persistence for watchlist and analysis history."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from trendscope.settings import settings
from trendscope.watchlist.models import AnalysisRecord, WatchItem


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


class WatchlistStore:
    """SQLite store for watchlist and historical analysis records."""

    def __init__(self, db_path: str | Path | None = None):
        self.path = Path(db_path or f"{settings.data_dir}/watchlist.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with _connect(self.path) as conn:
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
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    alert_webhook TEXT,
                    alert_min_score REAL,
                    alert_sentiment_flip INTEGER NOT NULL DEFAULT 0,
                    org_id TEXT NOT NULL DEFAULT 'default'
                )
                """
            )
            # Migración simple para DBs existentes
            for col_def in (
                "ALTER TABLE watchlist ADD COLUMN alert_webhook TEXT",
                "ALTER TABLE watchlist ADD COLUMN alert_min_score REAL",
                "ALTER TABLE watchlist ADD COLUMN alert_sentiment_flip INTEGER NOT NULL DEFAULT 0",
                "ALTER TABLE watchlist ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default'",
                "ALTER TABLE history ADD COLUMN org_id TEXT NOT NULL DEFAULT 'default'",
            ):
                try:
                    conn.execute(col_def)
                except sqlite3.OperationalError:
                    pass
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
                    payload_json TEXT,
                    org_id TEXT NOT NULL DEFAULT 'default'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_topic_at ON history(topic, analyzed_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_watchlist_org ON watchlist(org_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_org ON history(org_id)"
            )

    def add(self, item: WatchItem) -> WatchItem:
        """Add a watch item."""
        with _connect(self.path) as conn:
            cur = conn.execute(
                """
                INSERT INTO watchlist (
                    topic, category, geo, interval_minutes, sentiment_engine, active,
                    alert_webhook, alert_min_score, alert_sentiment_flip, org_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.topic,
                    item.category,
                    item.geo,
                    item.interval_minutes,
                    item.sentiment_engine,
                    int(item.active),
                    item.alert_webhook,
                    item.alert_min_score,
                    int(item.alert_sentiment_flip),
                    item.org_id,
                ),
            )
            item.id = cur.lastrowid
            item.created_at = datetime.now(timezone.utc)
        return item

    def list_all(self, org_id: str | None = None) -> list[WatchItem]:
        """Return all watch items (optionally filtered by org)."""
        with _connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            if org_id:
                rows = conn.execute(
                    "SELECT * FROM watchlist WHERE org_id = ? ORDER BY created_at DESC",
                    (org_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM watchlist ORDER BY created_at DESC"
                ).fetchall()
        return [self._row_to_watchitem(r) for r in rows]

    def list_active(self, org_id: str | None = None) -> list[WatchItem]:
        """Return active watch items (optionally filtered by org)."""
        with _connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            if org_id:
                rows = conn.execute(
                    "SELECT * FROM watchlist WHERE active = 1 AND org_id = ? ORDER BY created_at DESC",
                    (org_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM watchlist WHERE active = 1 ORDER BY created_at DESC"
                ).fetchall()
        return [self._row_to_watchitem(r) for r in rows]

    def get(self, item_id: int, org_id: str | None = None) -> Optional[WatchItem]:
        """Return a single watch item by id (org-checked if provided)."""
        with _connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            if org_id:
                row = conn.execute(
                    "SELECT * FROM watchlist WHERE id = ? AND org_id = ?",
                    (item_id, org_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM watchlist WHERE id = ?", (item_id,)
                ).fetchone()
        return self._row_to_watchitem(row) if row else None

    def update(self, item: WatchItem) -> WatchItem:
        """Update an existing watch item."""
        with _connect(self.path) as conn:
            conn.execute(
                """
                UPDATE watchlist
                SET topic = ?, category = ?, geo = ?, interval_minutes = ?,
                    sentiment_engine = ?, active = ?,
                    alert_webhook = ?, alert_min_score = ?, alert_sentiment_flip = ?,
                    org_id = ?
                WHERE id = ?
                """,
                (
                    item.topic,
                    item.category,
                    item.geo,
                    item.interval_minutes,
                    item.sentiment_engine,
                    int(item.active),
                    item.alert_webhook,
                    item.alert_min_score,
                    int(item.alert_sentiment_flip),
                    item.org_id,
                    item.id,
                ),
            )
        return item

    def delete(self, item_id: int, org_id: str | None = None) -> bool:
        """Delete a watch item (org-checked if provided)."""
        with _connect(self.path) as conn:
            if org_id:
                cur = conn.execute(
                    "DELETE FROM watchlist WHERE id = ? AND org_id = ?",
                    (item_id, org_id),
                )
            else:
                cur = conn.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
            return cur.rowcount > 0

    def save_history(self, payload: dict, org_id: str = "default") -> AnalysisRecord:
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
            org_id=org_id,
        )
        with _connect(self.path) as conn:
            cur = conn.execute(
                """
                INSERT INTO history
                (topic, geo, analyzed_at, total_signals, top_score, positive, negative, neutral, payload_json, org_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    record.org_id,
                ),
            )
            record.id = cur.lastrowid
        return record

    def get_history(
        self,
        topic: Optional[str] = None,
        days: int = 7,
        limit: int = 100,
        org_id: str | None = None,
    ) -> list[AnalysisRecord]:
        """Return historical analysis records."""
        with _connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            clauses = ["analyzed_at >= datetime('now', '-' || ? || ' days')"]
            params: list = [days]
            if topic:
                clauses.append("topic = ?")
                params.append(topic)
            if org_id:
                clauses.append("org_id = ?")
                params.append(org_id)
            params.append(limit)
            rows = conn.execute(
                f"SELECT * FROM history WHERE {' AND '.join(clauses)} "
                "ORDER BY analyzed_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def _row_to_watchitem(self, row: sqlite3.Row) -> WatchItem:
        keys = row.keys()
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
            alert_webhook=row["alert_webhook"] if "alert_webhook" in keys else None,
            alert_min_score=row["alert_min_score"] if "alert_min_score" in keys else None,
            alert_sentiment_flip=bool(row["alert_sentiment_flip"])
            if "alert_sentiment_flip" in keys
            else False,
            org_id=row["org_id"] if "org_id" in keys else "default",
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
            org_id=row["org_id"] if "org_id" in row.keys() else "default",
        )

    def get_stats(self) -> dict:
        """Return aggregate stats for the dashboard."""
        with _connect(self.path) as conn:
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

    def prune_history(self, keep_days: int = 90, keep_payload_days: int = 14) -> dict:
        """
        Retención: borra filas muy viejas y limpia payload_json de las más antiguas
        (conserva el resumen numérico para gráficas).
        """
        with _connect(self.path) as conn:
            deleted = conn.execute(
                "DELETE FROM history WHERE analyzed_at < datetime('now', '-' || ? || ' days')",
                (int(keep_days),),
            ).rowcount
            trimmed = conn.execute(
                """
                UPDATE history
                SET payload_json = NULL
                WHERE payload_json IS NOT NULL
                  AND analyzed_at < datetime('now', '-' || ? || ' days')
                """,
                (int(keep_payload_days),),
            ).rowcount
        return {"deleted_rows": deleted, "trimmed_payloads": trimmed}


def get_store() -> WatchlistStore:
    """Factory for the default watchlist store."""
    return WatchlistStore()
