"""Global unsubscribe suppression list."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UnsubscribeList(Base):
    __tablename__ = "unsubscribe_list"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True
    )
    unsubscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)

    user = relationship("User", back_populates="unsubscribes")
