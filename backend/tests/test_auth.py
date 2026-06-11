"""Auth unit and integration tests."""

import pytest
from httpx import AsyncClient

from app.services.auth_service import AuthService
from app.utils.crypto import decrypt, encrypt


@pytest.mark.asyncio
async def test_auth_register_login(client: AsyncClient):
    email = "newuser@example.com"
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePass1", "full_name": "New User"},
    )
    assert register.status_code == 201
    assert register.json()["email"] == email

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePass1"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == email


@pytest.mark.asyncio
async def test_token_encryption_roundtrip():
    plaintext = "mock_refresh_token_value"
    payload = encrypt(plaintext)
    assert decrypt(payload.ciphertext, payload.key_id) == plaintext


@pytest.mark.asyncio
async def test_password_hash_verify(db_session):
    auth = AuthService(db_session)
    hashed = auth.hash_password("TestPass1")
    assert auth.verify_password("TestPass1", hashed)
    assert not auth.verify_password("WrongPass1", hashed)
