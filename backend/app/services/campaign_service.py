"""Campaign CRUD and lifecycle management."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.send_job import SendJob
from app.services.audit_service import AuditService
from app.services.preflight_service import PreflightService
from app.services.risk_service import RiskService


class CampaignServiceError(Exception):
    pass


class CampaignService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.preflight = PreflightService(db)
        self.risk = RiskService(db)

    async def get_campaign(self, campaign_id: UUID, user_id: UUID) -> Campaign | None:
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.user_id == user_id,
                Campaign.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID, data: dict) -> Campaign:
        campaign = Campaign(user_id=user_id, **data)
        self.db.add(campaign)
        await self.db.flush()
        await self.audit.log(
            action="campaign.create",
            resource_type="campaign",
            user_id=user_id,
            resource_id=campaign.id,
        )
        return campaign

    async def update(self, campaign: Campaign, data: dict) -> Campaign:
        if campaign.status not in ("draft", "paused"):
            raise CampaignServiceError("Can only update draft or paused campaigns")
        for key, value in data.items():
            if value is not None:
                setattr(campaign, key, value)
        await self.db.flush()
        return campaign

    async def soft_delete(self, campaign: Campaign) -> None:
        campaign.deleted_at = datetime.now(UTC)
        campaign.status = "cancelled"
        await self.db.execute(
            update(SendJob)
            .where(
                SendJob.campaign_id == campaign.id,
                SendJob.status.in_(["pending", "locked"]),
            )
            .values(status="cancelled")
        )
        await self.audit.log(
            action="campaign.delete",
            resource_type="campaign",
            user_id=campaign.user_id,
            resource_id=campaign.id,
        )

    async def start(self, campaign: Campaign) -> Campaign:
        if campaign.status == "paused":
            return await self.resume(campaign)

        if await self.risk.is_risk_blocked(campaign.user_id):
            raise CampaignServiceError("Global risk budget exceeded")

        preflight = await self.preflight.run(campaign.id)
        if not preflight["passed"]:
            raise CampaignServiceError("Campaign preflight check failed")

        now = datetime.now(UTC)
        if campaign.scheduled_start_at and campaign.scheduled_start_at > now:
            campaign.status = "scheduled"
        else:
            campaign.status = "running"
        await self.audit.log(
            action="campaign.start",
            resource_type="campaign",
            user_id=campaign.user_id,
            resource_id=campaign.id,
        )
        await self.db.flush()
        return campaign

    async def pause(self, campaign: Campaign, reason: str = "manual") -> Campaign:
        campaign.status = "paused"
        campaign.paused_reason = reason
        await self.db.execute(
            update(SendJob)
            .where(
                SendJob.campaign_id == campaign.id,
                SendJob.status.in_(["pending", "locked"]),
            )
            .values(status="cancelled")
        )
        await self.audit.log(
            action="campaign.pause",
            resource_type="campaign",
            user_id=campaign.user_id,
            resource_id=campaign.id,
            metadata={"reason": reason},
        )
        await self.db.flush()
        return campaign

    async def resume(self, campaign: Campaign) -> Campaign:
        if await self.risk.is_risk_blocked(campaign.user_id):
            raise CampaignServiceError("Global risk budget exceeded")
        if not campaign.preflight_passed_at:
            raise CampaignServiceError("Preflight must pass before resume")
        campaign.status = "running"
        campaign.paused_reason = None
        await self.audit.log(
            action="campaign.resume",
            resource_type="campaign",
            user_id=campaign.user_id,
            resource_id=campaign.id,
        )
        await self.db.flush()
        return campaign

    async def has_remaining_sends(self, campaign_id: UUID) -> bool:
        await self.reconcile_stuck_leads(campaign_id)
        stats = await self.get_lead_stats(campaign_id)
        if stats["pending"] + stats["queued"] > 0:
            return True
        pending_jobs = await self.db.execute(
            select(func.count(SendJob.id)).where(
                SendJob.campaign_id == campaign_id,
                SendJob.status.in_(["pending", "locked"]),
            )
        )
        return (pending_jobs.scalar() or 0) > 0

    async def reconcile_stuck_leads(self, campaign_id: UUID) -> None:
        """Align lead rows with terminal send jobs so completion can proceed."""
        result = await self.db.execute(
            select(Lead).where(
                Lead.campaign_id == campaign_id,
                Lead.deleted_at.is_(None),
                Lead.status.in_(["pending", "queued"]),
            )
        )
        changed = False
        for lead in result.scalars():
            if lead.validation_status not in ("valid", "pending"):
                lead.status = "skipped"
                lead.do_not_contact_reason = f"invalid:{lead.validation_status}"
                changed = True
                continue

            job_result = await self.db.execute(
                select(SendJob)
                .where(
                    SendJob.lead_id == lead.id,
                    SendJob.campaign_id == campaign_id,
                )
                .order_by(SendJob.created_at.desc())
                .limit(1)
            )
            job = job_result.scalar_one_or_none()
            if job is None:
                continue
            if job.status == "failed" and lead.status == "queued":
                lead.status = "failed"
                changed = True
            elif job.status == "sent" and lead.status == "queued":
                lead.status = "sent"
                changed = True
        if changed:
            await self.db.flush()

    async def complete(self, campaign: Campaign, reason: str = "all_leads_sent") -> Campaign:
        campaign.status = "completed"
        campaign.paused_reason = reason
        await self.db.execute(
            update(SendJob)
            .where(
                SendJob.campaign_id == campaign.id,
                SendJob.status.in_(["pending", "locked"]),
            )
            .values(status="cancelled")
        )
        await self.audit.log(
            action="campaign.complete",
            resource_type="campaign",
            user_id=campaign.user_id,
            resource_id=campaign.id,
            metadata={"reason": reason},
        )
        await self.db.flush()
        return campaign

    async def complete_if_finished(self, campaign: Campaign) -> bool:
        """Mark a running campaign completed when every lead has been emailed."""
        if campaign.status != "running":
            return False
        if await self.has_remaining_sends(campaign.id):
            return False
        await self.complete(campaign)
        return True

    async def get_lead_stats(self, campaign_id: UUID) -> dict:
        result = await self.db.execute(
            select(Lead.status, func.count())
            .where(Lead.campaign_id == campaign_id, Lead.deleted_at.is_(None))
            .group_by(Lead.status)
        )
        counts = {row[0]: row[1] for row in result.all()}
        failed_jobs = await self.db.execute(
            select(func.count(SendJob.id)).where(
                SendJob.campaign_id == campaign_id,
                SendJob.status == "failed",
            )
        )
        return {
            "total_leads": sum(counts.values()),
            "pending": counts.get("pending", 0),
            "queued": counts.get("queued", 0),
            "sent": counts.get("sent", 0) + counts.get("replied", 0),
            "replied": counts.get("replied", 0),
            "bounced": counts.get("bounced", 0),
            "unsubscribed": counts.get("unsubscribed", 0),
            "failed": failed_jobs.scalar() or 0,
            "skipped": counts.get("skipped", 0),
        }
