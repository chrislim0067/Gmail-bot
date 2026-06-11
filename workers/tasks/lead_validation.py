"""Lead email validation worker with optional MX check (mockable)."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.lead_validation.validate_lead")
def validate_lead(lead_id: str, check_mx: bool = False) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.lead_validation_service import validate_lead_email

    async def _run() -> dict:
        async with session_scope() as session:
            return await validate_lead_email(session, UUID(lead_id), check_mx=check_mx)

    result = run_async(_run())
    logger.info(
        "lead_validation",
        extra={"lead_id": lead_id, "action": "lead_validation", **result},
    )
    return result
