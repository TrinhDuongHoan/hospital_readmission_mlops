import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from inference.app import auth


def test_hash_and_verify_password_round_trip():
    password_hash = auth.hash_password("doctor123")

    assert password_hash != "doctor123"
    assert auth.verify_password("doctor123", password_hash)
    assert not auth.verify_password("wrong-password", password_hash)


def test_authenticate_user_returns_none_for_unknown_user(monkeypatch):
    monkeypatch.setattr(auth, "get_user_by_username", lambda username: None)

    assert auth.authenticate_user("missing", "password") is None


def test_authenticate_user_validates_password(monkeypatch):
    password_hash = auth.hash_password("doctor123")

    monkeypatch.setattr(
        auth,
        "get_user_by_username",
        lambda username: {
            "id": 1,
            "username": username,
            "password_hash": password_hash,
            "role": "doctor",
        },
    )

    assert auth.authenticate_user("doctor01", "doctor123")["username"] == "doctor01"
    assert auth.authenticate_user("doctor01", "wrong-password") is None


def test_create_access_token_contains_subject_and_role():
    token = auth.create_access_token(
        {
            "sub": "admin01",
            "role": "admin",
            "user_id": 2,
        }
    )

    payload = jwt.decode(
        token,
        auth.SECRET_KEY,
        algorithms=[auth.ALGORITHM],
    )

    assert payload["sub"] == "admin01"
    assert payload["role"] == "admin"
    assert payload["user_id"] == 2
    assert "exp" in payload


def test_get_current_user_rejects_token_without_subject():
    token = auth.create_access_token({"role": "admin"})

    with pytest.raises(HTTPException) as exc_info:
        auth.get_current_user(
            HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=token,
            )
        )

    assert exc_info.value.status_code == 401


def test_require_role_allows_expected_roles_and_rejects_others():
    checker = auth.require_role("doctor", "admin")

    assert checker({"role": "doctor"}) == {"role": "doctor"}

    with pytest.raises(HTTPException) as exc_info:
        checker({"role": "guest"})

    assert exc_info.value.status_code == 403
