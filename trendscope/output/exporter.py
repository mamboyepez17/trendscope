"""Exportadores de resultados de TrendScope a CSV, JSON y Excel."""

import csv
import json
from pathlib import Path
from typing import Any

from trendscope.settings import settings


_FLAT_FIELDS = [
    "title",
    "source",
    "url",
    "trend_score",
    "sentiment",
    "sentiment_score",
    "volume",
    "likes",
    "comments",
    "shares",
    "views",
    "published_at",
]


def _flatten_trend(trend: dict) -> dict[str, Any]:
    """Convierte una tendencia en un diccionario plano para CSV/Excel."""
    flat = {}
    for field in _FLAT_FIELDS:
        flat[field] = trend.get(field, "")
    # Keywords extra si existen
    flat["keywords"] = ", ".join(trend.get("keywords", []))
    return flat


def _ensure_data_dir() -> Path:
    path = Path(settings.data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_json(payload: dict, filename: str | None = None, output_dir: Path | None = None) -> Path:
    """Exporta el payload completo a JSON."""
    data_dir = output_dir or _ensure_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    topic = payload.get("meta", {}).get("query", {}).get("topic", "trend")
    filename = filename or f"export_{topic.replace(' ', '_')[:30]}_{_now()}.json"
    path = data_dir / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_csv(payload: dict, filename: str | None = None, output_dir: Path | None = None) -> Path:
    """Exporta las tendencias top a CSV."""
    data_dir = output_dir or _ensure_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    topic = payload.get("meta", {}).get("query", {}).get("topic", "trend")
    filename = filename or f"export_{topic.replace(' ', '_')[:30]}_{_now()}.csv"
    path = data_dir / filename

    rows = [_flatten_trend(t) for t in payload.get("top_trends", [])]
    if not rows:
        # Escribir encabezados vacíos
        rows = [dict.fromkeys(_FLAT_FIELDS + ["keywords"], "")]

    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def export_excel(payload: dict, filename: str | None = None, output_dir: Path | None = None) -> Path:
    """Exporta el payload a Excel con dos hojas: Tendencias y Metadatos."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl no está instalado. Instálalo con: pip install openpyxl")

    data_dir = output_dir or _ensure_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    topic = payload.get("meta", {}).get("query", {}).get("topic", "trend")
    filename = filename or f"export_{topic.replace(' ', '_')[:30]}_{_now()}.xlsx"
    path = data_dir / filename

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tendencias"

    rows = [_flatten_trend(t) for t in payload.get("top_trends", [])]
    if rows:
        ws.append(list(rows[0].keys()))
        for row in rows:
            ws.append(list(row.values()))
    else:
        ws.append(_FLAT_FIELDS + ["keywords"])

    # Hoja de metadatos
    meta_ws = wb.create_sheet("Metadatos")
    meta = payload.get("meta", {})
    query = meta.get("query", {})
    sentiment = meta.get("sentiment_summary", {})
    meta_ws.append(["Campo", "Valor"])
    meta_ws.append(["Tema", query.get("topic", "")])
    meta_ws.append(["Geo", query.get("geo", "")])
    meta_ws.append(["Señales analizadas", meta.get("total_analyzed", 0)])
    meta_ws.append(["Positivo", sentiment.get("positive", 0)])
    meta_ws.append(["Negativo", sentiment.get("negative", 0)])
    meta_ws.append(["Neutral", sentiment.get("neutral", 0)])

    wb.save(str(path))
    return path


def _now() -> str:
    """Timestamp simple para nombres de archivo."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


__all__ = ["export_json", "export_csv", "export_excel"]
