"""Multi-signal bounce detection parser for DSN messages."""

import email
import re
from dataclasses import dataclass
from email import policy
from typing import BinaryIO


@dataclass
class BounceResult:
    bounced_email: str | None
    bounce_type: str
    smtp_status_code: str | None
    detection_method: str
    diagnostic: str | None
    raw_headers: dict


BOUNCE_FROM_PATTERNS = (
    "mailer-daemon",
    "postmaster",
    "mail delivery subsystem",
)

BOUNCE_SUBJECT_PATTERNS = (
    "delivery status notification",
    "undelivered mail returned to sender",
    "delivery has failed",
    "address not found",
    "mail delivery failed",
)

EMAIL_REGEX = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")

SYSTEM_EMAIL_PATTERNS = (
    "mailer-daemon",
    "postmaster",
    "mail delivery subsystem",
)


def _is_system_address(email_addr: str) -> bool:
    lowered = email_addr.lower()
    return any(p in lowered for p in SYSTEM_EMAIL_PATTERNS)


def parse_bounce_message(source: str | bytes | BinaryIO) -> BounceResult | None:
    raw_text = ""
    if isinstance(source, bytes):
        raw_text = source.decode("utf-8", errors="replace")
        msg = email.message_from_bytes(source, policy=policy.default)
    elif isinstance(source, str):
        raw_text = source
        msg = email.message_from_string(source, policy=policy.default)
    else:
        raw_bytes = source.read()
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)

    from_hdr = (msg.get("From") or "").lower()
    subject = (msg.get("Subject") or "").lower()

    from_signal = any(p in from_hdr for p in BOUNCE_FROM_PATTERNS)
    subject_signal = any(p in subject for p in BOUNCE_SUBJECT_PATTERNS)
    if not from_signal and not subject_signal:
        return None

    bounced_email = None
    smtp_status = None
    diagnostic = None
    detection_method = "subject_fallback"
    bounce_type = "soft"

    full_text_parts: list[str] = []

    for part in msg.walk():
        ctype = part.get_content_type()
        payload = part.get_payload(decode=True)
        if payload:
            text = payload.decode("utf-8", errors="replace")
            full_text_parts.append(text)
        else:
            raw_payload = part.get_payload()
            if isinstance(raw_payload, str):
                full_text_parts.append(raw_payload)

        if ctype == "message/delivery-status":
            text = full_text_parts[-1] if full_text_parts else ""
            bounced_email = bounced_email or _extract_dsn_field(text, "Final-Recipient")
            bounced_email = bounced_email or _extract_dsn_field(text, "Original-Recipient")
            smtp_status = smtp_status or _extract_dsn_field(text, "Status")
            diagnostic = diagnostic or _extract_dsn_field(text, "Diagnostic-Code")
            detection_method = "dsn_body"
        elif ctype == "text/rfc822-headers":
            text = full_text_parts[-1] if full_text_parts else ""
            if not bounced_email:
                match = EMAIL_REGEX.search(text)
                if match:
                    bounced_email = match.group(0)
                    detection_method = "rfc822_headers"

    full_body = "\n".join(full_text_parts)
    if raw_text:
        full_body = f"{full_body}\n{raw_text}" if full_body else raw_text
    if not smtp_status:
        smtp_status = _extract_dsn_field(full_body, "Status")
    if not bounced_email:
        bounced_email = _extract_dsn_field(full_body, "Final-Recipient")
        bounced_email = bounced_email or _extract_dsn_field(full_body, "Original-Recipient")
    if not diagnostic:
        diagnostic = _extract_dsn_field(full_body, "Diagnostic-Code")

    if not bounced_email:
        body_text = _collect_text(msg) or "\n".join(full_text_parts)
        matches = [m for m in EMAIL_REGEX.findall(body_text) if not _is_system_address(m)]
        if matches:
            bounced_email = matches[0]
            detection_method = "regex_fallback"

    if smtp_status:
        if smtp_status.startswith("5"):
            bounce_type = "hard"
        elif smtp_status.startswith("4"):
            bounce_type = "soft"

    if not bounced_email:
        return BounceResult(
            bounced_email="",
            bounce_type="soft",
            smtp_status_code=smtp_status,
            detection_method="malformed",
            diagnostic=diagnostic,
            raw_headers={"from": from_hdr, "subject": subject},
        )

    cleaned_email = bounced_email.lower().replace("rfc822;", "").strip()
    if cleaned_email and "@" not in cleaned_email:
        email_match = EMAIL_REGEX.search(cleaned_email)
        cleaned_email = email_match.group(0) if email_match else cleaned_email

    return BounceResult(
        bounced_email=cleaned_email,
        bounce_type=bounce_type,
        smtp_status_code=smtp_status,
        detection_method=detection_method,
        diagnostic=diagnostic,
        raw_headers={"from": from_hdr, "subject": subject},
    )


def _extract_dsn_field(text: str, field: str) -> str | None:
    pattern = rf"{field}:\s*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip()
    if ";" in value:
        value = value.split(";", 1)[-1].strip()
    return value


def _collect_text(msg: email.message.Message) -> str:
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode("utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            parts.append(payload.decode("utf-8", errors="replace"))
    return "\n".join(parts)
