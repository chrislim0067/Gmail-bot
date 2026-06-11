"""Campaign preflight validation before send."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.account_pool import GmailAccountPool, GmailAccountPoolMember
from app.models.campaign import Campaign
from app.models.gmail_account import GmailAccount
from app.models.lead import Lead
from app.models.email_subject import EmailSubject
from app.models.template import EmailTemplate
from app.models.user import User


async def run_campaign_preflight(session, campaign_id: UUID) -> dict:
    settings = get_settings()
    checks: list[dict] = []

    campaign = await session.get(Campaign, campaign_id)
    if campaign is None or campaign.deleted_at is not None:
        checks.append({"name": "campaign_exists", "passed": False, "message": "Campaign not found"})
        return {"passed": False, "checks": checks}

    user = await session.get(User, campaign.user_id)
    checks.append({
        "name": "user_active",
        "passed": user is not None and user.is_active,
        "message": "User inactive or missing",
    })
    checks.append({
        "name": "risk_budget",
        "passed": user is not None and user.global_risk_score < settings.global_risk_score_threshold,
        "message": "Global risk budget exceeded",
    })

    template_count = await session.execute(
        select(func.count())
        .select_from(EmailTemplate)
        .where(
            EmailTemplate.user_id == campaign.user_id,
            EmailTemplate.is_active.is_(True),
            EmailTemplate.deleted_at.is_(None),
        )
    )
    active_templates = int(template_count.scalar_one())
    checks.append({
        "name": "message_templates",
        "passed": active_templates > 0,
        "message": "Add at least one message template before sending",
    })

    subject_count = await session.execute(
        select(func.count())
        .select_from(EmailSubject)
        .where(
            EmailSubject.user_id == campaign.user_id,
            EmailSubject.is_active.is_(True),
            EmailSubject.deleted_at.is_(None),
        )
    )
    active_subjects = int(subject_count.scalar_one())
    checks.append({
        "name": "subject_lines",
        "passed": active_subjects > 0,
        "message": "Add at least one subject line before sending",
    })

    pool = await session.get(GmailAccountPool, campaign.campaign_account_pool_id)
    checks.append({
        "name": "pool_active",
        "passed": pool is not None and pool.status == "active",
        "message": "Account pool missing or inactive",
    })

    active_accounts = 0
    if pool:
        member_result = await session.execute(
            select(func.count())
            .select_from(GmailAccountPoolMember)
            .join(GmailAccount, GmailAccountPoolMember.gmail_account_id == GmailAccount.id)
            .where(
                GmailAccountPoolMember.pool_id == pool.id,
                GmailAccountPoolMember.is_active.is_(True),
                GmailAccount.status == "active",
                GmailAccount.account_tier.notin_(("restricted", "paused")),
                GmailAccount.review_required.is_(False),
            )
        )
        active_accounts = int(member_result.scalar_one())
        checks.append({
            "name": "pool_has_accounts",
            "passed": active_accounts > 0,
            "message": "No active send-capable accounts in pool",
        })
        checks.append({
            "name": "pool_active_limit",
            "passed": active_accounts <= pool.active_account_limit,
            "message": "Pool active account limit exceeded",
        })

    lead_count = await session.execute(
        select(func.count()).select_from(Lead).where(
            Lead.campaign_id == campaign_id,
            Lead.deleted_at.is_(None),
            Lead.status.in_(("pending", "queued")),
        )
    )
    pending_leads = int(lead_count.scalar_one())
    checks.append({
        "name": "has_leads",
        "passed": pending_leads > 0,
        "message": "No pending leads to send",
    })

    passed = all(c["passed"] for c in checks)
    if passed:
        campaign.preflight_passed_at = datetime.now(UTC)

    return {"passed": passed, "checks": checks}


class PreflightService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(self, campaign_id: UUID) -> dict:
        return await run_campaign_preflight(self.db, campaign_id)
