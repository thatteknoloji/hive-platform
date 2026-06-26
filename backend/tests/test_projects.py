from __future__ import annotations

from fastapi.testclient import TestClient

from app import panel_identity
from app.moduller import project_engine as pe


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    panel_identity.bootstrap()
    from app.main import app
    client = TestClient(app)
    token = client.post("/api/auth/login", json={"email": "hive@thiqos.com", "password": "hive123"}).json()["token"]
    return client, {"Authorization": f"Bearer {token}"}


def test_no_balkutusu_bootstrap_seed(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    items = panel_identity.list_projects()
    assert not any(p.get("project_id") == "balkutusu" for p in items)
    assert panel_identity.get_active_project_id() == ""


def test_create_project_set_active_v3_store(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post(
        "/api/v3/projects",
        headers=headers,
        json={"name": "Enamou", "sector": "listing", "domain": "www.enamou.com"},
    )
    assert create.status_code == 200
    pid = create.json()["project"]["id"]
    activate = client.post(f"/api/v3/projects/{pid}/set-active", headers=headers)
    assert activate.status_code == 200
    active = client.get("/api/v3/projects/active", headers=headers).json()
    assert active["active_project_id"] == pid
