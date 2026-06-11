"""Email subject line CRUD."""

from uuid import UUID

from datetime import UTC, datetime

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select, update

from app.dependencies import CurrentUser, DbSession
from app.models.email_subject import EmailSubject
from app.schemas.common import PaginatedResponse
from app.schemas.subject import SubjectCreate, SubjectOut, SubjectUpdate
from app.schemas.text_import import TextImportResponse
from app.services.subject_service import SubjectService
from app.services.template_service import TemplateValidationError
from app.services.text_import_service import TextImportError, TextImportService

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.post("/import-text", response_model=TextImportResponse)
async def import_subjects_text(
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
        result = await svc.import_subjects(current_user.id, content)
    except TextImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TextImportResponse(
        imported=result.imported,
        skipped=result.skipped,
        errors=result.errors,
    )


@router.post("", response_model=SubjectOut, status_code=201)
async def create_subject(body: SubjectCreate, current_user: CurrentUser, db: DbSession):
    svc = SubjectService(db)
    try:
        subject = await svc.create(current_user.id, body.text)
    except TemplateValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SubjectOut.model_validate(subject)


@router.get("")
async def list_subjects(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    query = select(EmailSubject).where(
        EmailSubject.user_id == current_user.id,
        EmailSubject.deleted_at.is_(None),
    )
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    result = await db.execute(
        query.order_by(EmailSubject.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [SubjectOut.model_validate(s) for s in result.scalars()]
    pages = max(1, (total + limit - 1) // limit)
    return PaginatedResponse(items=items, total=total, page=page, limit=limit, pages=pages)


@router.post("/delete-all")
async def delete_all_subjects(current_user: CurrentUser, db: DbSession):
    """Soft-delete every subject line for the current user."""
    result = await db.execute(
        update(EmailSubject)
        .where(
            EmailSubject.user_id == current_user.id,
            EmailSubject.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC), is_active=False)
        .returning(EmailSubject.id)
    )
    deleted = len(result.fetchall())
    return {"deleted": deleted}


@router.patch("/{subject_id}", response_model=SubjectOut)
async def update_subject(
    subject_id: UUID,
    body: SubjectUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    svc = SubjectService(db)
    subject = await svc.get_subject(subject_id, current_user.id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    data = body.model_dump(exclude_none=True)
    if "text" in data:
        try:
            svc.validate_subject(data["text"])
            data["text"] = data["text"].strip()
        except TemplateValidationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    for key, value in data.items():
        setattr(subject, key, value)
    await db.flush()
    return SubjectOut.model_validate(subject)


@router.delete("/{subject_id}", status_code=204)
async def delete_subject(subject_id: UUID, current_user: CurrentUser, db: DbSession):
    svc = SubjectService(db)
    subject = await svc.get_subject(subject_id, current_user.id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await svc.soft_delete(subject)
