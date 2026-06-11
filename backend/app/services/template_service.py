"""Email template CRUD and Jinja2 rendering."""

import re
from uuid import UUID

from jinja2 import Environment, select_autoescape
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.template import EmailTemplate

URL_SHORTENER_PATTERN = re.compile(r"https?://(bit\.ly|tinyurl\.com|t\.co)/", re.I)


class TemplateValidationError(Exception):
    pass


class TemplateService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.env: Environment = SandboxedEnvironment(
            autoescape=select_autoescape(default_for_string=True),
        )

    def validate_no_deceptive_subject(self, subject: str) -> None:
        upper = subject.strip().upper()
        if upper.startswith("RE:") or upper.startswith("FWD:"):
            raise TemplateValidationError("Subject must not start with RE: or FWD:")

    async def get_template(self, template_id: UUID, user_id: UUID) -> EmailTemplate | None:
        result = await self.db.execute(
            select(EmailTemplate).where(
                EmailTemplate.id == template_id,
                EmailTemplate.user_id == user_id,
                EmailTemplate.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def build_context(self, lead: Lead, unsubscribe_url: str) -> dict:
        full_name = " ".join(
            part for part in (lead.first_name, lead.last_name) if part
        )
        context = {
            "email": lead.email,
            "name": full_name or lead.first_name or "",
            "first_name": lead.first_name or "",
            "last_name": lead.last_name or "",
            "company": lead.company or "",
            "unsubscribe_url": unsubscribe_url,
        }
        if lead.custom_fields:
            context.update(lead.custom_fields)
        return context

    def render_message(
        self,
        template: EmailTemplate,
        subject_line: str,
        lead: Lead,
        unsubscribe_url: str,
    ) -> dict[str, str | None]:
        """Render body from message template and subject from subject pool."""
        context = self.build_context(lead, unsubscribe_url)
        self.validate_no_deceptive_subject(subject_line)
        subject = self.env.from_string(subject_line).render(**context)
        html = self.env.from_string(template.html_template).render(**context)
        text = None
        if template.text_template:
            text = self.env.from_string(template.text_template).render(**context)
        return {"subject": subject, "html": html, "text": text}

    def render(
        self,
        template: EmailTemplate,
        lead: Lead,
        unsubscribe_url: str,
    ) -> dict[str, str | None]:
        subject_template = template.subject_template or "Hello {{first_name}}"
        return self.render_message(template, subject_template, lead, unsubscribe_url)

    async def create(
        self,
        user_id: UUID,
        name: str,
        html_template: str,
        text_template: str | None = None,
        subject_template: str | None = None,
    ) -> EmailTemplate:
        if subject_template:
            self.validate_no_deceptive_subject(subject_template)
        template = EmailTemplate(
            user_id=user_id,
            name=name,
            subject_template=subject_template,
            html_template=html_template,
            text_template=text_template,
        )
        self.db.add(template)
        await self.db.flush()
        return template
