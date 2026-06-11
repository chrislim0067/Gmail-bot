"""User send timing settings."""

from fastapi import APIRouter, HTTPException

from app.dependencies import CurrentUser, DbSession
from app.schemas.send_settings import SendTimingOut, SendTimingUpdate
from app.services.send_settings_service import (
    get_send_timing_settings,
    update_send_timing_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/send-timing", response_model=SendTimingOut)
async def get_send_timing(current_user: CurrentUser, db: DbSession) -> SendTimingOut:
    timing = await get_send_timing_settings(db, current_user.id)
    return SendTimingOut(**timing.to_dict())


@router.patch("/send-timing", response_model=SendTimingOut)
async def update_send_timing(
    body: SendTimingUpdate, current_user: CurrentUser, db: DbSession
) -> SendTimingOut:
    try:
        timing = await update_send_timing_settings(
            db,
            current_user,
            account_cooldown_minutes=body.account_cooldown_minutes,
            inter_account_delay_min_minutes=body.inter_account_delay_min_minutes,
            inter_account_delay_max_minutes=body.inter_account_delay_max_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return SendTimingOut(**timing.to_dict())
