import pytest

from schemas import UserCreate, LoginRequest, RefreshRequest


def test_usercreate_scopes_default_and_normalize():
    u = UserCreate(email="a@example.com", password="password123")
    assert u.scopes == ["user"]

    u2 = UserCreate(email="b@example.com", password="password123", scopes="admin")
    assert u2.scopes == ["admin"]

    u3 = UserCreate(email="c@example.com", password="password123", scopes=["admin", "invalid"]) 
    assert u3.scopes == ["admin"]


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
