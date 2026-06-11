"""Campaign preflight worker."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.preflight.run_preflight")
def run_preflight(campaign_id: str) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.preflight_service import run_campaign_preflight

    async def _run() -> dict:
        async with session_scope() as session:
            return await run_campaign_preflight(session, UUID(campaign_id))

    result = run_async(_run())
    logger.info(
        "preflight",
        extra={"campaign_id": campaign_id, "action": "preflight", **result},
    )
    return result
