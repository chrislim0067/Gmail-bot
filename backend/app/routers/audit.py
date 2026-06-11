"""Audit log query routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models.audit_log import AuditLog
from app.schemas.analytics import AuditLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("")
async def list_audit_logs(
    current_user: CurrentUser,
    db: DbSession,
    action: str | None = None,
    resource_type: str | None = None,
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    query = select(AuditLog).where(AuditLog.user_id == current_user.id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if from_date:
        query = query.where(AuditLog.created_at >= from_date)
    if to_date:
        query = query.where(AuditLog.created_at <= to_date)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    result = await db.execute(
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [
        AuditLogOut(
            id=e.id,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            metadata=e.metadata_,
            created_at=e.created_at.isoformat(),
        )
        for e in result.scalars()
    ]
    return {"items": items, "total": total, "page": page, "limit": limit}
