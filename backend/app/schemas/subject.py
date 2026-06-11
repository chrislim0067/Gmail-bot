"""Email subject line schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubjectCreate(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class SubjectUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=500)
    is_active: bool | None = None


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
