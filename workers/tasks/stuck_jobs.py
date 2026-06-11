"""Stuck send job sweeper worker."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.stuck_jobs.sweep_stuck_jobs")
def sweep_stuck_jobs() -> dict:
    from app.services.db import session_scope
    from app.services.stuck_jobs_service import sweep_stuck_jobs as _sweep

    async def _run() -> dict:
        async with session_scope() as session:
            return await _sweep(session)

    result = run_async(_run())
    logger.info("stuck_jobs_sweeper", extra={"action": "stuck_jobs", **result})
    return result
