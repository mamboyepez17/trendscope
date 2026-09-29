# core/query.py
from dataclasses import dataclass
from typing import Optional

from trendscope.config import (
    CATEGORIES,
    SUBREDDITS_BY_CATEGORY,
    SENTIMENT_ENGINE_DEFAULT,
    TOP_N,
    GEO_TARGET,
    MAX_AGE_DAYS,
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
    max_age_days: int = MAX_AGE_DAYS       # solo contenido reciente
    lang: Optional[str] = None             # idioma de los textos (None → el del país)

    @property
    def ui_lang(self) -> str:
        """Idioma de etiquetas y titulares: el pedido (es/en/pt) o el del país."""
        from trendscope.core.locale import ui_language

        return ui_language(self.lang, self.geo)

    @property
    def keywords(self) -> list[str]:
        """Keywords para buscar en todas las fuentes.

        Tema libre → solo el tema tal cual. Antes se añadían variantes
        ("tema CO", "tema 2026", "tendencias tema") que los buscadores leían
        como palabras sueltas y traían noticias de cualquier cosa. La frescura
        la dan los filtros de fecha y el país va como parámetro de región.
        """
        if self.mode == "category" and self.category in CATEGORIES:
            return CATEGORIES[self.category]
        elif self.mode == "free" and self.free_topic:
            return [self.free_topic.strip()]
        return []

    @property
    def search_phrases(self) -> list[str]:
        """Consultas para buscadores de noticias: frase exacta entre comillas
        si el tema tiene varias palabras (evita "reforma" o "salud" sueltas)."""
        out = []
        for kw in self.keywords:
            kw = kw.strip().strip('"')
            if not kw:
                continue
            out.append(f'"{kw}"' if " " in kw else kw)
        return out

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
