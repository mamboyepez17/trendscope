# TweetClaw OpenClaw Source

TrendScope can score tweet results that were collected by TweetClaw in OpenClaw. Use this path when you want TrendScope to keep its Reddit, Google Trends, Amazon, TikTok, and sentiment pipeline while using a managed OpenClaw plugin for X/Twitter search data.

TweetClaw is optional. The existing `xactions-py` cookie source remains the default live Twitter/X scraper.

## When To Use It

Use the TweetClaw JSON source when an OpenClaw agent needs to:

- Search tweets or search tweet replies before TrendScope scoring.
- Reuse an approved TweetClaw result without sharing X cookies with TrendScope.
- Keep X/Twitter collection separate from TrendScope's CLI, REST API, or MCP server.

## Collect Results In OpenClaw

Install TweetClaw:

```bash
openclaw plugins install @xquik/tweetclaw
```

If the tools are not visible to the agent, allow only the two TweetClaw tools:

```bash
openclaw config set tools.alsoAllow '["explore", "tweetclaw"]'
```

Ask the agent to discover the tweet search endpoint:

```json
{ "query": "search tweets", "category": "twitter", "method": "GET", "limit": 5 }
```

Then run a narrow search and save the tool result as JSON:

```json
{
  "path": "/api/v1/x/tweets/search",
  "method": "GET",
  "query": {
    "q": "crypto Colombia",
    "limit": 50
  }
}
```

Store the result locally, for example:

```text
data/tweetclaw_crypto_colombia.json
```

Do not paste API keys, signing keys, cookies, passwords, or account material into prompts, issues, logs, or saved JSON fixtures.

## Use It In TrendScope

Set `TWEETCLAW_RESULTS_FILE` before running the CLI, REST API, or MCP server:

```bash
TWEETCLAW_RESULTS_FILE=data/tweetclaw_crypto_colombia.json python main.py
```

For the REST API:

```bash
TWEETCLAW_RESULTS_FILE=data/tweetclaw_crypto_colombia.json python server_api.py
```

For the MCP server:

```bash
TWEETCLAW_RESULTS_FILE=data/tweetclaw_crypto_colombia.json python server_mcp.py
```

TrendScope accepts these TweetClaw/Xquik JSON shapes:

```json
{ "tweets": [{ "id": "123", "text": "Example", "like_count": 10 }] }
```

```json
{ "data": { "tweets": [{ "id": "123", "text": "Example" }] } }
```

```json
[{ "id": "123", "text": "Example" }]
```

Each tweet is normalized to TrendScope's source contract with `source`, `keyword`, `text`, `likes`, `retweets`, `replies`, `user_followers`, and `url`.
