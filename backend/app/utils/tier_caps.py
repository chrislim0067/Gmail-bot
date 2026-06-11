"""Account tier default and hard-max daily/hourly send caps."""

from dataclasses import dataclass
from typing import Literal

AccountTier = Literal[
    "new", "warming", "stable", "trusted", "restricted", "paused"
]


@dataclass(frozen=True)
class TierCaps:
    daily_default: int
    daily_hard_max: int
    hourly_cap: int
    sends_allowed: bool


TIER_CAPS: dict[str, TierCaps] = {
    "new": TierCaps(daily_default=5, daily_hard_max=10, hourly_cap=1, sends_allowed=True),
    "warming": TierCaps(daily_default=10, daily_hard_max=20, hourly_cap=3, sends_allowed=True),
    "stable": TierCaps(daily_default=20, daily_hard_max=50, hourly_cap=5, sends_allowed=True),
    "trusted": TierCaps(daily_default=30, daily_hard_max=75, hourly_cap=8, sends_allowed=True),
    "restricted": TierCaps(daily_default=0, daily_hard_max=0, hourly_cap=0, sends_allowed=False),
    "paused": TierCaps(daily_default=0, daily_hard_max=0, hourly_cap=0, sends_allowed=False),
}


def get_tier_caps(account_tier: str) -> TierCaps:
    return TIER_CAPS.get(account_tier, TIER_CAPS["new"])


def effective_daily_cap(
    account_tier: str,
    user_daily_limit: int,
) -> int:
    caps = get_tier_caps(account_tier)
    if not caps.sends_allowed:
        return 0
    return min(user_daily_limit, caps.daily_hard_max)


def effective_hourly_cap(
    account_tier: str,
    user_hourly_limit: int,
) -> int:
    caps = get_tier_caps(account_tier)
    if not caps.sends_allowed:
        return 0
    return min(user_hourly_limit, caps.hourly_cap)


ROLE_BASED_PREFIXES = (
    "info",
    "support",
    "admin",
    "sales",
    "contact",
    "noreply",
    "no-reply",
)


def is_role_based_email(email: str) -> bool:
    local = email.split("@", 1)[0].lower()
    return any(local == prefix or local.startswith(f"{prefix}+") for prefix in ROLE_BASED_PREFIXES)


def normalize_email(email: str) -> str:
    return email.strip().lower()
