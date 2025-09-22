import uuid


def test_register_ignores_scopes(client):
    email = f"scopetest+{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "s3cretpass", "scopes": ["admin"]}
    resp = client.post("/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == email
    assert body.get("scopes") == ["user"]


def test_register_conflict_same_email(client):
    payload = {"email": "scopetest@example.com", "password": "s3cretpass"}
    resp = client.post("/register", json=payload)
    assert resp.status_code == 409
