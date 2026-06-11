"""Gmail account connected via OAuth."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin
from app.utils.tier_caps import get_tier_caps


class GmailAccount(Base, TimestampMixin):
    __tablename__ = "gmail_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    google_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    account_tier: Mapped[str] = mapped_column(
        String(32), default="new", index=True
    )
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    first_send_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_successful_send_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consecutive_success_days: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failure_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    review_required: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )
    daily_send_limit: Mapped[int] = mapped_column(Integer, default=5)
    hourly_send_limit: Mapped[int] = mapped_column(Integer, default=1)
    tier_daily_default: Mapped[int] = mapped_column(Integer, nullable=False)
    tier_daily_hard_max: Mapped[int] = mapped_column(Integer, nullable=False)
    bounce_rate_7d: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0")
    )
    error_rate_7d: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0")
    )
    reply_rate_7d: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0")
    )
    lifetime_send_count: Mapped[int] = mapped_column(Integer, default=0)
    health_score: Mapped[int] = mapped_column(Integer, default=100)
    last_send_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", back_populates="gmail_accounts")
    oauth_token = relationship(
        "OAuthToken", back_populates="gmail_account", uselist=False
    )
    pool_memberships = relationship(
        "GmailAccountPoolMember", back_populates="gmail_account"
    )
    send_jobs = relationship("SendJob", back_populates="gmail_account")
    sent_emails = relationship("SentEmail", back_populates="gmail_account")
    bounce_events = relationship("BounceEvent", back_populates="gmail_account")
    health_events = relationship("AccountHealthEvent", back_populates="gmail_account")
    sync_cursor = relationship(
        "GmailSyncCursor", back_populates="gmail_account", uselist=False
    )

    @staticmethod
    def tier_fields_for(account_tier: str) -> tuple[int, int]:
        caps = get_tier_caps(account_tier)
        return caps.daily_default, caps.daily_hard_max
