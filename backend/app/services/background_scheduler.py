"""In-process scheduler loop — processes running campaigns without Celery."""

import asyncio
import logging

from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_factory
from app.models.campaign import Campaign
from app.services.campaign_service import CampaignService
from app.services.sender_service import SenderService
from app.services.stuck_jobs_service import sweep_stuck_jobs

logger = logging.getLogger(__name__)


async def run_scheduler_tick_once() -> dict:
    """Create send jobs and process one pending job per running campaign."""
    total_created = 0
    total_processed = 0
    stuck_reset = 0
    async with async_session_factory() as session:
        stuck = await sweep_stuck_jobs(session)
        stuck_reset = stuck.get("reset_count", 0)

        result = await session.execute(
            select(Campaign).where(
                Campaign.status == "running",
                Campaign.deleted_at.is_(None),
            )
        )
        sender = SenderService(session)
        campaign_svc = CampaignService(session)
        for campaign in result.scalars():
            total_created += await sender.create_send_jobs(campaign.id)
            proc = await sender.process_pending_jobs(campaign.id, limit=1)
            total_processed += proc["processed"]
            await campaign_svc.complete_if_finished(campaign)
        await session.commit()
    return {
        "jobs_created": total_created,
        "jobs_processed": total_processed,
        "stuck_jobs_reset": stuck_reset,
    }


async def background_scheduler_loop(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    interval = settings.scheduler_tick_interval_seconds
    logger.info("Background scheduler started (interval=%ss)", interval)

    while True:
        try:
            stats = await run_scheduler_tick_once()
            if stats["jobs_created"] or stats["jobs_processed"] or stats.get("stuck_jobs_reset"):
                logger.info(
                    "Scheduler tick: created=%s processed=%s stuck_reset=%s",
                    stats["jobs_created"],
                    stats["jobs_processed"],
                    stats.get("stuck_jobs_reset", 0),
                )
        except Exception:
            logger.exception("Background scheduler tick failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
            logger.info("Background scheduler stopped")
            return
        except asyncio.TimeoutError:
            continue
