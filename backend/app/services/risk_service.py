"""Global risk budget tracking and acknowledgment."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.campaign import Campaign
from app.models.risk_budget_event import RiskBudgetEvent
from app.models.user import User

RISK_DELTAS = {
    "quota_error": 30,
    "auth_error": 50,
    "bounce_spike": 40,
    "high_failure_rate": 30,
    "manual_warning": 20,
}


class RiskService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    async def record_event(
        self,
        *,
        user_id: UUID,
        event_type: str,
        severity: str = "medium",
        score_delta: int | None = None,
        gmail_account_id: UUID | None = None,
        campaign_id: UUID | None = None,
        pool_id: UUID | None = None,
        details: dict | None = None,
    ) -> dict:
        delta = score_delta if score_delta is not None else RISK_DELTAS.get(event_type, 20)
        event = RiskBudgetEvent(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            gmail_account_id=gmail_account_id,
            campaign_id=campaign_id,
            pool_id=pool_id,
            score_delta=delta,
            details=details or {},
            created_at=datetime.now(UTC),
        )
        self.db.add(event)

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.global_risk_score += delta
        threshold_exceeded = user.global_risk_score >= self.settings.global_risk_score_threshold
        if threshold_exceeded:
            user.risk_review_required = True
        await self.db.flush()
        return {
            "new_score": user.global_risk_score,
            "threshold_exceeded": threshold_exceeded,
            "event_id": event.id,
        }

    async def is_risk_blocked(self, user_id: UUID) -> bool:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return True
        return (
            user.risk_review_required
            or user.global_risk_score >= self.settings.global_risk_score_threshold
        )

    async def get_overview(self, user_id: UUID) -> dict:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        since = datetime.now(UTC) - timedelta(days=7)
        events_result = await self.db.execute(
            select(func.count(RiskBudgetEvent.id)).where(
                RiskBudgetEvent.user_id == user_id,
                RiskBudgetEvent.created_at >= since,
            )
        )
        paused_result = await self.db.execute(
            select(func.count(Campaign.id)).where(
                Campaign.user_id == user_id,
                Campaign.status == "paused",
            )
        )
        return {
            "global_risk_score": user.global_risk_score,
            "threshold": self.settings.global_risk_score_threshold,
            "review_required": user.risk_review_required,
            "recent_events_count": events_result.scalar() or 0,
            "paused_campaigns": paused_result.scalar() or 0,
        }

    async def acknowledge(
        self,
        user_id: UUID,
        *,
        event_ids: list[UUID] | None = None,
        acknowledge_all: bool = False,
        notes: str | None = None,
    ) -> User:
        now = datetime.now(UTC)
        if acknowledge_all:
            await self.db.execute(
                update(RiskBudgetEvent)
                .where(
                    RiskBudgetEvent.user_id == user_id,
                    RiskBudgetEvent.acknowledged_at.is_(None),
                )
                .values(acknowledged_at=now)
            )
        elif event_ids:
            await self.db.execute(
                update(RiskBudgetEvent)
                .where(
                    RiskBudgetEvent.user_id == user_id,
                    RiskBudgetEvent.id.in_(event_ids),
                )
                .values(acknowledged_at=now)
            )

        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        user.risk_review_required = False
        user.global_risk_score = max(
            0,
            user.global_risk_score - self.settings.global_risk_score_threshold // 2,
        )
        if notes:
            await self.record_event(
                user_id=user_id,
                event_type="manual_acknowledge",
                severity="low",
                score_delta=0,
                details={"notes": notes},
            )
        await self.db.flush()
        return user


async def record_risk_event(session: AsyncSession, user_id: UUID, event_type: str, **kwargs) -> dict:
    return await RiskService(session).record_event(
        user_id=user_id, event_type=event_type, **kwargs
    )
