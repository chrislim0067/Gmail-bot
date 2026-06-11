"""Analytics daily rollup worker."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.rollups.run_hourly_rollup")
def run_hourly_rollup() -> dict:
    from app.services.analytics_service import run_hourly_rollup as _rollup
    from app.services.db import session_scope

    async def _run() -> dict:
        async with session_scope() as session:
            return await _rollup(session)

    result = run_async(_run())
    logger.info("analytics_rollup", extra={"action": "rollup", **result})
    return result
