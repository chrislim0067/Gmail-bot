"""Redis distributed locks for workers."""

import uuid

import redis

from app.utils.redis_client import create_sync_redis

RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def _redis_client() -> redis.Redis:
    return create_sync_redis()


def new_lock_token() -> str:
    return uuid.uuid4().hex


def account_send_lock_key(account_id: str) -> str:
    return f"lock:gmail_account:{account_id}"


def scheduler_lock_key(campaign_id: str) -> str:
    return f"lock:campaign_scheduler:{campaign_id}"


def token_refresh_lock_key(account_id: str) -> str:
    return f"lock:token_refresh:{account_id}"


def acquire_lock(key: str, token: str, ttl_seconds: int) -> bool:
    client = _redis_client()
    return bool(client.set(key, token, nx=True, ex=ttl_seconds))


def release_lock(key: str, token: str) -> bool:
    client = _redis_client()
    script = client.register_script(RELEASE_LOCK_SCRIPT)
    return bool(script(keys=[key], args=[token]))


def get_lock_holder(key: str) -> str | None:
    client = _redis_client()
    return client.get(key)
