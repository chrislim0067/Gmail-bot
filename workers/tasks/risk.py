"""Risk budget event recording worker."""

import logging
from typing import Any

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.risk.record_risk_event_task")
def record_risk_event_task(
    user_id: str,
    event_type: str,
    score_delta: int | None = None,
    severity: str = "warning",
    gmail_account_id: str | None = None,
    campaign_id: str | None = None,
    pool_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.risk_service import record_risk_event

    async def _run() -> dict:
        async with session_scope() as session:
            return await record_risk_event(
                session,
                UUID(user_id),
                event_type,
                score_delta=score_delta,
                severity=severity,
                gmail_account_id=UUID(gmail_account_id) if gmail_account_id else None,
                campaign_id=UUID(campaign_id) if campaign_id else None,
                pool_id=UUID(pool_id) if pool_id else None,
                details=details,
            )

    result = run_async(_run())
    logger.info(
        "record_risk_event",
        extra={"user_id": user_id, "action": "risk_event", **result},
    )
    return result
