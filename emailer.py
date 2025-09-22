"""Simple test-friendly email helper.

Usage in tests: call `emailer.last_sent_for(email)` to retrieve the last
verification message and token.
"""
from datetime import datetime, timedelta
import secrets
import logging

logger = logging.getLogger(__name__)

# list of dicts: {to, subject, body, token, when, expires_at}
SENT = []


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def send_verification(to_email: str, token: str, expires_in_minutes: int = 60):
    now = datetime.utcnow()
    msg = {
        "to": to_email,
        "subject": "Verify your email",
        "body": f"Visit /verify-email?token={token}",
        "token": token,
        "when": now,
        "expires_at": now + timedelta(minutes=expires_in_minutes),
    }
    SENT.append(msg)
    logger.info("Sent verification email", extra={"to": to_email})


def last_sent_for(email: str):
    for msg in reversed(SENT):
        if msg["to"] == email:
            return msg
    return None
