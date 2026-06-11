"""Random template + subject selection and Chris signature append."""

import random
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_subject import EmailSubject
from app.models.lead import Lead
from app.models.template import EmailTemplate
from app.services.template_service import TemplateService

SIGNATURE_HTML = "<p>Thanks<br>Chris</p>"
SIGNATURE_TEXT = "Thanks\nChris"

_UNSUBSCRIBE_HTML_PATTERN = re.compile(
    r'<p[^>]*>.*?Unsubscribe from these emails.*?</p>\s*',
    re.I | re.DOTALL,
)
_UNSUBSCRIBE_TEXT_PATTERN = re.compile(r"\n---\nUnsubscribe:.*$", re.I | re.DOTALL)


def strip_unsubscribe_footer(html: str, text: str | None) -> tuple[str, str | None]:
    """Remove legacy in-body unsubscribe links from stored templates."""
    cleaned_html = _UNSUBSCRIBE_HTML_PATTERN.sub("", html).rstrip()
    cleaned_text = (
        _UNSUBSCRIBE_TEXT_PATTERN.sub("", text).rstrip() if text else None
    )
    return cleaned_html, cleaned_text


class OutreachComposeError(Exception):
    pass


class OutreachComposeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.templates = TemplateService(db)

    async def list_active_message_templates(self, user_id: UUID) -> list[EmailTemplate]:
        result = await self.db.execute(
            select(EmailTemplate).where(
                EmailTemplate.user_id == user_id,
                EmailTemplate.is_active.is_(True),
                EmailTemplate.deleted_at.is_(None),
            )
        )
        return list(result.scalars())

    async def list_active_subjects(self, user_id: UUID) -> list[EmailSubject]:
        result = await self.db.execute(
            select(EmailSubject).where(
                EmailSubject.user_id == user_id,
                EmailSubject.is_active.is_(True),
                EmailSubject.deleted_at.is_(None),
            )
        )
        return list(result.scalars())

    def pick_random_message_template(
        self, templates: list[EmailTemplate]
    ) -> EmailTemplate:
        if not templates:
            raise OutreachComposeError("No active message templates")
        return random.choice(templates)

    def pick_random_subject(self, subjects: list[EmailSubject]) -> EmailSubject:
        if not subjects:
            raise OutreachComposeError("No active subject lines")
        return random.choice(subjects)

    def append_signature(self, html: str, text: str | None) -> tuple[str, str | None]:
        html_with_sig = f"{html.rstrip()}\n{SIGNATURE_HTML}"
        if text:
            text_with_sig = f"{text.rstrip()}\n\n{SIGNATURE_TEXT}"
        else:
            text_with_sig = SIGNATURE_TEXT
        return html_with_sig, text_with_sig

    async def compose_for_lead(
        self,
        user_id: UUID,
        lead: Lead,
        unsubscribe_url: str,
    ) -> dict[str, str | None]:
        message_templates = await self.list_active_message_templates(user_id)
        subjects = await self.list_active_subjects(user_id)
        message_template = self.pick_random_message_template(message_templates)
        subject_line = self.pick_random_subject(subjects)

        rendered = self.templates.render_message(
            message_template,
            subject_line.text,
            lead,
            unsubscribe_url,
        )
        html, text = strip_unsubscribe_footer(
            rendered["html"], rendered.get("text")
        )
        html, text = self.append_signature(html, text)
        return {
            "subject": rendered["subject"],
            "html": html,
            "text": text,
            "message_template_id": str(message_template.id),
            "subject_id": str(subject_line.id),
        }
