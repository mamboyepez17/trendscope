"""Startup validation of settings — clear warnings for operators."""

from __future__ import annotations

from trendscope.settings import settings


def validate_settings() -> list[str]:
    """Returns human-readable warnings (empty list if all good)."""
    warnings: list[str] = []

    exposed = settings.api_host not in {"127.0.0.1", "localhost", "::1"}
    if exposed and not settings.api_key_required:
        warnings.append(
            f"API bound to {settings.api_host} without API keys "
            "(set API_KEY_REQUIRED=true and API_KEYS=...)"
        )
    if settings.api_key_required:
        keys = {k.strip() for k in (settings.api_keys or "").split(",") if k.strip()}
        if not keys:
            warnings.append("API_KEY_REQUIRED=true but API_KEYS is empty — all requests will be 401")
    if not (settings.twitter_auth_token or settings.twitter_cookies):
        warnings.append("Twitter/X cookies not configured — that source will be skipped")
    if settings.watchlist_enabled and settings.watchlist_default_interval_minutes < 5:
        warnings.append("WATCHLIST_DEFAULT_INTERVAL_MINUTES < 5 may overload the pipeline")
    return warnings
