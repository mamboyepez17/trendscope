# TrendScope

> Universal trend intelligence infrastructure — analyze any topic from multiple free sources with sentiment analysis included.

## What is it?

TrendScope aggregates trend signals from Reddit, Google Trends, Twitter/X, TweetClaw, Amazon and TikTok. It scores each signal 0-100 and analyzes sentiment in both Spanish and English (auto-detected). Generates structured JSON for AI agents and Markdown reports for humans.

## Installation

```bash
git clone https://github.com/mamboyepez17/trendscope
cd trendscope
pip install -r requirements.txt
pip install git+https://github.com/mamboyepez17/xactions-py.git
cp .env.example .env  # fill in your credentials
```

## Usage

### CLI (for humans)
```bash
python main.py
```

### REST API (for HTTP agents)
```bash
python server_api.py
# GET http://localhost:8000/trends?topic=crypto+Colombia
# GET http://localhost:8000/trends?category=tecnologia&sentiment_engine=claude
# GET http://localhost:8000/report?topic=crypto
# GET http://localhost:8000/categories
# GET http://localhost:8000/health
# GET http://localhost:8000/cache/stats
# DELETE http://localhost:8000/cache
# Interactive docs: http://localhost:8000/docs
```

### MCP Server (for MCP-compatible agents)
```bash
python server_mcp.py
```

Available tools:
- `analyze_trends` — Analyze trends on any topic
- `get_categories` — List predefined categories
- `get_latest_report` — Get the latest generated report

### Run tests
```bash
python -m pytest tests/ -v
```

## Data Sources

| Source | Method | Cost | Requires Auth |
|---|---|---|---|
| Reddit | PRAW + public JSON fallback | Free | Optional (works without) |
| Google Trends | RSS primary + pytrends + relevance scoring | Free | No |
| Twitter/X | xactions-py | Free | Yes (cookies) |
| TweetClaw/OpenClaw | Optional local JSON export | Free | No (bring your own file) |
| Amazon Best Sellers | Scrapling StealthyFetcher | Free | No |
| TikTok Creative Center | API JSON + Scrapling fallback | Free | No |

## Sentiment Analysis

| Engine | Technology | Cost |
|---|---|---|
| `local` | pysentimiento (Spanish + English, auto-detected) | Free |
| `local` (fallback) | Keyword-based bilingue (auto-activates if torch unavailable) | Free |
| `claude` | Claude Haiku API (multilingual) | Low cost |

Language is auto-detected per text — no configuration needed. Spanish content uses the Latin American Spanish model, English content uses the English model. Both engines handle mixed-language inputs seamlessly.

If pysentimiento or torch is unavailable (e.g., Windows WDAC policies, Python 3.14), TrendScope automatically falls back to keyword-based bilingual sentiment analysis.

## Predefined Categories

tecnologia, economia, salud, moda, deportes, politica, emprendimiento, educacion, inmobiliario, crypto

Also accepts **free topic** — any text you want to analyze.

## Output

Each analysis generates two files in `data/`:
- `trends_DATE_TOPIC.json` — Structured JSON for AI agents (includes `agent_prompt`)
- `report_DATE_TOPIC.md` — Human-readable Markdown report

## Architecture

```
User / Agent
      |
      v
TrendQuery (category or free topic)
      |
      v
Pipeline (concurrent execution)
  ├── Reddit        → items[]    ─┐
  ├── Google Trends → items[]    ─┤  ThreadPoolExecutor
  ├── Amazon        → items[]    ─┤  (4 parallel workers)
  ├── TikTok        → items[]    ─┘
  ├── Twitter/X     → items[]    ───  serial (rate-limit safe)
  └── TweetClaw     → items[]    ───  serial
      |
      v
Deduplicator (hash + 72% similarity threshold)
      |
      v
Sentiment Analysis (local or Claude, 1:1 aligned)
      |
      v
Scorer (0-100 per source + keyword bonus + sentiment bonus)
      |
      v
  ┌───┴───┐
  v       v
JSON    Markdown
      |
      v
  In-memory cache (5 min TTL)
```

### Key Design Decisions

| Decision | Reason |
|---|---|
| Scrapling > Playwright + requests | Adaptativo, anti-bot, 240x more faster, one package |
| RSS before pytrends | No JS, no captcha, always stable |
| Reddit public JSON fallback | Works without API key, more resilient |
| Concurrent pipeline | 4 sources in parallel = 3x faster end-to-end |
| In-memory cache (5 min) | Avoid redundant scraping on repeated API calls |
| Sentiment alignment 1:1 | Critical: empty texts get neutral, not skipped |
| pysentimiento + keyword fallback | Works even if torch is blocked by OS policies |
| Claude Haiku for sentiment | Cheaper than Sonnet/Opus, multilingual |
| FastAPI for API REST | Lightweight, async, auto-docs at /docs |
| MCP server | Native protocol for Claude agents |
| Hash + similarity dedup | O(1) exact match first, O(n) similarity for near-dups |

## Stack

- Python 3.10+
- Scrapling (replaces Playwright + requests + BeautifulSoup)
- PRAW (Reddit API)
- pytrends (Google Trends fallback)
- pysentimiento (bilingual sentiment: Spanish + English)
- anthropic (Claude Haiku API)
- FastAPI + uvicorn (REST API)
- mcp (MCP server)
- rich (CLI)
- loguru (logging)

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Reddit (create at reddit.com/prefs/apps)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret

# Twitter/X (DevTools > Application > Cookies)
TWITTER_AUTH_TOKEN=your_auth_token
TWITTER_CT0=your_ct0

# TweetClaw/OpenClaw optional JSON export path
TWEETCLAW_RESULTS_FILE=data/tweetclaw_crypto_colombia.json

# Claude API (optional, for premium sentiment)
ANTHROPIC_API_KEY=your_api_key

# Default sentiment engine: local | claude
SENTIMENT_ENGINE=local

# Geo target (ISO 3166-1 alpha-2, default: CO)
GEO_TARGET=CO

# Number of results per source (default: 25)
TOP_N=25

# API REST
API_HOST=0.0.0.0
API_PORT=8000
```

**Note:** All credentials are optional. Without them, TrendScope uses sources that don't require authentication (Google Trends RSS, Amazon via Scrapling, TikTok API).

For OpenClaw agents, TweetClaw can collect tweet search results first and TrendScope can score them from a local JSON file. See [TweetClaw OpenClaw Source](docs/tweetclaw-openclaw-source.md).

## Troubleshooting

### pysentimiento / torch import error on Windows
If you see `OSError: [WinError 4551]` when loading pysentimiento, this is caused by Windows WDAC (Windows Defender Application Control) blocking PyTorch DLLs. TrendScope automatically falls back to keyword-based bilingual sentiment analysis — no action needed.

### Google Trends RSS returns empty
The RSS endpoint provides trending topics for the specified geo region. If your topic doesn't match any trending topic, TrendScope also queries pytrends for keyword-specific interest data. Results are ranked by relevance to your query.

### Reddit returns 0 items without API key
Without Reddit API credentials, TrendScope uses the public JSON endpoint which works but may be rate-limited. Add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` to your `.env` for better results (create at reddit.com/prefs/apps).

### Amazon scraper fails
Amazon has aggressive anti-bot protection. The StealthyFetcher from Scrapling handles most cases, but if it fails, the other sources continue working. TrendScope is designed to be resilient — if one source fails, the rest keep going.

### TikTok API returns empty
The TikTok Creative Center API may change without notice. The scraper has a fallback to HTML scraping with DynamicFetcher, but this requires Scrapling's browser dependencies to be installed.

## Tests

```bash
python -m pytest tests/ -v
```

Test coverage:
- `test_cache.py` — In-memory cache operations
- `test_deduplicator.py` — Cross-source deduplication (exact + near-duplicate)
- `test_query.py` — TrendQuery dataclass (keywords, subreddits, slugs)
- `test_scorer.py` — Trend scoring per source + keyword bonus
- `test_sentiment_alignment.py` — Sentiment alignment + bilingue fallback
- `test_tweetclaw_scraper.py` — TweetClaw JSON loading and normalization

## Related

- [xactions-py](https://github.com/mamboyepez17/xactions-py) — Twitter/X toolkit

## License

MIT
