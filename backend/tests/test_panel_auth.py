"""HIVE panel auth tests."""

from __future__ import annotations

import pytest

from app.auth import auth_enabled, create_access_token, hash_password, login, me_from_token, verify_access_token, verify_password


@pytest.fixture
def auth_env(monkeypatch):
    monkeypatch.setenv("HIVE_ADMIN_EMAIL", "admin@thiqos.com")
    monkeypatch.setenv("HIVE_ADMIN_PASSWORD_HASH", hash_password("test-password-12"))
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-jwt-secret-key-minimum-32-bytes-long!!")
    from app import config
    config.reload_env()


def test_auth_disabled_without_env(monkeypatch):
    monkeypatch.delenv("HIVE_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("HIVE_ADMIN_PASSWORD_HASH", raising=False)
    from app import config
    config.reload_env()
    assert auth_enabled() is False


def test_login_success(auth_env):
    assert auth_enabled() is True
    res = login("admin@thiqos.com", "test-password-12")
    assert res["success"] is True
    assert res["token"]


def test_login_invalid_password(auth_env):
    res = login("admin@thiqos.com", "wrong")
    assert res["success"] is False


def test_jwt_roundtrip(auth_env):
    token = create_access_token(email="admin@thiqos.com")
    payload = verify_access_token(token)
    assert payload and payload.get("sub") == "admin@thiqos.com"
    me = me_from_token(token)
    assert me["authenticated"] is True


def test_password_hash_verify():
    h = hash_password("long-password-99")
    assert verify_password("long-password-99", h)
    assert not verify_password("nope", h)
