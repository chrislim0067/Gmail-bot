"""Reply sync and listing."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.dependencies import CurrentUser, DbSession
from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccount
from app.models.lead import Lead
from app.models.reply_event import ReplyEvent
from app.models.sent_email import SentEmail
from app.schemas.analytics import ReplyOut, ReplySyncResponse
from app.services.reply_sync_service import sync_replies as do_sync_replies

router = APIRouter(tags=["replies"])


@router.post("/gmail/accounts/{account_id}/sync-replies", response_model=ReplySyncResponse)
async def sync_replies(account_id: UUID, current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(GmailAccount).where(
            GmailAccount.id == account_id,
            GmailAccount.user_id == current_user.id,
            GmailAccount.deleted_at.is_(None),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        outcome = await do_sync_replies(db, account_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ReplySyncResponse(**outcome)


@router.get("/replies")
async def list_replies(
    current_user: CurrentUser,
    db: DbSession,
    campaign_id: UUID | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    campaigns_result = await db.execute(
        select(Campaign.id, Campaign.name).where(Campaign.user_id == current_user.id)
    )
    campaign_rows = campaigns_result.all()
    campaign_ids = [row[0] for row in campaign_rows]
    campaign_names = {row[0]: row[1] for row in campaign_rows}

    if campaign_id:
        if campaign_id not in campaign_ids:
            raise HTTPException(status_code=404, detail="Campaign not found")
        campaign_ids = [campaign_id]

    if not campaign_ids:
        return {"items": [], "page": page, "limit": limit, "total": 0, "pages": 1}

    sent_result = await db.execute(
        select(SentEmail.id).where(SentEmail.campaign_id.in_(campaign_ids))
    )
    sent_ids = list(sent_result.scalars().all())
    if not sent_ids:
        return {"items": [], "page": page, "limit": limit, "total": 0, "pages": 1}

    count_result = await db.execute(
        select(func.count(ReplyEvent.id)).where(ReplyEvent.sent_email_id.in_(sent_ids))
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(ReplyEvent)
        .where(ReplyEvent.sent_email_id.in_(sent_ids))
        .order_by(ReplyEvent.received_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = []
    for reply in result.scalars():
        sent_result = await db.execute(
            select(SentEmail).where(SentEmail.id == reply.sent_email_id)
        )
        sent = sent_result.scalar_one_or_none()
        lead_email = None
        if sent:
            lead_result = await db.execute(select(Lead.email).where(Lead.id == sent.lead_id))
            lead_email = lead_result.scalar_one_or_none()
        items.append(
            ReplyOut(
                id=reply.id,
                sent_email_id=reply.sent_email_id,
                from_email=reply.from_email,
                snippet=reply.snippet,
                received_at=reply.received_at.isoformat(),
                campaign_id=sent.campaign_id if sent else None,
                campaign_name=(
                    campaign_names.get(sent.campaign_id) if sent else None
                ),
                lead_email=lead_email,
                subject=sent.subject if sent else None,
                gmail_account_id=sent.gmail_account_id if sent else None,
            )
        )
    pages = max(1, (total + limit - 1) // limit)
    return {"items": items, "page": page, "limit": limit, "total": total, "pages": pages}
