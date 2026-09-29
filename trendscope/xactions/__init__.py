"""xactions — X/Twitter automation toolkit (sin npm, sin Puppeteer)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("xactions-py")
except PackageNotFoundError:
    __version__ = "1.5.0.dev0"

from .actions import (
    bulk_unfollow,
    create_bookmark,
    delete_bookmark,
    delete_tweet,
    follow_user,
    like_tweet,
    post_thread,
    post_tweet,
    retweet,
    unfollow_user,
    unlike_tweet,
    unretweet,
    upload_media,
)
from .analyzer import analyze_tweets, compare_accounts, parse_tweet_date
from .caps import WriteCapExceeded, try_charge
from .client import (
    GRAPHQL_ENDPOINTS,
    AuthError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    TwitterClient,
    TwitterError,
    refresh_graphql_endpoints,
)
from .db import TrackerDB, compute_profile_delta
from .doctor import run_doctor
from .pool import ClientPool
from .scrapers import (
    clear_user_id_cache,
    get_bookmarks,
    get_bookmarks_sync,
    get_home_timeline,
    get_home_timeline_sync,
    get_trends,
    get_trends_sync,
    get_tweet_favoriters,
    get_tweet_favoriters_sync,
    get_tweet_replies,
    get_tweet_replies_sync,
    get_tweet_retweeters,
    get_tweet_retweeters_sync,
    get_user_id,
    get_user_likes,
    get_user_likes_sync,
    scrape_followers,
    scrape_following,
    scrape_non_followers,
    scrape_profile,
    scrape_profile_sync,
    scrape_tweets,
    scrape_tweets_sync,
    search_tweets,
    search_tweets_sync,
    validate_cookies_sync,
)
from .search_query import build_search_query

__all__ = [
    "__version__",
    # client
    "TwitterClient",
    "ClientPool",
    "TwitterError",
    "AuthError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitError",
    # scrapers
    "scrape_profile",
    "scrape_profile_sync",
    "scrape_tweets",
    "scrape_tweets_sync",
    "scrape_followers",
    "scrape_following",
    "scrape_non_followers",
    "search_tweets",
    "search_tweets_sync",
    "get_user_id",
    "clear_user_id_cache",
    "get_user_likes",
    "get_user_likes_sync",
    "get_tweet_replies",
    "get_tweet_replies_sync",
    "get_tweet_favoriters",
    "get_tweet_favoriters_sync",
    "get_tweet_retweeters",
    "get_tweet_retweeters_sync",
    "get_bookmarks",
    "get_bookmarks_sync",
    "get_home_timeline",
    "get_home_timeline_sync",
    "get_trends",
    "get_trends_sync",
    "validate_cookies_sync",
    # graphql
    "GRAPHQL_ENDPOINTS",
    "refresh_graphql_endpoints",
    # actions
    "post_tweet",
    "post_thread",
    "delete_tweet",
    "like_tweet",
    "unlike_tweet",
    "retweet",
    "unretweet",
    "create_bookmark",
    "delete_bookmark",
    "follow_user",
    "unfollow_user",
    "upload_media",
    "bulk_unfollow",
    # analytics / storage / search
    "analyze_tweets",
    "compare_accounts",
    "build_search_query",
    "parse_tweet_date",
    "TrackerDB",
    "compute_profile_delta",
    # v1.6
    "WriteCapExceeded",
    "try_charge",
    "run_doctor",
]
