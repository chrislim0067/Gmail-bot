"""Google OAuth connect/callback flow with mock support."""

import json
import secrets
from datetime import UTC, datetime
from urllib.parse import urlencode
from uuid import UUID

import httpx
import redis.asyncio as redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.utils.redis_client import create_async_redis
from app.models.gmail_account import GmailAccount
from app.models.gmail_sync_cursor import GmailSyncCursor
from app.models.oauth_token import OAuthToken
from app.services.token_service import TokenService
from app.utils.tier_caps import get_tier_caps

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "openid",
    "email",
    "profile",
]


class OAuthStateError(Exception):
    pass


class TokenExchangeError(Exception):
    pass


class OAuthCapExceededError(Exception):
    pass


class OAuthService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis | None = None) -> None:
        self.db = db
        self.settings = get_settings()
        self._client = redis_client
        self.token_service = TokenService(db, redis_client)

    async def get_redis(self) -> redis.Redis:
        if self._client is None:
            self._client = create_async_redis()
        return self._client

    def _state_key(self, nonce: str) -> str:
        return f"oauth_state:{nonce}"

    async def create_connect_url(self, user_id: UUID, redirect_uri: str | None = None) -> str:
        if self.settings.google_oauth_publishing_status == "testing":
            count_result = await self.db.execute(
                select(func.count(GmailAccount.id)).where(
                    GmailAccount.deleted_at.is_(None),
                    GmailAccount.status != "revoked",
                )
            )
            count = count_result.scalar() or 0
            if count >= self.settings.google_oauth_test_user_limit:
                raise OAuthCapExceededError(
                    "OAuth test user limit reached while app is in Testing mode"
                )

        nonce = secrets.token_urlsafe(32)
        client = await self.get_redis()
        await client.setex(
            self._state_key(nonce),
            self.settings.oauth_state_ttl_seconds,
            json.dumps({"user_id": str(user_id)}),
        )

        if self.settings.use_mock_gmail:
            params = urlencode({"state": nonce, "mock": "1"})
            return f"{self.settings.frontend_url}/accounts/connect/mock?{params}"

        redirect = redirect_uri or self.settings.google_redirect_uri
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": nonce,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def validate_state(self, state: str) -> UUID:
        client = await self.get_redis()
        raw = await client.get(self._state_key(state))
        if not raw:
            raise OAuthStateError("Invalid or expired OAuth state")
        await client.delete(self._state_key(state))
        data = json.loads(raw)
        return UUID(data["user_id"])

    async def exchange_code(self, code: str) -> dict:
        if self.settings.use_mock_gmail:
            return {
                "access_token": f"mock_access_{code[:8]}",
                "refresh_token": f"mock_refresh_{code[:8]}",
                "expires_in": 3600,
                "scope": " ".join(SCOPES),
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "redirect_uri": self.settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
        if response.status_code != 200:
            raise TokenExchangeError("Failed to exchange authorization code")
        return response.json()

    async def fetch_user_info(self, access_token: str) -> dict:
        if self.settings.use_mock_gmail:
            suffix = access_token[-8:]
            return {
                "sub": f"mock_google_{suffix}",
                "email": f"mock.user.{suffix}@gmail.com",
                "name": f"Mock User {suffix}",
            }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if response.status_code != 200:
            raise TokenExchangeError("Failed to fetch user info")
        return response.json()

    async def connect_account(
        self,
        code: str,
        state: str,
    ) -> GmailAccount:
        user_id = await self.validate_state(state)

        token_data = await self.exchange_code(code)
        user_info = await self.fetch_user_info(token_data["access_token"])
        email = user_info["email"].lower()
        google_user_id = user_info["sub"]
        scopes = token_data.get("scope", " ".join(SCOPES)).split()

        result = await self.db.execute(
            select(GmailAccount).where(
                GmailAccount.user_id == user_id,
                GmailAccount.email == email,
                GmailAccount.deleted_at.is_(None),
            )
        )
        account = result.scalar_one_or_none()
        tier_caps = get_tier_caps("new")

        if account:
            account.google_user_id = google_user_id
            account.display_name = user_info.get("name")
            account.status = "active"
            account.deleted_at = None
        else:
            account = GmailAccount(
                user_id=user_id,
                email=email,
                google_user_id=google_user_id,
                display_name=user_info.get("name"),
                connected_at=datetime.now(UTC),
                tier_daily_default=tier_caps.daily_default,
                tier_daily_hard_max=tier_caps.daily_hard_max,
                daily_send_limit=tier_caps.daily_default,
                hourly_send_limit=tier_caps.hourly_cap,
            )
            self.db.add(account)
            await self.db.flush()
            self.db.add(GmailSyncCursor(gmail_account_id=account.id))

        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            await self.token_service.store_refresh_token(
                account.id,
                refresh_token,
                scopes,
            )
        elif not await self.token_service.get_refresh_token_optional(account.id):
            raise TokenExchangeError(
                "Google did not return a refresh token. Revoke app access in "
                "Google Account settings and connect again."
            )

        await self.token_service.cache_access_token(
            account.id,
            token_data["access_token"],
            int(token_data.get("expires_in", 3600)),
        )
        await self.db.flush()
        return account

    async def mock_connect(self, user_id: UUID, state: str) -> GmailAccount:
        account = await self.connect_account(
            code=secrets.token_urlsafe(16),
            state=state,
        )
        if account.user_id != user_id:
            raise OAuthStateError("OAuth state user mismatch")
        return account

    async def revoke_account(self, account: GmailAccount) -> None:
        if not self.settings.use_mock_gmail:
            try:
                refresh = await self.token_service.get_refresh_token(account.id)
                async with httpx.AsyncClient() as client:
                    await client.post(GOOGLE_REVOKE_URL, params={"token": refresh})
            except Exception:
                pass
        await self.token_service.revoke_tokens(account)
        account.status = "revoked"
        account.deleted_at = datetime.now(UTC)

    async def get_granted_scopes(self, account_id: UUID) -> list[str]:
        result = await self.db.execute(
            select(OAuthToken.granted_scopes).where(
                OAuthToken.gmail_account_id == account_id
            )
        )
        scopes = result.scalar_one_or_none()
        return list(scopes) if scopes else []
