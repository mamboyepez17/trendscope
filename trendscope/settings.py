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
    reddit_user_agent: str = "TrendScope/1.4.0"

    # Twitter/X
    twitter_auth_token: str = ""
    twitter_ct0: str = ""
    tweetclaw_results_file: str = ""

    # Claude
    anthropic_api_key: str = ""

    # Sentimiento
    sentiment_engine: str = "local"

    # General
    geo_target: str = "CO"
    top_n: int = 25
    data_dir: str = "data"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Ollama local
    ollama_enabled: bool = True
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"

    # Cache
    cache_ttl_seconds: int = 300


settings = Settings()
