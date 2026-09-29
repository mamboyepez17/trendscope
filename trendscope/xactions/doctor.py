"""
XActions-PY — doctor: health checks for local setup.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .caps import status_report as caps_status
from .client import GRAPHQL_ENDPOINTS
from .gql_refresh import cache_status as gql_cache_status


def _check(name: str, status: str, message: str, **extra: Any) -> dict[str, Any]:
    entry = {"check": name, "status": status, "message": message}
    entry.update(extra)
    return entry


def run_doctor(cookies: str | None = None, cookies_file: str | None = None) -> dict[str, Any]:
    """
    Returns {ok: bool, checks: [...], summary: str}.
    ok is True only if there are no 'error' checks.
    """
    checks: list[dict[str, Any]] = []

    # Python / package
    checks.append(
        _check(
            "python",
            "ok",
            f"Python {sys.version.split()[0]}",
            version=sys.version.split()[0],
        )
    )
    checks.append(_check("xactions", "ok", f"xactions-py {__version__}", version=__version__))

    # Cookies
    if cookies_file:
        p = Path(cookies_file)
        if not p.exists():
            checks.append(_check("cookies_file", "error", f"Not found: {cookies_file}"))
        else:
            try:
                lines = [
                    ln.strip()
                    for ln in p.read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.strip().startswith("#")
                ]
                checks.append(
                    _check(
                        "cookies_file",
                        "ok" if lines else "warn",
                        f"{len(lines)} account(s) in {cookies_file}",
                        count=len(lines),
                    )
                )
            except OSError as e:
                checks.append(_check("cookies_file", "error", str(e)))
    else:
        env = cookies or os.getenv("TWITTER_COOKIES", "")
        if env:
            parts = [c.strip() for c in env.replace("\n", "|||").split("|||") if c.strip()]
            has_auth = any("auth_token=" in c for c in parts)
            has_ct0 = any("ct0=" in c for c in parts)
            if has_auth and has_ct0:
                checks.append(
                    _check(
                        "cookies",
                        "ok",
                        f"{len(parts)} cookie string(s) in env/.env (values hidden)",
                        count=len(parts),
                    )
                )
            else:
                checks.append(
                    _check(
                        "cookies",
                        "warn",
                        "TWITTER_COOKIES present but missing auth_token and/or ct0",
                    )
                )
        else:
            checks.append(
                _check(
                    "cookies",
                    "warn",
                    "No cookies — public reads only. Set TWITTER_COOKIES or --cookies-file.",
                )
            )

    # GraphQL endpoints / cache
    gql = gql_cache_status()
    n_eps = len(GRAPHQL_ENDPOINTS)
    if n_eps < 5:
        checks.append(_check("graphql", "error", f"Only {n_eps} endpoints loaded"))
    else:
        msg = f"{n_eps} endpoints"
        if gql.get("exists"):
            msg += f" (cache {gql.get('updated_at')}, source={gql.get('source')})"
        else:
            msg += " (defaults only, no cache yet — run xactions gql-refresh)"
        checks.append(
            _check(
                "graphql",
                "ok",
                msg,
                endpoints=n_eps,
                cache=gql,
            )
        )

    # Write caps
    try:
        caps = caps_status()
        checks.append(
            _check(
                "write_caps",
                "ok",
                f"{caps['events_24h']} write(s) in last 24h",
                **{k: caps[k] for k in ("path", "events_24h", "by_operation")},
            )
        )
    except Exception as e:  # noqa: BLE001 — doctor must not crash
        checks.append(_check("write_caps", "warn", f"Could not read caps: {e}"))

    # Tracking DB
    db_path = Path(os.getenv("XACTIONS_DB", str(Path.home() / ".xactions" / "xactions.db")))
    if db_path.exists():
        checks.append(_check("sqlite", "ok", f"DB present: {db_path}", path=str(db_path)))
    else:
        checks.append(
            _check("sqlite", "ok", f"No DB yet (created on first track): {db_path}", path=str(db_path))
        )

    # Proxy
    proxy = os.getenv("TWITTER_PROXY")
    if proxy:
        checks.append(_check("proxy", "ok", "TWITTER_PROXY set (value hidden)"))
    else:
        checks.append(_check("proxy", "ok", "No proxy"))

    errors = [c for c in checks if c["status"] == "error"]
    warns = [c for c in checks if c["status"] == "warn"]
    ok = not errors
    if ok and not warns:
        summary = "All checks passed"
    elif ok:
        summary = f"OK with {len(warns)} warning(s)"
    else:
        summary = f"{len(errors)} error(s), {len(warns)} warning(s)"

    return {"ok": ok, "summary": summary, "version": __version__, "checks": checks}
