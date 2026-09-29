"""Registro de proveedores de IA.

Casi todos hablan el protocolo de OpenAI (`/chat/completions`, `/models`), así
que un solo cliente sirve para ChatGPT, DeepSeek, OpenCode, OpenRouter, Gemini,
Groq, Mistral, xAI, Ollama o cualquier servidor compatible ("custom": LM Studio,
vLLM, LiteLLM…). Claude usa el SDK oficial de Anthropic.

Cada proveedor se configura con su API key y, opcionalmente, su modelo por
defecto en .env (p. ej. OPENAI_API_KEY + OPENAI_MODEL). El modelo también se
puede elegir en cada petición.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from trendscope.settings import settings


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    kind: str                    # "openai" (compatible) | "anthropic"
    key_setting: str | None      # atributo de settings con la API key (None = sin key)
    model_setting: str | None    # atributo de settings con el modelo por defecto
    base_url: str = ""           # vacío → se toma de base_url_setting
    base_url_setting: str | None = None
    keys_url: str = ""
    extra_headers: dict = field(default_factory=dict)
    key_header: str = ""         # encabezado extra con la key (además de Bearer)

    @property
    def api_key(self) -> str:
        return str(getattr(settings, self.key_setting, "") or "") if self.key_setting else ""

    @property
    def default_model(self) -> str:
        return str(getattr(settings, self.model_setting, "") or "") if self.model_setting else ""

    @property
    def url(self) -> str:
        if self.base_url_setting:
            return str(getattr(settings, self.base_url_setting, "") or self.base_url).rstrip("/")
        return self.base_url.rstrip("/")

    @property
    def configured(self) -> bool:
        if self.id == "ollama":
            return bool(getattr(settings, "ollama_enabled", False))
        if self.id == "custom":
            return bool(self.url)
        return bool(self.api_key)


PROVIDERS: dict[str, Provider] = {p.id: p for p in (
    Provider("openai", "OpenAI (ChatGPT)", "openai", "openai_api_key", "openai_model",
             "https://api.openai.com/v1", keys_url="https://platform.openai.com/api-keys"),
    Provider("claude", "Anthropic (Claude)", "anthropic", "anthropic_api_key", "claude_model",
             keys_url="https://console.anthropic.com/settings/keys"),
    Provider("deepseek", "DeepSeek", "openai", "deepseek_api_key", "deepseek_model",
             "https://api.deepseek.com", base_url_setting="deepseek_base_url",
             keys_url="https://platform.deepseek.com/api_keys"),
    Provider("opencode", "OpenCode Zen", "openai", "opencode_api_key", "opencode_model",
             "https://opencode.ai/zen/v1", base_url_setting="opencode_base_url",
             keys_url="https://opencode.ai/auth"),
    Provider("openrouter", "OpenRouter", "openai", "openrouter_api_key", "openrouter_model",
             "https://openrouter.ai/api/v1", base_url_setting="openrouter_base_url",
             keys_url="https://openrouter.ai/keys",
             extra_headers={"HTTP-Referer": "https://github.com/mamboyepez17/trendscope",
                            "X-Title": "TrendScope"}),
    Provider("gemini", "Google Gemini", "openai", "gemini_api_key", "gemini_model",
             "https://generativelanguage.googleapis.com/v1beta/openai",
             keys_url="https://aistudio.google.com/apikey"),
    Provider("groq", "Groq", "openai", "groq_api_key", "groq_model",
             "https://api.groq.com/openai/v1", keys_url="https://console.groq.com/keys"),
    Provider("mistral", "Mistral", "openai", "mistral_api_key", "mistral_model",
             "https://api.mistral.ai/v1", keys_url="https://console.mistral.ai/api-keys"),
    Provider("xai", "xAI (Grok)", "openai", "xai_api_key", "xai_model",
             "https://api.x.ai/v1", keys_url="https://console.x.ai"),
    # Proveedores chinos, todos compatibles con OpenAI. La URL base se puede
    # cambiar en .env (región China, Coding Plan / Token Plan…).
    Provider("qwen", "Qwen (Alibaba Model Studio)", "openai", "qwen_api_key", "qwen_model",
             "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
             base_url_setting="qwen_base_url",
             keys_url="https://www.alibabacloud.com/help/en/model-studio/get-api-key"),
    Provider("glm", "GLM (Z.ai / Zhipu)", "openai", "glm_api_key", "glm_model",
             "https://api.z.ai/api/paas/v4", base_url_setting="glm_base_url",
             keys_url="https://z.ai/manage-apikey/apikey-list"),
    Provider("kimi", "Kimi (Moonshot)", "openai", "kimi_api_key", "kimi_model",
             "https://api.moonshot.ai/v1", base_url_setting="kimi_base_url",
             keys_url="https://platform.moonshot.ai"),
    Provider("mimo", "Xiaomi MiMo", "openai", "mimo_api_key", "mimo_model",
             "https://api.xiaomimimo.com/v1", base_url_setting="mimo_base_url",
             keys_url="https://platform.xiaomimimo.com/console/api-keys",
             key_header="api-key"),
    Provider("ollama", "Ollama (local)", "openai", None, "ollama_model",
             "http://localhost:11434", base_url_setting="ollama_host"),
    Provider("custom", "Custom (OpenAI-compatible)", "openai", "llm_api_key", "llm_model",
             "", base_url_setting="llm_base_url"),
)}

# Nombres alternativos que la gente escribe
ALIASES = {"anthropic": "claude", "chatgpt": "openai", "gpt": "openai", "grok": "xai",
           "google": "gemini", "zen": "opencode", "local": "ollama",
           "alibaba": "qwen", "dashscope": "qwen", "zhipu": "glm", "zai": "glm", "z.ai": "glm",
           "moonshot": "kimi", "xiaomi": "mimo"}


def get(provider_id: str | None) -> Provider | None:
    if not provider_id:
        return None
    pid = provider_id.strip().lower()
    return PROVIDERS.get(ALIASES.get(pid, pid))


def chat_base_url(p: Provider) -> str:
    """URL base para /chat/completions (Ollama expone la API compatible en /v1)."""
    url = p.url
    if p.id == "ollama" and not url.endswith("/v1"):
        url = f"{url}/v1"
    return url
