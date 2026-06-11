"""Sweeper for send jobs stuck in locked state."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.send_job import SendJob


async def sweep_stuck_jobs(session, stale_minutes: int = 9) -> dict:
    now = datetime.now(UTC)
    cutoff = now - timedelta(minutes=stale_minutes)

    result = await session.execute(
        select(SendJob).where(
            SendJob.status == "locked",
            SendJob.locked_at.isnot(None),
            SendJob.locked_at < cutoff,
        )
    )
    jobs = result.scalars().all()
    reset_count = 0

    for job in jobs:
        if job.lock_expires_at and job.lock_expires_at > now:
            continue
        job.status = "pending"
        job.locked_at = None
        job.lock_token = None
        job.lock_expires_at = None
        job.worker_id = None
        job.last_error = "stuck_lock_swept"
        job.next_retry_at = now + timedelta(minutes=1)
        reset_count += 1

    expired_result = await session.execute(
        select(SendJob).where(
            SendJob.status == "locked",
            SendJob.lock_expires_at.isnot(None),
            SendJob.lock_expires_at < now,
        )
    )
    for job in expired_result.scalars():
        job.status = "pending"
        job.locked_at = None
        job.lock_token = None
        job.lock_expires_at = None
        job.worker_id = None
        job.last_error = "lock_expired"
        job.next_retry_at = now + timedelta(seconds=30)
        reset_count += 1

    return {"reset_count": reset_count}
