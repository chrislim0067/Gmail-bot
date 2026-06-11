"""Account tier evaluation worker."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.tier_evaluation.evaluate_all_tiers")
def evaluate_all_tiers() -> dict:
    from app.services.db import session_scope
    from app.services.tier_service import evaluate_all_account_tiers

    async def _run() -> dict:
        async with session_scope() as session:
            count = await evaluate_all_account_tiers(session)
            return {"accounts_evaluated": count}

    result = run_async(_run())
    logger.info("tier_evaluation_all", extra={"action": "tier_evaluation", **result})
    return result


@app.task(name="workers.tasks.tier_evaluation.evaluate_account_tier_task")
def evaluate_account_tier_task(gmail_account_id: str) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.tier_service import evaluate_account_tier

    async def _run() -> dict:
        async with session_scope() as session:
            return await evaluate_account_tier(session, UUID(gmail_account_id))

    result = run_async(_run())
    logger.info(
        "tier_evaluation_account",
        extra={"account_id": gmail_account_id, "action": "tier_evaluation", **result},
    )
    return result
