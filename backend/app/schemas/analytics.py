"""Analytics schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    sent: int
    replied: int
    bounced: int
    unsubscribed: int
    reply_rate: float
    bounce_rate: float


class DailyBreakdown(BaseModel):
    date: date
    sent: int
    replied: int
    bounced: int
    unsubscribed: int


class AccountBreakdown(BaseModel):
    gmail_account_id: UUID
    email: str
    sent: int
    replied: int
    bounced: int


class CampaignAnalytics(BaseModel):
    funnel: dict[str, int]
    daily_breakdown: list[DailyBreakdown]
    account_breakdown: list[AccountBreakdown]


class QueueStats(BaseModel):
    pending: int
    locked: int
    failed: int
    sent_today: int


class HealthAccountOut(BaseModel):
    id: UUID
    email: str
    health_score: int
    account_tier: str
    status: str
    risk_level: str
    review_required: bool
    bounce_rate_7d: float
    error_rate_7d: float
    alerts: list[str]


class HealthEventOut(BaseModel):
    id: UUID
    score: int
    event_type: str
    bounce_rate_24h: float | None
    send_count_24h: int | None
    failure_count_24h: int | None
    details: dict
    recorded_at: str


class AuditLogOut(BaseModel):
    id: UUID
    action: str
    resource_type: str
    resource_id: UUID | None
    metadata: dict
    created_at: str


class ReplyOut(BaseModel):
    id: UUID
    sent_email_id: UUID
    from_email: str
    snippet: str | None
    received_at: str
    campaign_id: UUID | None
    campaign_name: str | None = None
    lead_email: str | None
    subject: str | None = None
    gmail_account_id: UUID | None = None


class ReplySyncResponse(BaseModel):
    new_replies: int = 0
    messages_scanned: int = 0
    reason: str = "ok"
