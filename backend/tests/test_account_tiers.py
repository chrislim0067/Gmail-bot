"""Account tier promotion and restriction tests."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gmail_account import GmailAccount
from app.services.health_service import HealthService
from app.services.rate_limit_service import RateLimitService
from app.services.redis_lock_service import RedisLockService
from app.utils.tier_caps import effective_daily_cap, get_tier_caps


@pytest.mark.asyncio
async def test_account_tier_promotion(db_session: AsyncSession, test_user):
    account = GmailAccount(
        user_id=test_user.id,
        email=f"tier_{uuid4().hex[:6]}@gmail.com",
        google_user_id=f"gid_{uuid4().hex[:8]}",
        connected_at=datetime.now(UTC),
        account_tier="new",
        consecutive_success_days=7,
        bounce_rate_7d=Decimal("0.01"),
        tier_daily_default=5,
        tier_daily_hard_max=10,
    )
    db_session.add(account)
    await db_session.flush()

    health = HealthService(db_session)
    result = await health.evaluate_account_tier(account.id)
    assert result["account_tier"] == "warming"
    assert result["promoted"] is True


@pytest.mark.asyncio
async def test_account_tier_demotion_on_quota_error(db_session: AsyncSession, test_user):
    account = GmailAccount(
        user_id=test_user.id,
        email=f"quota_{uuid4().hex[:6]}@gmail.com",
        google_user_id=f"gid_{uuid4().hex[:8]}",
        connected_at=datetime.now(UTC),
        account_tier="stable",
        bounce_rate_7d=Decimal("0.10"),
        tier_daily_default=20,
        tier_daily_hard_max=50,
    )
    db_session.add(account)
    await db_session.flush()

    health = HealthService(db_session)
    result = await health.evaluate_account_tier(account.id)
    assert result["account_tier"] == "restricted"
    assert result["demoted"] is True


@pytest.mark.asyncio
async def test_restricted_account_cannot_send():
    caps = get_tier_caps("restricted")
    assert caps.sends_allowed is False
    assert effective_daily_cap("restricted", 100) == 0

    rate = RateLimitService()
    result = await rate.check_account_rate_limit(
        account_id=uuid4(),
        account_tier="restricted",
        user_daily_limit=30,
        user_hourly_limit=8,
        last_send_at=None,
    )
    assert result["allowed"] is False


@pytest.mark.asyncio
async def test_token_refresh_lock():
    import redis.exceptions

    locks = RedisLockService()
    account_id = str(uuid4())
    try:
        acquired1, token1 = await locks.acquire_token_refresh_lock(account_id)
        if not acquired1:
            pytest.skip("Redis not available")
        acquired2, _ = await locks.acquire_token_refresh_lock(account_id)
        assert acquired2 is False
        await locks.release("token_refresh", account_id, token1)
    except (redis.exceptions.RedisError, OSError, ConnectionError):
        pytest.skip("Redis not available")
    finally:
        try:
            client = await locks.get_client()
            await client.aclose()
        except Exception:
            pass
