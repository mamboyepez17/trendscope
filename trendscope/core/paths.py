"""Safe path helpers: slug sanitization and data-dir containment."""

from __future__ import annotations

import re
from pathlib import Path

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def safe_slug(raw: str | None, max_len: int = 30) -> str:
    """Slug seguro para nombres de fichero. Sin '..', '/', '\\', ni glob chars."""
    if not raw:
        return "general"
    s = _SLUG_RE.sub("_", raw.strip())
    s = s.strip("._-") or "general"
    return s[:max_len]


def safe_data_path(data_dir: Path, filename: str) -> Path:
    """Une filename a data_dir y garantiza que el resultado no escapa del directorio."""
    base = Path(data_dir).resolve()
    # Filename alone must not contain separators or parent refs
    name = Path(filename).name
    if not name or name in {".", ".."}:
        raise ValueError(f"Invalid filename: {filename!r}")
    path = (base / name).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Path escape detected: {filename!r}") from exc
    return path
