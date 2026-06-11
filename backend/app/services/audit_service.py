"""Append-only audit log service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.utils.logging import correlation_id_var


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        action: str,
        resource_type: str,
        user_id: UUID | None = None,
        resource_id: UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        corr = correlation_id_var.get()
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=metadata or {},
            correlation_id=UUID(corr) if corr else None,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
