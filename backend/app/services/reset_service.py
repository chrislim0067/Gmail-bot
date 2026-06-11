"""Reset send history for retesting campaigns."""

from uuid import UUID

from sqlalchemy import delete, select, update

from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccount
from app.models.lead import Lead
from app.models.reply_event import ReplyEvent
from app.models.send_job import SendJob
from app.models.send_job_dlq import SendJobDlq
from app.models.sent_email import SentEmail
from app.utils.redis_client import create_async_redis


async def reset_send_history(
    session,
    user_id: UUID,
    *,
    campaign_id: UUID | None = None,
) -> dict:
    """Pause campaigns, wipe sends/jobs, clear account timers and Redis limits."""
    campaign_query = select(Campaign).where(
        Campaign.user_id == user_id,
        Campaign.deleted_at.is_(None),
    )
    if campaign_id:
        campaign_query = campaign_query.where(Campaign.id == campaign_id)
    result = await session.execute(campaign_query)
    campaigns = list(result.scalars().all())
    if not campaigns:
        return {"campaigns_reset": 0, "reason": "no_campaigns"}

    campaign_ids = [c.id for c in campaigns]

    for campaign in campaigns:
        if campaign.status == "running":
            campaign.status = "paused"
    await session.flush()

    sent_result = await session.execute(
        select(SentEmail.id).where(SentEmail.campaign_id.in_(campaign_ids))
    )
    sent_ids = list(sent_result.scalars())
    if sent_ids:
        await session.execute(
            delete(ReplyEvent).where(ReplyEvent.sent_email_id.in_(sent_ids))
        )

    await session.execute(
        delete(SentEmail).where(SentEmail.campaign_id.in_(campaign_ids))
    )

    job_result = await session.execute(
        select(SendJob.id).where(SendJob.campaign_id.in_(campaign_ids))
    )
    job_ids = list(job_result.scalars())
    if job_ids:
        await session.execute(
            delete(SendJobDlq).where(SendJobDlq.send_job_id.in_(job_ids))
        )
    await session.execute(delete(SendJob).where(SendJob.campaign_id.in_(campaign_ids)))

    await session.execute(
        update(Lead)
        .where(
            Lead.campaign_id.in_(campaign_ids),
            Lead.deleted_at.is_(None),
            Lead.status.notin_(["unsubscribed", "skipped"]),
        )
        .values(status="pending", last_contacted_at=None)
    )

    await session.execute(
        update(Campaign)
        .where(Campaign.id.in_(campaign_ids))
        .values(sent_count=0, replied_count=0, status="paused")
    )

    await session.execute(
        update(GmailAccount)
        .where(
            GmailAccount.user_id == user_id,
            GmailAccount.deleted_at.is_(None),
        )
        .values(last_send_at=None, lifetime_send_count=0)
    )

    redis_cleared = await _clear_redis_limits()

    await session.flush()

    return {
        "campaigns_reset": len(campaign_ids),
        "campaigns_paused": len(campaign_ids),
        "redis_keys_cleared": redis_cleared,
        "reason": "ok",
    }


async def _clear_redis_limits() -> int:
    client = create_async_redis()
    cleared = 0
    for pattern in ("rate:*", "lock:*"):
        async for key in client.scan_iter(match=pattern):
            await client.delete(key)
            cleared += 1
    return cleared
