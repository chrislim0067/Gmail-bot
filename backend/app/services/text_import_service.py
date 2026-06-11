"""Parse plain-text files into message templates or subject lines."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.subject_service import SubjectService
from app.services.template_service import TemplateService, TemplateValidationError

MAX_IMPORT_ITEMS = 100
MAX_FILE_CHARS = 500_000

class TextImportError(Exception):
    pass


@dataclass
class TextImportResult:
    imported: int
    skipped: int
    errors: list[str]


def _format_paragraph(text: str) -> str:
    lines = [html.escape(line.strip()) for line in text.split("\n")]
    return "<br>".join(lines)


def plain_body_to_templates(body: str) -> tuple[str, str]:
    """Convert plain message body to stored HTML + text templates."""
    parts: list[str] = []
    for block in body.split("\n\n"):
        trimmed = block.strip()
        if trimmed:
            parts.append(f"<p>{_format_paragraph(trimmed)}</p>")
    html_template = "\n".join(parts)
    text_template = body.strip()
    return html_template, text_template


def parse_subject_lines(content: str) -> list[str]:
    """One subject per non-empty line. Lines starting with # are ignored."""
    subjects: list[str] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        subjects.append(line)
    return subjects


def parse_message_blocks(content: str) -> list[tuple[str, str]]:
    """
    Split a text file into message templates.

    Separate templates with a line containing only --- or --- Name ---.
    If no separators exist, the whole file becomes one template.
    """
    text = content.strip()
    if not text:
        return []

    blocks: list[tuple[str | None, str]] = []
    current_name: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_name, current_lines
        body = "\n".join(current_lines).strip()
        if body:
            blocks.append((current_name, body))
        current_name = None
        current_lines = []

    for line in content.splitlines():
        named = re.match(r"^\s*---\s*(.+?)\s*---\s*$", line)
        if named:
            flush()
            current_name = named.group(1).strip() or None
            continue
        if re.match(r"^\s*---\s*$", line):
            flush()
            continue
        current_lines.append(line)

    flush()

    if not blocks:
        return []

    if len(blocks) == 1 and blocks[0][0] is None:
        return [("Imported message 1", blocks[0][1])]

    results: list[tuple[str, str]] = []
    for index, (name, body) in enumerate(blocks, start=1):
        label = name or f"Imported message {index}"
        results.append((label, body))
    return results


class TextImportService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.templates = TemplateService(db)
        self.subjects = SubjectService(db)

    def _validate_size(self, content: str) -> None:
        if len(content) > MAX_FILE_CHARS:
            raise TextImportError("Text file is too large (max 500 KB)")

    async def import_subjects(self, user_id: UUID, content: str) -> TextImportResult:
        self._validate_size(content)
        lines = parse_subject_lines(content)
        if not lines:
            raise TextImportError("No subject lines found in file")
        if len(lines) > MAX_IMPORT_ITEMS:
            raise TextImportError(f"Maximum {MAX_IMPORT_ITEMS} subjects per import")

        imported = 0
        skipped = 0
        errors: list[str] = []

        for index, line in enumerate(lines, start=1):
            try:
                await self.subjects.create(user_id, line)
                imported += 1
            except TemplateValidationError as exc:
                skipped += 1
                errors.append(f"Line {index}: {exc}")

        if imported == 0:
            raise TextImportError(
                errors[0] if errors else "No valid subject lines could be imported"
            )

        return TextImportResult(imported=imported, skipped=skipped, errors=errors)

    async def import_message_templates(
        self, user_id: UUID, content: str
    ) -> TextImportResult:
        self._validate_size(content)
        blocks = parse_message_blocks(content)
        if not blocks:
            raise TextImportError("No message templates found in file")
        if len(blocks) > MAX_IMPORT_ITEMS:
            raise TextImportError(f"Maximum {MAX_IMPORT_ITEMS} templates per import")

        imported = 0
        skipped = 0
        errors: list[str] = []

        for index, (name, body) in enumerate(blocks, start=1):
            try:
                html_template, text_template = plain_body_to_templates(body)
                await self.templates.create(
                    user_id=user_id,
                    name=name,
                    html_template=html_template,
                    text_template=text_template,
                )
                imported += 1
            except TemplateValidationError as exc:
                skipped += 1
                errors.append(f"Template {index} ({name}): {exc}")

        if imported == 0:
            raise TextImportError(
                errors[0] if errors else "No valid message templates could be imported"
            )

        return TextImportResult(imported=imported, skipped=skipped, errors=errors)
