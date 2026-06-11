"""Analytics from daily rollups and live aggregates."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics_daily_rollup import AnalyticsDailyRollup
from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccount
from app.models.lead import Lead
from app.models.sent_email import SentEmail
from app.models.unsubscribe import UnsubscribeList


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_overview(
        self,
        user_id: UUID,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict:
        query = select(
            func.coalesce(func.sum(AnalyticsDailyRollup.sent_count), 0),
            func.coalesce(func.sum(AnalyticsDailyRollup.replied_count), 0),
            func.coalesce(func.sum(AnalyticsDailyRollup.bounced_count), 0),
            func.coalesce(func.sum(AnalyticsDailyRollup.unsubscribed_count), 0),
        ).where(
            AnalyticsDailyRollup.user_id == user_id,
            AnalyticsDailyRollup.campaign_id.is_(None),
        )
        if from_date:
            query = query.where(AnalyticsDailyRollup.rollup_date >= from_date)
        if to_date:
            query = query.where(AnalyticsDailyRollup.rollup_date <= to_date)

        result = await self.db.execute(query)
        sent, replied, bounced, unsubscribed = result.one()

        if sent == 0:
            return await self._live_overview(user_id)

        reply_rate = replied / sent if sent else 0.0
        bounce_rate = bounced / sent if sent else 0.0
        return {
            "sent": int(sent),
            "replied": int(replied),
            "bounced": int(bounced),
            "unsubscribed": int(unsubscribed),
            "reply_rate": round(reply_rate, 4),
            "bounce_rate": round(bounce_rate, 4),
        }

    async def _live_overview(self, user_id: UUID) -> dict:
        campaigns_result = await self.db.execute(
            select(Campaign.id).where(Campaign.user_id == user_id)
        )
        campaign_ids = list(campaigns_result.scalars().all())
        if not campaign_ids:
            return {
                "sent": 0, "replied": 0, "bounced": 0,
                "unsubscribed": 0, "reply_rate": 0.0, "bounce_rate": 0.0,
            }

        sent_result = await self.db.execute(
            select(func.count(SentEmail.id)).where(
                SentEmail.campaign_id.in_(campaign_ids)
            )
        )
        sent = sent_result.scalar() or 0
        replied_result = await self.db.execute(
            select(func.count(Lead.id)).where(
                Lead.campaign_id.in_(campaign_ids),
                Lead.status == "replied",
            )
        )
        replied = replied_result.scalar() or 0
        bounced_result = await self.db.execute(
            select(func.count(Lead.id)).where(
                Lead.campaign_id.in_(campaign_ids),
                Lead.status == "bounced",
            )
        )
        bounced = bounced_result.scalar() or 0
        unsub_result = await self.db.execute(
            select(func.count(Lead.id)).where(
                Lead.campaign_id.in_(campaign_ids),
                Lead.status == "unsubscribed",
            )
        )
        unsubscribed = unsub_result.scalar() or 0
        return {
            "sent": sent,
            "replied": replied,
            "bounced": bounced,
            "unsubscribed": unsubscribed,
            "reply_rate": round(replied / sent, 4) if sent else 0.0,
            "bounce_rate": round(bounced / sent, 4) if sent else 0.0,
        }

    async def get_campaign_analytics(self, campaign_id: UUID) -> dict:
        status_result = await self.db.execute(
            select(Lead.status, func.count(Lead.id))
            .where(Lead.campaign_id == campaign_id, Lead.deleted_at.is_(None))
            .group_by(Lead.status)
        )
        funnel = {row[0]: row[1] for row in status_result.all()}
        for key in (
            "pending", "queued", "sent", "replied", "bounced",
            "unsubscribed", "skipped", "failed",
        ):
            funnel.setdefault(key, 0)

        daily_result = await self.db.execute(
            select(AnalyticsDailyRollup)
            .where(AnalyticsDailyRollup.campaign_id == campaign_id)
            .order_by(AnalyticsDailyRollup.rollup_date)
        )
        daily_breakdown = [
            {
                "date": r.rollup_date,
                "sent": r.sent_count,
                "replied": r.replied_count,
                "bounced": r.bounced_count,
                "unsubscribed": r.unsubscribed_count,
            }
            for r in daily_result.scalars()
        ]

        account_result = await self.db.execute(
            select(
                SentEmail.gmail_account_id,
                func.count(SentEmail.id),
            )
            .where(SentEmail.campaign_id == campaign_id)
            .group_by(SentEmail.gmail_account_id)
        )
        account_breakdown = []
        for account_id, count in account_result.all():
            acc_result = await self.db.execute(
                select(GmailAccount.email).where(GmailAccount.id == account_id)
            )
            email = acc_result.scalar_one_or_none() or ""
            account_breakdown.append({
                "gmail_account_id": account_id,
                "email": email,
                "sent": count,
                "replied": 0,
                "bounced": 0,
            })

        return {
            "funnel": funnel,
            "daily_breakdown": daily_breakdown,
            "account_breakdown": account_breakdown,
        }


async def rollup_daily_for_user(
    session: AsyncSession,
    user_id: UUID,
    rollup_date: date | None = None,
) -> dict:
    if rollup_date is None:
        rollup_date = (datetime.now(UTC) - timedelta(days=1)).date()

    day_start = datetime.combine(rollup_date, datetime.min.time()).replace(tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    campaigns_result = await session.execute(
        select(Campaign.id).where(
            Campaign.user_id == user_id,
            Campaign.deleted_at.is_(None),
        )
    )
    campaign_ids = list(campaigns_result.scalars())
    rollups_written = 0

    for campaign_id in campaign_ids:
        sent = await session.execute(
            select(func.count())
            .select_from(SentEmail)
            .where(
                SentEmail.campaign_id == campaign_id,
                SentEmail.sent_at >= day_start,
                SentEmail.sent_at < day_end,
            )
        )
        sent_count = int(sent.scalar_one())

        bounced = await session.execute(
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.campaign_id == campaign_id,
                Lead.status == "bounced",
                Lead.updated_at >= day_start,
                Lead.updated_at < day_end,
            )
        )
        bounced_count = int(bounced.scalar_one())

        replied = await session.execute(
            select(func.count())
            .select_from(Lead)
            .where(
                Lead.campaign_id == campaign_id,
                Lead.status == "replied",
                Lead.updated_at >= day_start,
                Lead.updated_at < day_end,
            )
        )
        replied_count = int(replied.scalar_one())

        unsub = await session.execute(
            select(func.count())
            .select_from(UnsubscribeList)
            .where(
                UnsubscribeList.user_id == user_id,
                UnsubscribeList.campaign_id == campaign_id,
                UnsubscribeList.unsubscribed_at >= day_start,
                UnsubscribeList.unsubscribed_at < day_end,
            )
        )
        unsub_count = int(unsub.scalar_one())

        existing = await session.execute(
            select(AnalyticsDailyRollup).where(
                AnalyticsDailyRollup.user_id == user_id,
                AnalyticsDailyRollup.campaign_id == campaign_id,
                AnalyticsDailyRollup.rollup_date == rollup_date,
            )
        )
        rollup = existing.scalar_one_or_none()
        if rollup is None:
            rollup = AnalyticsDailyRollup(
                user_id=user_id,
                campaign_id=campaign_id,
                rollup_date=rollup_date,
            )
            session.add(rollup)

        rollup.sent_count = sent_count
        rollup.bounced_count = bounced_count
        rollup.replied_count = replied_count
        rollup.unsubscribed_count = unsub_count
        rollups_written += 1

    return {"rollups_written": rollups_written, "rollup_date": str(rollup_date)}
