"""Configuración tipada y validada para TrendScope."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Todas las variables de entorno con valores por defecto."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="",
    )

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "TrendScope/1.5.0"
    # Cookie de sesión para reddit-actions cuando Reddit responde 403
    reddit_session_cookie: str = ""
    reddit_cookie_header: str = ""

    # Twitter/X
    twitter_auth_token: str = ""
    twitter_ct0: str = ""
    # Alternativa: cookie string completa (auth_token=...; ct0=...)
    twitter_cookies: str = ""
    tweetclaw_results_file: str = ""

    # Claude
    anthropic_api_key: str = ""

    # OpenRouter (modelos gratuitos compatibles con OpenAI)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-chat-v3-0324:free"
    openrouter_site_url: str = "https://github.com/mamboyepez17/trendscope"
    openrouter_site_name: str = "TrendScope"

    # DeepSeek (API oficial, compatible OpenAI)
    # Preferido: DeepSeek-V4.1-Flash. Fallback automático a flash/v4-pro/chat.
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"

    # ── IA: cualquier proveedor (ver trendscope/llm/providers.py) ────────────
    # Proveedor por defecto para narrativas y sentimiento "llm". Vacío → el de
    # NARRATOR_PROVIDER. Opciones: openai, claude, deepseek, opencode,
    # openrouter, gemini, groq, mistral, xai, ollama, custom, none.
    llm_provider: str = ""
    openai_api_key: str = ""
    openai_model: str = ""
    claude_model: str = "claude-opus-5-5"
    opencode_api_key: str = ""
    opencode_base_url: str = "https://opencode.ai/zen/v1"
    opencode_model: str = ""
    gemini_api_key: str = ""
    gemini_model: str = ""
    groq_api_key: str = ""
    groq_model: str = ""
    mistral_api_key: str = ""
    mistral_model: str = ""
    xai_api_key: str = ""
    xai_model: str = ""
    # Qwen (Alibaba Model Studio). Región: intl por defecto; EE. UU.
    # https://dashscope-us.aliyuncs.com/compatible-mode/v1; China
    # https://dashscope.aliyuncs.com/compatible-mode/v1
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = ""
    # GLM (Z.ai). China: https://open.bigmodel.cn/api/paas/v4;
    # Coding Plan: https://api.z.ai/api/coding/paas/v4
    glm_api_key: str = ""
    glm_base_url: str = "https://api.z.ai/api/paas/v4"
    glm_model: str = ""
    # Kimi (Moonshot). China: https://api.moonshot.cn/v1
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.ai/v1"
    kimi_model: str = ""
    # Xiaomi MiMo. Con Token Plan usa la URL y la key tp-… de tu suscripción
    mimo_api_key: str = ""
    mimo_base_url: str = "https://api.xiaomimimo.com/v1"
    mimo_model: str = ""
    # Cualquier servidor compatible con OpenAI (LM Studio, vLLM, LiteLLM…)
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    sentiment_engine: str = "local"
    # Modelo del motor "claude" (sentimiento + emociones)
    claude_sentiment_model: str = "claude-haiku-4-5"
    # Léxico propio (JSON) para jerga local, marcas o sectores. Ver
    # trendscope/sentiment/lexicons/__init__.py para el formato.
    custom_lexicon_path: str = ""
    # /trends también recolecta comentarios para el Índice de Ánimo
    pipeline_collect_comments: bool = True

    # General
    geo_target: str = "CO"
    top_n: int = 25
    # Ventana de frescura: solo contenido de los últimos N días (1–30)
    max_age_days: int = 7
    data_dir: str = "data"

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_rate_limit: int = 60
    api_rate_window: int = 60
    org_rate_limit: int = 120
    api_key_required: bool = False
    api_keys: str = ""
    trust_proxy_headers: bool = False

    # Ollama local
    ollama_enabled: bool = False
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"

    # Narrador: openrouter | claude | ollama | none
    narrator_provider: str = "openrouter"
    narrative_enabled: bool = True

    # Watchlist
    watchlist_enabled: bool = True
    watchlist_default_interval_minutes: int = 60

    # Alerts
    alerts_enabled: bool = True
    alerts_timeout_seconds: int = 5

    # Cache
    cache_ttl_seconds: int = 300

    # Source health
    source_health_skip: bool = True


settings = Settings()
