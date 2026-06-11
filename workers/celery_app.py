"""Celery application and beat schedule."""

from celery import Celery
from celery.schedules import crontab

from workers.config import get_worker_settings
from workers.redis_compat import patch_kombu_redis_resp2

patch_kombu_redis_resp2()

settings = get_worker_settings()

app = Celery("gmail_outreach", broker=settings.celery_broker_url)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_routes={
        "workers.tasks.sender.*": {"queue": "send"},
        "workers.tasks.reply_sync.*": {"queue": "sync"},
        "workers.tasks.bounce_detection.*": {"queue": "sync"},
        "workers.tasks.token_refresh.*": {"queue": "sync"},
        "workers.tasks.lead_import.*": {"queue": "import"},
        "workers.tasks.lead_validation.*": {"queue": "import"},
        "workers.tasks.health_monitor.*": {"queue": "health"},
        "workers.tasks.tier_evaluation.*": {"queue": "health"},
        "workers.tasks.stuck_jobs.*": {"queue": "health"},
        "workers.tasks.scheduler.*": {"queue": "default"},
        "workers.tasks.preflight.*": {"queue": "default"},
        "workers.tasks.risk.*": {"queue": "default"},
        "workers.tasks.rollups.*": {"queue": "default"},
    },
    beat_schedule={
        "scheduler-tick": {
            "task": "workers.tasks.scheduler.run_scheduler_tick",
            "schedule": 30.0,
        },
        "reply-sync-all": {
            "task": "workers.tasks.reply_sync.sync_all_accounts",
            "schedule": 900.0,
        },
        "health-monitor-all": {
            "task": "workers.tasks.health_monitor.run_health_monitor_all",
            "schedule": 3600.0,
        },
        "token-refresh-all": {
            "task": "workers.tasks.token_refresh.refresh_all_tokens",
            "schedule": 300.0,
        },
        "tier-evaluation-daily": {
            "task": "workers.tasks.tier_evaluation.evaluate_all_tiers",
            "schedule": crontab(hour=2, minute=0),
        },
        "stuck-jobs-sweeper": {
            "task": "workers.tasks.stuck_jobs.sweep_stuck_jobs",
            "schedule": 300.0,
        },
        "analytics-rollup-hourly": {
            "task": "workers.tasks.rollups.run_hourly_rollup",
            "schedule": 3600.0,
        },
    },
)

app.autodiscover_tasks(["workers.tasks"])
