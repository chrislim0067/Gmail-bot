"""Campaign CRUD tests."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account_pool import GmailAccountPool


@pytest.mark.asyncio
async def test_create_campaign(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user,
):
    pool = GmailAccountPool(user_id=test_user.id, name="Default Pool")
    db_session.add(pool)
    await db_session.flush()

    response = await client.post(
        "/api/v1/campaigns",
        headers=auth_headers,
        json={
            "name": "Test Campaign",
            "campaign_account_pool_id": str(pool.id),
            "scheduled_start_at": datetime.now(UTC).isoformat(),
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Campaign"
