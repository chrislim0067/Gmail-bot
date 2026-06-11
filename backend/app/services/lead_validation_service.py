"""Lead email validation with optional MX DNS check (mockable)."""

import os
from uuid import UUID

from email_validator import EmailNotValidError, validate_email

from app.models.lead import Lead


async def validate_lead_email(session, lead_id: UUID, check_mx: bool | None = None) -> dict:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        return {"validation_status": "invalid", "error": "lead_not_found"}

    if check_mx is None:
        check_mx = os.environ.get("LEAD_VALIDATION_CHECK_MX", "false").lower() == "true"

    try:
        if check_mx:
            validate_email(lead.email, check_deliverability=True)
        else:
            validate_email(lead.email, check_deliverability=False)
        lead.validation_status = "valid"
        lead.validation_error = None
        return {"validation_status": "valid", "lead_id": str(lead_id)}
    except EmailNotValidError as exc:
        lead.validation_status = "invalid"
        lead.validation_error = str(exc)
        return {"validation_status": "invalid", "error": str(exc)}
    except Exception as exc:
        lead.validation_status = "unknown"
        lead.validation_error = str(exc)
        return {"validation_status": "unknown", "error": str(exc)}
