"""Mock Gmail API client for development and tests."""

import uuid
from uuid import UUID


class MockGmailClient:
    async def send_message(self, account_id: UUID, message: dict) -> dict:
        msg_id = f"mock_{uuid.uuid4().hex[:16]}"
        return {
            "gmail_message_id": msg_id,
            "thread_id": f"thread_{msg_id}",
            "rfc_message_id": message.get("rfc_message_id", f"<{msg_id}@mock.gmail>"),
        }

    async def list_messages(
        self,
        account_id: UUID,
        query: str = "",
        *,
        max_results: int = 50,
    ) -> list[dict]:
        return []

    async def get_message(self, account_id: UUID, message_id: str) -> dict:
        return {"id": message_id, "snippet": "", "headers": {}}

    async def revoke_token(self, token: str) -> bool:
        return True


def list_recent_messages(
    email: str,
    query: str = "",
    *,
    max_results: int = 50,
) -> list[dict]:
    """Legacy helper kept for bounce_service compatibility in mock mode."""
    return []


def get_message_raw(email: str, message_id: str) -> str:
    """Legacy helper kept for bounce_service compatibility in mock mode."""
    return ""
