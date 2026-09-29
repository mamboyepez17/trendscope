"""
XActions-PY — Shareable reports (Markdown / HTML).

No extra deps: stdlib only.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any

from .analyzer import analyze_tweets, compare_accounts


def _fmt_int(n: Any) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(n: Any) -> str:
    if n is None:
        return "—"
    try:
        return f"{float(n):.4f}%"
    except (TypeError, ValueError):
        return str(n)


def _tweet_rows_md(tweets: list[dict[str, Any]], limit: int = 10) -> str:
    rows = []
    for t in tweets[:limit]:
        text = (t.get("text") or "").replace("\n", " ")[:100]
        rows.append(
            f"| {t.get('id', '')} | {text} | {_fmt_int(t.get('likes'))} | "
            f"{_fmt_int(t.get('retweets'))} | {_fmt_int(t.get('views'))} |"
        )
    header = "| ID | Text | Likes | RTs | Views |\n|---|---|---:|---:|---:|"
    if not rows:
        return "_No tweets._"
    return header + "\n" + "\n".join(rows)


def render_account_report_md(
    profile: dict[str, Any],
    tweets: list[dict[str, Any]],
    *,
    title: str | None = None,
) -> str:
    """Markdown report for one account."""
    report = analyze_tweets(tweets, profile=profile)
    username = profile.get("username") or "unknown"
    title = title or f"X report — @{username}"
    avg = report.get("averages") or {}
    content = report.get("content") or {}
    lines = [
        f"# {title}",
        "",
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        "## Profile",
        "",
        f"- **@{username}** — {profile.get('name') or ''}",
        f"- Followers: **{_fmt_int(profile.get('followers'))}** · Following: {_fmt_int(profile.get('following'))}",
        f"- Tweets (account): {_fmt_int(profile.get('tweets_count'))}",
        f"- Verified: {'yes' if profile.get('verified') else 'no'}",
        f"- Bio: {(profile.get('bio') or '—').replace(chr(10), ' ')[:200]}",
        "",
        "## Engagement (sample)",
        "",
        f"- Tweets analyzed: **{report.get('total_tweets', 0)}**",
        f"- Avg likes: {_fmt_int(avg.get('likes'))} · RTs: {_fmt_int(avg.get('retweets'))} · "
        f"replies: {_fmt_int(avg.get('replies'))} · views: {_fmt_int(avg.get('views'))}",
        f"- Engagement rate (followers): **{_fmt_pct(report.get('engagement_rate_followers'))}**",
        f"- Engagement rate (views): {_fmt_pct(report.get('engagement_rate_views'))}",
        f"- With media: {content.get('with_media_pct', 0)}% · replies: {content.get('replies_pct', 0)}%",
        "",
    ]
    if report.get("best_hours"):
        hours = ", ".join(f"{h['hour']:02d}:00" for h in report["best_hours"])
        lines += [f"- Best hours (UTC): {hours}", ""]
    if report.get("top_tweets"):
        lines += ["## Top tweets", "", _tweet_rows_md(report["top_tweets"], 5), ""]
    if tweets:
        lines += ["## Recent sample", "", _tweet_rows_md(tweets, 10), ""]
    return "\n".join(lines)


def render_compare_report_md(
    profile_a: dict[str, Any],
    tweets_a: list[dict[str, Any]],
    profile_b: dict[str, Any],
    tweets_b: list[dict[str, Any]],
) -> str:
    cmp = compare_accounts(profile_a, tweets_a, profile_b, tweets_b)
    a, b = cmp["a"], cmp["b"]
    w = cmp.get("winner") or {}
    lines = [
        f"# Comparison @{a.get('username')} vs @{b.get('username')}",
        "",
        f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"| Metric | @{a.get('username')} | @{b.get('username')} |",
        "|---|---:|---:|",
        f"| Followers | {_fmt_int(a.get('followers'))} | {_fmt_int(b.get('followers'))} |",
        f"| Avg likes | {_fmt_int((a.get('averages') or {}).get('likes'))} | {_fmt_int((b.get('averages') or {}).get('likes'))} |",
        f"| ER followers | {_fmt_pct(a.get('engagement_rate_followers'))} | {_fmt_pct(b.get('engagement_rate_followers'))} |",
        "",
        f"**Winners:** followers=`{w.get('followers')}` · ER=`{w.get('engagement_rate_followers')}` · likes=`{w.get('avg_likes')}`",
        "",
    ]
    return "\n".join(lines)


def _md_to_simple_html(md_text: str, title: str) -> str:
    """Minimal MD→HTML for headings, lists, tables, bold. Good enough for sharing."""
    lines_out: list[str] = []
    in_table = False
    in_list = False

    def close_lists():
        nonlocal in_list, in_table
        if in_list:
            lines_out.append("</ul>")
            in_list = False
        if in_table:
            lines_out.append("</table>")
            in_table = False

    for raw in md_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_lists()
            lines_out.append("")
            continue
        if line.startswith("# "):
            close_lists()
            lines_out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            close_lists()
            lines_out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("_") and line.endswith("_") and len(line) > 2:
            close_lists()
            lines_out.append(f"<p><em>{html.escape(line.strip('_'))}</em></p>")
        elif line.startswith("- "):
            if not in_list:
                close_lists()
                lines_out.append("<ul>")
                in_list = True
            content = line[2:]
            content = _inline_bold(content)
            lines_out.append(f"<li>{content}</li>")
        elif line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # separator
            if not in_table:
                if in_list:
                    lines_out.append("</ul>")
                    in_list = False
                lines_out.append("<table>")
                in_table = True
                tag = "th"
            else:
                tag = "td"
            tds = "".join(f"<{tag}>{_inline_bold(c)}</{tag}>" for c in cells)
            lines_out.append(f"<tr>{tds}</tr>")
        else:
            close_lists()
            lines_out.append(f"<p>{_inline_bold(line)}</p>")
    close_lists()
    body = "\n".join(lines_out)
    return (
        "<!DOCTYPE html>\n<html><head><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;line-height:1.5}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ddd;padding:.4rem .6rem;text-align:left}"
        "th{background:#f5f5f5}</style></head><body>\n"
        f"{body}\n</body></html>\n"
    )


def _inline_bold(text: str) -> str:
    import re

    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def render_account_report_html(profile: dict[str, Any], tweets: list[dict[str, Any]]) -> str:
    md = render_account_report_md(profile, tweets)
    username = profile.get("username") or "account"
    return _md_to_simple_html(md, f"X report @{username}")


def render_compare_report_html(
    profile_a: dict[str, Any],
    tweets_a: list[dict[str, Any]],
    profile_b: dict[str, Any],
    tweets_b: list[dict[str, Any]],
) -> str:
    md = render_compare_report_md(profile_a, tweets_a, profile_b, tweets_b)
    return _md_to_simple_html(
        md,
        f"Compare @{profile_a.get('username')} vs @{profile_b.get('username')}",
    )
