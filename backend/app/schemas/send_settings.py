"""Send timing settings schemas."""

from pydantic import BaseModel, Field


class SendTimingOut(BaseModel):
    account_cooldown_seconds: int
    account_cooldown_minutes: int
    inter_account_delay_min_seconds: int
    inter_account_delay_max_seconds: int
    inter_account_delay_min_minutes: int
    inter_account_delay_max_minutes: int
    scheduler_tick_interval_seconds: int


class SendTimingUpdate(BaseModel):
    account_cooldown_minutes: int | None = Field(
        default=None, ge=1, le=240, description="Minutes before the same account can send again"
    )
    inter_account_delay_min_minutes: int | None = Field(
        default=None, ge=1, le=60, description="Minimum minutes between accounts in a pool"
    )
    inter_account_delay_max_minutes: int | None = Field(
        default=None, ge=1, le=60, description="Maximum minutes between accounts in a pool"
    )
