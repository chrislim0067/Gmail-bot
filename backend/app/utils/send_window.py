"""Campaign send-window helpers (local timezone hours)."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.campaign import Campaign


def _campaign_tz(campaign: Campaign) -> ZoneInfo:
    try:
        return ZoneInfo(campaign.timezone or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def is_within_send_window(campaign: Campaign, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    start_h = campaign.send_window_start_hour
    end_h = campaign.send_window_end_hour
    if start_h == end_h:
        return True

    local = now.astimezone(_campaign_tz(campaign))
    hour = local.hour
    if start_h < end_h:
        return start_h <= hour < end_h
    return hour >= start_h or hour < end_h


def next_send_window_start(campaign: Campaign, now: datetime | None = None) -> datetime:
    """UTC datetime when the campaign's next send window opens."""
    now = now or datetime.now(UTC)
    if is_within_send_window(campaign, now):
        return now

    tz = _campaign_tz(campaign)
    local = now.astimezone(tz)
    start_h = campaign.send_window_start_hour
    end_h = campaign.send_window_end_hour

    if start_h == end_h:
        return now

    candidate = local.replace(hour=start_h, minute=0, second=0, microsecond=0)
    if start_h < end_h:
        if local.hour >= end_h:
            candidate += timedelta(days=1)
    elif end_h <= local.hour < start_h:
        pass
    else:
        return now

    return candidate.astimezone(UTC)
