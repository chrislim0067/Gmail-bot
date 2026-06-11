"""Account health scoring and tier evaluation."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gmail_account import GmailAccount
from app.models.health_event import AccountHealthEvent
from app.services.audit_service import AuditService
from app.utils.tier_caps import get_tier_caps


class HealthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def get_account(self, account_id: UUID) -> GmailAccount | None:
        result = await self.db.execute(
            select(GmailAccount).where(GmailAccount.id == account_id)
        )
        return result.scalar_one_or_none()

    def apply_penalty(self, score: int, reason: str) -> int:
        penalties = {
            "auth_error": 50,
            "quota_exceeded": 30,
            "bounce_spike": 40,
            "send_failure": 10,
        }
        return max(0, score - penalties.get(reason, 5))

    async def pause_account(self, account: GmailAccount, reason: str) -> GmailAccount:
        account.status = "paused"
        account.paused_reason = reason
        account.paused_at = datetime.now(UTC)
        account.health_score = self.apply_penalty(account.health_score, reason)
        await self.audit.log(
            action="gmail_account.pause",
            resource_type="gmail_account",
            user_id=account.user_id,
            resource_id=account.id,
            metadata={"reason": reason},
        )
        await self.db.flush()
        return account

    async def evaluate_account_tier(self, account_id: UUID) -> dict:
        account = await self.get_account(account_id)
        if not account:
            raise ValueError("Account not found")

        promoted = False
        demoted = False
        previous_tier = account.account_tier

        if account.account_tier == "restricted" or account.status == "auth_error":
            pass
        elif account.bounce_rate_7d > Decimal("0.08"):
            account.account_tier = "restricted"
            account.review_required = True
            demoted = True
        elif account.account_tier == "new" and account.consecutive_success_days >= 7:
            if account.bounce_rate_7d < Decimal("0.03"):
                account.account_tier = "warming"
                promoted = True
        elif account.account_tier == "warming" and account.consecutive_success_days >= 14:
            if account.bounce_rate_7d < Decimal("0.03"):
                account.account_tier = "stable"
                promoted = True
        elif account.account_tier == "stable" and account.consecutive_success_days >= 30:
            if account.bounce_rate_7d < Decimal("0.02"):
                account.account_tier = "trusted"
                promoted = True

        caps = get_tier_caps(account.account_tier)
        account.tier_daily_default = caps.daily_default
        account.tier_daily_hard_max = caps.daily_hard_max
        if account.daily_send_limit > caps.daily_hard_max:
            account.daily_send_limit = caps.daily_hard_max
        if account.hourly_send_limit > caps.hourly_cap:
            account.hourly_send_limit = caps.hourly_cap

        if account.health_score < 30 and account.status == "active":
            await self.pause_account(account, "health_score_low")

        if promoted or demoted:
            await self.audit.log(
                action="gmail_account.tier_change",
                resource_type="gmail_account",
                user_id=account.user_id,
                resource_id=account.id,
                metadata={
                    "from": previous_tier,
                    "to": account.account_tier,
                    "promoted": promoted,
                    "demoted": demoted,
                },
            )

        event = AccountHealthEvent(
            gmail_account_id=account.id,
            score=account.health_score,
            bounce_rate_24h=account.bounce_rate_7d,
            event_type="snapshot",
            recorded_at=datetime.now(UTC),
        )
        self.db.add(event)
        await self.db.flush()

        return {
            "account_tier": account.account_tier,
            "tier_daily_default": account.tier_daily_default,
            "tier_daily_hard_max": account.tier_daily_hard_max,
            "promoted": promoted,
            "demoted": demoted,
            "review_required": account.review_required,
            "should_pause": account.status == "paused",
        }

    async def set_tier_manual(
        self,
        account: GmailAccount,
        new_tier: str,
        reason: str,
    ) -> GmailAccount:
        caps = get_tier_caps(new_tier)
        account.account_tier = new_tier
        account.tier_daily_default = caps.daily_default
        account.tier_daily_hard_max = caps.daily_hard_max
        if new_tier == "restricted":
            account.review_required = True
        await self.audit.log(
            action="gmail_account.set_tier",
            resource_type="gmail_account",
            user_id=account.user_id,
            resource_id=account.id,
            metadata={"tier": new_tier, "reason": reason},
        )
        await self.db.flush()
        return account
