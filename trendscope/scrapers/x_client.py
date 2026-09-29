"""Acceso a xactions: el paquete oficial si está instalado, si no la copia interna.

El paquete (github.com/mamboyepez17/xactions-py, `pip install -e ".[x]"`) está
más al día: por ejemplo firma las llamadas GraphQL con x-client-transaction-id,
que la copia vendorizada en trendscope/xactions no hace.
"""

from __future__ import annotations

from types import ModuleType

from trendscope.config import TWITTER_AUTH_TOKEN, TWITTER_CT0


def xactions() -> ModuleType:
    try:
        import xactions as xa  # paquete xactions-py

        if hasattr(xa, "search_tweets_sync"):
            return xa
    except ImportError:
        pass
    from trendscope import xactions as xa  # copia vendorizada

    return xa


def cookie_string() -> str | None:
    if not TWITTER_AUTH_TOKEN or not TWITTER_CT0:
        return None
    return f"auth_token={TWITTER_AUTH_TOKEN}; ct0={TWITTER_CT0}"
