"""Lead schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    email: str
    normalized_email: str
    first_name: str | None
    last_name: str | None
    company: str | None
    custom_fields: dict
    source: str | None
    source_url: str | None
    consent_basis: str | None
    status: str
    validation_status: str
    validation_error: str | None
    import_batch_id: UUID | None
    last_contacted_at: datetime | None
    do_not_contact_reason: str | None
    created_at: datetime


class LeadImportResponse(BaseModel):
    import_batch_id: UUID
    status: str
    imported: int = 0
    skipped: int = 0
    invalid: int = 0
    errors: list[str] = []


class LeadImportStatusResponse(BaseModel):
    status: str
    imported: int
    skipped: int
    invalid: int
    errors: list[str]


class LeadCreate(BaseModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    source: str | None = None
    compliance_acknowledged: bool
    allow_role_based_emails: bool = False
