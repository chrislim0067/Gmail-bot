"""Campaign preflight check tests."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account_pool import GmailAccountPool
from app.models.campaign import Campaign
from app.models.template import EmailTemplate
from app.services.preflight_service import PreflightService


@pytest.mark.asyncio
async def test_preflight_blocks_invalid_campaign(db_session: AsyncSession, test_user):
    template = EmailTemplate(
        user_id=test_user.id,
        name="Bad Template",
        subject_template="Hello",
        html_template="<p>No unsubscribe link here</p>",
    )
    pool = GmailAccountPool(user_id=test_user.id, name="Empty Pool")
    db_session.add_all([template, pool])
    await db_session.flush()
    campaign = Campaign(
        user_id=test_user.id,
        name="Invalid Campaign",
        template_id=template.id,
        campaign_account_pool_id=pool.id,
        status="draft",
    )
    db_session.add(campaign)
    await db_session.flush()

    preflight = PreflightService(db_session)
    result = await preflight.run(campaign.id)
    assert result["passed"] is False
    check_names = [c["name"] for c in result["checks"]]
    assert "leads" in check_names or "subject_lines" in check_names


@pytest.mark.asyncio
async def test_import_requires_compliance_acknowledgement(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user,
):
    template = EmailTemplate(
        user_id=test_user.id,
        name="Import Template",
        subject_template="Hi",
        html_template="<p>{{unsubscribe_url}}</p>",
    )
    pool = GmailAccountPool(user_id=test_user.id, name="Import Pool")
    db_session.add_all([template, pool])
    await db_session.flush()
    campaign = Campaign(
        user_id=test_user.id,
        name="Import Campaign",
        template_id=template.id,
        campaign_account_pool_id=pool.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    csv_content = "email,first_name\ntest@example.com,Test\n"
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/leads/import",
        headers=auth_headers,
        data={"compliance_acknowledged": "false"},
        files={"file": ("leads.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_role_based_email_blocked(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user,
):
    template = EmailTemplate(
        user_id=test_user.id,
        name="Role Template",
        subject_template="Hi",
        html_template="<p>{{unsubscribe_url}}</p>",
    )
    pool = GmailAccountPool(user_id=test_user.id, name="Role Pool")
    db_session.add_all([template, pool])
    await db_session.flush()
    campaign = Campaign(
        user_id=test_user.id,
        name="Role Campaign",
        template_id=template.id,
        campaign_account_pool_id=pool.id,
    )
    db_session.add(campaign)
    await db_session.flush()

    csv_content = "email\ninfo@company.com\n"
    response = await client.post(
        f"/api/v1/campaigns/{campaign.id}/leads/import",
        headers=auth_headers,
        data={"compliance_acknowledged": "true"},
        files={"file": ("leads.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 202
    batch_id = response.json()["import_batch_id"]
    status = await client.get(
        f"/api/v1/campaigns/{campaign.id}/leads/import/{batch_id}",
        headers=auth_headers,
    )
    assert status.json()["skipped"] >= 1


@pytest.mark.asyncio
async def test_bounce_parser_gmail_mailer_daemon():
    from pathlib import Path

    from app.gmail.bounce_parser import parse_bounce_message

    fixture = Path(__file__).parent / "fixtures" / "bounce_gmail_mailer_daemon.eml"
    result = parse_bounce_message(fixture.read_bytes())
    assert result is not None
    assert "bounced.recipient@example.com" in result.bounced_email
    assert result.bounce_type == "hard"


@pytest.mark.asyncio
async def test_bounce_parser_soft_bounce():
    from pathlib import Path

    from app.gmail.bounce_parser import parse_bounce_message

    fixture = Path(__file__).parent / "fixtures" / "bounce_soft.eml"
    result = parse_bounce_message(fixture.read_bytes())
    assert result is not None
    assert result.bounce_type == "soft"
    assert result.smtp_status_code == "4.4.1"


@pytest.mark.asyncio
async def test_bounce_parser_malformed_message():
    from pathlib import Path

    from app.gmail.bounce_parser import parse_bounce_message

    fixture = Path(__file__).parent / "fixtures" / "bounce_malformed.eml"
    result = parse_bounce_message(fixture.read_bytes())
    assert result is not None
    assert result.detection_method == "malformed"


@pytest.mark.asyncio
async def test_global_risk_budget_pauses_new_campaigns(db_session: AsyncSession, test_user):
    from app.config import get_settings
    from app.services.risk_service import RiskService

    settings = get_settings()
    risk = RiskService(db_session)
    await risk.record_event(
        user_id=test_user.id,
        event_type="auth_error",
        severity="critical",
        score_delta=settings.global_risk_score_threshold,
    )
    blocked = await risk.is_risk_blocked(test_user.id)
    assert blocked is True
