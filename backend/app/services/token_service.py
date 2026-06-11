"""OAuth token encryption, Redis cache, and refresh."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.oauth_token import OAuthToken
from app.utils.redis_client import create_async_redis
from app.services.redis_lock_service import RedisLockService
from app.utils.crypto import decrypt, encrypt


class TokenServiceError(Exception):
    pass


class InvalidGrantError(TokenServiceError):
    pass


class TokenService:
    def __init__(
        self,
        db: AsyncSession,
        redis_client: redis.Redis | None = None,
    ) -> None:
        self.db = db
        self.settings = get_settings()
        self._client = redis_client
        self.lock_service = RedisLockService(redis_client)

    async def get_redis(self) -> redis.Redis:
        if self._client is None:
            self._client = create_async_redis()
        return self._client

    def _access_key(self, account_id: UUID) -> str:
        return f"gmail:access:{account_id}"

    async def store_refresh_token(
        self,
        account_id: UUID,
        refresh_token: str,
        granted_scopes: list[str],
    ) -> OAuthToken:
        encrypted = encrypt(refresh_token)
        result = await self.db.execute(
            select(OAuthToken).where(OAuthToken.gmail_account_id == account_id)
        )
        token_row = result.scalar_one_or_none()
        if token_row:
            token_row.encrypted_refresh_token = encrypted.ciphertext
            token_row.encryption_key_id = encrypted.key_id
            token_row.granted_scopes = granted_scopes
            token_row.refresh_fail_count = 0
            token_row.revoked_at = None
        else:
            token_row = OAuthToken(
                gmail_account_id=account_id,
                encrypted_refresh_token=encrypted.ciphertext,
                encryption_key_id=encrypted.key_id,
                granted_scopes=granted_scopes,
            )
            self.db.add(token_row)
        await self.db.flush()
        return token_row

    async def get_refresh_token(self, account_id: UUID) -> str:
        result = await self.db.execute(
            select(OAuthToken).where(OAuthToken.gmail_account_id == account_id)
        )
        token_row = result.scalar_one_or_none()
        if not token_row or token_row.revoked_at:
            raise TokenServiceError("No refresh token for account")
        return decrypt(
            bytes(token_row.encrypted_refresh_token),
            token_row.encryption_key_id,
        )

    async def get_refresh_token_optional(self, account_id: UUID) -> str | None:
        try:
            return await self.get_refresh_token(account_id)
        except TokenServiceError:
            return None

    async def cache_access_token(
        self,
        account_id: UUID,
        access_token: str,
        expires_in: int,
    ) -> None:
        client = await self.get_redis()
        ttl = max(expires_in - 60, 60)
        await client.setex(self._access_key(account_id), ttl, access_token)

    async def refresh_access_token(self, account_id: UUID) -> dict:
        acquired, lock_token = await self.lock_service.acquire_token_refresh_lock(
            str(account_id)
        )
        if not acquired:
            raise TokenServiceError("Token refresh already in progress")
        try:
            if self.settings.use_mock_gmail:
                access_token = f"mock_access_{account_id}"
                expires_in = 3600
                await self.cache_access_token(account_id, access_token, expires_in)
                result = await self.db.execute(
                    select(OAuthToken).where(OAuthToken.gmail_account_id == account_id)
                )
                token_row = result.scalar_one_or_none()
                if token_row:
                    token_row.last_refreshed_at = datetime.now(UTC)
                    token_row.access_token_expires_at = datetime.now(UTC) + timedelta(
                        seconds=expires_in
                    )
                return {"access_token": access_token, "expires_in": expires_in}

            refresh_token = await self.get_refresh_token(account_id)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": self.settings.google_client_id,
                        "client_secret": self.settings.google_client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
            if response.status_code != 200:
                data = response.json()
                if data.get("error") == "invalid_grant":
                    raise InvalidGrantError("invalid_grant")
                raise TokenServiceError("Token refresh failed")

            data = response.json()
            access_token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))
            await self.cache_access_token(account_id, access_token, expires_in)

            result = await self.db.execute(
                select(OAuthToken).where(OAuthToken.gmail_account_id == account_id)
            )
            token_row = result.scalar_one_or_none()
            if token_row:
                token_row.last_refreshed_at = datetime.now(UTC)
                token_row.access_token_expires_at = datetime.now(UTC) + timedelta(
                    seconds=expires_in
                )
                if "refresh_token" in data:
                    encrypted = encrypt(data["refresh_token"])
                    token_row.encrypted_refresh_token = encrypted.ciphertext
            return {"access_token": access_token, "expires_in": expires_in}
        finally:
            if lock_token:
                await self.lock_service.release("token_refresh", str(account_id), lock_token)

    async def revoke_tokens(self, account) -> None:
        result = await self.db.execute(
            select(OAuthToken).where(OAuthToken.gmail_account_id == account.id)
        )
        token_row = result.scalar_one_or_none()
        if token_row:
            token_row.revoked_at = datetime.now(UTC)
        client = await self.get_redis()
        await client.delete(self._access_key(account.id))


async def refresh_google_token(session: AsyncSession, account_id: UUID) -> dict:
    """Refresh one account's access token; mark auth_error on invalid_grant."""
    from app.models.gmail_account import GmailAccount
    from app.models.oauth_token import OAuthToken
    from app.services.audit_service import AuditService

    account = await session.get(GmailAccount, account_id)
    if account is None or account.deleted_at is not None:
        return {"status": "skipped", "reason": "account_not_found", "account_id": str(account_id)}

    if account.status == "auth_error":
        return {"status": "skipped", "reason": "auth_error", "account_id": str(account_id)}

    token_result = await session.execute(
        select(OAuthToken).where(OAuthToken.gmail_account_id == account_id)
    )
    token_row = token_result.scalar_one_or_none()
    if token_row is None or token_row.revoked_at is not None:
        return {"status": "skipped", "reason": "no_token", "account_id": str(account_id)}

    service = TokenService(session)
    audit = AuditService(session)
    try:
        data = await service.refresh_access_token(account_id)
        token_row.refresh_fail_count = 0
        await session.flush()
        return {
            "status": "ok",
            "account_id": str(account_id),
            "expires_in": data.get("expires_in"),
        }
    except InvalidGrantError:
        token_row.refresh_fail_count += 1
        account.status = "auth_error"
        account.paused_reason = "auth_error"
        account.paused_at = datetime.now(UTC)
        account.health_score = max(0, account.health_score - 50)
        token_row.revoked_at = datetime.now(UTC)
        await audit.log(
            action="gmail_account.auth_error",
            resource_type="gmail_account",
            user_id=account.user_id,
            resource_id=account.id,
            metadata={"reason": "invalid_grant"},
        )
        await session.flush()
        return {"status": "auth_error", "account_id": str(account_id)}
    except TokenServiceError as exc:
        token_row.refresh_fail_count += 1
        await session.flush()
        return {
            "status": "failed",
            "account_id": str(account_id),
            "error": str(exc),
        }


async def refresh_all_tokens(session: AsyncSession) -> dict:
    """Proactively refresh access tokens for all active connected accounts."""
    from app.models.gmail_account import GmailAccount
    from app.models.oauth_token import OAuthToken

    result = await session.execute(
        select(GmailAccount.id)
        .join(OAuthToken, OAuthToken.gmail_account_id == GmailAccount.id)
        .where(
            GmailAccount.deleted_at.is_(None),
            GmailAccount.status == "active",
            OAuthToken.revoked_at.is_(None),
        )
    )
    refreshed = 0
    failed = 0
    skipped = 0
    auth_errors = 0
    for account_id in result.scalars():
        outcome = await refresh_google_token(session, account_id)
        status = outcome.get("status")
        if status == "ok":
            refreshed += 1
        elif status == "skipped":
            skipped += 1
        elif status == "auth_error":
            auth_errors += 1
        else:
            failed += 1
    return {
        "refreshed": refreshed,
        "failed": failed,
        "skipped": skipped,
        "auth_errors": auth_errors,
    }
