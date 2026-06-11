"""Campaign model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    scheduled_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    scheduled_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    send_window_start_hour: Mapped[int] = mapped_column(Integer, default=9)
    send_window_end_hour: Mapped[int] = mapped_column(Integer, default=17)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    campaign_account_pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gmail_account_pools.id"),
        nullable=False,
        index=True,
    )
    preflight_passed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    replied_count: Mapped[int] = mapped_column(Integer, default=0)
    bounced_count: Mapped[int] = mapped_column(Integer, default=0)
    paused_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user = relationship("User", back_populates="campaigns")
    template = relationship("EmailTemplate", back_populates="campaigns")
    account_pool = relationship("GmailAccountPool", back_populates="campaigns")
    leads = relationship("Lead", back_populates="campaign")
    send_jobs = relationship("SendJob", back_populates="campaign")
    import_batches = relationship("LeadImportBatch", back_populates="campaign")
