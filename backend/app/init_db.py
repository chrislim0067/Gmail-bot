"""Create database tables on startup (MVP — use Alembic in production)."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

import app.models  # noqa: F401 — register all models with Base.metadata

from app.database import Base, engine

logger = logging.getLogger(__name__)

_USER_SEND_COLUMNS = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS account_send_cooldown_seconds INTEGER",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS inter_account_delay_min_seconds INTEGER",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS inter_account_delay_max_seconds INTEGER",
)

_SCHEMA_PATCHES = (
    "ALTER TABLE campaigns ALTER COLUMN template_id DROP NOT NULL",
    "ALTER TABLE email_templates ALTER COLUMN subject_template DROP NOT NULL",
    """
    ALTER TABLE email_templates
    ALTER COLUMN deleted_at TYPE TIMESTAMP WITH TIME ZONE
    USING CASE
        WHEN deleted_at IS NULL THEN NULL
        ELSE deleted_at AT TIME ZONE 'UTC'
    END
    """,
    """
    ALTER TABLE email_subjects
    ALTER COLUMN deleted_at TYPE TIMESTAMP WITH TIME ZONE
    USING CASE
        WHEN deleted_at IS NULL THEN NULL
        ELSE deleted_at AT TIME ZONE 'UTC'
    END
    """,
)


async def init_db(db_engine: AsyncEngine | None = None) -> None:
    eng = db_engine or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in _USER_SEND_COLUMNS:
            await conn.execute(text(stmt))
        for stmt in _SCHEMA_PATCHES:
            try:
                await conn.execute(text(stmt))
            except Exception:
                logger.debug("Schema patch skipped or already applied: %s", stmt)
    logger.info("Database tables created")
