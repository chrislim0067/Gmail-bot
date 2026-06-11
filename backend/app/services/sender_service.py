"""Send job materialization and mock sender worker logic."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.gmail.client import get_gmail_client
from app.gmail.message_builder import build_mime_message
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.send_job import SendJob
from app.models.sent_email import SentEmail
from app.services.pool_service import PoolService
from app.services.rate_limit_service import RateLimitService
from app.services.redis_lock_service import RedisLockService
from app.services.risk_service import RiskService
from app.services.suppression_service import SuppressionService
from app.services.send_settings_service import get_send_timing_settings
from app.services.outreach_compose_service import (
    OutreachComposeError,
    OutreachComposeService,
)
from app.services.token_service import TokenService
from app.services.campaign_service import CampaignService
from app.utils.jwt_unsubscribe import create_unsubscribe_token
from app.utils.send_window import is_within_send_window, next_send_window_start


class SenderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.locks = RedisLockService()
        self.rate_limit = RateLimitService()
        self.pool = PoolService(db)
        self.suppression = SuppressionService(db)
        self.compose = OutreachComposeService(db)
        self.risk = RiskService(db)
        self.token_service = TokenService(db)

    async def create_send_jobs(self, campaign_id: UUID) -> int:
        acquired, lock_token = await self.locks.acquire_scheduler_lock(str(campaign_id))
        if not acquired:
            return 0
        try:
            result = await self.db.execute(
                select(Campaign).where(Campaign.id == campaign_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign or campaign.status != "running":
                return 0
            if await self.risk.is_risk_blocked(campaign.user_id):
                return 0

            leads_result = await self.db.execute(
                select(Lead).where(
                    Lead.campaign_id == campaign_id,
                    Lead.deleted_at.is_(None),
                    Lead.validation_status.in_(("valid", "pending")),
                    Lead.status.in_(["pending", "queued"]),
                )
            )
            count = 0
            now = datetime.now(UTC)
            for lead in leads_result.scalars():
                if lead.validation_status not in ("valid", "pending"):
                    lead.status = "skipped"
                    lead.do_not_contact_reason = f"invalid:{lead.validation_status}"
                    continue
                suppressed, reason = await self.suppression.is_suppressed(
                    campaign.user_id, lead.email
                )
                if suppressed:
                    lead.status = "skipped"
                    lead.do_not_contact_reason = reason or "suppressed"
                    continue
                idempotency_key = f"{campaign_id}:{lead.id}"
                existing = await self.db.execute(
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
                )
                self.db.add(job)
                lead.status = "queued"
                count += 1
            await self.db.flush()
            return count
        finally:
            if lock_token:
                await self.locks.release("campaign_scheduler", str(campaign_id), lock_token)

    async def process_pending_jobs(
        self, campaign_id: UUID, *, limit: int = 1
    ) -> dict:
        """Process pending send jobs one at a time to stagger account usage."""
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(SendJob.id)
            .where(
                SendJob.campaign_id == campaign_id,
                SendJob.status == "pending",
                SendJob.scheduled_at <= now,
            )
            .order_by(SendJob.scheduled_at)
            .limit(limit)
        )
        job_ids = list(result.scalars())
        outcomes: dict[str, int] = {}
        for job_id in job_ids:
            res = await self.process_send_job(job_id, worker_id="api")
            status = res.get("status", "unknown")
            outcomes[status] = outcomes.get(status, 0) + 1
        await self._maybe_finish_campaign(campaign_id)
        return {"processed": len(job_ids), "outcomes": outcomes}

    async def _maybe_finish_campaign(self, campaign_id: UUID) -> None:
        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            await CampaignService(self.db).complete_if_finished(campaign)

    async def process_send_job(self, job_id: UUID, worker_id: str = "worker") -> dict:
        result = await self.db.execute(select(SendJob).where(SendJob.id == job_id))
        job = result.scalar_one_or_none()
        if not job or job.status not in ("pending", "locked"):
            return {"status": "skipped"}

        campaign_result = await self.db.execute(
            select(Campaign).where(Campaign.id == job.campaign_id)
        )
        campaign = campaign_result.scalar_one()
        if campaign.status != "running":
            return {"status": "skipped", "reason": "campaign_not_running"}

        now = datetime.now(UTC)
        if not is_within_send_window(campaign, now):
            job.scheduled_at = next_send_window_start(campaign, now)
            await self.db.flush()
            return {"status": "rescheduled", "reason": "outside_send_window"}

        timing = await get_send_timing_settings(self.db, campaign.user_id)
        rate_limit = RateLimitService(timing=timing)

        account, retry_after = await self.pool.select_available_account(
            campaign.campaign_account_pool_id
        )
        pool_id = campaign.campaign_account_pool_id
        pool_acquired, pool_lock_token = await self.locks.acquire(
            "pool_send", str(pool_id), worker_id=worker_id, ttl_seconds=120
        )
        if not pool_acquired:
            job.scheduled_at = datetime.now(UTC) + timedelta(seconds=15)
            await self.db.flush()
            return {"status": "rescheduled", "reason": "pool_lock_held"}

        if not account:
            if pool_lock_token:
                await self.locks.release("pool_send", str(pool_id), pool_lock_token)
            next_pool_at = await rate_limit.get_pool_next_send_at(pool_id)
            now = datetime.now(UTC)
            if next_pool_at and next_pool_at > now:
                job.scheduled_at = next_pool_at
                await self._defer_pending_jobs_for_pool(campaign.id, pool_id)
            else:
                wait_seconds = max(30, retry_after or 300)
                job.scheduled_at = now + timedelta(seconds=wait_seconds)
            await self.db.flush()
            return {
                "status": "rescheduled",
                "reason": "no_account",
                "retry_after_seconds": max(
                    0, int((job.scheduled_at - now).total_seconds())
                ),
            }

        acquired, lock_token = await self.locks.acquire_gmail_account_lock(
            str(account.id), worker_id=worker_id
        )
        if not acquired:
            if pool_lock_token:
                await self.locks.release("pool_send", str(pool_id), pool_lock_token)
            job.scheduled_at = datetime.now(UTC) + timedelta(seconds=45)
            await self.db.flush()
            return {"status": "rescheduled", "reason": "lock_held"}

        try:
            job.status = "locked"
            job.locked_at = datetime.now(UTC)
            job.gmail_account_id = account.id
            job.lock_token = lock_token
            job.worker_id = worker_id
            job.lock_expires_at = datetime.now(UTC) + timedelta(minutes=10)
            job.client_send_id = job.client_send_id or uuid4()
            await self.db.flush()

            lead_result = await self.db.execute(select(Lead).where(Lead.id == job.lead_id))
            lead = lead_result.scalar_one()
            unsub_token = create_unsubscribe_token(
                user_id=campaign.user_id,
                campaign_id=campaign.id,
                lead_id=lead.id,
                email=lead.email,
            )
            unsub_url = f"/api/v1/unsubscribe/{unsub_token}"
            try:
                rendered = await self.compose.compose_for_lead(
                    campaign.user_id,
                    lead,
                    unsub_url,
                )
            except OutreachComposeError as exc:
                job.status = "failed"
                job.last_error = str(exc)
                lead.status = "failed"
                await self.db.flush()
                return {"status": "failed", "error": str(exc)}

            await self.token_service.refresh_access_token(account.id)
            client = get_gmail_client()
            mime_msg = build_mime_message(
                to=lead.email,
                from_email=account.email,
                subject=rendered["subject"],
                html_body=rendered["html"],
                text_body=rendered.get("text"),
                unsubscribe_url=unsub_url,
            )
            response = await client.send_message(account.id, mime_msg)

            now = datetime.now(UTC)
            sent = SentEmail(
                send_job_id=job.id,
                campaign_id=campaign.id,
                lead_id=lead.id,
                gmail_account_id=account.id,
                gmail_message_id=response.get("gmail_message_id"),
                rfc_message_id=response.get("rfc_message_id"),
                thread_id=response.get("thread_id"),
                recipient_email=lead.email,
                subject=rendered["subject"],
                sent_at=now,
            )
            self.db.add(sent)
            job.status = "sent"
            lead.status = "sent"
            lead.last_contacted_at = now
            campaign.sent_count += 1
            account.last_send_at = now
            account.lifetime_send_count += 1
            account.consecutive_failure_count = 0
            await rate_limit.record_account_send(account.id, sent_at=now)
            await rate_limit.record_pool_send(
                campaign.campaign_account_pool_id, sent_at=now
            )
            await rate_limit.record_pool_stagger(campaign.campaign_account_pool_id)
            await rate_limit.record_global_send(campaign.user_id)
            await self._defer_pending_jobs_for_pool(campaign.id, campaign.campaign_account_pool_id)
            await self.db.flush()
            return {"status": "sent", "gmail_message_id": response.get("gmail_message_id")}
        except Exception as exc:
            job.attempts += 1
            job.last_error = str(exc)
            if job.attempts >= 2:
                job.status = "failed"
                lead_result = await self.db.execute(
                    select(Lead).where(Lead.id == job.lead_id)
                )
                failed_lead = lead_result.scalar_one_or_none()
                if failed_lead:
                    failed_lead.status = "failed"
            else:
                job.status = "pending"
                job.scheduled_at = datetime.now(UTC) + timedelta(minutes=30)
            account.consecutive_failure_count += 1
            await self.db.flush()
            return {"status": "failed", "error": str(exc)}
        finally:
            if lock_token:
                await self.locks.release("gmail_account", str(account.id), lock_token)
            if pool_lock_token:
                await self.locks.release("pool_send", str(pool_id), pool_lock_token)

    async def _defer_pending_jobs_for_pool(
        self, campaign_id: UUID, pool_id: UUID
    ) -> None:
        """Push pending jobs back until the pool stagger window clears."""
        next_at = await self.rate_limit.get_pool_next_send_at(pool_id)
        if not next_at:
            return
        now = datetime.now(UTC)
        if next_at <= now:
            return
        await self.db.execute(
            update(SendJob)
            .where(
                SendJob.campaign_id == campaign_id,
                SendJob.status == "pending",
                SendJob.scheduled_at < next_at,
            )
            .values(scheduled_at=next_at)
        )
