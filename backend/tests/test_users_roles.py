from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    panel_identity.bootstrap()
    return TestClient(app)


def _token(client: TestClient) -> str:
    res = client.post("/api/auth/login", json={"email": "hive@thiqos.com", "password": "hive123"})
    return res.json()["token"]


def test_create_user_and_disable(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    create = client.post("/api/users", headers=headers, json={
        "email": "editor@thiqos.com",
        "name": "Editor",
        "role": "editor",
        "password": "editor1234",
    })
    assert create.status_code == 200
    users = client.get("/api/users", headers=headers).json()["items"]
    created = next(u for u in users if u["email"] == "editor@thiqos.com")
    disable = client.patch(f"/api/users/{created['user_id']}", headers=headers, json={"status": "disabled"})
    assert disable.status_code == 200


def test_role_permission_deny_allow(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch)
    token = _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/api/users", headers=headers, json={
        "email": "viewer@thiqos.com", "name": "Viewer", "role": "viewer", "password": "viewer1234",
    })
    viewer_login = client.post("/api/auth/login", json={"email": "viewer@thiqos.com", "password": "viewer1234"})
    viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['token']}"}
    assert client.get("/api/users", headers=viewer_headers).status_code == 403
    assert client.get("/health", headers=viewer_headers).status_code == 200
