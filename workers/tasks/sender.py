"""Sender worker — full send gate, mock Gmail send, Redis lock acquire/release."""

import logging

from workers.async_runner import run_async
from workers.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="workers.tasks.sender.send_email_job", bind=True, max_retries=0)
def send_email_job(self, send_job_id: str) -> dict:
    from uuid import UUID

    from app.services.db import session_scope
    from app.services.sender_service import SenderService

    worker_id = self.request.hostname or "worker"

    async def _run() -> dict:
        async with session_scope() as session:
            return await SenderService(session).process_send_job(
                UUID(send_job_id), worker_id
            )

    result = run_async(_run())
    logger.info(
        "send_email_job completed",
        extra={"job_id": send_job_id, "status": result.get("status"), "action": "send"},
    )
    return result
