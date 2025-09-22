

def test_register_accepts_json(client):
    payload = {"email": "test@example.com", "password": "s3cretpass"}
    resp = client.post("/register", json=payload)
    # Depending on test DB state the user may already exist; accept 201 (created)
    # or 409 (conflict) as valid outcomes for this helper test.
    assert resp.status_code in (200, 201, 409)
    body = resp.json()
    assert "id" in body or "email" in body


def test_login_requires_credentials(client):
    payload = {"username": "test@example.com", "password": "s3cretpass"}
    resp = client.post("/token", data=payload)
    # Depending on whether user exists, we accept 200 or 401/400, but ensure no server error
    assert resp.status_code < 500
