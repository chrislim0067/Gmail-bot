"""Gmail account pools and membership."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class GmailAccountPool(Base, TimestampMixin):
    __tablename__ = "gmail_account_pools"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_daily_send: Mapped[int] = mapped_column(Integer, default=200)
    max_hourly_send: Mapped[int] = mapped_column(Integer, default=40)
    active_account_limit: Mapped[int] = mapped_column(Integer, default=10)
    risk_policy: Mapped[str] = mapped_column(String(64), default="conservative")
    status: Mapped[str] = mapped_column(String(32), default="active")

    user = relationship("User", back_populates="account_pools")
    members = relationship("GmailAccountPoolMember", back_populates="pool")
    campaigns = relationship("Campaign", back_populates="account_pool")


class GmailAccountPoolMember(Base):
    __tablename__ = "gmail_account_pool_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    pool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gmail_account_pools.id"),
        nullable=False,
        index=True,
    )
    gmail_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("gmail_accounts.id"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    pool = relationship("GmailAccountPool", back_populates="members")
    gmail_account = relationship("GmailAccount", back_populates="pool_memberships")
