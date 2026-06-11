"""Lead import, list, export."""

from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models.lead import Lead
from app.models.lead_import_batch import LeadImportBatch
from app.schemas.common import PaginatedResponse
from app.schemas.lead import (
    LeadCreate,
    LeadImportResponse,
    LeadImportStatusResponse,
    LeadOut,
)
from app.services.campaign_service import CampaignService
from app.services.lead_service import LeadImportError, LeadService

router = APIRouter(prefix="/campaigns/{campaign_id}/leads", tags=["leads"])


@router.post("/import", response_model=LeadImportResponse, status_code=202)
async def import_leads(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    compliance_acknowledged: bool = Form(...),
    source_label: str | None = Form(None),
    allow_role_based_emails: bool = Form(False),
):
    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    lead_svc = LeadService(db)
    try:
        batch = await lead_svc.create_import_batch(
            campaign,
            current_user.id,
            file.filename or "import.csv",
            compliance_acknowledged=compliance_acknowledged,
            source_label=source_label,
            allow_role_based_emails=allow_role_based_emails,
        )
        content = (await file.read()).decode("utf-8-sig")
        result = await lead_svc.process_csv(
            batch,
            campaign,
            content,
            allow_role_based_emails=allow_role_based_emails,
        )
    except LeadImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result["imported"] == 0 and result["skipped"] == 0 and result["invalid"] > 0:
        raise HTTPException(
            status_code=400,
            detail=result["errors"][0] if result["errors"] else "No valid leads in CSV",
        )

    return LeadImportResponse(
        import_batch_id=batch.id,
        status=batch.status,
        imported=result["imported"],
        skipped=result["skipped"],
        invalid=result["invalid"],
        errors=result["errors"],
    )


@router.get("/import/{job_id}", response_model=LeadImportStatusResponse)
async def import_status(
    campaign_id: UUID,
    job_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await db.execute(
        select(LeadImportBatch).where(
            LeadImportBatch.id == job_id,
            LeadImportBatch.campaign_id == campaign_id,
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")
    return LeadImportStatusResponse(
        status=batch.status,
        imported=batch.imported_count,
        skipped=batch.skipped_count,
        invalid=batch.invalid_count,
        errors=[],
    )


@router.get("")
async def list_leads(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    query = select(Lead).where(
        Lead.campaign_id == campaign_id,
        Lead.deleted_at.is_(None),
    )
    if status:
        query = query.where(Lead.status == status)
    if search:
        query = query.where(Lead.email.ilike(f"%{search}%"))
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    result = await db.execute(
        query.order_by(Lead.created_at.desc()).offset((page - 1) * limit).limit(limit)
    )
    items = [LeadOut.model_validate(l) for l in result.scalars()]
    pages = max(1, (total + limit - 1) // limit)
    return PaginatedResponse(items=items, total=total, page=page, limit=limit, pages=pages)


@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(
    campaign_id: UUID,
    body: LeadCreate,
    current_user: CurrentUser,
    db: DbSession,
):
    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    lead_svc = LeadService(db)
    try:
        lead = await lead_svc.create_lead(
            campaign,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            company=body.company,
            source=body.source,
            compliance_acknowledged=body.compliance_acknowledged,
            allow_role_based_emails=body.allow_role_based_emails,
        )
    except LeadImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LeadOut.model_validate(lead)


@router.get("/export")
async def export_leads(
    campaign_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    status: str | None = None,
):
    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    lead_svc = LeadService(db)
    csv_content = await lead_svc.export_csv(campaign_id, status)
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_{campaign_id}.csv"},
    )


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(
    campaign_id: UUID,
    lead_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    from datetime import UTC, datetime

    campaign_svc = CampaignService(db)
    campaign = await campaign_svc.get_campaign(campaign_id, current_user.id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    result = await db.execute(
        select(Lead).where(Lead.id == lead_id, Lead.campaign_id == campaign_id)
    )
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.status == "sent":
        raise HTTPException(status_code=400, detail="Cannot delete sent lead")
    lead.deleted_at = datetime.now(UTC)
