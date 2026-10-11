"""Application Configuration module using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: str = Field(default="local", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://insurai:change_me@localhost:5432/insurai",
        alias="DATABASE_URL",
    )
    postgres_user: str = Field(default="insurai", alias="POSTGRES_USER")
    postgres_password: str = Field(default="change_me", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="insurai", alias="POSTGRES_DB")

    # Authentication
    jwt_secret: str = Field(
        default="dev_secret_insecure_default_key_change_in_production_min_32",
        alias="JWT_SECRET",
    )
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    # LLM Settings
    llm_provider: str = Field(default="fake", alias="LLM_PROVIDER")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="gemini-2.0-flash", alias="LLM_MODEL")
    embedding_model: str = Field(default="text-embedding-004", alias="EMBEDDING_MODEL")
    embedding_dim: int = Field(default=768, alias="EMBEDDING_DIM")
    llm_daily_request_cap: int = Field(default=200, alias="LLM_DAILY_REQUEST_CAP")
    llm_request_timeout_seconds: int = Field(default=60, alias="LLM_REQUEST_TIMEOUT_SECONDS")
    llm_cache_enabled: bool = Field(default=True, alias="LLM_CACHE_ENABLED")
    store_full_prompts: bool = Field(default=False, alias="STORE_FULL_PROMPTS")

    # Agent Runtime Defaults
    llm_max_retries: int = Field(default=4, alias="LLM_MAX_RETRIES")
    agent_max_steps: int = Field(default=8, alias="AGENT_MAX_STEPS")
    agent_max_total_tokens: int = Field(default=10000, alias="AGENT_MAX_TOTAL_TOKENS")
    agent_timeout_seconds: int = Field(default=90, alias="AGENT_TIMEOUT_SECONDS")
    confidence_threshold: float = Field(default=0.75, alias="CONFIDENCE_THRESHOLD")
    auto_approve_enabled: bool = Field(default=False, alias="AUTO_APPROVE_ENABLED")
    auto_approve_max_amount: float = Field(default=500.0, alias="AUTO_APPROVE_MAX_AMOUNT")
    cost_per_million_input_tokens: float = Field(
        default=0.15, alias="COST_PER_MILLION_INPUT_TOKENS"
    )
    cost_per_million_output_tokens: float = Field(
        default=0.60, alias="COST_PER_MILLION_OUTPUT_TOKENS"
    )


settings = Settings()
