"""Global suppression for unsubscribes and bounces."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bounce_event import BounceEvent
from app.models.unsubscribe import UnsubscribeList
from app.utils.tier_caps import normalize_email


class SuppressionService:
    SOFT_BOUNCE_STRIKE_LIMIT = 3

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def is_unsubscribed(self, user_id: UUID, email: str) -> bool:
        normalized = normalize_email(email)
        result = await self.db.execute(
            select(UnsubscribeList.id).where(
                UnsubscribeList.user_id == user_id,
                UnsubscribeList.email == normalized,
            )
        )
        return result.scalar_one_or_none() is not None

    async def is_bounce_suppressed(self, user_id: UUID, email: str) -> bool:
        normalized = normalize_email(email)
        hard = await self.db.execute(
            select(BounceEvent.id).where(
                BounceEvent.bounced_email == normalized,
                BounceEvent.bounce_type == "hard",
            ).limit(1)
        )
        if hard.scalar_one_or_none():
            return True

        soft_count_result = await self.db.execute(
            select(func.count(BounceEvent.id)).where(
                BounceEvent.bounced_email == normalized,
                BounceEvent.bounce_type == "soft",
            )
        )
        soft_count = soft_count_result.scalar() or 0
        return soft_count >= self.SOFT_BOUNCE_STRIKE_LIMIT

    async def is_suppressed(self, user_id: UUID, email: str) -> tuple[bool, str | None]:
        if await self.is_unsubscribed(user_id, email):
            return True, "unsubscribed"
        if await self.is_bounce_suppressed(user_id, email):
            return True, "bounced"
        return False, None

    async def add_unsubscribe(
        self,
        *,
        user_id: UUID,
        email: str,
        source: str,
        campaign_id: UUID | None = None,
        ip_address: str | None = None,
    ) -> UnsubscribeList:
        normalized = normalize_email(email)
        existing = await self.db.execute(
            select(UnsubscribeList).where(
                UnsubscribeList.user_id == user_id,
                UnsubscribeList.email == normalized,
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row
        entry = UnsubscribeList(
            user_id=user_id,
            email=normalized,
            source=source,
            campaign_id=campaign_id,
            unsubscribed_at=datetime.now(UTC),
            ip_address=ip_address,
        )
        self.db.add(entry)
        await self.db.flush()
        return entry

    async def remove_unsubscribe(self, user_id: UUID, entry_id: UUID) -> bool:
        result = await self.db.execute(
            select(UnsubscribeList).where(
                UnsubscribeList.id == entry_id,
                UnsubscribeList.user_id == user_id,
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            return False
        await self.db.delete(entry)
        await self.db.flush()
        return True


async def is_unsubscribed(session: AsyncSession, user_id: UUID, email: str) -> bool:
    return await SuppressionService(session).is_unsubscribed(user_id, email)


async def is_bounce_suppressed(session: AsyncSession, user_id: UUID, email: str) -> bool:
    return await SuppressionService(session).is_bounce_suppressed(user_id, email)
