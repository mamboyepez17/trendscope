# sentiment/claude_engine.py
# Claude Haiku — analisis premium, bajo costo por token
import json

from loguru import logger

from config import ANTHROPIC_API_KEY
from sentiment.base import SentimentResult


def analyze(texts: list[str]) -> list[SentimentResult]:
    """Analiza sentimiento usando Claude Haiku API en batches."""
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY no configurada en .env")
        return []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        results: list[SentimentResult] = []
        batch_size = 10

        for i in range(0, len(texts), batch_size):
            batch = [t[:300] for t in texts[i:i + batch_size] if t and len(t.strip()) > 3]
            if not batch:
                continue

            prompt = (
                "Analiza el sentimiento de estos textos en espanol latinoamericano.\n"
                "Responde SOLO con un JSON array sin explicaciones ni markdown.\n"
                "Formato por item:\n"
                '{"label":"positive|negative|neutral","score":0.0-1.0,'
                '"emotions":{"joy":0.0,"anger":0.0,"fear":0.0,"sadness":0.0,"surprise":0.0}}\n\n'
                f"Textos:\n{json.dumps(batch, ensure_ascii=False)}"
            )

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            # Limpiar posibles bloques de codigo markdown
            raw = raw.replace("```json", "").replace("```", "").strip()

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.warning(f"Claude JSON parse error: {e}")
                continue

            for idx, item in enumerate(parsed):
                if idx < len(batch):
                    results.append(SentimentResult(
                        text=batch[idx][:100],
                        label=item.get("label", "neutral"),
                        score=float(item.get("score", 0.5)),
                        engine="claude",
                        emotions=item.get("emotions", {}),
                    ))

        logger.success(f"Claude sentiment: {len(results)} textos analizados")
        return results

    except ImportError:
        logger.error("anthropic no instalado. Ejecuta: pip install anthropic")
        return []
    except Exception as e:
        logger.error(f"Claude sentiment engine: {e}")
        return []
