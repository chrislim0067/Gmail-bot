"""Campaign scheduler — materialize send jobs for eligible leads."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.config import get_settings
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.send_job import SendJob
from app.services.lock_service import (
    acquire_lock,
    new_lock_token,
    release_lock,
    scheduler_lock_key,
)
from app.services.suppression_service import is_bounce_suppressed, is_unsubscribed


async def create_send_jobs(session, campaign_id: UUID) -> dict:
    settings = get_settings()
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None or campaign.deleted_at is not None:
        return {"jobs_created": 0, "reason": "campaign_not_found"}

    if campaign.status not in ("running", "scheduled"):
        return {"jobs_created": 0, "reason": f"campaign_status_{campaign.status}"}

    if campaign.status == "scheduled":
        if campaign.scheduled_start_at is None:
            return {"jobs_created": 0, "reason": "no_scheduled_start"}
        start_at = campaign.scheduled_start_at
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=UTC)
        if datetime.now(UTC) < start_at:
            return {"jobs_created": 0, "reason": "not_started_yet"}

    lock_key = scheduler_lock_key(str(campaign_id))
    token = new_lock_token()
    if not acquire_lock(lock_key, token, settings.lock_ttl_seconds):
        return {"jobs_created": 0, "reason": "scheduler_lock_held"}

    try:
        result = await session.execute(
            select(Lead).where(
                Lead.campaign_id == campaign_id,
                Lead.deleted_at.is_(None),
                Lead.status.in_(("pending", "queued")),
            )
        )
        leads = result.scalars().all()
        created = 0
        now = datetime.now(UTC)

        for lead in leads:
            if lead.validation_status not in ("valid", "pending"):
                lead.status = "skipped"
                lead.do_not_contact_reason = f"invalid:{lead.validation_status}"
                continue
            if await is_unsubscribed(session, campaign.user_id, lead.normalized_email):
                lead.status = "skipped"
                lead.do_not_contact_reason = "unsubscribed"
                continue
            if await is_bounce_suppressed(session, campaign.user_id, lead.normalized_email):
                lead.status = "skipped"
                lead.do_not_contact_reason = "hard_bounce"
                continue

            idempotency_key = f"{campaign_id}:{lead.id}"
            existing = await session.execute(
                select(SendJob.id).where(SendJob.idempotency_key == idempotency_key)
            )
            if existing.scalar_one_or_none():
                continue

            job = SendJob(
                campaign_id=campaign_id,
                lead_id=lead.id,
                status="pending",
                scheduled_at=now,
                idempotency_key=idempotency_key,
                created_at=now,
            )
            session.add(job)
            lead.status = "queued"
            created += 1

        if created and campaign.status == "scheduled":
            campaign.status = "running"

        return {"jobs_created": created, "reason": "ok"}
    finally:
        release_lock(lock_key, token)


async def find_runnable_campaigns(session) -> list[UUID]:
    now = datetime.now(UTC)
    result = await session.execute(
        select(Campaign.id).where(
            Campaign.deleted_at.is_(None),
            Campaign.status.in_(("running", "scheduled")),
        )
    )
    campaign_ids = list(result.scalars())
    runnable: list[UUID] = []
    for cid in campaign_ids:
        campaign = await session.get(Campaign, cid)
        if campaign is None:
            continue
        if campaign.status == "running":
            runnable.append(cid)
            continue
        if campaign.scheduled_start_at is None:
            continue
        start_at = campaign.scheduled_start_at
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=UTC)
        if now >= start_at:
            runnable.append(cid)
    return runnable


async def run_scheduler_tick(session) -> dict:
    from app.services.campaign_service import CampaignService
    from app.services.sender_service import SenderService
    from app.services.stuck_jobs_service import sweep_stuck_jobs

    stuck = await sweep_stuck_jobs(session)
    total_created = 0
    total_processed = 0
    campaigns_processed = 0
    sender = SenderService(session)
    campaign_svc = CampaignService(session)
    for campaign_id in await find_runnable_campaigns(session):
        result = await create_send_jobs(session, campaign_id)
        total_created += result.get("jobs_created", 0)
        proc = await sender.process_pending_jobs(campaign_id, limit=1)
        total_processed += proc["processed"]
        campaign = await session.get(Campaign, campaign_id)
        if campaign:
            await campaign_svc.complete_if_finished(campaign)
        campaigns_processed += 1
    return {
        "campaigns_processed": campaigns_processed,
        "jobs_created": total_created,
        "jobs_processed": total_processed,
        "stuck_jobs_reset": stuck.get("reset_count", 0),
    }
