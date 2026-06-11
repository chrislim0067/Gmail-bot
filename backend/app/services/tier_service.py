"""Account tier promotion and demotion logic."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.config import get_settings
from app.models.gmail_account import GmailAccount
from app.utils.tier_caps import get_tier_caps

TIER_ORDER = ["new", "warming", "stable", "trusted"]


async def evaluate_account_tier(session, gmail_account_id: UUID) -> dict:
    settings = get_settings()
    account = await session.get(GmailAccount, gmail_account_id)
    if account is None:
        return {"error": "account_not_found"}

    promoted = False
    demoted = False
    previous_tier = account.account_tier

    bounce_rate = float(account.bounce_rate_7d or Decimal("0"))
    error_rate = float(account.error_rate_7d or Decimal("0"))
    success_days = account.consecutive_success_days

    if account.review_required or account.status == "paused":
        new_tier = "restricted"
    elif account.consecutive_failure_count >= 3 or error_rate > 0.1:
        new_tier = "restricted"
        account.review_required = True
        demoted = True
    elif bounce_rate > 0.08:
        new_tier = "restricted"
        account.review_required = True
        demoted = True
    else:
        new_tier = account.account_tier
        if account.account_tier in TIER_ORDER:
            idx = TIER_ORDER.index(account.account_tier)
            target_idx = idx
            if success_days >= 30 and bounce_rate < 0.02 and error_rate < 0.01:
                target_idx = max(target_idx, 3)
            elif success_days >= 14 and bounce_rate < 0.03:
                target_idx = max(target_idx, 2)
            elif success_days >= 7 and bounce_rate < 0.03:
                target_idx = max(target_idx, 1)
            if target_idx > idx:
                new_tier = TIER_ORDER[target_idx]
                promoted = True

    if new_tier != previous_tier:
        account.account_tier = new_tier
        if demoted or new_tier == "restricted":
            caps = get_tier_caps("restricted")
        else:
            caps = get_tier_caps(new_tier)
        account.tier_daily_default = caps.daily_default
        account.tier_daily_hard_max = caps.daily_hard_max
        account.daily_send_limit = min(account.daily_send_limit, caps.daily_default)
        account.hourly_send_limit = min(account.hourly_send_limit, caps.hourly_cap)

    if account.account_tier == "new" and settings.default_tier_new_daily:
        account.daily_send_limit = min(
            account.daily_send_limit, settings.default_tier_new_daily
        )

    return {
        "account_tier": account.account_tier,
        "tier_daily_default": account.tier_daily_default,
        "tier_daily_hard_max": account.tier_daily_hard_max,
        "promoted": promoted,
        "demoted": demoted,
        "previous_tier": previous_tier,
    }


async def evaluate_all_account_tiers(session) -> int:
    result = await session.execute(
        select(GmailAccount.id).where(GmailAccount.deleted_at.is_(None))
    )
    count = 0
    for account_id in result.scalars():
        await evaluate_account_tier(session, account_id)
        count += 1
    return count
