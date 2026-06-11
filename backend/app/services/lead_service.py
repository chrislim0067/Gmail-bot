"""Lead import, validation, and export."""

import csv
import io
import re
from datetime import UTC, datetime
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.lead_import_batch import LeadImportBatch
from app.services.suppression_service import SuppressionService
from app.utils.tier_caps import is_role_based_email, normalize_email

MAX_IMPORT_ROWS = 50_000
ROLE_PREFIXES = ("info@", "support@", "admin@", "sales@", "contact@", "noreply@", "no-reply@")


class LeadImportError(Exception):
    pass


def _parse_name_fields(row: dict) -> tuple[str | None, str | None]:
    """Support name or first_name/last_name CSV columns."""
    raw_name = (row.get("name") or "").strip()
    first_name = (row.get("first_name") or "").strip() or None
    last_name = (row.get("last_name") or "").strip() or None
    if not first_name and raw_name:
        name_parts = raw_name.split(None, 1)
        first_name = name_parts[0]
        if len(name_parts) > 1 and not last_name:
            last_name = name_parts[1]
    return first_name, last_name


class LeadService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.suppression = SuppressionService(db)

    def validate_email_syntax(self, email: str) -> tuple[bool, str | None]:
        try:
            validate_email(email, check_deliverability=False)
            return True, None
        except EmailNotValidError as exc:
            return False, str(exc)

    async def create_import_batch(
        self,
        campaign: Campaign,
        user_id: UUID,
        filename: str,
        *,
        compliance_acknowledged: bool,
        source_label: str | None = None,
        allow_role_based_emails: bool = False,
    ) -> LeadImportBatch:
        if not compliance_acknowledged:
            raise LeadImportError("compliance_acknowledged must be true")
        batch = LeadImportBatch(
            campaign_id=campaign.id,
            uploaded_by_user_id=user_id,
            filename=filename,
            source_label=source_label,
            compliance_acknowledged=compliance_acknowledged,
            allow_role_based_emails=allow_role_based_emails,
            status="processing",
            created_at=datetime.now(UTC),
        )
        self.db.add(batch)
        await self.db.flush()
        return batch

    async def process_csv(
        self,
        batch: LeadImportBatch,
        campaign: Campaign,
        content: str,
        *,
        allow_role_based_emails: bool = False,
    ) -> dict:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        if len(rows) > MAX_IMPORT_ROWS:
            raise LeadImportError(f"Import exceeds maximum of {MAX_IMPORT_ROWS} rows")

        batch.row_count = len(rows)
        imported = skipped = invalid = 0
        errors: list[str] = []

        existing_result = await self.db.execute(
            select(Lead.normalized_email).where(
                Lead.campaign_id == campaign.id,
                Lead.deleted_at.is_(None),
            )
        )
        existing_emails = set(existing_result.scalars().all())

        for i, row in enumerate(rows, start=2):
            email = (row.get("email") or "").strip()
            if not email:
                invalid += 1
                errors.append(f"Row {i}: missing email")
                continue

            normalized = normalize_email(email)
            valid, err = self.validate_email_syntax(email)
            if not valid:
                invalid += 1
                errors.append(f"Row {i}: {err}")
                continue

            if not allow_role_based_emails and is_role_based_email(email):
                skipped += 1
                errors.append(f"Row {i}: role-based email blocked ({email})")
                continue

            if normalized in existing_emails:
                skipped += 1
                errors.append(f"Row {i}: already in campaign ({email})")
                continue

            suppressed, reason = await self.suppression.is_suppressed(
                campaign.user_id, email
            )
            if suppressed:
                skipped += 1
                errors.append(f"Row {i}: suppressed ({reason})")
                continue

            first_name, last_name = _parse_name_fields(row)

            custom_fields = {
                k: v
                for k, v in row.items()
                if k.startswith("custom_") and v
            }
            lead = Lead(
                campaign_id=campaign.id,
                email=email,
                normalized_email=normalized,
                first_name=first_name,
                last_name=last_name,
                company=row.get("company") or None,
                custom_fields=custom_fields,
                source=row.get("source") or batch.source_label,
                source_url=row.get("source_url") or None,
                consent_basis=row.get("consent_basis") or None,
                consent_notes=row.get("consent_notes") or None,
                import_batch_id=batch.id,
                validation_status="valid",
                status="pending",
            )
            self.db.add(lead)
            existing_emails.add(normalized)
            imported += 1

        batch.imported_count = imported
        batch.skipped_count = skipped
        batch.invalid_count = invalid
        batch.status = "completed"
        campaign.total_leads += imported
        await self.db.flush()
        return {
            "imported": imported,
            "skipped": skipped,
            "invalid": invalid,
            "errors": errors[:100],
        }

    async def create_lead(
        self,
        campaign: Campaign,
        *,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        company: str | None = None,
        source: str | None = None,
        compliance_acknowledged: bool,
        allow_role_based_emails: bool = False,
    ) -> Lead:
        if not compliance_acknowledged:
            raise LeadImportError("compliance_acknowledged must be true")

        email = email.strip()
        normalized = normalize_email(email)
        valid, err = self.validate_email_syntax(email)
        if not valid:
            raise LeadImportError(err or "Invalid email")

        if not allow_role_based_emails and is_role_based_email(email):
            raise LeadImportError(f"Role-based email blocked ({email})")

        existing = await self.db.execute(
            select(Lead.id).where(
                Lead.campaign_id == campaign.id,
                Lead.normalized_email == normalized,
                Lead.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise LeadImportError("Lead with this email already exists in campaign")

        suppressed, reason = await self.suppression.is_suppressed(campaign.user_id, email)
        if suppressed:
            raise LeadImportError(f"Email is suppressed ({reason})")

        lead = Lead(
            campaign_id=campaign.id,
            email=email,
            normalized_email=normalized,
            first_name=first_name or None,
            last_name=last_name or None,
            company=company or None,
            source=source,
            validation_status="valid",
            status="pending",
        )
        self.db.add(lead)
        campaign.total_leads += 1
        await self.db.flush()
        return lead

    async def export_csv(self, campaign_id: UUID, status: str | None = None) -> str:
        query = select(Lead).where(
            Lead.campaign_id == campaign_id,
            Lead.deleted_at.is_(None),
        )
        if status:
            query = query.where(Lead.status == status)
        result = await self.db.execute(query)
        leads = result.scalars().all()

        output = io.StringIO()
        fieldnames = [
            "email", "first_name", "last_name", "company",
            "status", "validation_status", "source",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow({
                "email": lead.email,
                "first_name": lead.first_name or "",
                "last_name": lead.last_name or "",
                "company": lead.company or "",
                "status": lead.status,
                "validation_status": lead.validation_status,
                "source": lead.source or "",
            })
        return output.getvalue()
