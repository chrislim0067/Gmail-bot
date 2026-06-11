"""Email template CRUD."""

from uuid import UUID

from datetime import UTC, datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select, update

from app.dependencies import CurrentUser, DbSession
from app.models.template import EmailTemplate
from app.schemas.common import PaginatedResponse
from app.schemas.template import (
    TemplateCreate,
    TemplateOut,
    TemplatePreviewRequest,
    TemplatePreviewResponse,
    TemplateUpdate,
)
from app.schemas.text_import import TextImportResponse
from app.services.text_import_service import TextImportError, TextImportService
from app.services.template_service import TemplateService, TemplateValidationError

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("/import-text", response_model=TextImportResponse)
async def import_templates_text(
    current_user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
):
    if file.filename and not file.filename.lower().endswith((".txt", ".text")):
        raise HTTPException(
            status_code=400,
            detail="Upload a plain text file (.txt)",
        )
    content = (await file.read()).decode("utf-8-sig")
    svc = TextImportService(db)
    try:
        result = await svc.import_message_templates(current_user.id, content)
    except TextImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TextImportResponse(
        imported=result.imported,
        skipped=result.skipped,
        errors=result.errors,
    )


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(body: TemplateCreate, current_user: CurrentUser, db: DbSession):
    svc = TemplateService(db)
    try:
        template = await svc.create(
            current_user.id,
            body.name,
            body.html_template,
            body.text_template,
            body.subject_template,
        )
    except TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TemplateOut.model_validate(template)


@router.get("")
async def list_templates(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    query = select(EmailTemplate).where(
        EmailTemplate.user_id == current_user.id,
        EmailTemplate.deleted_at.is_(None),
    )
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    result = await db.execute(
        query.order_by(EmailTemplate.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [TemplateOut.model_validate(t) for t in result.scalars()]
    pages = max(1, (total + limit - 1) // limit)
    return PaginatedResponse(items=items, total=total, page=page, limit=limit, pages=pages)


@router.post("/delete-all")
async def delete_all_templates(current_user: CurrentUser, db: DbSession):
    """Soft-delete every message template for the current user."""
    result = await db.execute(
        update(EmailTemplate)
        .where(
            EmailTemplate.user_id == current_user.id,
            EmailTemplate.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC), is_active=False)
        .returning(EmailTemplate.id)
    )
    deleted = len(result.fetchall())
    return {"deleted": deleted}


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(template_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = TemplateService(db)
    template = await svc.get_template(template_id, current_user.id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateOut.model_validate(template)


@router.patch("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: UUID,
    body: TemplateUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    svc = TemplateService(db)
    template = await svc.get_template(template_id, current_user.id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    data = body.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(template, key, value)
    await db.flush()
    return TemplateOut.model_validate(template)


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = TemplateService(db)
    template = await svc.get_template(template_id, current_user.id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    template.deleted_at = datetime.now(UTC)
    template.is_active = False


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: UUID,
    body: TemplatePreviewRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    from app.models.lead import Lead

    svc = TemplateService(db)
    template = await svc.get_template(template_id, current_user.id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    sample = body.lead_sample
    lead = Lead(
        campaign_id=UUID(int=0),
        email=sample.get("email", "preview@example.com"),
        normalized_email=sample.get("email", "preview@example.com"),
        first_name=sample.get("first_name"),
        last_name=sample.get("last_name"),
        company=sample.get("company"),
        custom_fields={k: v for k, v in sample.items() if k.startswith("custom_")},
    )
    rendered = svc.render(template, lead, "https://example.com/unsubscribe/token")
    return TemplatePreviewResponse(**rendered)
