"""User model for app authentication."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    account_send_cooldown_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    inter_account_delay_min_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    inter_account_delay_max_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    global_risk_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_review_required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    gmail_accounts = relationship("GmailAccount", back_populates="user")
    campaigns = relationship("Campaign", back_populates="user")
    email_templates = relationship("EmailTemplate", back_populates="user")
    email_subjects = relationship("EmailSubject", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    risk_budget_events = relationship("RiskBudgetEvent", back_populates="user")
    unsubscribes = relationship("UnsubscribeList", back_populates="user")
    account_pools = relationship("GmailAccountPool", back_populates="user")
