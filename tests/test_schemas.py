import pytest

from schemas import LoginRequest, RefreshRequest


def test_usercreate_scopes_removed_from_public_schema(client):
    # The public UserCreate schema no longer includes `scopes`.
    # Ensure registration ignores any scopes provided by the client and
    # the created user receives default ['user'].
    import uuid
    email = f"schema-scope+{uuid.uuid4().hex}@example.com"
    payload = {"email": email, "password": "password123", "scopes": ["admin"]}
    resp = client.post("/register", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["scopes"] == ["user"]


def test_login_password_min_length():
    with pytest.raises(Exception):
        LoginRequest(username="x@x.com", password="short")

    lr = LoginRequest(username="x@x.com", password="longenough")
    assert lr.password == "longenough"


def test_refresh_request_requires_token():
    with pytest.raises(Exception):
        RefreshRequest()  # missing required field

    r = RefreshRequest(refresh_token="abc")
    assert r.refresh_token == "abc"
