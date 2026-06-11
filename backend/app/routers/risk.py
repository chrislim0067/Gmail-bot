"""Global risk budget routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.dependencies import CurrentUser, DbSession
from app.models.risk_budget_event import RiskBudgetEvent
from app.schemas.common import MessageResponse
from app.schemas.risk import RiskAcknowledgeRequest, RiskEventOut, RiskOverview
from app.services.audit_service import AuditService
from app.services.risk_service import RiskService

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/overview", response_model=RiskOverview)
async def risk_overview(current_user: CurrentUser, db: DbSession):
    svc = RiskService(db)
    data = await svc.get_overview(current_user.id)
    return RiskOverview(**data)


@router.get("/events")
async def risk_events(
    current_user: CurrentUser,
    db: DbSession,
    event_type: str | None = None,
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    query = select(RiskBudgetEvent).where(RiskBudgetEvent.user_id == current_user.id)
    if event_type:
        query = query.where(RiskBudgetEvent.event_type == event_type)
    if from_date:
        query = query.where(RiskBudgetEvent.created_at >= from_date)
    if to_date:
        query = query.where(RiskBudgetEvent.created_at <= to_date)
    result = await db.execute(
        query.order_by(RiskBudgetEvent.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [RiskEventOut.model_validate(e) for e in result.scalars()]
    return {"items": items, "page": page, "limit": limit}


@router.post("/acknowledge", response_model=MessageResponse)
async def acknowledge_risk(
    body: RiskAcknowledgeRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    svc = RiskService(db)
    await svc.acknowledge(
        current_user.id,
        event_ids=body.event_ids,
        acknowledge_all=body.acknowledge_all,
        notes=body.notes,
    )
    await AuditService(db).log(
        action="risk.acknowledge",
        resource_type="user",
        user_id=current_user.id,
        metadata={"notes": body.notes},
    )
    return MessageResponse(status="acknowledged")
