"""Gmail API client factory — mock or real based on USE_MOCK_GMAIL."""

from uuid import UUID

import httpx

from app.config import get_settings
from app.gmail.mock_client import MockGmailClient

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"


class GoogleGmailClient:
    """Real Gmail API wrapper (used when USE_MOCK_GMAIL=false)."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def _access_token(self, account_id: UUID) -> str:
        from app.database import async_session_factory
        from app.services.token_service import TokenService

        async with async_session_factory() as session:
            token_service = TokenService(session)
            token_data = await token_service.refresh_access_token(account_id)
            return token_data["access_token"]

    async def send_message(self, account_id: UUID, message: dict) -> dict:
        access_token = await self._access_token(account_id)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GMAIL_API}/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": message["raw"]},
            )
        if response.status_code != 200:
            raise RuntimeError(f"Gmail send failed: {response.status_code}")
        data = response.json()
        gmail_message_id = data.get("id")
        thread_id = data.get("threadId")
        rfc_message_id = message.get("rfc_message_id")

        # Gmail may replace the Message-ID we set in MIME with its own.
        if gmail_message_id:
            try:
                sent = await self.get_message(account_id, gmail_message_id)
                rfc_message_id = sent.get("headers", {}).get("Message-ID") or rfc_message_id
            except Exception:
                pass

        return {
            "gmail_message_id": gmail_message_id,
            "thread_id": thread_id,
            "rfc_message_id": rfc_message_id,
        }

    async def list_messages(
        self,
        account_id: UUID,
        query: str = "in:inbox newer_than:30d",
        *,
        max_results: int = 50,
    ) -> list[dict]:
        access_token = await self._access_token(account_id)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GMAIL_API}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"q": query, "maxResults": max_results},
            )
        if response.status_code != 200:
            raise RuntimeError(f"Gmail list failed: {response.status_code} {response.text}")
        data = response.json()
        return [{"id": m["id"]} for m in data.get("messages", [])]

    async def get_message(self, account_id: UUID, message_id: str) -> dict:
        access_token = await self._access_token(account_id)
        metadata_headers = [
            "Message-ID",
            "In-Reply-To",
            "References",
            "From",
            "Subject",
            "Date",
        ]
        params: list[tuple[str, str]] = [("format", "metadata")]
        for header in metadata_headers:
            params.append(("metadataHeaders", header))

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GMAIL_API}/messages/{message_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        if response.status_code != 200:
            raise RuntimeError(
                f"Gmail get message failed: {response.status_code} {response.text}"
            )
        data = response.json()
        headers = {
            h["name"]: h["value"]
            for h in data.get("payload", {}).get("headers", [])
        }
        return {
            "id": data.get("id", message_id),
            "thread_id": data.get("threadId"),
            "snippet": data.get("snippet", ""),
            "headers": headers,
        }


def get_gmail_client() -> MockGmailClient | GoogleGmailClient:
    settings = get_settings()
    if settings.use_mock_gmail:
        return MockGmailClient()
    return GoogleGmailClient()
