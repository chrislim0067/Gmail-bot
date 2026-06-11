"""Bounce detection using multi-signal parser."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.config import get_settings
from app.gmail.bounce_parser import parse_bounce_raw
from app.gmail.mock_client import get_message_raw, list_recent_messages
from app.models.bounce_event import BounceEvent
from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccount
from app.models.gmail_sync_cursor import GmailSyncCursor
from app.models.lead import Lead


async def detect_bounces(session, gmail_account_id: UUID) -> dict:
    settings = get_settings()
    account = await session.get(GmailAccount, gmail_account_id)
    if account is None:
        return {"bounces_recorded": 0, "reason": "account_not_found"}

    cursor_result = await session.execute(
        select(GmailSyncCursor).where(GmailSyncCursor.gmail_account_id == gmail_account_id)
    )
    cursor = cursor_result.scalar_one_or_none()

    bounces_recorded = 0
    messages = list_recent_messages(
        account.email,
        query="from:mailer-daemon OR from:postmaster",
        max_results=50,
    )

    if settings.use_mock_gmail and not messages:
        return {"bounces_recorded": 0, "reason": "mock_no_bounces"}

    for msg in messages:
        raw = msg.get("raw")
        if raw is None:
            message_id = msg.get("id")
            if message_id:
                raw = get_message_raw(account.email, message_id)
        if not raw:
            continue

        parsed = parse_bounce_raw(raw)
        if parsed is None:
            continue
        if not parsed.bounced_email:
            continue

        existing = await session.execute(
            select(BounceEvent.id).where(
                BounceEvent.gmail_account_id == gmail_account_id,
                BounceEvent.bounced_email == parsed.bounced_email,
                BounceEvent.detection_method == parsed.detection_method,
            )
        )
        if existing.scalar_one_or_none():
            continue

        event = BounceEvent(
            gmail_account_id=gmail_account_id,
            bounced_email=parsed.bounced_email,
            bounce_type=parsed.bounce_type,
            smtp_status_code=parsed.smtp_status_code,
            detection_method=parsed.detection_method,
            diagnostic=parsed.diagnostic,
            raw_headers=parsed.raw_headers,
            detected_at=datetime.now(UTC),
        )
        session.add(event)
        bounces_recorded += 1

        lead_result = await session.execute(
            select(Lead).where(
                Lead.normalized_email == parsed.bounced_email,
                Lead.deleted_at.is_(None),
            )
        )
        for lead in lead_result.scalars():
            if parsed.bounce_type == "hard":
                lead.status = "bounced"
                lead.do_not_contact_reason = "hard_bounce"
            campaign = await session.get(Campaign, lead.campaign_id)
            if campaign and parsed.bounce_type == "hard":
                campaign.bounced_count += 1

    now = datetime.now(UTC)
    if cursor is None:
        session.add(
            GmailSyncCursor(
                gmail_account_id=gmail_account_id,
                bounce_sync_after=now,
            )
        )
    else:
        cursor.bounce_sync_after = now

    return {"bounces_recorded": bounces_recorded}
