"""
XActions-PY — Storage
Tracking histórico de métricas en SQLite (stdlib, cero dependencias).

Guarda snapshots de perfiles y tweets con timestamp para analizar cómo
evoluciona el engagement en el tiempo.

Por defecto la base vive en ~/.xactions/xactions.db
(se puede cambiar con la env var XACTIONS_DB o pasando un path).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(os.getenv("XACTIONS_DB", Path.home() / ".xactions" / "xactions.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profile_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    followers INTEGER,
    following INTEGER,
    tweets_count INTEGER
);
CREATE INDEX IF NOT EXISTS idx_profile_username ON profile_snapshots(username, captured_at);

CREATE TABLE IF NOT EXISTS tweet_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tweet_id TEXT NOT NULL,
    author TEXT,
    captured_at TEXT NOT NULL,
    likes INTEGER,
    retweets INTEGER,
    replies INTEGER,
    quotes INTEGER,
    views INTEGER,
    bookmarks INTEGER
);
CREATE INDEX IF NOT EXISTS idx_tweet_id ON tweet_snapshots(tweet_id, captured_at);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TrackerDB:
    """Capa mínima de acceso a la base de tracking."""

    def __init__(self, path: str | None = None):
        self.path = str(path or DEFAULT_DB_PATH)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        # WAL permite lecturas concurrentes mientras otro proceso escribe.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ─── Escritura ────────────────────────────────────────────────────────────

    def save_profile_snapshot(self, username: str, profile: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO profile_snapshots (username, captured_at, followers, following, tweets_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    username.lower(),
                    _utc_now(),
                    profile.get("followers"),
                    profile.get("following"),
                    profile.get("tweets_count"),
                ),
            )

    def save_tweet_snapshots(self, tweets: list[dict[str, Any]]) -> int:
        """Guarda un snapshot por tweet. Devuelve cuántos guardó."""
        rows = [
            (
                t.get("id"),
                (t.get("author") or {}).get("username"),
                _utc_now(),
                t.get("likes"),
                t.get("retweets"),
                t.get("replies"),
                t.get("quotes"),
                t.get("views"),
                t.get("bookmarks"),
            )
            for t in tweets
            if t.get("id")
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO tweet_snapshots (tweet_id, author, captured_at, likes, retweets, "
                "replies, quotes, views, bookmarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    # ─── Lectura ──────────────────────────────────────────────────────────────

    def get_last_profile_snapshot(self, username: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM profile_snapshots WHERE username = ? ORDER BY captured_at DESC LIMIT 1",
                (username.lower(),),
            ).fetchone()
        return dict(row) if row else None

    def get_profile_history(self, username: str, limit: int = 30) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM profile_snapshots WHERE username = ? ORDER BY captured_at DESC LIMIT ?",
                (username.lower(), limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_tweet_history(self, tweet_id: str, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tweet_snapshots WHERE tweet_id = ? ORDER BY captured_at DESC LIMIT ?",
                (tweet_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_tracked_usernames(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT username FROM profile_snapshots ORDER BY username"
            ).fetchall()
        return [r["username"] for r in rows]


def compute_profile_delta(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Calcula el delta de seguidores entre el snapshot previo y el perfil actual."""
    if not previous:
        return {"followers_delta": None, "following_delta": None, "tweets_delta": None}
    return {
        "followers_delta": (current.get("followers") or 0) - (previous.get("followers") or 0),
        "following_delta": (current.get("following") or 0) - (previous.get("following") or 0),
        "tweets_delta": (current.get("tweets_count") or 0) - (previous.get("tweets_count") or 0),
        "since": previous.get("captured_at"),
    }
