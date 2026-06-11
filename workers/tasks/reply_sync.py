"""Reply sync worker (mock Gmail)."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.reply_sync.sync_all_accounts")
def sync_all_accounts() -> dict:
    from app.services.db import session_scope
    from app.services.reply_sync_service import sync_all_accounts as _sync_all

    async def _run() -> dict:
        async with session_scope() as session:
            return await _sync_all(session)

    result = run_async(_run())
    logger.info("reply_sync_all", extra={"action": "reply_sync", **result})
    return result


@app.task(name="workers.tasks.reply_sync.sync_replies_for_account")
def sync_replies_for_account(gmail_account_id: str) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.reply_sync_service import sync_replies

    async def _run() -> dict:
        async with session_scope() as session:
            return await sync_replies(session, UUID(gmail_account_id))

    result = run_async(_run())
    logger.info(
        "reply_sync_account",
        extra={"account_id": gmail_account_id, "action": "reply_sync", **result},
    )
    return result
