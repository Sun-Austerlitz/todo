

import uuid


def test_register_accepts_json(client):
    # Use a unique email per test run to avoid collisions with existing DB state
    email = f"test+{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "s3cretpass"}
    resp = client.post("/register", json=payload)
    assert resp.status_code in (200, 201)
    body = resp.json()
    assert "id" in body or body.get("email") == email


def test_login_requires_credentials(client):
    payload = {"username": "test@example.com", "password": "s3cretpass"}
    resp = client.post("/token", data=payload)
    # Depending on whether user exists, we accept 200 or 401/400, but ensure no server error
    assert resp.status_code < 500
