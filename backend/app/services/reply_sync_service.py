"""Reply sync — matches replies to sent emails via Message-ID, thread, or sender."""

import re
from datetime import UTC, datetime
from email.utils import parseaddr
from uuid import UUID

from sqlalchemy import func, or_, select

from app.config import get_settings
from app.gmail.client import get_gmail_client
from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccount
from app.models.gmail_sync_cursor import GmailSyncCursor
from app.models.lead import Lead
from app.models.reply_event import ReplyEvent
from app.models.sent_email import SentEmail

_MESSAGE_ID_RE = re.compile(r"<[^>]+>")


def _extract_message_ids(value: str | None) -> list[str]:
    if not value:
        return []
    return [mid.strip() for mid in _MESSAGE_ID_RE.findall(value) if mid.strip()]


def _sender_email(from_header: str | None) -> str | None:
    if not from_header:
        return None
    _, addr = parseaddr(from_header)
    return addr.lower() if addr else None


async def _find_sent_email(
    session,
    gmail_account_id: UUID,
    *,
    candidate_ids: list[str],
    thread_id: str | None,
    from_header: str | None,
) -> SentEmail | None:
    """Match an inbound message to a sent email using multiple signals."""
    if candidate_ids:
        result = await session.execute(
            select(SentEmail).where(
                SentEmail.gmail_account_id == gmail_account_id,
                or_(*[SentEmail.rfc_message_id == mid for mid in candidate_ids]),
            )
        )
        sent = result.scalar_one_or_none()
        if sent:
            return sent

    if thread_id:
        result = await session.execute(
            select(SentEmail)
            .where(
                SentEmail.gmail_account_id == gmail_account_id,
                SentEmail.thread_id == thread_id,
            )
            .order_by(SentEmail.sent_at.desc())
        )
        sent = result.scalars().first()
        if sent:
            return sent

    sender = _sender_email(from_header)
    if sender:
        result = await session.execute(
            select(SentEmail)
            .where(
                SentEmail.gmail_account_id == gmail_account_id,
                func.lower(SentEmail.recipient_email) == sender,
            )
            .order_by(SentEmail.sent_at.desc())
            .limit(1)
        )
        sent = result.scalar_one_or_none()
        if sent:
            return sent

    return None


async def _backfill_rfc_message_ids(session, gmail_account_id: UUID) -> int:
    """Fix sent emails that stored our MIME Message-ID instead of Gmail's."""
    settings = get_settings()
    if settings.use_mock_gmail:
        return 0

    result = await session.execute(
        select(SentEmail).where(
            SentEmail.gmail_account_id == gmail_account_id,
            SentEmail.gmail_message_id.isnot(None),
        )
    )
    client = get_gmail_client()
    updated = 0
    for sent in result.scalars():
        if not sent.gmail_message_id:
            continue
        try:
            msg = await client.get_message(gmail_account_id, sent.gmail_message_id)
            actual_id = msg.get("headers", {}).get("Message-ID")
            if actual_id and actual_id != sent.rfc_message_id:
                sent.rfc_message_id = actual_id
                updated += 1
        except Exception:
            continue
    return updated


async def sync_replies(session, gmail_account_id: UUID) -> dict:
    settings = get_settings()
    account = await session.get(GmailAccount, gmail_account_id)
    if account is None:
        return {"new_replies": 0, "messages_scanned": 0, "reason": "account_not_found"}

    if settings.use_mock_gmail:
        return {"new_replies": 0, "messages_scanned": 0, "reason": "mock_no_replies"}

    await _backfill_rfc_message_ids(session, gmail_account_id)

    client = get_gmail_client()
    # Incoming mail only — exclude our own outbound messages in Sent.
    message_refs = await client.list_messages(
        gmail_account_id,
        query="in:inbox newer_than:30d -from:me",
        max_results=100,
    )

    cursor_result = await session.execute(
        select(GmailSyncCursor).where(GmailSyncCursor.gmail_account_id == gmail_account_id)
    )
    cursor = cursor_result.scalar_one_or_none()

    new_replies = 0
    for ref in message_refs:
        msg = await client.get_message(gmail_account_id, ref["id"])
        headers = msg.get("headers", {})
        candidate_ids = _extract_message_ids(headers.get("In-Reply-To"))
        candidate_ids.extend(_extract_message_ids(headers.get("References")))

        sent_email = await _find_sent_email(
            session,
            gmail_account_id,
            candidate_ids=candidate_ids,
            thread_id=msg.get("thread_id"),
            from_header=headers.get("From"),
        )
        if sent_email is None:
            continue

        existing = await session.execute(
            select(ReplyEvent.id).where(
                ReplyEvent.sent_email_id == sent_email.id,
                ReplyEvent.gmail_message_id == msg.get("id"),
            )
        )
        if existing.scalar_one_or_none():
            continue

        from_header = headers.get("From", sent_email.recipient_email)
        reply = ReplyEvent(
            sent_email_id=sent_email.id,
            gmail_message_id=msg.get("id", ""),
            from_email=from_header[:255],
            snippet=(msg.get("snippet") or "")[:500],
            received_at=datetime.now(UTC),
        )
        session.add(reply)
        new_replies += 1

        lead = await session.get(Lead, sent_email.lead_id)
        if lead and lead.status not in ("replied", "unsubscribed", "bounced"):
            lead.status = "replied"

        campaign = await session.get(Campaign, sent_email.campaign_id)
        if campaign:
            campaign.replied_count += 1

    now = datetime.now(UTC)
    if cursor is None:
        cursor = GmailSyncCursor(
            gmail_account_id=gmail_account_id,
            reply_sync_history_id=message_refs[0]["id"] if message_refs else None,
            bounce_sync_after=now,
        )
        session.add(cursor)
    else:
        if message_refs:
            cursor.reply_sync_history_id = message_refs[0]["id"]
        cursor.bounce_sync_after = now

    return {
        "new_replies": new_replies,
        "messages_scanned": len(message_refs),
        "reason": "ok",
    }


async def sync_all_accounts(session) -> dict:
    result = await session.execute(
        select(GmailAccount.id).where(
            GmailAccount.deleted_at.is_(None),
            GmailAccount.status == "active",
        )
    )
    total_replies = 0
    accounts = 0
    for account_id in result.scalars():
        outcome = await sync_replies(session, account_id)
        total_replies += outcome.get("new_replies", 0)
        accounts += 1
    return {"accounts_synced": accounts, "new_replies": total_replies}
