"""Run async coroutines from synchronous Celery tasks."""

import asyncio
from collections.abc import Coroutine
from typing import TypeVar

T = TypeVar("T")

_worker_loop: asyncio.AbstractEventLoop | None = None


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
    return _worker_loop


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Run a coroutine on a persistent worker event loop (Windows-safe)."""
    loop = _get_worker_loop()
    return loop.run_until_complete(coro)
