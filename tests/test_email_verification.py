from emailer import SENT
import uuid


def test_email_verification_flow(client):
    email = f"verify+{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "password123"}
    resp = client.post("/register", json=payload)
    assert resp.status_code == 201
    # Find the last sent verification for this email
    msg = None
    for m in reversed(SENT):
        if m["to"] == email:
            msg = m
            break
    assert msg is not None
    token = msg["token"]
    # Verify the token
    v = client.get(f"/verify-email?token={token}")
    assert v.status_code == 200
    # After verification, login should be allowed
    data = {"username": email, "password": "password123"}
    t = client.post("/token", data=data)
    assert t.status_code == 200
