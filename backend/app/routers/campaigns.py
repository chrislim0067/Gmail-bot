"""Campaign CRUD and lifecycle."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession
from app.models.campaign import Campaign
from app.schemas.campaign import (
    CampaignCreate,
    CampaignDetailOut,
    CampaignOut,
    CampaignStartResponse,
    CampaignStats,
    CampaignUpdate,
)
from app.schemas.common import PaginatedResponse, PreflightCheckResponse
from app.services.campaign_service import CampaignService, CampaignServiceError
from app.services.preflight_service import PreflightService
from app.services.reset_service import reset_send_history
from app.services.sender_service import SenderService

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


async def _campaign_out(db: AsyncSession, campaign: Campaign) -> CampaignOut:
    """Refresh ORM row so server-set timestamps load before Pydantic serialization."""
    await db.refresh(campaign)
    return CampaignOut.model_validate(campaign)


@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(body: CampaignCreate, current_user: CurrentUser, db: DbSession):
    svc = CampaignService(db)
    campaign = await svc.create(current_user.id, body.model_dump())
    return await _campaign_out(db, campaign)


@router.get("")
async def list_campaigns(
    current_user: CurrentUser,
    db: DbSession,
    status: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    from app.models.campaign import Campaign

    query = select(Campaign).where(
        Campaign.user_id == current_user.id,
        Campaign.deleted_at.is_(None),
    )
    if status:
        query = query.where(Campaign.status == status)
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        query.order_by(Campaign.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [CampaignOut.model_validate(c) for c in result.scalars()]
    pages = max(1, (total + limit - 1) // limit)
    return PaginatedResponse(items=items, total=total, page=page, limit=limit, pages=pages)


@router.get("/{campaign_id}", response_model=CampaignDetailOut)
async def get_campaign(campaign_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "running":
        await svc.complete_if_finished(campaign)
    stats = await svc.get_lead_stats(campaign_id)
    return CampaignDetailOut(
        **(await _campaign_out(db, campaign)).model_dump(),
        stats=CampaignStats(**stats),
    )


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: UUID,
    body: CampaignUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        campaign = await svc.update(campaign, body.model_dump(exclude_none=True))
    except CampaignServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return await _campaign_out(db, campaign)


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await svc.soft_delete(campaign)


@router.post("/{campaign_id}/reset-send-history")
async def reset_campaign_send_history(
    campaign_id: UUID, current_user: CurrentUser, db: DbSession
):
    """Clear send history for one campaign and pause it."""
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    result = await reset_send_history(db, current_user.id, campaign_id=campaign_id)
    await db.commit()
    return result


@router.post("/{campaign_id}/start", response_model=CampaignStartResponse)
async def start_campaign(campaign_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        campaign = await svc.start(campaign)
    except CampaignServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    jobs_created = 0
    jobs_processed = 0
    outcomes: dict[str, int] = {}
    if campaign.status == "running":
        sender = SenderService(db)
        jobs_created = await sender.create_send_jobs(campaign_id)
        proc = await sender.process_pending_jobs(campaign_id, limit=1)
        jobs_processed = proc["processed"]
        outcomes = proc.get("outcomes", {})
        await svc.complete_if_finished(campaign)

    return CampaignStartResponse(
        status=campaign.status,
        jobs_created=jobs_created,
        jobs_processed=jobs_processed,
        outcomes=outcomes,
    )


@router.post("/{campaign_id}/preflight-check", response_model=PreflightCheckResponse)
async def preflight_check(campaign_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    result = await PreflightService(db).run(campaign_id)
    return PreflightCheckResponse(**result)


@router.post("/{campaign_id}/pause", response_model=CampaignOut)
async def pause_campaign(campaign_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign = await svc.pause(campaign)
    return await _campaign_out(db, campaign)


@router.post("/{campaign_id}/resume", response_model=CampaignOut)
async def resume_campaign(campaign_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        campaign = await svc.resume(campaign)
    except CampaignServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if campaign.status == "running":
        sender = SenderService(db)
        await sender.create_send_jobs(campaign_id)
        await sender.process_pending_jobs(campaign_id, limit=1)
        await svc.complete_if_finished(campaign)
    return await _campaign_out(db, campaign)


@router.post("/{campaign_id}/process-queue")
async def process_campaign_queue(
    campaign_id: UUID, current_user: CurrentUser, db: DbSession
):
    """Create send jobs and process pending sends (used while campaign is running)."""
    svc = CampaignService(db)
    campaign = await svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status != "running":
        raise HTTPException(status_code=400, detail="Campaign is not running")

    sender = SenderService(db)
    jobs_created = await sender.create_send_jobs(campaign_id)
    proc = await sender.process_pending_jobs(campaign_id, limit=1)
    await svc.complete_if_finished(campaign)
    return {
        "jobs_created": jobs_created,
        "jobs_processed": proc["processed"],
        "outcomes": proc.get("outcomes", {}),
    }
