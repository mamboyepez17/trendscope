# TrendScope — Public Mood & Trend Intelligence Skill

## What it does

TrendScope measures **how people feel about any topic, in any country**, and what is trending around it — from **recent** content only (last 7 days by default).

- **Mood Index (−100…+100):** built from people's opinions, with a margin of error and a confidence level.
  - Sources: real replies on X, YouTube comments, Reddit and Hacker News comments, Bluesky posts.
  - Every opinion is classified as joy, anger, sadness, fear or neutral.
  - Weighting: one person = one vote, and viral comments are capped at 4×.
- **Media tone:** news headlines are measured separately (Google News, Bing, GDELT), so the press never gets mixed up with the public.
- **Trends:** signals from 12 free sources scored 0–100, plus insights, correlations and recommendations. All local; no paid AI needed.
- **Any country and language:**
  - Per-language lexicons: es, en, pt, fr, de, it.
  - Regional slang that only applies in its own country: CO, MX, AR, UY, CL, PE, VE, ES, BR, US.
  - Custom lexicons via `CUSTOM_LEXICON_PATH`.
  - Mood labels and AI narratives in es/en/pt.
- **Also:** watchlist + webhook alerts + digests, forecast (EMA/velocity/breakout), async jobs + SSE, multi-tenant API keys.

## How to use it

### API REST (for agents)
```bash
# Start the server (binds 127.0.0.1:8000 by default)
python -m trendscope.server_api

# How do people feel about a topic? (country, freshness window, output language)
curl "http://localhost:8000/trends?topic=health+reform&geo=CO&days=7&lang=en"

# Only people's comments + Mood Index (faster)
curl "http://localhost:8000/conversation?topic=Bitcoin&geo=US&days=3&lang=en"

# AI narrative in the requested language
curl "http://localhost:8000/narrate?topic=Bitcoin&geo=BR&lang=pt&style=executive"

# Async analysis
curl "http://localhost:8000/trends?topic=AI&async=true"

# Predefined category
curl "http://localhost:8000/trends?category=crypto"

# Compare two topics
curl "http://localhost:8000/compare?topic1=crypto&topic2=AI"

# Forecast from history
curl "http://localhost:8000/forecast?topic=crypto"

# Health of all sources
curl "http://localhost:8000/doctor"

# Dashboard (es / en / pt): http://localhost:8000/dashboard
```

Common parameters:

| Parameter | Values | Meaning |
|---|---|---|
| `geo` | ISO 3166-1 alpha-2 | Country |
| `days` | 1–30 | Freshness window (default 7) |
| `lang` | `es` / `en` / `pt` | Language of the output (default: the country's language) |
| `sentiment_engine` | `local` / `claude` / `llm` | Engine (`claude` and `llm` work for any language) |
| `llm_provider` | `openai`, `claude`, `deepseek`, `opencode`, `openrouter`, `gemini`, `groq`, `mistral`, `xai`, `qwen`, `glm`, `kimi`, `mimo`, `ollama`, `custom` | AI for `sentiment_engine=llm` and `/narrate` |
| `llm_model` | any model id | Model of that provider (`GET /llm/models?provider=...`) |

### MCP Server (for MCP-compatible agents)
```bash
python -m trendscope.server_mcp
```
Tools available:
- `analyze_trends` — Analyze trends and mood on any topic
- `get_categories` — List predefined categories
- `get_latest_report` — Latest Markdown report
- `narrate_trends` — AI narrative
- `compare_topics` — Side-by-side comparison
- `doctor` — Source probes
- `watchlist_add` / `watchlist_list` / `watchlist_run`
- `history_get` — Historical snapshots

### CLI (interactive)
```bash
python -m trendscope
```

### Doctor (diagnose sources)
```bash
python -c "from trendscope.core.doctor import run_doctor; from rich.console import Console; Console().print(run_doctor())"
```
Or via API: `GET http://localhost:8000/doctor`

## Output

`/trends` returns JSON with:
- `meta.mood_index` — how people feel:
  - `mood`, `label`, `emoji`, `headline`
  - `net_score` (−100…+100), `margin`, `confidence` (`high`/`medium`/`low`)
  - `emotions` (joy/anger/sadness/fear/neutral shares), `polarization`, `intensity`
  - `quotes` per emotion, `drivers` (words behind each emotion), `by_source`
- `meta.media_tone` — net tone of news headlines
- `meta.freshness` — window used, items dropped for being old, median age
- `meta.sentiment_summary` — counts + `overall` (from the weighted net index)
- `top_trends` — ranked recent signals with scores, date, emotion and engagement
- `insights` — executive summary, actionable insights, correlations, emerging vs established, recommendations
- `agent_prompt` — ready-to-use prompt for further AI analysis

Files generated in `data/`: `trends_DATE_TOPIC.json` and `report_DATE_TOPIC.md`.

## Configuration

Run `trendscope setup` (guided: AI provider/key/model, X cookies, Reddit — writes `.env`), or copy `.env.example` to `.env`. `trendscope setup --status` shows what is configured without revealing secrets. All credentials are optional; without any, TrendScope still reads YouTube comments, Hacker News, Reddit, Bluesky and the news sources.

- X/Twitter replies: set `TWITTER_AUTH_TOKEN` and `TWITTER_CT0` (x.com cookies). Optional: `pip install -e ".[x]"`.
- Reddit comments: optional `pip install -e ".[reddit]"`; set `REDDIT_SESSION_COOKIE` if Reddit returns 403.
- AI: set the key of any provider (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `OPENCODE_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, `XAI_API_KEY`, or `LLM_BASE_URL`+`LLM_API_KEY`) and choose the default with `LLM_PROVIDER`. `GET /llm/providers` shows what is configured.
- `GEO_TARGET` (default country), `MAX_AGE_DAYS` (default window), `CUSTOM_LEXICON_PATH` (your own slang/brand words).

## Tips for agents

- For decisions, read `meta.mood_index.headline`, `net_score ± margin` and `confidence` first; low confidence means few independent opinions.
- `quotes` and `drivers` explain *why* people feel that way — cite them.
- Compare `mood_index.net_score` (people) against `media_tone.net_score` (press): a gap is itself an insight.
- Use `days=1` for breaking topics and `days=30` for slow ones.
- Use `sentiment_engine=local` for free analysis; use `claude` or `llm` (with `llm_provider`/`llm_model`) for languages without a lexicon.
- The cache lasts 5 minutes, so repeated queries are instant.
- Run `doctor` first to check which sources are available.
