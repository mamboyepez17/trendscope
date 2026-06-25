# TrendScope — Trend Intelligence Skill

## What it does

TrendScope analyzes trends on ANY topic from 8 free sources:
- Twitter/X (with cookies)
- Reddit (RSS, no API key needed)
- Google Trends (RSS + pytrends)
- Hacker News (Algolia API)
- YouTube (internal search API)
- Amazon Best Sellers (Scrapling)
- TikTok Creative Center
- TweetClaw (local JSON)

It scores each signal 0-100, analyzes sentiment (Spanish + English, auto-detected),
and generates actionable insights, correlations, emerging vs established trends,
and recommendations — all locally, no external AI API needed.

## How to use it

### CLI (interactive)
```bash
cd /path/to/trendscope
python main.py
```

### API REST (for agents)
```bash
# Start the server
python server_api.py

# Analyze any topic
curl "http://localhost:8000/trends?topic=crypto+Colombia&sentiment_engine=local"

# Use a predefined category
curl "http://localhost:8000/trends?category=crypto"

# Get the Markdown report
curl "http://localhost:8000/report?topic=crypto"

# List categories
curl "http://localhost:8000/categories"

# Compare two topics
curl "http://localhost:8000/compare?topic1=crypto&topic2=AI"

# Check health of all sources
curl "http://localhost:8000/doctor"

# Dashboard (open in browser)
# http://localhost:8000/dashboard
```

### MCP Server (for MCP-compatible agents)
```bash
python server_mcp.py
```
Tools available:
- `analyze_trends` — Analyze trends on any topic
- `get_categories` — List predefined categories
- `get_latest_report` — Get latest report for a topic

### Doctor (diagnose sources)
```bash
python -c "from core.doctor import run_doctor; from rich.console import Console; Console().print(run_doctor())"
```
Or via API: `GET http://localhost:8000/doctor`

## Categories

tecnologia, economia, salud, moda, deportes, politica, emprendimiento, educacion, inmobiliario, crypto

Free topic also accepted — any text you want to analyze.

## Configuration

Copy `.env.example` to `.env`. All credentials are optional.
Without any credentials, TrendScope uses: Google Trends, Hacker News, YouTube, Amazon, TikTok.

For Twitter/X: set `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` (from x.com cookies).
For Reddit PRAW (optional, RSS works without): set `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`.

## Output

Each analysis returns JSON with:
- `meta` — query info, sources used, sentiment summary
- `top_trends` — ranked signals with scores, sentiment, engagement metrics
- `insights` — executive summary, actionable insights, correlations, emerging vs established, recommendations
- `agent_prompt` — ready-to-use prompt for further AI analysis

Files generated in `data/`:
- `trends_DATE_TOPIC.json` — structured JSON for agents
- `report_DATE_TOPIC.md` — human-readable Markdown report

## Tips for agents

- The JSON `insights` section contains everything you need for decision-making
- Use `sentiment_engine=local` for free analysis (no API cost)
- The cache lasts 5 minutes — repeated queries are instant
- Run `doctor` first to check which sources are available