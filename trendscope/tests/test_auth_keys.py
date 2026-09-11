"""Multi-tenant API keys with scopes."""

from trendscope.api.auth_keys import ALL_SCOPES, match_key, parse_api_keys


def test_parse_legacy_list():
    keys = parse_api_keys("k1, k2 ,")
    assert len(keys) == 2
    assert keys[0].key == "k1"
    assert keys[0].org_id == "default"
    assert "admin" in keys[0].scopes or keys[0].scopes == ALL_SCOPES


def test_parse_scoped_keys():
    keys = parse_api_keys("tokA|acme|trends:read+watchlist:read,tokB|beta|trends:read")
    assert len(keys) == 2
    assert keys[0].org_id == "acme"
    assert keys[0].scopes == frozenset({"trends:read", "watchlist:read"})
    assert not keys[0].allows("watchlist:write")
    assert keys[0].allows("trends:read")


def test_match_key_valid():
    raw = "secret|org1|trends:read"
    matched = match_key(raw, "secret")
    assert matched is not None
    assert matched.org_id == "org1"


def test_match_key_invalid():
    assert match_key("secret", "wrong") is None
    assert match_key("secret", None) is None
    assert match_key("", "anything") is None


def test_admin_scope_allows_all():
    keys = parse_api_keys("boss|root|admin")
    assert keys[0].allows("trends:read")
    assert keys[0].allows("watchlist:write")


def test_empty_list():
    assert parse_api_keys("") == []
    assert parse_api_keys("  , , ") == []
