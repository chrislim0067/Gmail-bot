"""Risk budget schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RiskOverview(BaseModel):
    global_risk_score: int
    threshold: int
    review_required: bool
    recent_events_count: int
    paused_campaigns: int


class RiskEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    severity: str
    score_delta: int
    gmail_account_id: UUID | None
    campaign_id: UUID | None
    pool_id: UUID | None
    details: dict
    acknowledged_at: datetime | None
    created_at: datetime


class RiskAcknowledgeRequest(BaseModel):
    event_ids: list[UUID] | None = None
    acknowledge_all: bool = False
    notes: str | None = None
