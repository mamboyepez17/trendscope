"""Async analysis jobs: SQLite-backed queue run in a background thread."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from trendscope.settings import settings

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ts-job")


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


class JobStore:
    def __init__(self, db_path: str | Path | None = None):
        self.path = Path(db_path or f"{settings.data_dir}/jobs.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with _connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    topic TEXT,
                    category TEXT,
                    geo TEXT DEFAULT 'CO',
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    result_path TEXT,
                    error TEXT
                )
                """
            )

    def create(self, kind: str, topic: str | None, category: str | None, geo: str) -> str:
        job_id = uuid.uuid4().hex[:16]
        with _connect(self.path) as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, kind, topic, category, geo, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
                """,
                (job_id, kind, topic, category, geo, datetime.now(timezone.utc).isoformat()),
            )
        return job_id

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        with _connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def mark_running(self, job_id: str) -> None:
        with _connect(self.path) as conn:
            conn.execute(
                "UPDATE jobs SET status='running', started_at=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), job_id),
            )

    def mark_done(self, job_id: str, result_path: str | None) -> None:
        with _connect(self.path) as conn:
            conn.execute(
                "UPDATE jobs SET status='done', finished_at=?, result_path=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), result_path, job_id),
            )

    def mark_error(self, job_id: str, error: str) -> None:
        with _connect(self.path) as conn:
            conn.execute(
                "UPDATE jobs SET status='error', finished_at=?, error=? WHERE id=?",
                (datetime.now(timezone.utc).isoformat(), error[:500], job_id),
            )


_store: JobStore | None = None
_store_lock = threading.Lock()


def get_job_store() -> JobStore:
    global _store
    with _store_lock:
        if _store is None:
            _store = JobStore()
        return _store


def reset_job_store(db_path: str | Path) -> JobStore:
    global _store
    with _store_lock:
        _store = JobStore(db_path=db_path)
        return _store


def submit_analysis_job(
    kind: str,
    topic: str | None,
    category: str | None,
    geo: str = "CO",
    sentiment_engine: str = "local",
    top_n: int = 25,
) -> str:
    """Encola un análisis y retorna job_id inmediatamente."""
    store = get_job_store()
    job_id = store.create(kind, topic, category, geo)

    def _run() -> None:
        store.mark_running(job_id)
        try:
            from trendscope.core.pipeline import run as run_pipeline
            from trendscope.core.query import TrendQuery

            query = TrendQuery(
                mode="category" if category else "free",
                category=category,
                free_topic=topic,
                geo=geo,
                sentiment_engine=sentiment_engine,
                top_n=top_n,
            )
            payload, _ = run_pipeline(query)
            from trendscope.output.exporter import export_json

            path = export_json(payload)
            store.mark_done(job_id, str(path))
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            store.mark_error(job_id, str(e))

    _executor.submit(_run)
    return job_id


def job_to_public(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["id"],
        "kind": job["kind"],
        "topic": job["topic"],
        "category": job["category"],
        "geo": job["geo"],
        "status": job["status"],
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
        "result_path": job["result_path"],
        "error": job["error"],
    }
