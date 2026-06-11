"""Lead CSV import tests."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccountPool
from app.models.lead import Lead
from app.models.template import EmailTemplate
from app.services.lead_service import LeadService, _parse_name_fields


def test_parse_name_column():
    first, last = _parse_name_fields({"email": "a@b.com", "name": "Chris"})
    assert first == "Chris"
    assert last is None


def test_parse_first_last_columns():
    first, last = _parse_name_fields(
        {"email": "a@b.com", "first_name": "Chris", "last_name": "Lim"}
    )
    assert first == "Chris"
    assert last == "Lim"


@pytest.mark.asyncio
async def test_import_csv_with_name_column(
    db_session: AsyncSession, test_user
):
    template = EmailTemplate(
        user_id=test_user.id,
        name="Lead Template",
        subject_template="Hi",
        html_template="<p>{{unsubscribe_url}}</p>",
    )
    pool = GmailAccountPool(user_id=test_user.id, name="Lead Pool")
    db_session.add_all([template, pool])
    await db_session.flush()
    campaign = Campaign(
        user_id=test_user.id,
        name="Lead Import Campaign",
        template_id=template.id,
        campaign_account_pool_id=pool.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    svc = LeadService(db_session)
    batch = await svc.create_import_batch(
        campaign,
        test_user.id,
        "Candidates.csv",
        compliance_acknowledged=True,
    )
    result = await svc.process_csv(
        batch,
        campaign,
        "email,name\ntest@example.com,Chris\n",
    )
    assert result["imported"] == 1

    lead = (
        await db_session.execute(
            select(Lead).where(Lead.campaign_id == campaign.id)
        )
    ).scalar_one()
    assert lead.first_name == "Chris"
