"""Random template + subject composition tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_subject import EmailSubject
from app.models.lead import Lead
from app.models.template import EmailTemplate
from app.services.outreach_compose_service import (
    SIGNATURE_HTML,
    SIGNATURE_TEXT,
    OutreachComposeService,
)


@pytest.mark.asyncio
async def test_compose_picks_random_template_and_subject(
    db_session: AsyncSession, test_user
):
    templates = [
        EmailTemplate(
            user_id=test_user.id,
            name=f"Message {i}",
            html_template=(
                f"<p>Body {i}</p>"
                '<p style="margin-top:24px;font-size:12px;color:#6b7280;">'
                '<a href="{{unsubscribe_url}}">Unsubscribe from these emails</a></p>'
            ),
            text_template=f"Body {i}\n\n---\nUnsubscribe: {{{{unsubscribe_url}}}}",
        )
        for i in range(2)
    ]
    subjects = [
        EmailSubject(user_id=test_user.id, text=f"Subject {i} for {{{{name}}}}")
        for i in range(2)
    ]
    db_session.add_all(templates + subjects)
    await db_session.flush()

    lead = Lead(
        campaign_id=templates[0].id,
        email="alex@example.com",
        normalized_email="alex@example.com",
        first_name="Alex",
    )
    svc = OutreachComposeService(db_session)
    rendered = await svc.compose_for_lead(test_user.id, lead, "https://example.com/unsub")

    assert rendered["subject"]
    assert "Alex" in rendered["subject"]
    assert SIGNATURE_HTML in rendered["html"]
    assert SIGNATURE_TEXT in (rendered["text"] or "")
    assert "Thanks" in rendered["html"]
    assert "Chris" in rendered["html"]
    assert "Unsubscribe from these emails" not in rendered["html"]
    assert "Unsubscribe:" not in (rendered["text"] or "")
