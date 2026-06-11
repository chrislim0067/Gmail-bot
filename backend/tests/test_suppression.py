"""Suppression and unsubscribe tests."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.suppression_service import SuppressionService
from app.utils.jwt_unsubscribe import create_unsubscribe_token, verify_unsubscribe_token


@pytest.mark.asyncio
async def test_unsubscribe_suppression(db_session: AsyncSession, test_user):
    suppression = SuppressionService(db_session)
    email = "lead@example.com"
    await suppression.add_unsubscribe(
        user_id=test_user.id,
        email=email,
        source="manual",
    )
    suppressed, reason = await suppression.is_suppressed(test_user.id, email)
    assert suppressed is True
    assert reason == "unsubscribed"


@pytest.mark.asyncio
async def test_unsubscribe_token_roundtrip():
    user_id = uuid4()
    campaign_id = uuid4()
    lead_id = uuid4()
    token = create_unsubscribe_token(
        user_id=user_id,
        campaign_id=campaign_id,
        lead_id=lead_id,
        email="lead@example.com",
    )
    payload = verify_unsubscribe_token(token)
    assert payload["sub"] == str(lead_id)
    assert payload["email"] == "lead@example.com"
