import uuid

from emailer import last_sent_for


def test_email_verification_flow(client):
    email = f"verify+{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "s3cretpass"}
    resp = client.post("/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    # new user should be inactive until verified
    assert body.get("is_active") is False

    sent = last_sent_for(email)
    assert sent is not None
    token = sent["token"]

    # Verify the token
    v = client.get(f"/verify-email?token={token}")
    assert v.status_code == 200
    assert v.json().get("ok") is True

    # Token should be invalidated after use
    v2 = client.get(f"/verify-email?token={token}")
    assert v2.status_code == 404

