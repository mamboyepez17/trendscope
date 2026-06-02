# TrendScope

> Universal trend intelligence infrastructure — analyze any topic from multiple free sources with sentiment analysis included.

## What is it?

TrendScope aggregates trend signals from Reddit, Google Trends, Twitter/X, Amazon and TikTok. It scores each signal 0-100 and analyzes sentiment in Latin American Spanish. Generates structured JSON for AI agents and Markdown reports for humans.

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

## Data Sources

| Source | Method | Cost |
|---|---|---|
| Reddit | PRAW + public JSON fallback | Free |
| Google Trends | RSS primary + pytrends fallback | Free |
| Twitter/X | xactions-py | Free |
| Amazon Best Sellers | Scrapling StealthyFetcher | Free |
| TikTok Creative Center | Scrapling DynamicFetcher | Free |

## Sentiment Analysis

| Engine | Technology | Cost |
|---|---|---|
| `local` | pysentimiento (Latin American Spanish) | Free |
| `claude` | Claude Haiku API | Low cost |

Configurable in `.env` or overridable per execution from the CLI.

## Predefined Categories

tecnologia, economia, salud, moda, deportes, politica, emprendimiento, educacion, inmobiliario, crypto

Also accepts **free topic** — any text you want to analyze.

## Output

Each analysis generates two files in `data/`:
- `trends_DATE_TOPIC.json` — Structured JSON for AI agents (includes `agent_prompt`)
- `report_DATE_TOPIC.md` — Human-readable Markdown report

## Stack

- Python 3.10+
- Scrapling (replaces Playwright + requests + BeautifulSoup)
- PRAW (Reddit API)
- pytrends (Google Trends fallback)
- pysentimiento (Latin American Spanish sentiment)
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

# Claude API (optional, for premium sentiment)
ANTHROPIC_API_KEY=your_api_key

# Default sentiment engine: local | claude
SENTIMENT_ENGINE=local
```

**Note:** All credentials are optional. Without them, TrendScope uses sources that don't require authentication (Google Trends RSS, Amazon via Scrapling).

## How it works

```
User / Agent
      |
      v
TrendQuery (category or free topic)
      |
      v
Pipeline
  ├── Reddit        → items[]
  ├── Google Trends → items[]
  ├── Twitter/X     → items[]
  ├── Amazon        → items[]
  └── TikTok        → items[]
      |
      v
Deduplicator (72% similarity threshold)
      |
      v
Sentiment Analysis (local or Claude)
      |
      v
Scorer (0-100 per source + keyword bonus + sentiment bonus)
      |
      v
  ┌───┴───┐
  v       v
JSON    Markdown
```

## Related

- [xactions-py](https://github.com/mamboyepez17/xactions-py) — Twitter/X toolkit

## License

MIT
