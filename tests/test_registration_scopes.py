def test_register_ignores_scopes(client):
    payload = {"email": "scopetest@example.com", "password": "s3cretpass", "scopes": ["admin"]}
    resp = client.post("/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "scopetest@example.com"
    assert body.get("scopes") == ["user"]


def test_register_conflict_same_email(client):
    payload = {"email": "scopetest@example.com", "password": "s3cretpass"}
    resp = client.post("/register", json=payload)
    assert resp.status_code == 409
