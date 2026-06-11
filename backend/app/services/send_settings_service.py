"""Per-user send timing settings (cooldowns and pool gaps)."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User


@dataclass(frozen=True)
class SendTimingSettings:
    account_cooldown_seconds: int
    inter_account_delay_min_seconds: int
    inter_account_delay_max_seconds: int
    scheduler_tick_interval_seconds: int

    @classmethod
    def from_app_config(cls) -> "SendTimingSettings":
        settings = get_settings()
        return cls(
            account_cooldown_seconds=settings.inter_send_delay_min_seconds,
            inter_account_delay_min_seconds=settings.inter_account_delay_min_seconds,
            inter_account_delay_max_seconds=settings.inter_account_delay_max_seconds,
            scheduler_tick_interval_seconds=settings.scheduler_tick_interval_seconds,
        )

    def to_dict(self) -> dict:
        return {
            "account_cooldown_seconds": self.account_cooldown_seconds,
            "account_cooldown_minutes": self.account_cooldown_seconds // 60,
            "inter_send_delay_seconds": self.account_cooldown_seconds,
            "inter_account_delay_min_seconds": self.inter_account_delay_min_seconds,
            "inter_account_delay_max_seconds": self.inter_account_delay_max_seconds,
            "inter_account_delay_min_minutes": self.inter_account_delay_min_seconds // 60,
            "inter_account_delay_max_minutes": self.inter_account_delay_max_seconds // 60,
            "scheduler_tick_interval_seconds": self.scheduler_tick_interval_seconds,
        }


async def get_send_timing_settings(
    session: AsyncSession, user_id: UUID
) -> SendTimingSettings:
    defaults = SendTimingSettings.from_app_config()
    user = await session.get(User, user_id)
    if user is None:
        return defaults
    return SendTimingSettings(
        account_cooldown_seconds=(
            user.account_send_cooldown_seconds or defaults.account_cooldown_seconds
        ),
        inter_account_delay_min_seconds=(
            user.inter_account_delay_min_seconds
            or defaults.inter_account_delay_min_seconds
        ),
        inter_account_delay_max_seconds=(
            user.inter_account_delay_max_seconds
            or defaults.inter_account_delay_max_seconds
        ),
        scheduler_tick_interval_seconds=defaults.scheduler_tick_interval_seconds,
    )


async def update_send_timing_settings(
    session: AsyncSession,
    user: User,
    *,
    account_cooldown_minutes: int | None = None,
    inter_account_delay_min_minutes: int | None = None,
    inter_account_delay_max_minutes: int | None = None,
) -> SendTimingSettings:
    if account_cooldown_minutes is not None:
        if account_cooldown_minutes < 1 or account_cooldown_minutes > 240:
            raise ValueError("Account cooldown must be between 1 and 240 minutes")
        user.account_send_cooldown_seconds = account_cooldown_minutes * 60

    if inter_account_delay_min_minutes is not None:
        if inter_account_delay_min_minutes < 1 or inter_account_delay_min_minutes > 60:
            raise ValueError("Pool gap minimum must be between 1 and 60 minutes")
        user.inter_account_delay_min_seconds = inter_account_delay_min_minutes * 60

    if inter_account_delay_max_minutes is not None:
        if inter_account_delay_max_minutes < 1 or inter_account_delay_max_minutes > 60:
            raise ValueError("Pool gap maximum must be between 1 and 60 minutes")
        user.inter_account_delay_max_seconds = inter_account_delay_max_minutes * 60

    effective = await get_send_timing_settings(session, user.id)
    if (
        effective.inter_account_delay_min_seconds
        > effective.inter_account_delay_max_seconds
    ):
        raise ValueError("Pool gap minimum cannot exceed maximum")

    await session.flush()
    return effective
