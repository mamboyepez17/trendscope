# TrendScope

> Universal trend intelligence infrastructure — analyze any topic from 8 free sources with sentiment analysis and a live dashboard.

## What is it?

TrendScope aggregates trend signals from Reddit, Google Trends, Twitter/X, Hacker News, YouTube, TweetClaw, Amazon and TikTok. It scores each signal 0-100 and analyzes sentiment in both Spanish and English (auto-detected). Generates structured JSON for AI agents, Markdown reports for humans, and serves a real-time web dashboard.

## Installation

```bash
git clone https://github.com/mamboyepez17/trendscope
cd trendscope
pip install -r requirements.txt
cp .env.example .env  # fill in your credentials (all optional)
```

> **Note:** `xactions-py` (Twitter/X toolkit) is included as a local module in the `xactions/` folder — no separate install needed.

## Usage

### CLI (for humans)
```bash
python main.py
```
Interactive menu with category selector, sentiment engine picker, and rich-formatted results table.

### Dashboard web
```bash
python server_api.py
```
Then open **http://localhost:8000/dashboard** in your browser.

The dashboard features:
- Dark theme with cyan accents
- Stats cards (total signals, sources active, sentiment breakdown, top score)
- Sentiment gauge (SVG donut chart)
- Source distribution bar chart
- Score distribution histogram
- Top trends table with score bars, source badges, engagement metrics (likes, RTs, comments, views, points)
- Modo Comparación: analyze 2 topics side by side
- Responsive (works on desktop and mobile)

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
# GET http://localhost:8000/dashboard        — web dashboard
# GET http://localhost:8000/compare?topic1=crypto&topic2=IA  — side-by-side comparison
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
| Reddit | RSS via old.reddit.com + PRAW fallback | Free | Optional (works without) |
| Google Trends | RSS primary + pytrends + relevance scoring | Free | No |
| Twitter/X | xactions-py (GraphQL internal API) | Free | Yes (cookies) |
| Hacker News | Algolia Search API + Firebase top stories | Free | No |
| YouTube | Internal search API (youtubei/v1/search) | Free | No |
| TweetClaw/OpenClaw | Optional local JSON export | Free | No (bring your own file) |
| Amazon Best Sellers | Scrapling StealthyFetcher | Free | No |
| TikTok Creative Center | API JSON + Scrapling fallback | Free | No |

## Sentiment Analysis

| Engine | Technology | Cost |
|---|---|---|
| `local` | pysentimiento (Spanish + English, auto-detected) | Free |
| `local` (fallback) | Keyword-based bilingüe (auto-activates if torch unavailable) | Free |
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
  ├── Google Trends → items[]    ─┤
  ├── Hacker News   → items[]    ─┤  ThreadPoolExecutor
  ├── YouTube       → items[]    ─┤  (6 parallel workers)
  ├── Amazon        → items[]    ─┤
  ├── TikTok        → items[]    ─┘
  ├── Twitter/X     → items[]    ───  serial (rate-limit safe)
  └── TweetClaw     → items[]    ───  serial
      |
      v
Deduplicator (MD5 hash + 72% similarity threshold)
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
      |
      v
  Dashboard (HTML + SVG, served at /dashboard)
```

### Key Design Decisions

| Decision | Reason |
|---|---|
| RSS for Reddit (old.reddit.com) | Works without API key, 100% free since Reddit blocked public JSON |
| RSS + pytrends for Google Trends | Combines trending topics with keyword-specific interest data |
| Concurrent pipeline | 6 sources in parallel = 3x faster end-to-end |
| In-memory cache (5 min) | Avoid redundant scraping on repeated API calls |
| Sentiment alignment 1:1 | Critical: empty texts get neutral, not skipped |
| pysentimiento + keyword fallback | Works even if torch is blocked by OS policies |
| Hash + similarity dedup | O(1) exact match first, O(n) similarity for near-dups |
| xactions-py included as local module | Avoids broken pyproject.toml build-backend issue |
| Dashboard as single HTML file | No build step, no frameworks, works standalone |

## Stack

- Python 3.10+
- xactions-py (Twitter/X — included locally)
- Scrapling (replaces Playwright + requests + BeautifulSoup)
- PRAW (Reddit API — optional)
- pytrends (Google Trends fallback)
- pysentimiento (bilingual sentiment: Spanish + English)
- anthropic (Claude Haiku API — optional)
- FastAPI + uvicorn (REST API + dashboard)
- mcp (MCP server)
- rich (CLI)
- loguru (logging)

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Reddit (optional — TrendScope uses RSS by default)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=***    "REDD...n
# Twitter/X (DevTools > Application > Cookies on x.com)
TWITTER_AUTH_TOKEN=***    "TWIT...n
# TweetClaw/OpenClaw optional JSON export path
TWEETCLAW_RESULTS_FILE=data/tweetclaw_crypto_colombia.json

# Claude API (optional, for premium sentiment)
ANTHROPIC_API_KEY=*** Default sentiment engine: local | claude
SENTIMENT_ENGINE=local

# Geo target (ISO 3166-1 alpha-2, default: CO)
GEO_TARGET=CO

# Number of results per source (default: 25)
TOP_N=25

# API REST
API_HOST=0.0.0.0
API_PORT=8000
```

**Note:** All credentials are optional. Without them, TrendScope uses sources that don't require authentication (Google Trends, Reddit RSS, Hacker News, YouTube, Amazon, TikTok). Only Twitter/X requires cookies.

For OpenClaw agents, TweetClaw can collect tweet search results first and TrendScope can score them from a local JSON file. See [TweetClaw OpenClaw Source](docs/tweetclaw-openclaw-source.md).

## Troubleshooting

### pysentimiento / torch import error on Windows
If you see `OSError: [WinError 4551]` when loading pysentimiento, this is caused by Windows WDAC (Windows Defender Application Control) blocking PyTorch DLLs. TrendScope automatically falls back to keyword-based bilingual sentiment analysis — no action needed.

### Reddit returns 403
Reddit blocked the public JSON endpoint. TrendScope now uses RSS via `old.reddit.com` which is 100% free and works without API credentials. If you have Reddit API credentials (PRAW), they're used automatically for better data (real scores, comments, upvote ratios).

### Twitter returns 401 or 403
Your cookies may have expired. Get fresh cookies from x.com → DevTools (F12) → Application → Cookies → x.com. Copy `auth_token` and `ct0` into your `.env` file.

### Amazon scraper fails
Amazon has aggressive anti-bot protection. Requires `curl_cffi` and Scrapling's StealthyFetcher. If it fails, the other sources continue working. TrendScope is designed to be resilient — if one source fails, the rest keep going.

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
- `test_scorer.py` — Trend scoring per source (Reddit, Twitter, HN, YouTube, etc.)
- `test_sentiment_alignment.py` — Sentiment alignment + bilingüe fallback
- `test_tweetclaw_scraper.py` — TweetClaw JSON loading and normalization

## Related

- [xactions-py](https://github.com/mamboyepez17/xactions-py) — Twitter/X toolkit (included locally)

## License

MIT
