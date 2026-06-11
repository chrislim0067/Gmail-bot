"""MIME message construction for Gmail API send."""

import base64
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_mime_message(
    *,
    to: str,
    from_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
    unsubscribe_url: str,
) -> dict:
    message = MIMEMultipart("alternative")
    message["To"] = to
    message["From"] = from_email
    message["Subject"] = subject
    message["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    message["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    message["Message-ID"] = f"<{uuid.uuid4()}@{from_email.split('@')[-1]}>"

    plain = text_body or _html_to_plain(html_body)
    message.attach(MIMEText(plain, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {
        "raw": raw,
        "rfc_message_id": message["Message-ID"],
    }


def _html_to_plain(html: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", "", html)
    return text.strip()
