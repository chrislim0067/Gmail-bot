"""Text file import response schemas."""

from pydantic import BaseModel, Field


class TextImportResponse(BaseModel):
    imported: int
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)
