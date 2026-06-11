"""Shared Redis client factories (RESP2 for legacy Windows Redis)."""

from __future__ import annotations

import redis
import redis.asyncio as aioredis

from app.config import get_settings

# Windows Redis builds often predate RESP3; redis-py 5+ sends HELLO by default.
_REDIS_KWARGS = {"decode_responses": True, "protocol": 2}

_sync_client: redis.Redis | None = None
_async_client: aioredis.Redis | None = None


def create_sync_redis() -> redis.Redis:
    global _sync_client
    if _sync_client is None:
        settings = get_settings()
        _sync_client = redis.from_url(settings.redis_url, **_REDIS_KWARGS)
    return _sync_client


def create_async_redis() -> aioredis.Redis:
    global _async_client
    if _async_client is None:
        settings = get_settings()
        _async_client = aioredis.from_url(
            settings.redis_url,
            **_REDIS_KWARGS,
            max_connections=20,
        )
    return _async_client


async def close_async_redis() -> None:
    global _async_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None


def close_sync_redis() -> None:
    global _sync_client
    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None
