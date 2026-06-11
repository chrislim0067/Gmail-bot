"""CSV lead import with compliance acknowledgement and role-based blocking."""

import csv
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select

from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.lead_import_batch import LeadImportBatch
from app.utils.tier_caps import is_role_based_email, normalize_email


def _upload_path(batch_id: UUID) -> Path:
    base = Path(os.environ.get("UPLOAD_DIR", "data/uploads"))
    return base / f"{batch_id}.csv"


async def process_lead_import_batch(session, import_batch_id: UUID) -> dict:
    batch = await session.get(LeadImportBatch, import_batch_id)
    if batch is None:
        return {"error": "batch_not_found"}

    if not batch.compliance_acknowledged:
        batch.status = "failed"
        return {"error": "compliance_not_acknowledged", "imported": 0}

    campaign = await session.get(Campaign, batch.campaign_id)
    if campaign is None:
        batch.status = "failed"
        return {"error": "campaign_not_found", "imported": 0}

    csv_path = _upload_path(import_batch_id)
    if not csv_path.exists():
        batch.status = "failed"
        return {"error": "csv_not_found", "path": str(csv_path), "imported": 0}

    imported = 0
    skipped = 0
    invalid = 0
    row_count = 0

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            raw_email = (row.get("email") or "").strip()
            if not raw_email:
                invalid += 1
                continue

            try:
                validated = validate_email(raw_email, check_deliverability=False)
                email = validated.normalized
            except EmailNotValidError:
                invalid += 1
                continue

            normalized = normalize_email(email)

            if is_role_based_email(normalized) and not batch.allow_role_based_emails:
                skipped += 1
                continue

            existing = await session.execute(
                select(Lead.id).where(
                    Lead.campaign_id == batch.campaign_id,
                    Lead.normalized_email == normalized,
                    Lead.deleted_at.is_(None),
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            raw_name = (row.get("name") or "").strip()
            first_name = (row.get("first_name") or "").strip() or None
            last_name = (row.get("last_name") or "").strip() or None
            if not first_name and raw_name:
                name_parts = raw_name.split(None, 1)
                first_name = name_parts[0]
                if len(name_parts) > 1 and not last_name:
                    last_name = name_parts[1]

            lead = Lead(
                campaign_id=batch.campaign_id,
                email=email,
                normalized_email=normalized,
                first_name=first_name,
                last_name=last_name,
                company=(row.get("company") or "").strip() or None,
                source=batch.source_label or "csv_import",
                import_batch_id=batch.id,
                status="pending",
                validation_status="pending",
            )
            session.add(lead)
            imported += 1

    batch.row_count = row_count
    batch.imported_count = imported
    batch.skipped_count = skipped
    batch.invalid_count = invalid
    batch.status = "completed"
    campaign.total_leads += imported

    return {
        "imported": imported,
        "skipped": skipped,
        "invalid": invalid,
        "row_count": row_count,
    }
