# output/report_exporter.py
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from config import DATA_DIR
from core.query import TrendQuery
from sentiment.base import SENTIMENT_EMOJI


def export(payload: dict, query: TrendQuery, insights: dict = None) -> str:
    """
    Genera reporte Markdown legible para humanos.
    Guarda archivo en data/ y retorna el contenido como string.
    """
    now = datetime.now(timezone.utc)
    meta = payload["meta"]
    top = payload["top_trends"]
    ss = meta["sentiment_summary"]

    lines = [
        "# TrendScope Report",
        "",
        f"**Tema:** {query.display_name}  ",
        f"**Fecha:** {now.strftime('%d/%m/%Y %H:%M')} UTC  ",
        f"**Fuentes:** {', '.join(meta['sources_used'])}  ",
        f"**Total analizado:** {meta['total_analyzed']} senales  ",
        f"**Motor sentimiento:** {ss['engine']}",
        "",
        "## Sentimiento General",
        "",
        "| [+] Positivo | [-] Negativo | [~] Neutral | Predominante |",
        "|---|---|---|---|",
        f"| {ss['positive']} | {ss['negative']} | {ss['neutral']} | **{ss['overall'].upper()}** |",
        "",
        "---",
        "",
        "## Top Tendencias",
        "",
    ]

    for item in top:
        score = item["trend_score"]
        if score >= 75:
            heat = "[HOT]"
        elif score >= 50:
            heat = "[MED]"
        else:
            heat = "[LOW]"

        sent = item["sentiment"]
        s_symbol = SENTIMENT_EMOJI.get(sent["label"], "?")
        title = item["title"]
        url = item["url"]
        sigs = item["signals"]

        lines.append(f"### {item['rank']}. {heat} {title}")
        lines.append(
            f"**Score:** {score}/100 | "
            f"**Fuente:** {item['source'].replace('_', ' ').title()} | "
            f"**Sentimiento:** {s_symbol} {sent['label']} ({sent['score']:.0%})"
        )

        # Emociones top 2
        if sent.get("emotions"):
            top_emo = sorted(sent["emotions"].items(), key=lambda x: x[1], reverse=True)[:2]
            if top_emo and top_emo[0][1] > 0:
                lines.append(f"**Emociones:** {', '.join(f'{e} {v:.0%}' for e, v in top_emo)}")

        # Senales disponibles
        sig_parts = []
        if sigs.get("reddit_score"):
            sig_parts.append(f"Upvotes: {sigs['reddit_score']}")
        if sigs.get("comments"):
            sig_parts.append(f"Comments: {sigs['comments']}")
        if sigs.get("likes"):
            sig_parts.append(f"Likes: {sigs['likes']}")
        if sigs.get("retweets"):
            sig_parts.append(f"RTs: {sigs['retweets']}")
        if sigs.get("google_traffic"):
            sig_parts.append(f"Traffic: {sigs['google_traffic']}")
        if sigs.get("amazon_rank"):
            sig_parts.append(f"Amazon #{sigs['amazon_rank']}")
        if sigs.get("price"):
            sig_parts.append(f"Price: {sigs['price']}")
        if sig_parts:
            lines.append(f"**Senales:** {' | '.join(sig_parts)}")
        if url:
            lines.append(f"**Link:** {url[:100]}")
        lines.append("")

    # --- Sección de Insights ---
    if insights:
        lines += [
            "---",
            "",
            "## 🧠 Análisis de TrendScope",
            "",
            f"**Resumen ejecutivo:** {insights.get('executive_summary', 'N/A')}",
            "",
        ]

        # Insights accionables
        actionable = insights.get("actionable_insights", [])
        if actionable:
            lines.append("### Insights accionables")
            lines.append("")
            for i in actionable:
                icon = "🎯" if i["type"] == "opportunity" else "⚠️" if i["type"] == "alert" else "📊"
                lines.append(f"{icon} **[{i['priority'].upper()}]** {i['title']}")
                lines.append(f"   {i['description']}")
                lines.append("")

        # Correlaciones
        correlations = insights.get("correlations", [])
        if correlations:
            lines.append("### Correlaciones entre fuentes")
            lines.append("")
            for c in correlations:
                icon = "🤝" if c["type"] == "consensus" else "🔀" if c["type"] == "divergence" else "📈"
                lines.append(f"{icon} {c['description']}")
                lines.append("")

        # Emergentes vs Establecidos
        em = insights.get("emerging_vs_established", {})
        if em.get("emerging"):
            lines.append("### ⚡ Tendencias emergentes")
            lines.append("")
            for e in em["emerging"]:
                lines.append(f"- **{e['title'][:70]}** (score: {e['score']}, fuente: {e['source']})")
            lines.append("")

        if em.get("established"):
            lines.append("### ✅ Tendencias establecidas")
            lines.append("")
            for e in em["established"]:
                lines.append(f"- **{e['title'][:70]}** (score: {e['score']}, fuentes: {e['sources_count']})")
            lines.append("")

        # Recomendaciones
        recs = insights.get("recommendations", [])
        if recs:
            lines.append("### 🎯 Recomendaciones")
            lines.append("")
            for r in recs:
                lines.append(f"- {r}")
            lines.append("")

    lines += [
        "---",
        "",
        "## Prompt para analisis IA",
        "",
        f"> {payload['agent_prompt']}",
        "",
        "---",
        f"*TrendScope v1.2 | mamboyepez17 | {now.strftime('%Y-%m-%d')}*",
    ]

    report = "\n".join(lines)
    Path(DATA_DIR).mkdir(exist_ok=True)
    filepath = Path(DATA_DIR) / f"report_{now.strftime('%Y-%m-%d')}_{query.topic_slug}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    logger.success(f"Reporte exportado: {filepath}")
    return report
