"""Analytics endpoints."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import CurrentUser, DbSession
from app.schemas.analytics import AnalyticsOverview, CampaignAnalytics
from app.services.analytics_service import AnalyticsService
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    current_user: CurrentUser,
    db: DbSession,
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
):
    svc = AnalyticsService(db)
    data = await svc.get_overview(current_user.id, from_date, to_date)
    return AnalyticsOverview(**data)


@router.get("/campaigns/{campaign_id}", response_model=CampaignAnalytics)
async def campaign_analytics(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    svc = AnalyticsService(db)
    data = await svc.get_campaign_analytics(campaign_id)
    return CampaignAnalytics(**data)
