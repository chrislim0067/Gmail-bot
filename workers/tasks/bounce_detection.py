"""Bounce detection worker — multi-signal parser."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.bounce_detection.detect_bounces_for_account")
def detect_bounces_for_account(gmail_account_id: str) -> dict:
    from uuid import UUID

    from app.services.bounce_service import detect_bounces
    from app.services.db import session_scope

    async def _run() -> dict:
        async with session_scope() as session:
            return await detect_bounces(session, UUID(gmail_account_id))

    result = run_async(_run())
    logger.info(
        "bounce_detection",
        extra={"account_id": gmail_account_id, "action": "bounce_detection", **result},
    )
    return result
