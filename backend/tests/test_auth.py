from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity


def _client_with_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    panel_identity.bootstrap()
    return TestClient(app)


def test_default_admin_creation(tmp_path, monkeypatch):
    _client_with_state(tmp_path, monkeypatch)
    users = panel_identity.list_users()
    assert any(u["email"] == "hive@thiqos.com" for u in users)


def test_login_success_and_me(tmp_path, monkeypatch):
    client = _client_with_state(tmp_path, monkeypatch)
    res = client.post("/api/auth/login", json={"email": "hive@thiqos.com", "password": "hive123"})
    assert res.status_code == 200
    token = res.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["authenticated"] is True


def test_login_wrong_password(tmp_path, monkeypatch):
    client = _client_with_state(tmp_path, monkeypatch)
    res = client.post("/api/auth/login", json={"email": "hive@thiqos.com", "password": "wrong"})
    assert res.status_code == 401
