"""
XActions-PY — Twitter HTTP Client
Replica del TwitterHttpClient de XActions pero en Python puro.
Sin npm, sin Puppeteer. Solo httpx + las GraphQL internas de Twitter.
"""

import httpx
import random
import asyncio
import json
from typing import Optional, Dict, Any
from urllib.parse import unquote

# ─── Bearer Token público (embebido en el JS bundle de Twitter) ───────────────
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

GRAPHQL_BASE = "https://x.com/i/api/graphql"
REST_BASE    = "https://x.com/i/api"
API_BASE     = "https://api.x.com"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ─── GraphQL endpoints (reverse-engineered, mismos que XActions) ──────────────
GRAPHQL_ENDPOINTS = {
    "UserByScreenName":     {"queryId": "NimuplG1OB7Fd2btCLdBOw", "operationName": "UserByScreenName"},
    "UserByRestId":         {"queryId": "tD8zKvQzwY3kdx5yz6YmOw", "operationName": "UserByRestId"},
    "UserTweets":           {"queryId": "QWF3SzpHmykQHsQMixG0cg", "operationName": "UserTweets"},
    "UserTweetsAndReplies": {"queryId": "vMkJyzx1wdmvOeeNG0n6Wg", "operationName": "UserTweetsAndReplies"},
    "UserMedia":            {"queryId": "2tLOJWwGuCTytDrGBg8VwQ", "operationName": "UserMedia"},
    "TweetDetail":          {"queryId": "U0HTv-bAWTBYylwEMT7x5A", "operationName": "TweetDetail"},
    "SearchTimeline":       {"queryId": "-TFXKoMnMTKdEXcCn-eahw", "operationName": "SearchTimeline", "method": "POST"},
    "Followers":            {"queryId": "gC_lyAxZOptAMLCJX5UhWw", "operationName": "Followers", "method": "POST"},
    "Following":            {"queryId": "2vUj-_Ek-UmBVDNtd8OnQA", "operationName": "Following"},
    # Mutations
    "CreateTweet":          {"queryId": "SiM_cAu83R0wnrpmKQQSEw", "operationName": "CreateTweet"},
    "FavoriteTweet":        {"queryId": "lI07N6Otwv1PhnEgXILM7A", "operationName": "FavoriteTweet"},
    "UnfavoriteTweet":      {"queryId": "ZYKSe-w7KEslx3JhSIk5LA", "operationName": "UnfavoriteTweet"},
    "CreateRetweet":        {"queryId": "ojPdsZsimiJrUGLR1sjUtA", "operationName": "CreateRetweet"},
    "DeleteRetweet":        {"queryId": "iQtK4dl5hBmXewYZuEOKVw", "operationName": "DeleteRetweet"},
    "FollowUser":           {"queryId": None, "operationName": None},  # REST endpoint
    "UnfollowUser":         {"queryId": None, "operationName": None},  # REST endpoint
    "DeleteTweet":          {"queryId": "VaenaVgh5q5ih7kvyVjgtg", "operationName": "DeleteTweet"},
}

DEFAULT_FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": False,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}


class TwitterError(Exception):
    pass

class RateLimitError(TwitterError):
    pass

class AuthError(TwitterError):
    pass

class NotFoundError(TwitterError):
    pass


class TwitterClient:
    """
    Cliente HTTP asíncrono para la GraphQL interna de Twitter/X.
    Equivalente directo del TwitterHttpClient de XActions en Python.
    """

    def __init__(
        self,
        cookies: Optional[str] = None,
        proxy: Optional[str] = None,
        max_retries: int = 3,
    ):
        self._cookie_str = cookies or ""
        self._cookies: Dict[str, str] = {}
        self._proxy = proxy
        self._max_retries = max_retries
        self._user_agent = random.choice(USER_AGENTS)
        self._csrf_token: Optional[str] = None

        if cookies:
            self._parse_cookies(cookies)

    def _parse_cookies(self, cookie_str: str):
        """Parsea string de cookies 'name=val; name2=val2' a dict."""
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                self._cookies[k.strip()] = v.strip()
        # ct0 es el CSRF token de Twitter
        # El x-csrf-token header debe coincidir EXACTAMENTE con el ct0 cookie
        self._csrf_token = self._cookies.get("ct0", "")

    def set_cookies(self, cookie_str: str):
        self._cookie_str = cookie_str
        self._parse_cookies(cookie_str)

    def is_authenticated(self) -> bool:
        return bool(self._cookies.get("auth_token"))

    def _build_headers(self, extra: Optional[Dict] = None) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "User-Agent": self._user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://x.com/",
            "Origin": "https://x.com",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
        }
        if self._csrf_token:
            headers["x-csrf-token"] = self._csrf_token
        if self._cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        if self.is_authenticated():
            headers["x-twitter-auth-type"] = "OAuth2Session"
        if extra:
            headers.update(extra)
        return headers

    async def graphql(
        self,
        endpoint_name: str,
        variables: Dict[str, Any],
        features: Optional[Dict] = None,
        mutation: bool = False,
    ) -> Dict:
        """
        Ejecuta una query o mutation GraphQL contra la API interna de Twitter.
        """
        ep = GRAPHQL_ENDPOINTS[endpoint_name]
        query_id = ep["queryId"]
        operation = ep["operationName"]
        url = f"{GRAPHQL_BASE}/{query_id}/{operation}"

        features_payload = features if features is not None else DEFAULT_FEATURES

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(
                    proxy=self._proxy,
                    timeout=30,
                    follow_redirects=True,
                ) as client:
                    use_post = mutation or ep.get("method") == "POST"
                    if use_post:
                        payload = {
                            "variables": variables,
                            "features": features_payload,
                            "queryId": query_id,
                        }
                        resp = await client.post(
                            url,
                            json=payload,
                            headers=self._build_headers({"Content-Type": "application/json"}),
                        )
                    else:
                        params = {
                            "variables": json.dumps(variables),
                            "features": json.dumps(features_payload),
                        }
                        resp = await client.get(
                            url,
                            params=params,
                            headers=self._build_headers(),
                        )

                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("x-rate-limit-reset", 0))
                        raise RateLimitError(f"Rate limited. Reset: {retry_after}")

                    if resp.status_code == 401:
                        raise AuthError("No autenticado o cookie expirada")

                    if resp.status_code == 404:
                        raise NotFoundError("Recurso no encontrado")

                    if resp.status_code >= 400:
                        raise TwitterError(f"HTTP {resp.status_code}: {resp.text[:200]}")

                    data = resp.json()
                    if "errors" in data and data["errors"]:
                        err = data["errors"][0]
                        code = err.get("code", 0)
                        if code == 32:
                            raise AuthError(err.get("message", "Auth error"))
                        if code == 88:
                            raise RateLimitError(err.get("message", "Rate limit"))
                        if code == 34:
                            raise NotFoundError(err.get("message", "Not found"))
                        raise TwitterError(f"API error {code}: {err.get('message')}")

                    return data

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == self._max_retries - 1:
                    raise TwitterError(f"Error de red: {e}")
                await asyncio.sleep(2 ** attempt)

        raise TwitterError("Max reintentos alcanzados")

    async def rest_post(self, path: str, data: Dict) -> Dict:
        """POST a un endpoint REST (usado para follow/unfollow)."""
        url = f"{REST_BASE}{path}"
        async with httpx.AsyncClient(proxy=self._proxy, timeout=30) as client:
            resp = await client.post(
                url,
                data=data,
                headers=self._build_headers({"Content-Type": "application/x-www-form-urlencoded"}),
            )
            if resp.status_code == 429:
                raise RateLimitError("Rate limited")
            if resp.status_code == 401:
                raise AuthError("No autenticado")
            resp.raise_for_status()
            return resp.json()
