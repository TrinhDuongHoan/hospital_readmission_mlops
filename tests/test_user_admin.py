import pytest
from fastapi import HTTPException

from inference.app import main
from inference.app.schemas import UserCreateRequest, UserStatusRequest, UserUpdateRequest


def test_admin_can_create_user(monkeypatch):
    created_user = {
        "id": 3,
        "username": "doctor02",
        "full_name": "Doctor Two",
        "role": "doctor",
        "is_active": True,
    }

    monkeypatch.setattr(main, "get_user_by_username", lambda username: None)
    monkeypatch.setattr(main, "hash_password", lambda password: f"hash:{password}")
    monkeypatch.setattr(main, "create_user", lambda **kwargs: created_user)

    result = main.create_user_api(
        UserCreateRequest(
            username="doctor02",
            password="doctor123",
            full_name="Doctor Two",
            role="doctor",
        ),
        current_user={"id": 1, "role": "admin"},
    )

    assert result == created_user


def test_admin_create_user_rejects_duplicate_username(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_user_by_username",
        lambda username: {
            "id": 3,
            "username": username,
            "role": "doctor",
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        main.create_user_api(
            UserCreateRequest(
                username="doctor02",
                password="doctor123",
                role="doctor",
            ),
            current_user={"id": 1, "role": "admin"},
        )

    assert exc_info.value.status_code == 409


def test_admin_cannot_remove_admin_role_from_own_account(monkeypatch):
    monkeypatch.setattr(
        main,
        "get_user_by_id",
        lambda user_id: {
            "id": user_id,
            "username": "admin01",
            "role": "admin",
        },
    )

    with pytest.raises(HTTPException) as exc_info:
        main.update_user_api(
            1,
            UserUpdateRequest(role="doctor"),
            current_user={"id": 1, "role": "admin"},
        )

    assert exc_info.value.status_code == 400


def test_admin_can_disable_user(monkeypatch):
    disabled_user = {
        "id": 3,
        "username": "doctor02",
        "full_name": "Doctor Two",
        "role": "doctor",
        "is_active": False,
    }

    monkeypatch.setattr(main, "set_user_active", lambda **kwargs: disabled_user)

    result = main.update_user_status_api(
        3,
        UserStatusRequest(is_active=False),
        current_user={"id": 1, "role": "admin"},
    )

    assert result == disabled_user


def test_admin_cannot_disable_own_account():
    with pytest.raises(HTTPException) as exc_info:
        main.update_user_status_api(
            1,
            UserStatusRequest(is_active=False),
            current_user={"id": 1, "role": "admin"},
        )

    assert exc_info.value.status_code == 400
