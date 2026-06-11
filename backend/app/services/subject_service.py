"""Email subject line CRUD."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_subject import EmailSubject
from app.services.template_service import TemplateValidationError


class SubjectService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def validate_subject(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            raise TemplateValidationError("Subject line cannot be empty")
        upper = cleaned.upper()
        if upper.startswith("RE:") or upper.startswith("FWD:"):
            raise TemplateValidationError("Subject must not start with RE: or FWD:")

    async def get_subject(self, subject_id: UUID, user_id: UUID) -> EmailSubject | None:
        result = await self.db.execute(
            select(EmailSubject).where(
                EmailSubject.id == subject_id,
                EmailSubject.user_id == user_id,
                EmailSubject.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: UUID, text: str) -> EmailSubject:
        self.validate_subject(text)
        subject = EmailSubject(user_id=user_id, text=text.strip())
        self.db.add(subject)
        await self.db.flush()
        return subject

    async def count_active(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(EmailSubject)
            .where(
                EmailSubject.user_id == user_id,
                EmailSubject.is_active.is_(True),
                EmailSubject.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def soft_delete(self, subject: EmailSubject) -> None:
        subject.deleted_at = datetime.now(UTC)
        subject.is_active = False
