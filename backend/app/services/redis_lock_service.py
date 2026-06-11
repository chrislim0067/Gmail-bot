"""Redis distributed locks for sender, scheduler, and token refresh."""

import uuid
from typing import Any

import redis.asyncio as redis

from app.config import get_settings
from app.utils.redis_client import create_async_redis

RELEASE_LOCK_LUA = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("DEL", KEYS[1])
else
  return 0
end
"""


class RedisLockService:
    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self.settings = get_settings()
        self._client = redis_client
        self._release_script: Any = None

    async def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = create_async_redis()
        return self._client

    def _lock_key(self, lock_type: str, resource_id: str) -> str:
        return f"lock:{lock_type}:{resource_id}"

    def _holder_token(self, worker_id: str, task_id: str | None = None) -> str:
        return f"{worker_id}:{task_id or 'sync'}:{uuid.uuid4()}"

    async def acquire(
        self,
        lock_type: str,
        resource_id: str,
        worker_id: str = "api",
        task_id: str | None = None,
        ttl_seconds: int | None = None,
    ) -> tuple[bool, str | None]:
        client = await self.get_client()
        key = self._lock_key(lock_type, resource_id)
        token = self._holder_token(worker_id, task_id)
        ttl = ttl_seconds or self.settings.lock_ttl_seconds
        acquired = await client.set(key, token, nx=True, ex=ttl)
        return bool(acquired), token if acquired else None

    async def release(self, lock_type: str, resource_id: str, token: str) -> bool:
        client = await self.get_client()
        key = self._lock_key(lock_type, resource_id)
        if self._release_script is None:
            self._release_script = client.register_script(RELEASE_LOCK_LUA)
        result = await self._release_script(keys=[key], args=[token])
        return bool(result)

    async def is_locked(self, lock_type: str, resource_id: str) -> bool:
        client = await self.get_client()
        key = self._lock_key(lock_type, resource_id)
        return await client.exists(key) > 0

    async def acquire_gmail_account_lock(
        self, account_id: str, worker_id: str = "worker"
    ) -> tuple[bool, str | None]:
        return await self.acquire("gmail_account", account_id, worker_id=worker_id)

    async def acquire_scheduler_lock(
        self, campaign_id: str, worker_id: str = "scheduler"
    ) -> tuple[bool, str | None]:
        return await self.acquire("campaign_scheduler", campaign_id, worker_id=worker_id)

    async def acquire_token_refresh_lock(
        self, account_id: str, worker_id: str = "token_refresh"
    ) -> tuple[bool, str | None]:
        return await self.acquire("token_refresh", account_id, worker_id=worker_id)

    async def ping(self) -> bool:
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception:
            return False
