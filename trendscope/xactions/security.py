"""
XActions-PY — Manejo seguro de cookies de sesión.

Reglas:
  - Nunca imprimir el valor de auth_token/ct0 (solo nombres + ***).
  - Avisar si las cookies llegan por línea de comandos (quedan en el historial).
  - Avisar si un archivo de cookies es legible por otros (Unix).
"""

from __future__ import annotations

import logging
import os
import re
import stat
import sys
from pathlib import Path

_log = logging.getLogger(__name__)

# Cookies sensibles (también redactamos cualquier valor largo por si acaso)
_SENSITIVE_KEYS = frozenset(
    {
        "auth_token",
        "ct0",
        "kdt",
        "att",
        "twid",
        "auth_multi",
        "auth_multi_token",
    }
)

_SECRET_IN_TEXT = re.compile(
    r"(?i)\b(auth_token|ct0|kdt|att|auth_multi(?:_token)?)\s*=\s*[^;\s,]+"
)


def redact_cookies(cookie_str: str | None) -> str:
    """
    Devuelve una forma segura de mostrar cookies: solo nombres.
    Ej: 'auth_token=abc; ct0=xyz' → 'auth_token=***, ct0=***'
    """
    if not cookie_str:
        return "(vacío)"
    names: list[str] = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            name = part.split("=", 1)[0].strip()
            if name:
                names.append(f"{name}=***")
        else:
            names.append("***")
    return ", ".join(names) if names else "***"


def redact_in_text(text: str) -> str:
    """Redacta auth_token=... / ct0=... que aparezcan en cualquier texto."""
    if not text:
        return text
    return _SECRET_IN_TEXT.sub(lambda m: f"{m.group(1)}=***", text)


def cookies_in_argv(argv: list[str] | None = None) -> bool:
    """True si el usuario pasó cookies con --cookies (no --cookies-file ni solo env)."""
    args = argv if argv is not None else sys.argv
    for a in args:
        if a == "--cookies":
            return True
        if a.startswith("--cookies=") and not a.startswith("--cookies-file"):
            return True
    return False


def warn_cli_cookies(cookies: str | None = None) -> str | None:
    """
    Si las cookies llegaron por --cookies en argv, devuelve un aviso (no bloquea).
    Sugerencia: .env (TWITTER_COOKIES) o --cookies-file con permisos 600.
    """
    if not cookies:
        return None
    if cookies_in_argv():
        msg = (
            "Cookies pasadas por --cookies: pueden quedar en el historial del shell. "
            "Prefiere TWITTER_COOKIES en .env o --cookies-file (chmod 600)."
        )
        _log.warning(msg)
        return msg
    return None


def check_cookies_file_permissions(path: str | Path) -> str | None:
    """
    En Unix, devuelve un aviso si el archivo es legible por group/other.
    En Windows no aplica (devuelve None).
    """
    if os.name == "nt":
        return None
    p = Path(path)
    try:
        mode = p.stat().st_mode
    except OSError:
        return None
    if mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
        return (
            f"El archivo de cookies {p} es accesible por otros usuarios "
            f"(mode {oct(stat.S_IMODE(mode))}). Ejecuta: chmod 600 {p}"
        )
    return None


def safe_cookie_summary(cookie_list: list[str]) -> str:
    """Resumen para logs/CLI: nº de cuentas + nombres de cookies, sin valores."""
    if not cookie_list:
        return "0 cuentas"
    parts = [redact_cookies(c) for c in cookie_list[:3]]
    extra = f" (+{len(cookie_list) - 3} más)" if len(cookie_list) > 3 else ""
    return f"{len(cookie_list)} cuenta(s): {parts}{extra}"
