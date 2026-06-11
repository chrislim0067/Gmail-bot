"""Lead CSV import worker with compliance ack and role-based block."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.lead_import.process_lead_import")
def process_lead_import(import_batch_id: str) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.lead_import_service import process_lead_import_batch

    async def _run() -> dict:
        async with session_scope() as session:
            return await process_lead_import_batch(session, UUID(import_batch_id))

    result = run_async(_run())
    logger.info(
        "lead_import",
        extra={"import_batch_id": import_batch_id, "action": "lead_import", **result},
    )
    return result
