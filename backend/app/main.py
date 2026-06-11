"""FastAPI application entry point."""

import asyncio
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if settings.is_development:
        await init_db()

    stop_event = asyncio.Event()
    scheduler_task: asyncio.Task | None = None
    if settings.scheduler_background_enabled:
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
