"""Bounce detection events."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BounceEvent(Base):
    __tablename__ = "bounce_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gmail_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gmail_accounts.id"), nullable=False, index=True
    )
    sent_email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sent_emails.id"), nullable=True
    )
    bounced_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    bounce_type: Mapped[str] = mapped_column(String(32), nullable=False)
    smtp_status_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    detection_method: Mapped[str] = mapped_column(String(64), nullable=False)
    diagnostic: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_headers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    gmail_account = relationship("GmailAccount", back_populates="bounce_events")
