"""Pre-aggregated daily analytics rollups."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalyticsDailyRollup(Base):
    __tablename__ = "analytics_daily_rollups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True
    )
    pool_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gmail_account_pools.id"), nullable=True
    )
    gmail_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gmail_accounts.id"), nullable=True
    )
    rollup_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    replied_count: Mapped[int] = mapped_column(Integer, default=0)
    bounced_count: Mapped[int] = mapped_column(Integer, default=0)
    unsubscribed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
