# TrendScope

> Universal trend intelligence infrastructure — analyze any topic from 8 free sources with sentiment analysis, AI-powered insights, multi-provider narrative generation, data exports, and a live dashboard.

## What is it?

TrendScope aggregates trend signals from Reddit, Google Trends, Twitter/X, Hacker News, YouTube, TweetClaw, Amazon and TikTok. It scores each signal 0-100, analyzes sentiment in both Spanish and English (auto-detected), and generates actionable insights, correlations, emerging vs established trend detection, and recommendations — all locally, no external AI API needed. It also generates AI-powered narratives using OpenRouter (free models), Claude, or Ollama, and exports results to CSV, JSON, or Excel. Outputs structured JSON for agents, Markdown reports for humans, and serves a real-time web dashboard.

## Installation (Windows)

TrendScope requiere **Python 3.11 o 3.12**. Si tienes `uv` instalado (recomendado), el entorno se crea automáticamente:

```cmd
cd /d D:\Proyectos\TrendScope
uv venv --python 3.11 .venv
uv pip install -e ".[dev]"
```

> **Nota:** El comando `cd` en Windows requiere `/d` para cambiar de unidad (de `C:` a `D:`). Sin `/d` te quedas en la unidad anterior.

### Sin uv

Si no tienes `uv`, descarga Python 3.11 desde [python.org](https://www.python.org/downloads/release/python-31111/) y luego:

```cmd
cd /d D:\Proyectos\TrendScope
python311 -m venv .venv
.venv\Scripts\activate.bat
pip install -e ".[dev]"
```

### Atajos incluidos

En el proyecto dejé tres archivos `.bat` para que no escribas comandos:

- `run_tests.bat` — corre todos los tests
- `start_api.bat` — inicia la API en `http://localhost:8000`
- `start_cli.bat` — inicia la interfaz interactiva

> **Note:** `xactions-py` (Twitter/X toolkit) is included as a local module in the `trendscope/xactions/` folder — no separate install needed.

## Usage

### CLI (for humans)
```cmd
.venv\Scripts\trendscope.exe
```

O simplemente haz doble clic en `start_cli.bat`.

Or from source:
```bash
python -m trendscope
```
Interactive menu with category selector, sentiment engine picker, and rich-formatted results table with analysis panel.

### Dashboard web
```cmd
.venv\Scripts\trendscope-api.exe
```

O haz doble clic en `start_api.bat`.

Then open **http://localhost:8000/dashboard** in your browser.

Features: dark theme, stats cards, sentiment gauge (SVG donut), source distribution bars, score histogram, top trends table with engagement metrics (likes, RTs, comments, views, points), modo comparación (2 topics side by side), responsive.

### Doctor (diagnose sources)
Check which sources are working and how to fix the ones that aren't:
```bash
python -c "from trendscope.core.doctor import run_doctor; from rich.console import Console; Console().print(run_doctor())"
```
Or via API: `GET http://localhost:8000/doctor`

The doctor performs real probes on each source (not just file existence) and reports status with actionable fix instructions.

### REST API (for HTTP agents)
```bash
trendscope-api
# GET http://localhost:8000/trends?topic=crypto+Colombia
# GET http://localhost:8000/trends?category=tecnologia&sentiment_engine=claude
# GET http://localhost:8000/narrate?topic=crypto+Colombia&style=executive
# GET http://localhost:8000/export/csv?topic=crypto+Colombia
# GET http://localhost:8000/export/json?topic=crypto+Colombia
# GET http://localhost:8000/export/xlsx?topic=crypto+Colombia
# GET http://localhost:8000/report?topic=crypto
# GET http://localhost:8000/categories
# GET http://localhost:8000/health
# GET http://localhost:8000/doctor              — diagnose all sources
# GET http://localhost:8000/cache/stats
# DELETE http://localhost:8000/cache
# GET http://localhost:8000/dashboard            — web dashboard
# GET http://localhost:8000/compare?topic1=crypto&topic2=IA  — side-by-side comparison
# Interactive docs: http://localhost:8000/docs
```

### MCP Server (for MCP-compatible agents)
```cmd
.venv\Scripts\trendscope-mcp.exe
```

Or from source:
```cmd
.venv\Scripts\python.exe -m trendscope.server_mcp
```

Available tools:
- `analyze_trends` — Analyze trends on any topic
- `get_categories` — List predefined categories
- `get_latest_report` — Get the latest generated report

### SKILL.md (for agent discovery)
TrendScope includes a `SKILL.md` file that AI agents (Claude Code, OpenClaw, Hermes, Cursor) can discover automatically. It describes all available commands, endpoints, and configuration options.

### Run tests
```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

O haz doble clic en `run_tests.bat`.

## AI-Powered Narrative Generation

Generate human-readable summaries, creative copy, technical analysis, or risk alerts from any trend query:

```bash
# OpenRouter (free models) — default
curl "http://localhost:8000/narrate?topic=crypto+Colombia&style=executive"

# Styles: executive, creative, technical, alert
```

Providers supported:
- **OpenRouter** (default) — uses free models like `deepseek/deepseek-chat-v3-0324:free`. Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys).
- **Claude** — via `ANTHROPIC_API_KEY`
- **Ollama** — local models via `OLLAMA_ENABLED=true`
- **Statistical fallback** — if no provider is configured, returns a structured local summary.

## Data Export

Every analysis can be exported to common formats:

| Format | Endpoint | Use case |
|---|---|---|
| JSON | `/export/json?topic=...` | Structured data for agents / BI |
| CSV | `/export/csv?topic=...` | Spreadsheets, data science |
| Excel | `/export/xlsx?topic=...` | Reports with two sheets: Tendencias + Metadatos |

## API Protection

TrendScope includes built-in API protection for public deployments:

- **Rate limiting** — per-IP limits (default 60 requests/minute)
- **Optional API keys** — enable with `API_KEY_REQUIRED=true` and `API_KEYS=key1,key2`

Configure in `.env`:
```env
API_RATE_LIMIT=60
API_RATE_WINDOW=60
API_KEY_REQUIRED=false
API_KEYS=your-secret-key
```

## AI-Powered Analysis (v1.3.0)

TrendScope doesn't just collect data — it **analyzes it**:

1. **Executive summary** — natural language summary of the findings
2. **Actionable insights** — opportunities (🎯), alerts (⚠️), info (📊) with priorities
3. **Correlations** — consensus (🤝), divergence (🔀), score gaps (📈) between sources
4. **Emerging vs established** — trends in 1 source only (emerging) vs multi-source (established)
5. **Recommendations** — actionable next steps

All analysis runs locally with pure logic — no API keys, no cost.

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

Language is auto-detected per text — no configuration needed. Spanish content uses the Latin American Spanish model, English content uses the English model.

If pysentimiento or torch is unavailable (e.g., Windows WDAC policies, Python 3.14), TrendScope automatically falls back to keyword-based bilingual sentiment analysis.

## Predefined Categories

- tecnologia, economia, salud, moda, deportes, politica, emprendimiento, educacion, inmobiliario, crypto

Also accepts **free topic** — any text you want to analyze.

## Output

Each analysis generates two files in `data/`:
- `trends_DATE_TOPIC.json` — Structured JSON for AI agents (includes `insights` and `agent_prompt`)
- `report_DATE_TOPIC.md` — Human-readable Markdown report with analysis section

Plus exported files via `/export/*`:
- `export_TOPIC_DATE.json`
- `export_TOPIC_DATE.csv`
- `export_TOPIC_DATE.xlsx`

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
Insights Engine (summary, actionable, correlations, emerging, recommendations)
      |
      v
  ┌───┴───┐
  v       v       v
JSON    Markdown  Narrative
  |
  v
Persistent SQLite cache (configurable TTL)
  |
  v
  Dashboard (HTML + SVG, served at /dashboard)
  |
  v
  Doctor (health check for all sources)
```

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
- loguru (structured logging)
- pydantic-settings (typed config)
- openpyxl (Excel export)
- httpx (OpenRouter client)

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```env
# Reddit (optional — TrendScope uses RSS by default)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=TrendScope/1.0

# Twitter/X (DevTools > Application > Cookies on x.com)
TWITTER_AUTH_TOKEN=your_auth_token
TWITTER_CT0=your_ct0

# TweetClaw/OpenClaw optional JSON export path
TWEETCLAW_RESULTS_FILE=data/tweetclaw_crypto_colombia.json

# Claude API (optional, for premium sentiment)
ANTHROPIC_API_KEY=your_api_key

# OpenRouter (free models for narrative generation)
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=deepseek/deepseek-chat-v3-0324:free
NARRATOR_PROVIDER=openrouter
NARRATIVE_ENABLED=true

# Sentiment engine
SENTIMENT_ENGINE=local

# Geo target (ISO 3166-1 alpha-2, default: CO)
GEO_TARGET=CO
TOP_N=25

# API
API_HOST=0.0.0.0
API_PORT=8000
API_RATE_LIMIT=60
API_RATE_WINDOW=60
API_KEY_REQUIRED=false
API_KEYS=""

# Ollama (optional, for local narratives)
OLLAMA_ENABLED=false
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3.5:9b

# Cache
CACHE_TTL_SECONDS=300
```

**Note:** All credentials are optional. Without them, TrendScope uses sources that don't require authentication (Google Trends, Reddit RSS, Hacker News, YouTube, Amazon, TikTok). Only Twitter/X requires cookies.

## Troubleshooting

### Run the doctor first
```cmd
.venv\Scripts\python.exe -c "from trendscope.core.doctor import run_doctor; from rich.console import Console; Console().print(run_doctor())"
```
This will tell you exactly what's working, what's not, and how to fix it.

### pysentimiento / torch import error on Windows
If you see `OSError: [WinError 4551]`, Windows WDAC is blocking PyTorch DLLs. TrendScope automatically falls back to keyword-based bilingual sentiment analysis — no action needed.

### Reddit returns 403
Reddit blocked the public JSON endpoint. TrendScope uses RSS via `old.reddit.com` which is 100% free. PRAW credentials are optional for better data.

### Twitter returns 401 or 403
Your cookies may have expired. Get fresh cookies from x.com → DevTools (F12) → Application → Cookies → x.com. Copy `auth_token` and `ct0` into your `.env`.

### OpenRouter returns 401
Your API key may be invalid or missing. Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys) and add it to `.env` as `OPENROUTER_API_KEY`.

## Tests

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

O haz doble clic en `run_tests.bat`.

72 tests covering: cache, persistent cache, deduplicator, query, scorer (all sources), sentiment alignment, tweetclaw, settings, narrator, exporter, middleware.

## Roadmap

- [x] Paquete instalable con pyproject.toml
- [x] Configuración tipada con pydantic-settings
- [x] Cache persistente en SQLite
- [x] Narrador multi-proveedor (OpenRouter, Claude, Ollama)
- [x] Exportación CSV / JSON / Excel
- [x] Rate limiting y API keys
- [ ] Watchlist + monitoreo recurrente
- [ ] Dashboard con WebSockets e historial
- [ ] Docker + CI/CD

## Related

- [xactions-py](https://github.com/mamboyepez17/xactions-py) — Twitter/X toolkit (included locally)

## License

MIT