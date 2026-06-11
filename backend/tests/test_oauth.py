"""OAuth mock flow tests."""

import json

import pytest
from httpx import AsyncClient

from app.services.oauth_service import OAuthService, OAuthStateError


@pytest.mark.asyncio
async def test_oauth_state_invalid_rejected(db_session):
    oauth = OAuthService(db_session)
    with pytest.raises(OAuthStateError):
        await oauth.validate_state("invalid-state-nonce")


@pytest.mark.asyncio
async def test_oauth_mock_connect(
    client: AsyncClient,
    auth_headers: dict,
    db_session,
    test_user,
):
    oauth = OAuthService(db_session)
    url = await oauth.create_connect_url(test_user.id)
    assert "state=" in url

    state = url.split("state=")[-1].split("&")[0]
    response = await client.post(
        f"/api/v1/gmail/mock-connect?state={state}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "active"
