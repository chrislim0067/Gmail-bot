"""Send queue stats and scheduler tick."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import func, select

from app.config import get_settings
from app.dependencies import CurrentUser, DbSession
from app.models.lead import Lead
from app.models.send_job import SendJob
from app.models.sent_email import SentEmail
from app.schemas.analytics import QueueStats
from app.services.campaign_service import CampaignService
from app.services.pool_service import PoolService
from app.services.reset_service import reset_send_history
from app.services.sender_service import SenderService

router = APIRouter(tags=["queue"])
settings = get_settings()


@router.get("/queue/stats", response_model=QueueStats)
async def queue_stats(current_user: CurrentUser, db: DbSession):
    from app.models.campaign import Campaign

    campaigns_result = await db.execute(
        select(Campaign.id).where(Campaign.user_id == current_user.id)
    )
    campaign_ids = list(campaigns_result.scalars().all())
    if not campaign_ids:
        return QueueStats(pending=0, locked=0, failed=0, sent_today=0)

    pending = await db.execute(
        select(func.count(SendJob.id)).where(
            SendJob.campaign_id.in_(campaign_ids),
            SendJob.status == "pending",
        )
    )
    locked = await db.execute(
        select(func.count(SendJob.id)).where(
            SendJob.campaign_id.in_(campaign_ids),
            SendJob.status == "locked",
        )
    )
    failed = await db.execute(
        select(func.count(SendJob.id)).where(
            SendJob.campaign_id.in_(campaign_ids),
            SendJob.status == "failed",
        )
    )
    today = datetime.now(UTC).date()
    sent_today = await db.execute(
        select(func.count(SentEmail.id)).where(
            SentEmail.campaign_id.in_(campaign_ids),
            func.date(SentEmail.sent_at) == today,
        )
    )
    return QueueStats(
        pending=pending.scalar() or 0,
        locked=locked.scalar() or 0,
        failed=failed.scalar() or 0,
        sent_today=sent_today.scalar() or 0,
    )


@router.get("/queue/account-timeline")
async def account_send_timeline(current_user: CurrentUser, db: DbSession):
    """Per-account send cooldown timeline for live UI countdowns."""
    return await PoolService(db).list_account_send_timeline(current_user.id)


@router.post("/queue/reset-send-history")
async def reset_queue_send_history(current_user: CurrentUser, db: DbSession):
    """Clear all send history, pause campaigns, and reset account timers for retesting."""
    result = await reset_send_history(db, current_user.id)
    await db.commit()
    return result


@router.get("/campaigns/{campaign_id}/send-jobs")
async def list_send_jobs(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = (
        select(
            SendJob,
            Lead.email,
            Lead.first_name,
            Lead.last_name,
            SentEmail.sent_at,
            SentEmail.subject,
        )
        .join(Lead, Lead.id == SendJob.lead_id)
        .outerjoin(SentEmail, SentEmail.send_job_id == SendJob.id)
        .where(SendJob.campaign_id == campaign_id)
    )
    if status:
        query = query.where(SendJob.status == status)
    count_query = select(func.count()).select_from(
        select(SendJob.id).where(SendJob.campaign_id == campaign_id).subquery()
    )
    if status:
        count_query = select(func.count(SendJob.id)).where(
            SendJob.campaign_id == campaign_id, SendJob.status == status
        )
    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(
        query.order_by(func.coalesce(SentEmail.sent_at, SendJob.scheduled_at).desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = result.all()
    return {
        "items": [
            {
                "id": str(job.id),
                "campaign_id": str(job.campaign_id),
                "lead_id": str(job.lead_id),
                "lead_email": lead_email,
                "lead_name": " ".join(
                    part for part in (first_name, last_name) if part
                )
                or None,
                "subject": subject,
                "status": job.status,
                "scheduled_at": job.scheduled_at.isoformat(),
                "sent_at": sent_at.isoformat() if sent_at else None,
                "attempts": job.attempts,
                "error_message": job.last_error,
            }
            for job, lead_email, first_name, last_name, sent_at, subject in rows
        ],
        "page": page,
        "limit": limit,
        "total": total,
        "pages": max(1, (total + limit - 1) // limit),
    }


@router.post("/scheduler/tick")
async def scheduler_tick(
    db: DbSession,
    authorization: str | None = Header(None),
):
    if settings.service_token:
        if not authorization or authorization != f"Bearer {settings.service_token}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    from app.services.background_scheduler import run_scheduler_tick_once

    return await run_scheduler_tick_once()
