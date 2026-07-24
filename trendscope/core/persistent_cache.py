"""Cache persistente en SQLite con TTL para resultados de TrendScope."""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from trendscope.settings import settings


class PersistentCache:
    """Cache con TTL almacenado en SQLite. Sobrevive a reinicios."""

    def __init__(self, db_path: str | Path | None = None, ttl: int | None = None):
        self.path = Path(db_path or f"{settings.data_dir}/cache.db")
        self.ttl = ttl if ttl is not None else settings.cache_ttl_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    ts REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_ts ON cache(ts)")

    def get(self, key: str) -> Any | None:
        """Obtiene valor si no ha expirado."""
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT value, ts FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if not row:
                return None
            value, ts = row
            if time.time() - ts > self.ttl:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
            return json.loads(value)

    def set(self, key: str, value: Any) -> None:
        """Guarda valor con timestamp actual."""
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, ts) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False, default=str), time.time()),
            )

    def clear(self) -> None:
        """Elimina todas las entradas."""
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM cache")

    def stats(self) -> dict:
        """Estadísticas del cache."""
        with sqlite3.connect(self.path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            now = time.time()
            valid = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE ? - ts <= ?", (now, self.ttl)
            ).fetchone()[0]
        return {"total_entries": total, "valid_entries": valid, "ttl_seconds": self.ttl}

    def cleanup(self) -> int:
        """Elimina entradas expiradas. Retorna cantidad eliminada."""
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("DELETE FROM cache WHERE ? - ts > ?", (time.time(), self.ttl))
            return cur.rowcount


cache = PersistentCache()
