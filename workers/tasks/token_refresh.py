"""Token refresh worker with distributed refresh lock."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.token_refresh.refresh_all_tokens")
def refresh_all_tokens() -> dict:
    from app.services.db import session_scope
    from app.services.token_service import refresh_all_tokens as _refresh_all

    async def _run() -> dict:
        async with session_scope() as session:
            return await _refresh_all(session)

    result = run_async(_run())
    logger.info("token_refresh_all", extra={"action": "token_refresh", **result})
    return result


@app.task(name="workers.tasks.token_refresh.refresh_account_token")
def refresh_account_token(gmail_account_id: str) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.token_service import refresh_google_token

    async def _run() -> dict:
        async with session_scope() as session:
            return await refresh_google_token(session, UUID(gmail_account_id))

    result = run_async(_run())
    logger.info(
        "token_refresh_account",
        extra={"account_id": gmail_account_id, "action": "token_refresh", **result},
    )
    return result
