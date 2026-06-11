"""Signed JWT tokens for one-click unsubscribe links."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from jose import JWTError, jwt

from app.config import get_settings

UNSUBSCRIBE_ALGORITHM = "HS256"


class UnsubscribeTokenError(Exception):
    """Raised when unsubscribe token is invalid or expired."""


def create_unsubscribe_token(
    *,
    user_id: UUID,
    campaign_id: UUID,
    lead_id: UUID,
    email: str,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(lead_id),
        "uid": str(user_id),
        "cid": str(campaign_id),
        "email": email,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.unsubscribe_token_expire_days),
        "typ": "unsubscribe",
    }
    return jwt.encode(payload, settings.unsubscribe_secret, algorithm=UNSUBSCRIBE_ALGORITHM)


def verify_unsubscribe_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.unsubscribe_secret,
            algorithms=[UNSUBSCRIBE_ALGORITHM],
        )
    except JWTError as exc:
        raise UnsubscribeTokenError("Invalid or expired unsubscribe token") from exc
    if payload.get("typ") != "unsubscribe":
        raise UnsubscribeTokenError("Invalid token type")
    required = ("sub", "uid", "cid", "email")
    if not all(payload.get(k) for k in required):
        raise UnsubscribeTokenError("Missing token claims")
    return payload
