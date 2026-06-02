# server_mcp.py
# Servidor MCP — TrendScope como herramienta para agentes MCP
# Uso: python server_mcp.py
import json
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from config import CATEGORIES
from core.query import TrendQuery
from core.pipeline import run as run_pipeline

app = Server("trendscope")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_trends",
            description=(
                "Analiza tendencias sobre cualquier tema desde multiples fuentes "
                "gratuitas (Reddit, Google Trends, Twitter/X, Amazon, TikTok) "
                "con analisis de sentimiento incluido. "
                "Retorna JSON con top tendencias, scores y resumen de sentimiento."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Tema libre a analizar. Ej: 'crypto Colombia', 'salud mental 2026'",
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoria predefinida: " + ", ".join(CATEGORIES.keys()),
                    },
                    "geo": {
                        "type": "string",
                        "description": "Codigo pais ISO (default: CO)",
                        "default": "CO",
                    },
                    "sentiment_engine": {
                        "type": "string",
                        "enum": ["local", "claude"],
                        "description": "Motor de sentimiento (default: local)",
                        "default": "local",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Numero de tendencias a retornar (default: 25)",
                        "default": 25,
                    },
                },
            },
        ),
        Tool(
            name="get_categories",
            description="Lista las categorias predefinidas disponibles en TrendScope.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_latest_report",
            description="Obtiene el ultimo reporte Markdown generado para un tema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Tema del reporte a buscar",
                    }
                },
                "required": ["topic"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "analyze_trends":
        topic = arguments.get("topic")
        category = arguments.get("category")

        query = TrendQuery(
            mode="category" if category else "free",
            category=category,
            free_topic=topic,
            geo=arguments.get("geo", "CO"),
            sentiment_engine=arguments.get("sentiment_engine", "local"),
            top_n=arguments.get("top_n", 25),
        )

        loop = asyncio.get_event_loop()
        payload, _ = await loop.run_in_executor(None, run_pipeline, query)

        return [TextContent(
            type="text",
            text=json.dumps(payload, ensure_ascii=False, indent=2),
        )]

    elif name == "get_categories":
        return [TextContent(
            type="text",
            text=json.dumps(
                {"categories": list(CATEGORIES.keys())},
                ensure_ascii=False,
                indent=2,
            ),
        )]

    elif name == "get_latest_report":
        from pathlib import Path
        from config import DATA_DIR
        slug = arguments.get("topic", "").replace(" ", "_")[:30]
        reports = sorted(Path(DATA_DIR).glob(f"report_*{slug}*.md"), reverse=True)
        if reports:
            return [TextContent(type="text", text=reports[0].read_text(encoding="utf-8"))]
        return [TextContent(type="text", text=f"No hay reportes para '{slug}'")]

    return [TextContent(type="text", text="Herramienta no encontrada")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
