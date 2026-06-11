"""Email template schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TemplateCreate(BaseModel):
    name: str
    html_template: str
    text_template: str | None = None
    subject_template: str | None = None


class TemplateUpdate(BaseModel):
    name: str | None = None
    subject_template: str | None = None
    html_template: str | None = None
    text_template: str | None = None
    is_active: bool | None = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    subject_template: str | None
    html_template: str
    text_template: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TemplatePreviewRequest(BaseModel):
    lead_sample: dict = Field(default_factory=dict)


class TemplatePreviewResponse(BaseModel):
    subject: str
    html: str
    text: str | None
