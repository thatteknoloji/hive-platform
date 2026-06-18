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
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"email": "hive@thiqos.com", "password": "hive123"}).json()["token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_balkutusu_default_project_migration(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    items = panel_identity.list_projects()
    assert any(p["project_id"] == "balkutusu" for p in items)


def test_create_project_set_active(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/projects", headers=headers, json={
        "name": "Enamou",
        "domain": "https://www.enamou.com",
        "type": "listing",
    })
    assert create.status_code == 200
    pid = create.json()["project_id"]
    activate = client.post(f"/api/projects/{pid}/set-active", headers=headers)
    assert activate.status_code == 200
    listed = client.get("/api/projects", headers=headers).json()
    assert listed["active_project_id"] == pid
