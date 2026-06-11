"""Text file import parser tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.text_import_service import (
    TextImportService,
    parse_message_blocks,
    parse_subject_lines,
    plain_body_to_templates,
)


def test_parse_subject_lines():
    content = """
# Comments ignored
Quick question for {{name}}

Following up, {{name}}
"""
    assert parse_subject_lines(content) == [
        "Quick question for {{name}}",
        "Following up, {{name}}",
    ]


def test_parse_single_message_block():
    content = "Hi {{name}},\n\nHope you're well."
    assert parse_message_blocks(content) == [
        ("Imported message 1", "Hi {{name}},\n\nHope you're well.")
    ]


def test_parse_multiple_message_blocks():
    content = """--- Intro ---
Hi {{name}},

First message here.

---

Hi {{name}},

Second message here.
"""
    blocks = parse_message_blocks(content)
    assert len(blocks) == 2
    assert blocks[0][0] == "Intro"
    assert "First message" in blocks[0][1]
    assert blocks[1][0] == "Imported message 2"


def test_plain_body_excludes_unsubscribe_footer():
    html, text = plain_body_to_templates("Hi {{name}},\n\nTest body.")
    assert "Unsubscribe from these emails" not in html
    assert "Unsubscribe:" not in text


@pytest.mark.asyncio
async def test_import_subjects_from_text(db_session: AsyncSession, test_user):
    svc = TextImportService(db_session)
    result = await svc.import_subjects(
        test_user.id,
        "Hello {{name}}\nQuick note for {{name}}\n",
    )
    assert result.imported == 2
    assert result.skipped == 0


@pytest.mark.asyncio
async def test_import_messages_from_text(db_session: AsyncSession, test_user):
    svc = TextImportService(db_session)
    result = await svc.import_message_templates(
        test_user.id,
        "--- A ---\nHi {{name}},\n\nMessage A.\n\n--- B ---\nHi {{name}},\n\nMessage B.\n",
    )
    assert result.imported == 2
