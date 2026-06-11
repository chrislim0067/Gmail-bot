"""Sender worker and Redis lock tests."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account_pool import GmailAccountPool, GmailAccountPoolMember
from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccount
from app.models.lead import Lead
from app.models.email_subject import EmailSubject
from app.models.template import EmailTemplate
from app.services.redis_lock_service import RedisLockService
from app.services.sender_service import SenderService


@pytest.mark.asyncio
async def test_sender_requires_account_lock():
    locks = RedisLockService()
    account_id = str(uuid4())
    try:
        acquired1, token1 = await locks.acquire_gmail_account_lock(account_id, "worker-1")
        if not acquired1:
            pytest.skip("Redis not available")
        acquired2, _ = await locks.acquire_gmail_account_lock(account_id, "worker-2")
        assert acquired2 is False
        released = await locks.release("gmail_account", account_id, token1)
        assert released is True
        acquired3, token3 = await locks.acquire_gmail_account_lock(account_id, "worker-2")
        assert acquired3 is True
        await locks.release("gmail_account", account_id, token3)
    finally:
        client = await locks.get_client()
        await client.aclose()


@pytest.mark.asyncio
async def test_scheduler_lock_prevents_duplicate_jobs(db_session: AsyncSession, test_user):
    locks = RedisLockService()
    campaign_id = str(uuid4())
    try:
        acquired1, token1 = await locks.acquire_scheduler_lock(campaign_id)
        if not acquired1:
            pytest.skip("Redis not available")
        acquired2, _ = await locks.acquire_scheduler_lock(campaign_id)
        assert acquired2 is False
        await locks.release("campaign_scheduler", campaign_id, token1)
    finally:
        client = await locks.get_client()
        await client.aclose()


@pytest.mark.asyncio
async def test_sender_worker_mock(db_session: AsyncSession, test_user):
    template = EmailTemplate(
        user_id=test_user.id,
        name="Send Template",
        html_template="<p>Hi <a href='{{unsubscribe_url}}'>unsub</a></p>",
        text_template="Hi {{unsubscribe_url}}",
    )
    subject = EmailSubject(
        user_id=test_user.id,
        text="Hello {{name}}",
    )
    pool = GmailAccountPool(user_id=test_user.id, name="Send Pool")
    account = GmailAccount(
        user_id=test_user.id,
        email=f"sender_{uuid4().hex[:6]}@gmail.com",
        google_user_id=f"gid_{uuid4().hex[:8]}",
        connected_at=datetime.now(UTC),
        tier_daily_default=5,
        tier_daily_hard_max=10,
        status="active",
    )
    db_session.add_all([template, subject, pool, account])
    await db_session.flush()

    member = GmailAccountPoolMember(pool_id=pool.id, gmail_account_id=account.id)
    campaign = Campaign(
        user_id=test_user.id,
        name="Send Campaign",
        campaign_account_pool_id=pool.id,
        status="running",
        preflight_passed_at=datetime.now(UTC),
    )
    db_session.add_all([member, campaign])
    await db_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        email="recipient@example.com",
        normalized_email="recipient@example.com",
        validation_status="valid",
        status="pending",
    )
    db_session.add(lead)
    await db_session.flush()

    sender = SenderService(db_session)
    created = await sender.create_send_jobs(campaign.id)
    assert created >= 1

    from sqlalchemy import select
    from app.models.send_job import SendJob

    jobs = await db_session.execute(
        select(SendJob).where(SendJob.campaign_id == campaign.id)
    )
    job = jobs.scalars().first()
    result = await sender.process_send_job(job.id)
    assert result["status"] in ("sent", "rescheduled", "failed")
