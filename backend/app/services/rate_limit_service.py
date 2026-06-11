"""Redis sliding-window rate limit counters."""

import random
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

import redis.asyncio as redis

from app.config import get_settings
from app.services.send_settings_service import SendTimingSettings
from app.utils.redis_client import create_async_redis
from app.utils.tier_caps import effective_daily_cap, effective_hourly_cap, get_tier_caps


class RateLimitService:
    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        timing: SendTimingSettings | None = None,
    ) -> None:
        self.settings = get_settings()
        self.timing = timing or SendTimingSettings.from_app_config()
        self._client = redis_client

    @property
    def cooldown_window_seconds(self) -> int:
        return self.timing.account_cooldown_seconds

    async def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = create_async_redis()
        return self._client

    def _today_key(self, prefix: str, resource_id: str) -> str:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"rate:{prefix}:{resource_id}:daily:{today}"

    def _hour_key(self, prefix: str, resource_id: str) -> str:
        hour = datetime.now(UTC).strftime("%Y-%m-%d-%H")
        return f"rate:{prefix}:{resource_id}:hourly:{hour}"

    def _rolling_hourly_key(self, prefix: str, resource_id: str) -> str:
        return f"rate:{prefix}:{resource_id}:hourly_window"

    @staticmethod
    def _normalize_dt(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value

    async def _prune_rolling_window(self, key: str, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        cutoff = (now - timedelta(seconds=self.cooldown_window_seconds)).timestamp()
        client = await self.get_client()
        await client.zremrangebyscore(key, 0, cutoff)

    async def _count_rolling_window(
        self, prefix: str, resource_id: str, now: datetime | None = None
    ) -> int:
        now = now or datetime.now(UTC)
        client = await self.get_client()
        key = self._rolling_hourly_key(prefix, resource_id)
        await self._prune_rolling_window(key, now)
        cutoff = (now - timedelta(seconds=self.cooldown_window_seconds)).timestamp()
        return int(await client.zcount(key, cutoff, now.timestamp()))

    async def _record_rolling_send(
        self,
        prefix: str,
        resource_id: str,
        *,
        sent_at: datetime | None = None,
        member: str | None = None,
    ) -> None:
        sent_at = self._normalize_dt(sent_at or datetime.now(UTC))
        client = await self.get_client()
        key = self._rolling_hourly_key(prefix, resource_id)
        entry = member or str(uuid.uuid4())
        pipe = client.pipeline()
        pipe.zadd(key, {entry: sent_at.timestamp()})
        pipe.expire(key, self.cooldown_window_seconds * 2)
        await pipe.execute()

    async def _sync_rolling_window_from_last_send(
        self,
        prefix: str,
        resource_id: str,
        last_send_at: datetime | None,
        now: datetime | None = None,
    ) -> None:
        """Backfill rolling window from DB when Redis has no entries yet."""
        if not last_send_at:
            return
        now = now or datetime.now(UTC)
        last = self._normalize_dt(last_send_at)
        if (now - last).total_seconds() >= self.cooldown_window_seconds:
            return
        client = await self.get_client()
        key = self._rolling_hourly_key(prefix, resource_id)
        await self._prune_rolling_window(key, now)
        cutoff = (now - timedelta(seconds=self.cooldown_window_seconds)).timestamp()
        if await client.zcount(key, cutoff, now.timestamp()) > 0:
            return
        member = f"last_send:{int(last.timestamp())}"
        await client.zadd(key, {member: last.timestamp()})
        await client.expire(key, self.cooldown_window_seconds * 2)

    async def _rolling_hourly_available_at(
        self,
        prefix: str,
        resource_id: str,
        hourly_cap: int,
        last_send_at: datetime | None,
        now: datetime | None = None,
    ) -> datetime | None:
        now = now or datetime.now(UTC)
        client = await self.get_client()
        key = self._rolling_hourly_key(prefix, resource_id)
        await self._prune_rolling_window(key, now)
        cutoff = (now - timedelta(seconds=self.cooldown_window_seconds)).timestamp()
        count = int(await client.zcount(key, cutoff, now.timestamp()))
        if count < hourly_cap:
            return None

        oldest = await client.zrange(key, 0, 0, withscores=True)
        if oldest:
            oldest_ts = oldest[0][1]
            return datetime.fromtimestamp(oldest_ts, tz=UTC) + timedelta(
                seconds=self.cooldown_window_seconds
            )

        if last_send_at:
            last = self._normalize_dt(last_send_at)
            if (now - last).total_seconds() < self.cooldown_window_seconds:
                return last + timedelta(seconds=self.cooldown_window_seconds)
        return None

    def _hourly_cap_block(
        self,
        *,
        prefix: str,
        resource_id: str,
        hourly_cap: int,
        hourly_count: int,
        last_send_at: datetime | None,
        now: datetime,
        available_at: datetime | None,
    ) -> dict | None:
        if hourly_count < hourly_cap:
            return None
        if available_at is None:
            if last_send_at:
                last = self._normalize_dt(last_send_at)
                available_at = last + timedelta(seconds=self.cooldown_window_seconds)
            else:
                available_at = now + timedelta(seconds=self.cooldown_window_seconds)
        wait = max(0, int((available_at - now).total_seconds()))
        return {
            "retry_after_seconds": wait,
            "reason": "hourly_cap",
            "available_at": available_at.isoformat(),
            "cooldown_total_seconds": self.cooldown_window_seconds,
        }

    async def get_count(self, key: str) -> int:
        client = await self.get_client()
        value = await client.get(key)
        return int(value) if value else 0

    async def increment(self, key: str, ttl_seconds: int) -> int:
        client = await self.get_client()
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds)
        results = await pipe.execute()
        return int(results[0])

    async def get_account_daily_count(self, account_id: UUID) -> int:
        return await self.get_count(self._today_key("account", str(account_id)))

    async def get_account_hourly_count(
        self, account_id: UUID, last_send_at: datetime | None = None
    ) -> int:
        await self._sync_rolling_window_from_last_send(
            "account", str(account_id), last_send_at
        )
        return await self._count_rolling_window("account", str(account_id))

    async def get_pool_daily_count(self, pool_id: UUID) -> int:
        return await self.get_count(self._today_key("pool", str(pool_id)))

    async def get_pool_hourly_count(
        self, pool_id: UUID, pool_last_send_at: datetime | None = None
    ) -> int:
        await self._sync_rolling_window_from_last_send(
            "pool", str(pool_id), pool_last_send_at
        )
        return await self._count_rolling_window("pool", str(pool_id))

    async def get_global_daily_count(self, user_id: UUID) -> int:
        return await self.get_count(self._today_key("global", str(user_id)))

    def _pool_stagger_key(self, pool_id: UUID) -> str:
        return f"rate:pool:{pool_id}:next_send_at"

    def _inter_send_available_at(
        self, last_send_at: datetime | None, now: datetime | None = None
    ) -> datetime | None:
        if not last_send_at:
            return None
        now = now or datetime.now(UTC)
        last = last_send_at.replace(tzinfo=UTC) if last_send_at.tzinfo is None else last_send_at
        return last + timedelta(seconds=self.timing.account_cooldown_seconds)

    async def get_pool_next_send_at(self, pool_id: UUID) -> datetime | None:
        client = await self.get_client()
        value = await client.get(self._pool_stagger_key(pool_id))
        if not value:
            return None
        return datetime.fromtimestamp(float(value), tz=UTC)

    async def pool_stagger_retry_seconds(self, pool_id: UUID) -> int:
        next_at = await self.get_pool_next_send_at(pool_id)
        if not next_at:
            return 0
        return max(0, int((next_at - datetime.now(UTC)).total_seconds()))

    async def record_pool_stagger(self, pool_id: UUID) -> None:
        delay = random.randint(
            self.timing.inter_account_delay_min_seconds,
            self.timing.inter_account_delay_max_seconds,
        )
        next_at = datetime.now(UTC) + timedelta(seconds=delay)
        client = await self.get_client()
        await client.set(
            self._pool_stagger_key(pool_id),
            str(next_at.timestamp()),
            ex=86400,
        )

    def inter_account_delay_seconds(self) -> tuple[int, int]:
        return (
            self.timing.inter_account_delay_min_seconds,
            self.timing.inter_account_delay_max_seconds,
        )

    def _next_day_at(self, now: datetime | None = None) -> datetime:
        now = now or datetime.now(UTC)
        return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    def _seconds_until_next_day(self, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        return max(0, int((self._next_day_at(now) - now).total_seconds()))

    def _inter_send_retry_seconds(
        self, last_send_at: datetime | None, now: datetime | None = None
    ) -> int:
        if not last_send_at:
            return 0
        now = now or datetime.now(UTC)
        last = last_send_at.replace(tzinfo=UTC) if last_send_at.tzinfo is None else last_send_at
        min_delay = self.timing.account_cooldown_seconds
        available = last + timedelta(seconds=min_delay)
        return max(0, int((available - now).total_seconds()))

    async def check_account_rate_limit(
        self,
        *,
        account_id: UUID,
        account_tier: str,
        user_daily_limit: int,
        user_hourly_limit: int,
        last_send_at: datetime | None,
    ) -> dict:
        try:
            now = datetime.now(UTC)
            daily_cap = effective_daily_cap(account_tier, user_daily_limit)
            hourly_cap = effective_hourly_cap(account_tier, user_hourly_limit)
            caps = get_tier_caps(account_tier)
            min_delay = self.timing.account_cooldown_seconds
            blocks: list[dict] = []

            if not caps.sends_allowed:
                blocks.append(
                    {
                        "retry_after_seconds": 3600,
                        "reason": "tier_blocked",
                        "available_at": (now + timedelta(seconds=3600)).isoformat(),
                        "cooldown_total_seconds": 3600,
                    }
                )

            daily_count = await self.get_account_daily_count(account_id)
            if daily_count >= daily_cap:
                wait = self._seconds_until_next_day(now)
                blocks.append(
                    {
                        "retry_after_seconds": wait,
                        "reason": "daily_cap",
                        "available_at": self._next_day_at(now).isoformat(),
                        "cooldown_total_seconds": wait,
                    }
                )

            hourly_count = await self.get_account_hourly_count(account_id, last_send_at)
            hourly_available = await self._rolling_hourly_available_at(
                "account",
                str(account_id),
                hourly_cap,
                last_send_at,
                now,
            )
            hourly_block = self._hourly_cap_block(
                prefix="account",
                resource_id=str(account_id),
                hourly_cap=hourly_cap,
                hourly_count=hourly_count,
                last_send_at=last_send_at,
                now=now,
                available_at=hourly_available,
            )
            if hourly_block:
                blocks.append(hourly_block)

            inter_wait = self._inter_send_retry_seconds(last_send_at, now)
            if inter_wait > 0 and last_send_at:
                last = (
                    last_send_at.replace(tzinfo=UTC)
                    if last_send_at.tzinfo is None
                    else last_send_at
                )
                inter_available = last + timedelta(seconds=min_delay)
                blocks.append(
                    {
                        "retry_after_seconds": inter_wait,
                        "reason": "inter_send_delay",
                        "available_at": inter_available.isoformat(),
                        "cooldown_total_seconds": min_delay,
                    }
                )

            if blocks:
                primary = max(blocks, key=lambda item: item["retry_after_seconds"])
                return {
                    "allowed": False,
                    "retry_after_seconds": int(primary["retry_after_seconds"]),
                    "reason": primary["reason"],
                    "available_at": primary["available_at"],
                    "cooldown_total_seconds": int(primary["cooldown_total_seconds"]),
                    "constraints": blocks,
                    "sent_this_hour": hourly_count,
                    "hourly_cap": hourly_cap,
                    "sent_today": daily_count,
                    "daily_cap": daily_cap,
                }

            return {
                "allowed": True,
                "retry_after_seconds": 0,
                "reason": None,
                "available_at": now.isoformat(),
                "cooldown_total_seconds": 0,
                "constraints": [],
                "sent_this_hour": hourly_count,
                "hourly_cap": hourly_cap,
                "sent_today": daily_count,
                "daily_cap": daily_cap,
            }
        except Exception:
            return {
                "allowed": False,
                "retry_after_seconds": 300,
                "reason": "redis_unavailable",
                "available_at": None,
                "cooldown_total_seconds": 300,
                "constraints": [],
                "sent_this_hour": 0,
                "hourly_cap": 0,
                "sent_today": 0,
                "daily_cap": 0,
            }

    def inter_send_delay_seconds(self) -> int:
        return self.timing.account_cooldown_seconds

    async def account_send_status(
        self,
        account,
        pool_ids: list[UUID] | None = None,
        turn_position: int | None = None,
        pool_stagger_seconds: int = 0,
        pool_next_at: datetime | None = None,
    ) -> dict:
        now = datetime.now(UTC)
        delay_seconds = self.inter_send_delay_seconds()
        inter_min, inter_max = self.inter_account_delay_seconds()
        inter_send_at = self._inter_send_available_at(account.last_send_at, now)
        inter_send_available_at = inter_send_at.isoformat() if inter_send_at else None

        rate = await self.check_account_rate_limit(
            account_id=account.id,
            account_tier=account.account_tier,
            user_daily_limit=account.daily_send_limit,
            user_hourly_limit=account.hourly_send_limit,
            last_send_at=account.last_send_at,
        )
        base = {
            "inter_send_delay_seconds": delay_seconds,
            "inter_send_available_at": inter_send_available_at,
            "inter_account_delay_min_seconds": inter_min,
            "inter_account_delay_max_seconds": inter_max,
            "queue_position": turn_position,
        }
        if account.status != "active" or account.deleted_at is not None:
            return {
                **base,
                "available_now": False,
                "retry_after_seconds": 0,
                "available_at": None,
                "reason": "account_inactive",
            }
        if account.review_required or account.account_tier in ("restricted", "paused"):
            return {
                **base,
                "available_now": False,
                "retry_after_seconds": 0,
                "available_at": None,
                "reason": "account_blocked",
            }

        if not rate["allowed"]:
            available_at = rate.get("available_at")
            if not available_at:
                available_at = (
                    now + timedelta(seconds=int(rate["retry_after_seconds"]))
                ).isoformat()
            return {
                **base,
                "available_now": False,
                "retry_after_seconds": int(rate["retry_after_seconds"]),
                "available_at": available_at,
                "reason": rate["reason"],
                "cooldown_total_seconds": int(
                    rate.get("cooldown_total_seconds") or delay_seconds
                ),
                "constraints": rate.get("constraints") or [],
                "sent_this_hour": int(rate.get("sent_this_hour") or 0),
                "hourly_cap": int(rate.get("hourly_cap") or 0),
                "daily_cap": int(rate.get("daily_cap") or 0),
            }

        # Rate-ready: pool turn controls who sends next
        if turn_position is None:
            return {
                **base,
                "available_now": True,
                "retry_after_seconds": 0,
                "available_at": now.isoformat(),
                "reason": None,
                "cooldown_total_seconds": 0,
                "constraints": rate.get("constraints") or [],
                "sent_this_hour": int(rate.get("sent_this_hour") or 0),
                "hourly_cap": int(rate.get("hourly_cap") or 0),
                "daily_cap": int(rate.get("daily_cap") or 0),
            }

        if pool_stagger_seconds > 0 and pool_next_at and pool_next_at > now:
            if turn_position == 1:
                retry = max(0, int((pool_next_at - now).total_seconds()))
                return {
                    **base,
                    "available_now": False,
                    "retry_after_seconds": retry,
                    "available_at": pool_next_at.isoformat(),
                    "reason": "pool_stagger",
                    "cooldown_total_seconds": inter_max,
                    "constraints": [
                        {
                            "reason": "pool_stagger",
                            "available_at": pool_next_at.isoformat(),
                            "retry_after_seconds": retry,
                            "cooldown_total_seconds": inter_max,
                        }
                    ],
                    "sent_this_hour": int(rate.get("sent_this_hour") or 0),
                    "hourly_cap": int(rate.get("hourly_cap") or 0),
                    "daily_cap": int(rate.get("daily_cap") or 0),
                }
            return {
                **base,
                "available_now": False,
                "retry_after_seconds": 0,
                "available_at": None,
                "reason": "waiting_turn",
                "cooldown_total_seconds": 0,
                "constraints": [
                    {
                        "reason": "waiting_turn",
                        "available_at": None,
                        "retry_after_seconds": 0,
                        "cooldown_total_seconds": 0,
                    }
                ],
                "sent_this_hour": int(rate.get("sent_this_hour") or 0),
                "hourly_cap": int(rate.get("hourly_cap") or 0),
                "daily_cap": int(rate.get("daily_cap") or 0),
            }

        if turn_position == 1:
            return {
                **base,
                "available_now": True,
                "retry_after_seconds": 0,
                "available_at": now.isoformat(),
                "reason": "next_to_send",
                "cooldown_total_seconds": 0,
                "constraints": [],
                "sent_this_hour": int(rate.get("sent_this_hour") or 0),
                "hourly_cap": int(rate.get("hourly_cap") or 0),
                "daily_cap": int(rate.get("daily_cap") or 0),
            }

        return {
            **base,
            "available_now": False,
            "retry_after_seconds": 0,
            "available_at": None,
            "reason": "waiting_turn",
            "cooldown_total_seconds": 0,
            "constraints": [
                {
                    "reason": "waiting_turn",
                    "available_at": None,
                    "retry_after_seconds": 0,
                    "cooldown_total_seconds": 0,
                }
            ],
            "sent_this_hour": int(rate.get("sent_this_hour") or 0),
            "hourly_cap": int(rate.get("hourly_cap") or 0),
            "daily_cap": int(rate.get("daily_cap") or 0),
        }

    async def record_account_send(
        self, account_id: UUID, sent_at: datetime | None = None
    ) -> None:
        sent_at = self._normalize_dt(sent_at or datetime.now(UTC))
        await self.increment(self._today_key("account", str(account_id)), 86400)
        await self._record_rolling_send("account", str(account_id), sent_at=sent_at)

    async def record_pool_send(
        self, pool_id: UUID, sent_at: datetime | None = None
    ) -> None:
        sent_at = self._normalize_dt(sent_at or datetime.now(UTC))
        await self.increment(self._today_key("pool", str(pool_id)), 86400)
        await self._record_rolling_send("pool", str(pool_id), sent_at=sent_at)

    async def record_global_send(self, user_id: UUID) -> None:
        await self.increment(self._today_key("global", str(user_id)), 86400)
