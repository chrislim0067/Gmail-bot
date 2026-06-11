"""Gmail account and pool schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GmailAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    status: str
    account_tier: str
    risk_level: str
    review_required: bool
    health_score: int
    tier_daily_default: int
    tier_daily_hard_max: int
    daily_send_limit: int
    hourly_send_limit: int
    connected_at: datetime
    consecutive_success_days: int
    bounce_rate_7d: Decimal
    error_rate_7d: Decimal
    last_send_at: datetime | None
    granted_scopes: list[str] = Field(default_factory=list)
    sent_today: int = 0
    sent_this_hour: int = 0
    effective_daily_send_limit: int = 0
    effective_hourly_send_limit: int = 0
    remaining_today: int = 0
    recent_quota_errors: int = 0
    recent_auth_errors: int = 0


class GmailAccountDetailOut(GmailAccountOut):
    display_name: str | None
    paused_reason: str | None
    lifetime_send_count: int
    reply_rate_7d: Decimal


class GmailAccountLimitsUpdate(BaseModel):
    daily_send_limit: int | None = None
    hourly_send_limit: int | None = None


class GmailAccountPauseRequest(BaseModel):
    reason: str = "manual"


class GmailAccountReviewRequest(BaseModel):
    approved: bool
    notes: str | None = None
    new_tier: str | None = None


class GmailAccountSetTierRequest(BaseModel):
    account_tier: str
    reason: str


class PoolCreate(BaseModel):
    name: str
    description: str | None = None
    max_daily_send: int | None = None
    max_hourly_send: int | None = None
    active_account_limit: int | None = None
    risk_policy: str | None = None


class PoolUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    max_daily_send: int | None = None
    max_hourly_send: int | None = None
    active_account_limit: int | None = None
    risk_policy: str | None = None
    status: str | None = None


class PoolMemberCreate(BaseModel):
    gmail_account_id: UUID
    priority: int = 100
    is_active: bool = True


class PoolMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gmail_account_id: UUID
    priority: int
    is_active: bool


class PoolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    max_daily_send: int
    max_hourly_send: int
    active_account_limit: int
    risk_policy: str
    status: str
    member_count: int = 0
    sends_today: int = 0
    sends_this_hour: int = 0
    capacity_remaining: int = 0


class PoolDetailOut(PoolOut):
    members: list[PoolMemberOut] = Field(default_factory=list)
