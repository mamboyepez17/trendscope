"""
XActions-PY — Import session cookies from files or installed browsers.

Supported file formats:
  - One cookie string per line (auth_token=...; ct0=...)
  - Netscape cookies.txt
  - Cookie-Editor / EditThisCookie JSON export
  - Playwright storageState JSON

Browser import (--from-browser):
  Locates the profile cookie DB and reads auth_token + ct0.
  Chrome/Edge/Brave on Windows: DPAPI via ctypes (no extra deps).
  Values that stay encrypted are skipped with a clear warning.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

NEEDED = ("auth_token", "ct0")


def _cookie_dict_to_string(cookies: dict[str, str]) -> str | None:
    if not cookies.get("auth_token") or not cookies.get("ct0"):
        return None
    return "; ".join(f"{k}={v}" for k, v in cookies.items() if v)


def parse_cookie_line(line: str) -> dict[str, str] | None:
    """Parse 'auth_token=a; ct0=b' into a dict."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    out: dict[str, str] = {}
    for part in line.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out or None


def parse_netscape_cookies(text: str) -> dict[str, str]:
    """Netscape cookies.txt → {name: value} for x.com/twitter.com hosts."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, _path, _secure, _expiry, name, value = parts[:7]
        if "twitter.com" not in domain and "x.com" not in domain:
            continue
        out[name] = value
    return out


def parse_json_export(data: Any) -> dict[str, str]:
    """Cookie-Editor array or Playwright storageState."""
    out: dict[str, str] = {}
    if isinstance(data, dict):
        # Playwright storageState
        cookies = data.get("cookies") or []
        if isinstance(cookies, list):
            for c in cookies:
                if isinstance(c, dict) and c.get("name") and c.get("value") is not None:
                    out[str(c["name"])] = str(c["value"])
        return out
    if isinstance(data, list):
        for c in data:
            if isinstance(c, dict) and c.get("name") and c.get("value") is not None:
                out[str(c["name"])] = str(c["value"])
    return out


def load_cookies_from_file(path: str | Path) -> list[str]:
    """
    Detect format and return list of cookie strings (one per account if pool file).
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace")
    stripped = text.strip()
    if not stripped:
        return []

    # JSON export
    if stripped[0] in "[{":
        try:
            data = json.loads(stripped)
            cookies = parse_json_export(data)
            s = _cookie_dict_to_string(cookies)
            return [s] if s else []
        except json.JSONDecodeError:
            pass

    # Netscape (tab-separated, 7 fields)
    if any(ln.count("\t") >= 6 for ln in stripped.splitlines() if ln and not ln.startswith("#")):
        cookies = parse_netscape_cookies(stripped)
        s = _cookie_dict_to_string(cookies)
        return [s] if s else []

    # One cookie-string per line
    results: list[str] = []
    for line in stripped.splitlines():
        d = parse_cookie_line(line)
        if not d:
            continue
        s = _cookie_dict_to_string(d)
        if s:
            results.append(s)
    return results


# ─── Browser profile discovery ────────────────────────────────────────────────

def _windows_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))


def browser_cookie_db(browser: str) -> Path | None:
    """Return path to the browser cookie SQLite DB, if found."""
    browser = browser.lower()
    home = Path.home()
    candidates: list[Path] = []

    if sys.platform == "win32":
        local = _windows_appdata()
        if browser in ("chrome", "chromium", "brave", "edge"):
            roots = {
                "chrome": local / "Google" / "Chrome" / "User Data",
                "chromium": local / "Chromium" / "User Data",
                "brave": local / "BraveSoftware" / "Brave-Browser" / "User Data",
                "edge": local / "Microsoft" / "Edge" / "User Data",
            }
            root = roots.get(browser)
            if root:
                candidates = [
                    root / "Default" / "Network" / "Cookies",
                    root / "Default" / "Cookies",
                    root / "Profile 1" / "Network" / "Cookies",
                ]
        elif browser == "firefox":
            ff = home / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles"
            if ff.exists():
                for prof in ff.iterdir():
                    candidates.append(prof / "cookies.sqlite")
    elif sys.platform == "darwin":
        support = home / "Library" / "Application Support"
        mapping = {
            "chrome": support / "Google" / "Chrome" / "Default" / "Cookies",
            "chromium": support / "Chromium" / "Default" / "Cookies",
            "brave": support / "BraveSoftware" / "Brave-Browser" / "Default" / "Cookies",
            "edge": support / "Microsoft Edge" / "Default" / "Cookies",
        }
        if browser in mapping:
            candidates = [mapping[browser]]
        elif browser == "firefox":
            ff = support / "Firefox" / "Profiles"
            if ff.exists():
                for prof in ff.iterdir():
                    candidates.append(prof / "cookies.sqlite")
    else:  # Linux
        config = home / ".config"
        mapping = {
            "chrome": config / "google-chrome" / "Default" / "Cookies",
            "chromium": config / "chromium" / "Default" / "Cookies",
            "brave": config / "BraveSoftware" / "Brave-Browser" / "Default" / "Cookies",
            "edge": config / "microsoft-edge" / "Default" / "Cookies",
        }
        if browser in mapping:
            candidates = [mapping[browser]]
        elif browser == "firefox":
            ff = home / ".mozilla" / "firefox"
            if ff.exists():
                for prof in ff.iterdir():
                    if prof.is_dir():
                        candidates.append(prof / "cookies.sqlite")

    for c in candidates:
        if c.exists():
            return c
    return None


def _dpapi_unprotect(data: bytes) -> bytes | None:
    """Windows DPAPI CryptUnprotectData via ctypes (no pywin32)."""
    if sys.platform != "win32" or not data:
        return None
    try:
        import ctypes
        import ctypes.wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", ctypes.wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_char)),
            ]

        crypt32 = ctypes.windll.crypt32
        kernel32 = ctypes.windll.kernel32

        in_buf = ctypes.create_string_buffer(data)
        in_blob = DATA_BLOB(len(data), ctypes.cast(in_buf, ctypes.POINTER(ctypes.c_char)))
        out_blob = DATA_BLOB()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(out_blob),
        ):
            return None
        try:
            raw = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            kernel32.LocalFree(out_blob.pbData)
        return raw
    except Exception as e:  # noqa: BLE001
        _log.debug("DPAPI failed: %s", e)
        return None


def _decrypt_chrome_value(encrypted: bytes | None, plain: str | None) -> str | None:
    if plain:
        return plain
    if not encrypted:
        return None
    # v10/v11 prefix on Windows: DPAPI the whole blob; leftover may be AES — we only handle DPAPI layer
    if encrypted[:3] in (b"v10", b"v11"):
        blob = encrypted[3:]
        raw = _dpapi_unprotect(blob)
        if raw:
            # Often AES-GCM: last 16 bytes tag, first 12 nonce — if still not utf-8 text, try DPAPI whole
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                # Chrome sometimes stores DPAPI-encrypted utf-8 directly
                raw2 = _dpapi_unprotect(encrypted)
                if raw2:
                    try:
                        return raw2.decode("utf-8")
                    except UnicodeDecodeError:
                        return None
                return None
        raw2 = _dpapi_unprotect(encrypted)
        if raw2:
            try:
                return raw2.decode("utf-8")
            except UnicodeDecodeError:
                return None
        return None
    raw = _dpapi_unprotect(encrypted)
    if raw:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
    try:
        return encrypted.decode("utf-8")
    except UnicodeDecodeError:
        return None


def read_cookies_from_sqlite(db_path: str | Path, domains: tuple[str, ...] = (".x.com", ".twitter.com", "x.com", "twitter.com")) -> dict[str, str]:
    """
    Copy DB to temp (browsers lock the file) and read name/value for X domains.
    """
    src = Path(db_path)
    tmp = Path(tempfile.mkstemp(suffix=".sqlite")[1])
    try:
        shutil.copy2(src, tmp)
        conn = sqlite3.connect(f"file:{tmp}?mode=ro", uri=True)
        try:
            cur = conn.execute(
                "SELECT name, value, encrypted_value FROM cookies WHERE host_key IN "
                f"({','.join('?' * len(domains))})",
                domains,
            )
            out: dict[str, str] = {}
            for name, value, encrypted in cur.fetchall():
                val = _decrypt_chrome_value(encrypted or None, value or None)
                if val:
                    out[name] = val
            return out
        finally:
            conn.close()
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def import_from_browser(browser: str) -> str | None:
    """
    Returns a cookie string for auth_token+ct0, or None with logged reason.
    """
    db = browser_cookie_db(browser)
    if not db:
        _log.warning("No cookie DB found for browser %r", browser)
        return None
    try:
        cookies = read_cookies_from_sqlite(db)
    except (sqlite3.Error, OSError) as e:
        _log.warning("Could not read %s: %s", db, e)
        return None
    s = _cookie_dict_to_string(cookies)
    if not s:
        _log.warning(
            "Found DB %s but auth_token/ct0 missing or still encrypted. "
            "Fallback: export cookies with Cookie-Editor and use --cookies-file.",
            db,
        )
        return None
    return s
