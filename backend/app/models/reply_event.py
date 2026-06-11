"""Reply detection events."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ReplyEvent(Base):
    __tablename__ = "reply_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sent_email_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sent_emails.id"), nullable=False, index=True
    )
    gmail_message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_auto_reply: Mapped[bool] = mapped_column(Boolean, default=False)

    sent_email = relationship("SentEmail", back_populates="reply_events")
