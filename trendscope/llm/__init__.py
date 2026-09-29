"""Capa única de IA (narrativas y sentimiento premium) para cualquier proveedor."""

from trendscope.llm.client import (
    LLMError,
    LLMResult,
    chat,
    default_provider,
    list_models,
    providers_status,
    resolve,
)
from trendscope.llm.providers import PROVIDERS

__all__ = [
    "LLMError", "LLMResult", "PROVIDERS", "chat", "default_provider",
    "list_models", "providers_status", "resolve",
]
