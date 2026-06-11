"""Scheduler worker — create_send_jobs with scheduler lock."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.scheduler.run_scheduler_tick")
def run_scheduler_tick() -> dict:
    from app.services.db import session_scope
    from app.services.scheduler_service import run_scheduler_tick as _run_tick

    async def _run() -> dict:
        async with session_scope() as session:
            return await _run_tick(session)

    result = run_async(_run())
    logger.info("scheduler_tick", extra={"action": "scheduler_tick", **result})
    return result


@app.task(name="workers.tasks.scheduler.create_send_jobs")
def create_send_jobs(campaign_id: str) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.scheduler_service import create_send_jobs as _create

    async def _run() -> dict:
        async with session_scope() as session:
            return await _create(session, UUID(campaign_id))

    result = run_async(_run())
    logger.info(
        "create_send_jobs",
        extra={"campaign_id": campaign_id, "action": "create_send_jobs", **result},
    )
    return result
