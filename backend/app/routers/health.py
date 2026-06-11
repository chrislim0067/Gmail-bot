"""Account health and platform health probes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, text

from app.dependencies import CurrentUser, DbSession
from app.models.gmail_account import GmailAccount
from app.models.health_event import AccountHealthEvent
from app.schemas.analytics import HealthAccountOut, HealthEventOut
from app.services.redis_lock_service import RedisLockService
from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def health_live():
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready():
    redis_ok = await RedisLockService().ping()
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    status = "ok" if redis_ok and db_ok else "degraded"
    return {
        "status": status,
        "checks": {"database": db_ok, "redis": redis_ok},
    }


@router.get("/health/accounts")
async def health_accounts(current_user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(GmailAccount).where(
            GmailAccount.user_id == current_user.id,
            GmailAccount.deleted_at.is_(None),
        )
    )
    items = []
    for acc in result.scalars():
        alerts = []
        if acc.health_score < 30:
            alerts.append("health_score_low")
        if acc.review_required:
            alerts.append("review_required")
        if acc.status != "active":
            alerts.append(f"status_{acc.status}")
        items.append(
            HealthAccountOut(
                id=acc.id,
                email=acc.email,
                health_score=acc.health_score,
                account_tier=acc.account_tier,
                status=acc.status,
                risk_level=acc.risk_level,
                review_required=acc.review_required,
                bounce_rate_7d=float(acc.bounce_rate_7d),
                error_rate_7d=float(acc.error_rate_7d),
                alerts=alerts,
            )
        )
    return {"items": items}


@router.get("/health/accounts/{account_id}/events")
async def health_account_events(
    account_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
):
    result = await db.execute(
        select(GmailAccount).where(
            GmailAccount.id == account_id,
            GmailAccount.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    events_result = await db.execute(
        select(AccountHealthEvent)
        .where(AccountHealthEvent.gmail_account_id == account_id)
        .order_by(AccountHealthEvent.recorded_at.desc())
        .limit(50)
    )
    items = [
        HealthEventOut(
            id=e.id,
            score=e.score,
            event_type=e.event_type,
            bounce_rate_24h=float(e.bounce_rate_24h) if e.bounce_rate_24h else None,
            send_count_24h=e.send_count_24h,
            failure_count_24h=e.failure_count_24h,
            details=e.details,
            recorded_at=e.recorded_at.isoformat(),
        )
        for e in events_result.scalars()
    ]
    return {"items": items}
