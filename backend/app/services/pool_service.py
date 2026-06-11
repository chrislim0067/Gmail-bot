"""Gmail account pool management and account selection."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account_pool import GmailAccountPool, GmailAccountPoolMember
from app.models.gmail_account import GmailAccount
from app.services.rate_limit_service import RateLimitService
from app.services.send_settings_service import get_send_timing_settings
from app.utils.tier_caps import effective_daily_cap


class PoolService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _rate_limit_for_user(self, user_id: UUID) -> RateLimitService:
        timing = await get_send_timing_settings(self.db, user_id)
        return RateLimitService(timing=timing)

    async def get_pool(self, pool_id: UUID, user_id: UUID) -> GmailAccountPool | None:
        result = await self.db.execute(
            select(GmailAccountPool)
            .options(selectinload(GmailAccountPool.members))
            .where(
                GmailAccountPool.id == pool_id,
                GmailAccountPool.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_pool(self, user_id: UUID, data: dict) -> GmailAccountPool:
        pool = GmailAccountPool(user_id=user_id, **data)
        self.db.add(pool)
        await self.db.flush()
        return pool

    async def add_member(
        self,
        pool: GmailAccountPool,
        gmail_account_id: UUID,
        priority: int = 100,
        is_active: bool = True,
    ) -> GmailAccountPoolMember:
        account_result = await self.db.execute(
            select(GmailAccount).where(
                GmailAccount.id == gmail_account_id,
                GmailAccount.user_id == pool.user_id,
                GmailAccount.deleted_at.is_(None),
            )
        )
        if not account_result.scalar_one_or_none():
            raise ValueError("Gmail account not found or not owned by user")

        member = GmailAccountPoolMember(
            pool_id=pool.id,
            gmail_account_id=gmail_account_id,
            priority=priority,
            is_active=is_active,
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def remove_member(self, pool_id: UUID, account_id: UUID) -> bool:
        result = await self.db.execute(
            select(GmailAccountPoolMember).where(
                GmailAccountPoolMember.pool_id == pool_id,
                GmailAccountPoolMember.gmail_account_id == account_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False
        await self.db.delete(member)
        await self.db.flush()
        return True

    async def get_member_count(self, pool_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count(GmailAccountPoolMember.id)).where(
                GmailAccountPoolMember.pool_id == pool_id,
                GmailAccountPoolMember.is_active.is_(True),
            )
        )
        return result.scalar() or 0

    async def get_pool_capacity_remaining(self, pool_id: UUID) -> int:
        """How many emails this pool can still send today (accounts + pool caps)."""
        pool_result = await self.db.execute(
            select(GmailAccountPool).where(GmailAccountPool.id == pool_id)
        )
        pool = pool_result.scalar_one_or_none()
        if not pool or pool.status != "active":
            return 0

        rate_limit = await self._rate_limit_for_user(pool.user_id)
        pool_sent = await rate_limit.get_pool_daily_count(pool.id)
        pool_remaining = max(0, pool.max_daily_send - pool_sent)

        members_result = await self.db.execute(
            select(GmailAccountPoolMember, GmailAccount)
            .join(GmailAccount, GmailAccount.id == GmailAccountPoolMember.gmail_account_id)
            .where(
                GmailAccountPoolMember.pool_id == pool_id,
                GmailAccountPoolMember.is_active.is_(True),
                GmailAccount.deleted_at.is_(None),
            )
        )
        account_remaining = 0
        for _member, account in members_result.all():
            if account.status != "active" or account.review_required:
                continue
            if account.account_tier in ("restricted", "paused"):
                continue
            daily_cap = effective_daily_cap(account.account_tier, account.daily_send_limit)
            sent_today = await rate_limit.get_account_daily_count(account.id)
            account_remaining += max(0, daily_cap - sent_today)

        return min(pool_remaining, account_remaining)

    async def select_available_account(
        self, campaign_pool_id: UUID
    ) -> tuple[GmailAccount | None, int | None]:
        result = await self.db.execute(
            select(GmailAccountPool)
            .options(selectinload(GmailAccountPool.members))
            .where(GmailAccountPool.id == campaign_pool_id)
        )
        pool = result.scalar_one_or_none()
        if not pool or pool.status != "active":
            return None, None

        rate_limit = await self._rate_limit_for_user(pool.user_id)
        pool_daily = await rate_limit.get_pool_daily_count(pool.id)
        pool_hourly = await rate_limit.get_pool_hourly_count(pool.id)
        pool_stagger = await rate_limit.pool_stagger_retry_seconds(pool.id)
        if pool_daily >= pool.max_daily_send or pool_hourly >= pool.max_hourly_send:
            return None, 1800

        members = sorted(
            [m for m in pool.members if m.is_active],
            key=lambda m: m.priority,
        )
        min_retry: int | None = None
        candidates: list[tuple[int, datetime, GmailAccount]] = []
        for member in members:
            account_result = await self.db.execute(
                select(GmailAccount).where(GmailAccount.id == member.gmail_account_id)
            )
            account = account_result.scalar_one_or_none()
            if not account or account.deleted_at:
                continue
            if account.status != "active" or account.review_required:
                continue
            if account.account_tier in ("restricted", "paused"):
                continue
            if account.health_score < 30:
                continue

            rate_check = await rate_limit.check_account_rate_limit(
                account_id=account.id,
                account_tier=account.account_tier,
                user_daily_limit=account.daily_send_limit,
                user_hourly_limit=account.hourly_send_limit,
                last_send_at=account.last_send_at,
            )
            if not rate_check["allowed"]:
                retry = int(rate_check.get("retry_after_seconds") or 300)
                min_retry = retry if min_retry is None else min(min_retry, retry)
                continue

            last = account.last_send_at
            if last and last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            candidates.append(
                (
                    member.priority,
                    last or datetime.min.replace(tzinfo=UTC),
                    account,
                )
            )

        if not candidates:
            wait = min_retry
            if pool_stagger > 0:
                wait = min(wait, pool_stagger) if wait is not None else pool_stagger
            return None, wait

        if pool_stagger > 0:
            return None, pool_stagger

        if len(candidates) > pool.active_account_limit:
            candidates = candidates[: pool.active_account_limit]

        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2], None

    async def get_pool_send_turn(self, pool_id: UUID) -> dict:
        """Priority-ordered ready accounts and active pool gap timer."""
        pool_result = await self.db.execute(
            select(GmailAccountPool.user_id).where(GmailAccountPool.id == pool_id)
        )
        pool_user_id = pool_result.scalar_one_or_none()
        if not pool_user_id:
            return {
                "ready_order": [],
                "pool_stagger_seconds": 0,
                "pool_next_at": None,
            }
        rate_limit = await self._rate_limit_for_user(pool_user_id)

        result = await self.db.execute(
            select(GmailAccountPoolMember, GmailAccount)
            .join(GmailAccount, GmailAccount.id == GmailAccountPoolMember.gmail_account_id)
            .where(
                GmailAccountPoolMember.pool_id == pool_id,
                GmailAccountPoolMember.is_active.is_(True),
                GmailAccount.deleted_at.is_(None),
            )
            .order_by(GmailAccountPoolMember.priority, GmailAccount.email)
        )
        ready_order: list[UUID] = []
        for _member, account in result.all():
            if account.status != "active" or account.review_required:
                continue
            if account.account_tier in ("restricted", "paused"):
                continue
            if account.health_score < 30:
                continue
            rate = await rate_limit.check_account_rate_limit(
                account_id=account.id,
                account_tier=account.account_tier,
                user_daily_limit=account.daily_send_limit,
                user_hourly_limit=account.hourly_send_limit,
                last_send_at=account.last_send_at,
            )
            if rate["allowed"]:
                ready_order.append(account.id)

        pool_next = await rate_limit.get_pool_next_send_at(pool_id)
        pool_stagger = await rate_limit.pool_stagger_retry_seconds(pool_id)
        return {
            "ready_order": ready_order,
            "pool_stagger_seconds": pool_stagger,
            "pool_next_at": pool_next,
        }

    async def list_account_send_timeline(self, user_id: UUID) -> dict:
        from app.models.account_pool import GmailAccountPoolMember

        timing = await get_send_timing_settings(self.db, user_id)
        rate_limit = RateLimitService(timing=timing)

        result = await self.db.execute(
            select(GmailAccount).where(
                GmailAccount.user_id == user_id,
                GmailAccount.deleted_at.is_(None),
            )
        )
        accounts = result.scalars().all()

        member_result = await self.db.execute(
            select(GmailAccountPoolMember.gmail_account_id, GmailAccountPoolMember.pool_id)
            .join(GmailAccount, GmailAccount.id == GmailAccountPoolMember.gmail_account_id)
            .where(
                GmailAccount.user_id == user_id,
                GmailAccount.deleted_at.is_(None),
                GmailAccountPoolMember.is_active.is_(True),
            )
        )
        account_pools: dict[UUID, list[UUID]] = {}
        for account_id, pool_id in member_result.all():
            account_pools.setdefault(account_id, []).append(pool_id)

        pool_turns: dict[UUID, dict] = {}
        seen_pools: set[UUID] = set()
        for pool_ids in account_pools.values():
            for pool_id in pool_ids:
                if pool_id in seen_pools:
                    continue
                seen_pools.add(pool_id)
                pool_turns[pool_id] = await self.get_pool_send_turn(pool_id)

        def turn_position(account_id: UUID) -> int | None:
            best: int | None = None
            for pool_id in account_pools.get(account_id, []):
                turn = pool_turns.get(pool_id)
                if not turn:
                    continue
                try:
                    pos = turn["ready_order"].index(account_id) + 1
                except ValueError:
                    continue
                if best is None or pos < best:
                    best = pos
            return best

        items: list[dict] = []
        for account in accounts:
            primary_pool = (account_pools.get(account.id) or [None])[0]
            turn = pool_turns.get(primary_pool) if primary_pool else None
            status = await rate_limit.account_send_status(
                account,
                pool_ids=account_pools.get(account.id, []),
                turn_position=turn_position(account.id),
                pool_stagger_seconds=turn["pool_stagger_seconds"] if turn else 0,
                pool_next_at=turn["pool_next_at"] if turn else None,
            )
            items.append(
                {
                    "gmail_account_id": str(account.id),
                    "email": account.email,
                    "account_status": account.status,
                    "last_send_at": (
                        account.last_send_at.isoformat() if account.last_send_at else None
                    ),
                    "sent_today": await rate_limit.get_account_daily_count(account.id),
                    **status,
                }
            )
        items.sort(
            key=lambda row: (
                0 if row["available_now"] else 1,
                row.get("queue_position") if row.get("queue_position") is not None else 999,
                row.get("available_at") or "",
            )
        )
        return {
            **timing.to_dict(),
            "accounts": items,
        }
