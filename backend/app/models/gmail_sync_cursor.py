"""Gmail sync cursors for reply and bounce workers."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class GmailSyncCursor(Base, TimestampMixin):
    __tablename__ = "gmail_sync_cursors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gmail_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gmail_accounts.id"),
        unique=True,
        nullable=False,
    )
    reply_sync_history_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bounce_sync_after: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    gmail_account = relationship("GmailAccount", back_populates="sync_cursor")
