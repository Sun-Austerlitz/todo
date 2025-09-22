from datetime import datetime, timedelta
import secrets

# This module implements a test-friendly email sender used by the app.
# In production replace with a real sender (SMTP, SES, etc.).

SENT = []  # list of dicts: {to, subject, body, token, when}

def generate_token():
    return secrets.token_urlsafe(32)


def send_verification(to_email: str, token: str, expires_in_minutes: int = 60):
    now = datetime.utcnow()
    SENT.append({
        "to": to_email,
        "subject": "Verify your email",
        "body": f"Visit /verify-email?token={token}",
        "token": token,
        "when": now,
        "expires_at": now + timedelta(minutes=expires_in_minutes),
    })


def last_sent_for(email: str):
    for msg in reversed(SENT):
        if msg["to"] == email:
            return msg
    return None
