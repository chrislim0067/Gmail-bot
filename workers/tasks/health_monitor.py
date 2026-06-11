"""Account health monitor worker."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.health_monitor.run_health_monitor_all")
def run_health_monitor_all() -> dict:
    from app.services.db import session_scope
    from app.services.health_service import monitor_all_accounts

    async def _run() -> dict:
        async with session_scope() as session:
            return await monitor_all_accounts(session)

    result = run_async(_run())
    logger.info("health_monitor", extra={"action": "health_monitor", **result})
    return result
