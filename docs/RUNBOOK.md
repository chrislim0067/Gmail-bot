# Operations Runbook

## Degraded modes

- **Redis down:** Pause new sends; allow dashboard reads and unsubscribe processing.
- **Gmail API errors:** Per-account circuit breaker; pool continues with healthy accounts.
- **Global risk threshold:** Block new campaigns until `POST /risk/acknowledge`.

## Stuck jobs

Run stuck-job sweeper or reset `send_jobs` where `status=locked` and `lock_expires_at < now()`.
