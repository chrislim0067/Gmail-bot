"""Campaign schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str
    campaign_account_pool_id: UUID
    template_id: UUID | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    timezone: str = "UTC"
    send_window_start_hour: int = Field(default=9, ge=0, le=23)
    send_window_end_hour: int = Field(default=17, ge=0, le=23)


class CampaignUpdate(BaseModel):
    name: str | None = None
    template_id: UUID | None = None
    campaign_account_pool_id: UUID | None = None
    scheduled_start_at: datetime | None = None
    scheduled_end_at: datetime | None = None
    timezone: str | None = None
    send_window_start_hour: int | None = Field(default=None, ge=0, le=23)
    send_window_end_hour: int | None = Field(default=None, ge=0, le=23)


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    template_id: UUID | None
    status: str
    scheduled_start_at: datetime | None
    scheduled_end_at: datetime | None
    send_window_start_hour: int
    send_window_end_hour: int
    timezone: str
    campaign_account_pool_id: UUID
    preflight_passed_at: datetime | None
    total_leads: int
    sent_count: int
    replied_count: int
    bounced_count: int
    paused_reason: str | None
    created_at: datetime
    updated_at: datetime


class CampaignStartResponse(BaseModel):
    status: str
    jobs_created: int = 0
    jobs_processed: int = 0
    outcomes: dict[str, int] = Field(default_factory=dict)


class CampaignStats(BaseModel):
    total_leads: int = 0
    pending: int = 0
    queued: int = 0
    sent: int = 0
    replied: int = 0
    bounced: int = 0
    unsubscribed: int = 0
    failed: int = 0
    skipped: int = 0


class CampaignDetailOut(CampaignOut):
    stats: CampaignStats | None = None
