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
            batch_raw = texts[i:i + batch_size]
            batch = [t[:300] if t and len(t.strip()) > 3 else "" for t in batch_raw]
            # Filtrar solo los no-vacios para el prompt, pero mantener
            # alineacion 1:1 con los items originales.
            non_empty_indices = [j for j, t in enumerate(batch) if t]
            prompt_texts = [batch[j] for j in non_empty_indices]
            if not prompt_texts:
                # Todos vacios en este batch -> agregar neutrals
                for _ in batch:
                    results.append(SentimentResult(
                        text="",
                        label="neutral",
                        score=0.5,
                        engine="claude_skipped",
                        emotions={},
                    ))
                continue

            prompt = (
                "Analyze the sentiment of these texts. They may be in Spanish or English.\n"
                "Auto-detect the language and analyze accordingly.\n"
                "Respond ONLY with a JSON array, no explanations or markdown.\n"
                "Format per item:\n"
                '{"label":"positive|negative|neutral","score":0.0-1.0,'
                '"lang":"es|en",'
                '"emotions":{"joy":0.0,"anger":0.0,"fear":0.0,"sadness":0.0,"surprise":0.0}}\n\n'
                f"Texts:\n{json.dumps(prompt_texts, ensure_ascii=False)}"
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
                # Si falla el parse, agregar neutrals para todo el batch
                for _ in batch:
                    results.append(SentimentResult(
                        text="",
                        label="neutral",
                        score=0.5,
                        engine="claude_parse_error",
                        emotions={},
                    ))
                continue

            # Mapear resultados de Claude a las posiciones correctas del batch
            # Mantener alineacion 1:1: iterar el batch en orden, y para cada
            # posicion, si es non-empty usar el siguiente resultado de Claude,
            # si es empty, agregar neutral.
            parsed_idx = 0
            for batch_pos in range(len(batch)):
                if batch_pos in non_empty_indices:
                    if parsed_idx < len(parsed):
                        item = parsed[parsed_idx]
                        results.append(SentimentResult(
                            text=batch[batch_pos][:100],
                            label=item.get("label", "neutral"),
                            score=float(item.get("score", 0.5)),
                            engine="claude",
                            emotions=item.get("emotions", {}),
                        ))
                        parsed_idx += 1
                    else:
                        # Claude devolvio menos resultados de los esperados
                        results.append(SentimentResult(
                            text=batch[batch_pos][:100],
                            label="neutral",
                            score=0.5,
                            engine="claude_short_result",
                            emotions={},
                        ))
                else:
                    results.append(SentimentResult(
                        text="",
                        label="neutral",
                        score=0.5,
                        engine="claude_skipped",
                        emotions={},
                    ))

        logger.success(f"Claude sentiment: {len(results)} textos analizados")
        return results

    except ImportError:
        logger.error("anthropic no instalado. Ejecuta: pip install anthropic")
        return []
    except Exception as e:
        logger.error(f"Claude sentiment engine: {e}")
        return []
