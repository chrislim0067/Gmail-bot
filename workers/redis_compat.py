"""Compatibility shims for legacy Windows Redis (pre-6.0)."""

from __future__ import annotations


def patch_kombu_redis_resp2() -> None:
    """Force RESP2 for Celery's Redis broker on servers without HELLO support."""
    from kombu.transport import redis as kombu_redis

    if getattr(kombu_redis.Channel, "_resp2_patched", False):
        return

    original_connparams = kombu_redis.Channel._connparams

    def _connparams(self, asynchronous=False):
        params = original_connparams(self, asynchronous)
        params["protocol"] = 2
        return params

    kombu_redis.Channel._connparams = _connparams
    kombu_redis.Channel._resp2_patched = True
