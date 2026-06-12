"""FastAPI application entry point."""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.init_db import init_db
from app.middleware import RequestIdMiddleware
from app.routers import (
    analytics,
    audit,
    auth,
    campaigns,
    gmail,
    health,
    leads,
    queue,
    replies,
    risk,
    send_settings,
    subjects,
    templates,
    unsubscribe,
)
from app.services.background_scheduler import background_scheduler_loop
from app.utils.logging import setup_logging
from app.utils.redis_client import close_async_redis

settings = get_settings()


def _should_init_db_on_startup() -> bool:
    if settings.is_development:
        return True
    if not settings.is_vercel:
        return False
    url = settings.database_url.lower()
    return "localhost" not in url and "127.0.0.1" not in url


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if _should_init_db_on_startup():
        try:
            await init_db()
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Database init failed on startup — check DATABASE_URL"
            )

    stop_event = asyncio.Event()
    scheduler_task: asyncio.Task | None = None
    if settings.scheduler_background_enabled and not settings.is_vercel:
        scheduler_task = asyncio.create_task(background_scheduler_loop(stop_event))

    yield

    if scheduler_task is not None:
        stop_event.set()
        await scheduler_task

    await close_async_redis()


app = FastAPI(
    title="Gmail Cold-Email Outreach Platform",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)
def _cors_origins() -> list[str]:
    origins = list(settings.cors_origins)
    for origin in (settings.frontend_url, os.environ.get("VERCEL_URL")):
        if not origin:
            continue
        normalized = origin if origin.startswith("http") else f"https://{origin}"
        if normalized not in origins:
            origins.append(normalized)
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"

app.include_router(auth.router, prefix=api_prefix)
app.include_router(gmail.router, prefix=api_prefix)
app.include_router(gmail.pool_router, prefix=f"{api_prefix}/gmail")
app.include_router(campaigns.router, prefix=api_prefix)
app.include_router(leads.router, prefix=api_prefix)
app.include_router(templates.router, prefix=api_prefix)
app.include_router(subjects.router, prefix=api_prefix)
app.include_router(queue.router, prefix=api_prefix)
app.include_router(replies.router, prefix=api_prefix)
app.include_router(unsubscribe.router, prefix=api_prefix)
app.include_router(analytics.router, prefix=api_prefix)
app.include_router(health.router, prefix=api_prefix)
app.include_router(risk.router, prefix=api_prefix)
app.include_router(audit.router, prefix=api_prefix)
app.include_router(send_settings.router, prefix=api_prefix)


@app.get("/")
async def root():
    return {"service": "gmail-outreach-api", "version": "0.1.0", "docs": "/api/docs"}
