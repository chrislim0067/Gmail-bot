"""Worker settings loaded from environment (same as backend)."""

from app.config import Settings, get_settings


def get_worker_settings() -> Settings:
    return get_settings()
