# core/query.py
from dataclasses import dataclass
from typing import Optional

from trendscope.config import (
    CATEGORIES,
    SUBREDDITS_BY_CATEGORY,
    SENTIMENT_ENGINE_DEFAULT,
    TOP_N,
    GEO_TARGET,
)


@dataclass
class TrendQuery:
    """
    Modelo de consulta del usuario.
    Representa QUE analizar, COMO y con que configuracion.
    """
    mode: str                          # "category" | "free"
    category: Optional[str] = None     # clave de CATEGORIES
    free_topic: Optional[str] = None   # tema libre del usuario
    geo: str = GEO_TARGET
    top_n: int = TOP_N
    sentiment_engine: str = SENTIMENT_ENGINE_DEFAULT

    @property
    def keywords(self) -> list[str]:
        """Keywords para buscar en todas las fuentes."""
        from datetime import datetime

        if self.mode == "category" and self.category in CATEGORIES:
            return CATEGORIES[self.category]
        elif self.mode == "free" and self.free_topic:
            t = self.free_topic.strip()
            year = datetime.now().year
            return [t, f"{t} {self.geo}", f"{t} {year}", f"tendencias {t}"]
        return []

    @property
    def subreddits(self) -> list[str]:
        """Subreddits relevantes segun la categoria."""
        if self.mode == "category" and self.category in SUBREDDITS_BY_CATEGORY:
            return SUBREDDITS_BY_CATEGORY[self.category]
        return SUBREDDITS_BY_CATEGORY["libre"]

    @property
    def display_name(self) -> str:
        """Nombre legible para mostrar en CLI y reportes."""
        if self.mode == "category":
            return f"Categoria: {self.category}"
        return f"Tema libre: {self.free_topic}"

    @property
    def topic_slug(self) -> str:
        """Slug seguro para nombres de archivos de output."""
        from trendscope.core.paths import safe_slug

        return safe_slug(self.free_topic or self.category or "general")
