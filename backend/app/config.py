from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str
    postgres_db: str = "studyai"
    postgres_user: str = "studyai_user"
    postgres_password: str

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # JWT
    jwt_private_key: str
    jwt_public_key: str

    # Anthropic
    anthropic_api_key: str
    haiku_model: str = "claude-haiku-4-5"
    daily_cost_ceiling_usd: float = 5.00
    daily_token_limit_per_user: int = 50_000

    # Guardrail
    guardrail_url: str = "http://guardrail:8002/classify"

    # NAS
    nas_mount_path: str = "/data"

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # Encryption
    aes_master_key: str

    # App
    app_env: str = "production"
    debug: bool = False
    allowed_origins: str = "https://yourdomain.com"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
