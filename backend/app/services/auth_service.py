"""Authentication: password hashing and JWT tokens."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User

BCRYPT_ROUNDS = 12


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    def hash_password(self, password: str) -> str:
        digest = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS))
        return digest.decode("utf-8")

    def verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    def create_access_token(self, user_id: UUID) -> tuple[str, int]:
        expires_minutes = self.settings.jwt_expire_minutes
        expire = datetime.now(UTC) + timedelta(minutes=expires_minutes)
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "iat": datetime.now(UTC),
            "typ": "access",
        }
        token = jwt.encode(
            payload,
            self.settings.jwt_secret,
            algorithm=self.settings.jwt_algorithm,
        )
        return token, expires_minutes * 60

    def decode_access_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[self.settings.jwt_algorithm],
            )
        except JWTError as exc:
            raise AuthError("Invalid or expired token") from exc
        if payload.get("typ") != "access":
            raise AuthError("Invalid token type")
        sub = payload.get("sub")
        if not sub:
            raise AuthError("Missing subject")
        return UUID(sub)

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def register(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> User:
        existing = await self.get_user_by_email(email)
        if existing:
            raise AuthError("Email already registered")
        user = User(
            email=email.lower(),
            password_hash=self.hash_password(password),
            full_name=full_name,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.get_user_by_email(email)
        if not user or not self.verify_password(password, user.password_hash):
            raise AuthError("Invalid credentials")
        if not user.is_active:
            raise AuthError("Account is inactive")
        return user
