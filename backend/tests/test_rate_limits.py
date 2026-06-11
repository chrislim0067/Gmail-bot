"""Rate limit service tests."""

from uuid import uuid4

import pytest

from app.services.rate_limit_service import RateLimitService
from app.utils.tier_caps import effective_daily_cap, get_tier_caps


def test_tier_caps_new_account():
    caps = get_tier_caps("new")
    assert caps.daily_default == 5
    assert caps.daily_hard_max == 10
    assert caps.sends_allowed is True


def test_effective_daily_cap_respects_user_limit_up_to_hard_max():
    assert effective_daily_cap("stable", user_daily_limit=50) == 50
    assert effective_daily_cap("trusted", user_daily_limit=100) == 75
    assert effective_daily_cap("new", user_daily_limit=50) == 10


def test_restricted_tier_zero_sends():
    caps = get_tier_caps("restricted")
    assert caps.sends_allowed is False
    assert effective_daily_cap("restricted", 50) == 0


@pytest.mark.asyncio
async def test_rate_limit_counter_increment():
    svc = RateLimitService()
    account_id = uuid4()
    try:
        check = await svc.check_account_rate_limit(
            account_id=account_id,
            account_tier="new",
            user_daily_limit=5,
            user_hourly_limit=1,
            last_send_at=None,
        )
        if check["reason"] == "redis_unavailable":
            pytest.skip("Redis not available")
        await svc.record_account_send(account_id)
        count = await svc.get_account_daily_count(account_id)
        assert count >= 1
    finally:
        pass
