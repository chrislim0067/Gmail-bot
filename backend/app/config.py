"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    database_url: str = (
        "postgresql+asyncpg://outreach:outreach@localhost:5432/outreach"
    )
    redis_url: str = "redis://localhost:6379/1"
    celery_broker_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "CHANGE_ME_32_CHAR_MINIMUM_SECRET_KEY"
    jwt_expire_minutes: int = 60
    jwt_algorithm: str = "HS256"

    token_encryption_key: str = "CHANGE_ME_BASE64_32_BYTES"
    unsubscribe_secret: str = "CHANGE_ME_UNSUBSCRIBE_SECRET"
    unsubscribe_token_expire_days: int = 90

    google_client_id: str = "TODO.apps.googleusercontent.com"
    google_client_secret: str = "TODO"
    google_redirect_uri: str = "http://localhost:8000/api/v1/gmail/callback"
    google_oauth_publishing_status: str = "testing"
    google_oauth_test_user_limit: int = 100

    use_mock_gmail: bool = True

    global_daily_send_limit: int = 200
    global_risk_score_threshold: int = 100
    default_tier_new_daily: int = 5
    default_tier_new_hourly: int = 1
    default_tier_trusted_daily: int = 30
    default_tier_trusted_hard_max: int = 75

    inter_send_delay_min_seconds: int = 1800
    inter_send_delay_max_seconds: int = 1800

    # Minimum wait between sends from different accounts in the same pool
    inter_account_delay_min_seconds: int = 120
    inter_account_delay_max_seconds: int = 180

    oauth_state_ttl_seconds: int = 600
    lock_ttl_seconds: int = 600

    # How often the API background loop (and Celery beat) processes send queues
    scheduler_tick_interval_seconds: int = 30
    scheduler_background_enabled: bool = True

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    service_token: str | None = None

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
