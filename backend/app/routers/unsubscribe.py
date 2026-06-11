"""Public unsubscribe and suppression management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select, update

from app.dependencies import CurrentUser, DbSession
from app.models.lead import Lead
from app.models.send_job import SendJob
from app.models.unsubscribe import UnsubscribeList
from app.schemas.common import MessageResponse
from app.services.suppression_service import SuppressionService
from app.utils.jwt_unsubscribe import UnsubscribeTokenError, verify_unsubscribe_token

router = APIRouter(tags=["unsubscribe"])


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_page(token: str):
    return HTMLResponse(
        content="""
        <html><body>
        <h1>Unsubscribe</h1>
        <p>Click below to confirm you no longer wish to receive emails.</p>
        <form method="POST" action="">
          <button type="submit">Confirm Unsubscribe</button>
        </form>
        </body></html>
        """,
        status_code=200,
    )


@router.post("/unsubscribe/{token}", response_model=MessageResponse)
async def unsubscribe_post(token: str, request: Request, db: DbSession):
    try:
        payload = verify_unsubscribe_token(token)
    except UnsubscribeTokenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user_id = UUID(payload["uid"])
    campaign_id = UUID(payload["cid"])
    lead_id = UUID(payload["sub"])
    email = payload["email"]

    suppression = SuppressionService(db)
    await suppression.add_unsubscribe(
        user_id=user_id,
        email=email,
        source="link",
        campaign_id=campaign_id,
        ip_address=request.client.host if request.client else None,
    )

    lead_result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    if lead:
        lead.status = "unsubscribed"
        lead.do_not_contact_reason = "unsubscribed"

    await db.execute(
        update(SendJob)
        .where(
            SendJob.lead_id == lead_id,
            SendJob.status.in_(["pending", "locked"]),
        )
        .values(status="cancelled")
    )
    await db.flush()
    return MessageResponse(status="unsubscribed")


@router.get("/unsubscribes")
async def list_unsubscribes(
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    query = select(UnsubscribeList).where(UnsubscribeList.user_id == current_user.id)
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0
    result = await db.execute(
        query.order_by(UnsubscribeList.unsubscribed_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [
        {
            "id": str(u.id),
            "email": u.email,
            "source": u.source,
            "campaign_id": str(u.campaign_id) if u.campaign_id else None,
            "unsubscribed_at": u.unsubscribed_at.isoformat(),
        }
        for u in result.scalars()
    ]
    return {"items": items, "total": total, "page": page, "limit": limit}


@router.post("/unsubscribes/manual", status_code=201)
async def manual_unsubscribe(
    body: dict,
    current_user: CurrentUser,
    db: DbSession,
):
    email = body.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    suppression = SuppressionService(db)
    entry = await suppression.add_unsubscribe(
        user_id=current_user.id,
        email=email,
        source="manual",
    )
    return {"id": str(entry.id), "email": entry.email, "status": "suppressed"}


@router.delete("/unsubscribes/{entry_id}", status_code=204)
async def remove_unsubscribe(
    entry_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    suppression = SuppressionService(db)
    removed = await suppression.remove_unsubscribe(current_user.id, entry_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Suppression entry not found")
