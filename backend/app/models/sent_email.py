"""Record of successfully sent emails."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SentEmail(Base):
    __tablename__ = "sent_emails"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    send_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("send_jobs.id"), unique=True, nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False
    )
    gmail_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gmail_accounts.id"), nullable=False, index=True
    )
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rfc_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    delivery_status: Mapped[str] = mapped_column(String(32), default="sent")

    send_job = relationship("SendJob", back_populates="sent_email")
    lead = relationship("Lead", back_populates="sent_emails")
    gmail_account = relationship("GmailAccount", back_populates="sent_emails")
    reply_events = relationship("ReplyEvent", back_populates="sent_email")
