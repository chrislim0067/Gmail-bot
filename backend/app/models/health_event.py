"""Account health snapshot events."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AccountHealthEvent(Base):
    __tablename__ = "account_health_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    gmail_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gmail_accounts.id"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    bounce_rate_24h: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    send_count_24h: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_count_24h: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    gmail_account = relationship("GmailAccount", back_populates="health_events")
