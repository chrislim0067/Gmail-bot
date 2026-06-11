"""Lead model for campaign recipients."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_fields: Mapped[dict] = mapped_column(JSONB, default=dict)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consent_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead_import_batches.id"), nullable=True, index=True
    )
    last_contacted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    do_not_contact_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    validation_status: Mapped[str] = mapped_column(String(32), default="pending")
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    campaign = relationship("Campaign", back_populates="leads")
    import_batch = relationship("LeadImportBatch", back_populates="leads")
    send_jobs = relationship("SendJob", back_populates="lead")
    sent_emails = relationship("SentEmail", back_populates="lead")
