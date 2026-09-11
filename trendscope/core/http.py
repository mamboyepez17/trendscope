"""Shared HTTP session (thread-local) for scrapers."""

from __future__ import annotations

import threading

import requests

from trendscope import __version__

_tls = threading.local()


def get_session() -> requests.Session:
    """Devuelve una Session HTTP reutilizable por hilo (TCP/TLS reutilizado)."""
    session = getattr(_tls, "session", None)
    if session is None:
        session = requests.Session()
        session.headers["User-Agent"] = f"TrendScope/{__version__}"
        _tls.session = session
    return session
