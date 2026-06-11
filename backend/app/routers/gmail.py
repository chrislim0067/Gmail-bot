"""Gmail OAuth, accounts, and account pools."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import get_settings
from app.dependencies import CurrentUser, DbSession
from app.models.gmail_account import GmailAccount
from app.schemas.common import MessageResponse
from app.schemas.gmail import (
    GmailAccountDetailOut,
    GmailAccountLimitsUpdate,
    GmailAccountOut,
    GmailAccountPauseRequest,
    GmailAccountReviewRequest,
    GmailAccountSetTierRequest,
    PoolCreate,
    PoolDetailOut,
    PoolMemberCreate,
    PoolMemberOut,
    PoolOut,
    PoolUpdate,
)
from app.services.audit_service import AuditService
from app.services.health_service import HealthService
from app.services.oauth_service import (
    OAuthCapExceededError,
    OAuthService,
    OAuthStateError,
    TokenExchangeError,
)
from app.services.pool_service import PoolService
from app.services.rate_limit_service import RateLimitService
from app.services.token_service import TokenService
from app.utils.tier_caps import effective_daily_cap, effective_hourly_cap, get_tier_caps

router = APIRouter(prefix="/gmail", tags=["gmail"])
settings = get_settings()


@router.get("/connect-info")
async def connect_info() -> dict:
    """Public info for the Connect Gmail UI (mock vs real OAuth)."""
    client_id = settings.google_client_id
    redirect_uri = settings.google_redirect_uri
    return {
        "use_mock_gmail": settings.use_mock_gmail,
        "oauth_publishing_status": settings.google_oauth_publishing_status,
        "redirect_uri": redirect_uri,
        "redirect_uris_for_google_console": [
            redirect_uri,
            "http://127.0.0.1:8000/api/v1/gmail/callback",
        ],
        "google_client_id": client_id,
        "google_client_configured": not client_id.startswith("TODO"),
        "google_client_edit_url": (
            f"https://console.cloud.google.com/auth/clients/"
            f"{client_id}?project=coldmail-auto-project"
            if not client_id.startswith("TODO")
            else "https://console.cloud.google.com/apis/credentials"
        ),
    }


@router.get("/connect")
async def connect_gmail(
    current_user: CurrentUser,
    db: DbSession,
    redirect_uri: str | None = None,
):
    oauth = OAuthService(db)
    try:
        url = await oauth.create_connect_url(current_user.id, redirect_uri)
    except OAuthCapExceededError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
async def oauth_callback(
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    if error:
        return RedirectResponse(
            url=f"{settings.frontend_url}/accounts?error={error}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    oauth = OAuthService(db)
    try:
        await oauth.connect_account(code, state)
    except OAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TokenExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return RedirectResponse(
        url=f"{settings.frontend_url}/accounts?connected=1",
        status_code=302,
    )


@router.post("/mock-connect")
async def mock_connect(
    current_user: CurrentUser,
    db: DbSession,
    state: str = Query(...),
):
    if not settings.use_mock_gmail:
        raise HTTPException(status_code=400, detail="Mock connect disabled")
    oauth = OAuthService(db)
    try:
        account = await oauth.mock_connect(current_user.id, state)
    except OAuthStateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(account.id), "email": account.email, "status": account.status}


@router.delete("/accounts/mock", response_model=MessageResponse)
async def purge_mock_accounts(current_user: CurrentUser, db: DbSession):
    """Remove all mock.dev accounts created during USE_MOCK_GMAIL testing."""
    result = await db.execute(
        select(GmailAccount).where(
            GmailAccount.user_id == current_user.id,
            GmailAccount.email.like("mock.user.%@gmail.com"),
            GmailAccount.deleted_at.is_(None),
        )
    )
    accounts = result.scalars().all()
    oauth = OAuthService(db)
    for account in accounts:
        await oauth.revoke_account(account)
    return MessageResponse(status=f"removed_{len(accounts)}_mock_accounts")


@router.get("/accounts")
async def list_accounts(current_user: CurrentUser, db: DbSession) -> dict:
    result = await db.execute(
        select(GmailAccount).where(
            GmailAccount.user_id == current_user.id,
            GmailAccount.deleted_at.is_(None),
        )
    )
    accounts = result.scalars().all()
    rate_limit = RateLimitService()
    oauth = OAuthService(db)
    items = []
    for acc in accounts:
        scopes = await oauth.get_granted_scopes(acc.id)
        sent_today = await rate_limit.get_account_daily_count(acc.id)
        effective_daily = effective_daily_cap(acc.account_tier, acc.daily_send_limit)
        effective_hourly = effective_hourly_cap(acc.account_tier, acc.hourly_send_limit)
        items.append(
            GmailAccountOut(
                id=acc.id,
                email=acc.email,
                status=acc.status,
                account_tier=acc.account_tier,
                risk_level=acc.risk_level,
                review_required=acc.review_required,
                health_score=acc.health_score,
                tier_daily_default=acc.tier_daily_default,
                tier_daily_hard_max=acc.tier_daily_hard_max,
                daily_send_limit=acc.daily_send_limit,
                hourly_send_limit=acc.hourly_send_limit,
                connected_at=acc.connected_at,
                consecutive_success_days=acc.consecutive_success_days,
                bounce_rate_7d=acc.bounce_rate_7d,
                error_rate_7d=acc.error_rate_7d,
                last_send_at=acc.last_send_at,
                granted_scopes=scopes,
                sent_today=sent_today,
                sent_this_hour=await rate_limit.get_account_hourly_count(
                    acc.id, acc.last_send_at
                ),
                effective_daily_send_limit=effective_daily,
                effective_hourly_send_limit=effective_hourly,
                remaining_today=max(0, effective_daily - sent_today),
            )
        )
    return {"items": items}


async def _get_owned_account(
    db: DbSession, user_id: UUID, account_id: UUID
) -> GmailAccount:
    result = await db.execute(
        select(GmailAccount).where(
            GmailAccount.id == account_id,
            GmailAccount.user_id == user_id,
            GmailAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/accounts/{account_id}", response_model=GmailAccountDetailOut)
async def get_account(account_id: UUID, current_user: CurrentUser, db: DbSession):
    account = await _get_owned_account(db, current_user.id, account_id)
    oauth = OAuthService(db)
    scopes = await oauth.get_granted_scopes(account.id)
    return GmailAccountDetailOut(
        id=account.id,
        email=account.email,
        status=account.status,
        account_tier=account.account_tier,
        risk_level=account.risk_level,
        review_required=account.review_required,
        health_score=account.health_score,
        tier_daily_default=account.tier_daily_default,
        tier_daily_hard_max=account.tier_daily_hard_max,
        daily_send_limit=account.daily_send_limit,
        hourly_send_limit=account.hourly_send_limit,
        connected_at=account.connected_at,
        consecutive_success_days=account.consecutive_success_days,
        bounce_rate_7d=account.bounce_rate_7d,
        error_rate_7d=account.error_rate_7d,
        last_send_at=account.last_send_at,
        granted_scopes=scopes,
        display_name=account.display_name,
        paused_reason=account.paused_reason,
        lifetime_send_count=account.lifetime_send_count,
        reply_rate_7d=account.reply_rate_7d,
    )


@router.patch("/accounts/{account_id}", response_model=GmailAccountOut)
async def update_account_limits(
    account_id: UUID,
    body: GmailAccountLimitsUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    account = await _get_owned_account(db, current_user.id, account_id)
    caps = get_tier_caps(account.account_tier)
    if body.daily_send_limit is not None:
        if body.daily_send_limit < 1:
            raise HTTPException(status_code=400, detail="Daily limit must be at least 1")
        if body.daily_send_limit > caps.daily_hard_max:
            raise HTTPException(status_code=400, detail="Exceeds tier hard max")
        account.daily_send_limit = body.daily_send_limit
    if body.hourly_send_limit is not None:
        if body.hourly_send_limit < 1:
            raise HTTPException(status_code=400, detail="Hourly limit must be at least 1")
        if body.hourly_send_limit > caps.hourly_cap:
            raise HTTPException(status_code=400, detail="Exceeds tier hourly cap")
        account.hourly_send_limit = body.hourly_send_limit
    await db.flush()
    return GmailAccountOut(
        id=account.id,
        email=account.email,
        status=account.status,
        account_tier=account.account_tier,
        risk_level=account.risk_level,
        review_required=account.review_required,
        health_score=account.health_score,
        tier_daily_default=account.tier_daily_default,
        tier_daily_hard_max=account.tier_daily_hard_max,
        daily_send_limit=account.daily_send_limit,
        hourly_send_limit=account.hourly_send_limit,
        connected_at=account.connected_at,
        consecutive_success_days=account.consecutive_success_days,
        bounce_rate_7d=account.bounce_rate_7d,
        error_rate_7d=account.error_rate_7d,
        last_send_at=account.last_send_at,
    )


@router.post("/accounts/{account_id}/pause", response_model=MessageResponse)
async def pause_account(
    account_id: UUID,
    body: GmailAccountPauseRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    account = await _get_owned_account(db, current_user.id, account_id)
    health = HealthService(db)
    await health.pause_account(account, body.reason)
    return MessageResponse(status="paused")


@router.post("/accounts/{account_id}/resume", response_model=MessageResponse)
async def resume_account(account_id: UUID, current_user: CurrentUser, db: DbSession):
    account = await _get_owned_account(db, current_user.id, account_id)
    if account.status == "auth_error":
        raise HTTPException(status_code=400, detail="Cannot resume auth_error account")
    account.status = "active"
    account.paused_reason = None
    account.paused_at = None
    await AuditService(db).log(
        action="gmail_account.resume",
        resource_type="gmail_account",
        user_id=current_user.id,
        resource_id=account.id,
    )
    await db.flush()
    return MessageResponse(status="active")


@router.post("/accounts/{account_id}/review", response_model=MessageResponse)
async def review_account(
    account_id: UUID,
    body: GmailAccountReviewRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    account = await _get_owned_account(db, current_user.id, account_id)
    if not account.review_required:
        raise HTTPException(status_code=400, detail="Account not in review queue")
    health = HealthService(db)
    if body.approved:
        account.review_required = False
        if body.new_tier:
            await health.set_tier_manual(account, body.new_tier, body.notes or "review approved")
        elif account.account_tier == "restricted":
            account.account_tier = "new"
            caps = get_tier_caps("new")
            account.tier_daily_default = caps.daily_default
            account.tier_daily_hard_max = caps.daily_hard_max
    await AuditService(db).log(
        action="gmail_account.review",
        resource_type="gmail_account",
        user_id=current_user.id,
        resource_id=account.id,
        metadata={"approved": body.approved, "notes": body.notes},
    )
    await db.flush()
    return MessageResponse(status="reviewed")


@router.post("/accounts/{account_id}/set-tier", response_model=GmailAccountOut)
async def set_tier(
    account_id: UUID,
    body: GmailAccountSetTierRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    account = await _get_owned_account(db, current_user.id, account_id)
    health = HealthService(db)
    await health.set_tier_manual(account, body.account_tier, body.reason)
    return GmailAccountOut(
        id=account.id,
        email=account.email,
        status=account.status,
        account_tier=account.account_tier,
        risk_level=account.risk_level,
        review_required=account.review_required,
        health_score=account.health_score,
        tier_daily_default=account.tier_daily_default,
        tier_daily_hard_max=account.tier_daily_hard_max,
        daily_send_limit=account.daily_send_limit,
        hourly_send_limit=account.hourly_send_limit,
        connected_at=account.connected_at,
        consecutive_success_days=account.consecutive_success_days,
        bounce_rate_7d=account.bounce_rate_7d,
        error_rate_7d=account.error_rate_7d,
        last_send_at=account.last_send_at,
    )


@router.post("/accounts/{account_id}/revoke", response_model=MessageResponse)
async def revoke_account(account_id: UUID, current_user: CurrentUser, db: DbSession):
    account = await _get_owned_account(db, current_user.id, account_id)
    oauth = OAuthService(db)
    await oauth.revoke_account(account)
    await AuditService(db).log(
        action="gmail_account.revoke",
        resource_type="gmail_account",
        user_id=current_user.id,
        resource_id=account.id,
    )
    return MessageResponse(status="revoked")


# --- Account Pools ---

pool_router = APIRouter(prefix="/account-pools", tags=["account-pools"])


@pool_router.get("")
async def list_pools(current_user: CurrentUser, db: DbSession) -> dict:
    from app.models.account_pool import GmailAccountPool

    result = await db.execute(
        select(GmailAccountPool).where(GmailAccountPool.user_id == current_user.id)
    )
    pools = result.scalars().all()
    pool_svc = PoolService(db)
    rate_limit = RateLimitService()
    items = []
    for pool in pools:
        items.append(
            PoolOut(
                id=pool.id,
                name=pool.name,
                description=pool.description,
                max_daily_send=pool.max_daily_send,
                max_hourly_send=pool.max_hourly_send,
                active_account_limit=pool.active_account_limit,
                risk_policy=pool.risk_policy,
                status=pool.status,
                member_count=await pool_svc.get_member_count(pool.id),
                sends_today=await rate_limit.get_pool_daily_count(pool.id),
                sends_this_hour=await rate_limit.get_pool_hourly_count(pool.id),
                capacity_remaining=await pool_svc.get_pool_capacity_remaining(pool.id),
            )
        )
    return {"items": items, "total": len(items), "page": 1, "limit": 100, "pages": 1}


@pool_router.post("", response_model=PoolOut, status_code=201)
async def create_pool(body: PoolCreate, current_user: CurrentUser, db: DbSession):
    pool_svc = PoolService(db)
    data = body.model_dump(exclude_none=True)
    pool = await pool_svc.create_pool(current_user.id, data)
    return PoolOut(
        id=pool.id,
        name=pool.name,
        description=pool.description,
        max_daily_send=pool.max_daily_send,
        max_hourly_send=pool.max_hourly_send,
        active_account_limit=pool.active_account_limit,
        risk_policy=pool.risk_policy,
        status=pool.status,
    )


@pool_router.get("/{pool_id}", response_model=PoolDetailOut)
async def get_pool(pool_id: UUID, current_user: CurrentUser, db: DbSession):
    pool_svc = PoolService(db)
    pool = await pool_svc.get_pool(pool_id, current_user.id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    members = [PoolMemberOut.model_validate(m) for m in pool.members]
    rate_limit = RateLimitService()
    return PoolDetailOut(
        id=pool.id,
        name=pool.name,
        description=pool.description,
        max_daily_send=pool.max_daily_send,
        max_hourly_send=pool.max_hourly_send,
        active_account_limit=pool.active_account_limit,
        risk_policy=pool.risk_policy,
        status=pool.status,
        member_count=len(members),
        sends_today=await rate_limit.get_pool_daily_count(pool.id),
        sends_this_hour=await rate_limit.get_pool_hourly_count(pool.id),
        capacity_remaining=await pool_svc.get_pool_capacity_remaining(pool.id),
        members=members,
    )


@pool_router.patch("/{pool_id}", response_model=PoolOut)
async def update_pool(
    pool_id: UUID, body: PoolUpdate, current_user: CurrentUser, db: DbSession
):
    pool_svc = PoolService(db)
    pool = await pool_svc.get_pool(pool_id, current_user.id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(pool, key, value)
    await db.flush()
    return PoolOut.model_validate(pool)


@pool_router.post("/{pool_id}/members", response_model=PoolMemberOut, status_code=201)
async def add_pool_member(
    pool_id: UUID, body: PoolMemberCreate, current_user: CurrentUser, db: DbSession
):
    pool_svc = PoolService(db)
    pool = await pool_svc.get_pool(pool_id, current_user.id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    try:
        member = await pool_svc.add_member(
            pool, body.gmail_account_id, body.priority, body.is_active
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PoolMemberOut.model_validate(member)


@pool_router.delete("/{pool_id}/members/{account_id}", status_code=204)
async def remove_pool_member(
    pool_id: UUID, account_id: UUID, current_user: CurrentUser, db: DbSession
):
    pool_svc = PoolService(db)
    pool = await pool_svc.get_pool(pool_id, current_user.id)
    if not pool:
        raise HTTPException(status_code=404, detail="Pool not found")
    if not await pool_svc.remove_member(pool_id, account_id):
        raise HTTPException(status_code=404, detail="Member not found")
