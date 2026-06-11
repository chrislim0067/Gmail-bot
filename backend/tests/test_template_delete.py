"""Template and subject soft-delete tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import EmailTemplate


@pytest.mark.asyncio
async def test_delete_template(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user,
):
    template = EmailTemplate(
        user_id=test_user.id,
        name="Delete Me",
        html_template="<p>Hi <a href='{{unsubscribe_url}}'>unsub</a></p>",
        text_template="Hi {{unsubscribe_url}}",
    )
    db_session.add(template)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/templates/{template.id}",
        headers=auth_headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_all_templates(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user,
):
    for index in range(2):
        db_session.add(
            EmailTemplate(
                user_id=test_user.id,
                name=f"Bulk {index}",
                html_template="<p>{{unsubscribe_url}}</p>",
            )
        )
    await db_session.flush()

    response = await client.post(
        "/api/v1/templates/delete-all",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["deleted"] >= 2
