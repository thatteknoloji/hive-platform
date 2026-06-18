from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import project_engine as pe


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    panel_identity.bootstrap()
    from app.auth import create_access_token
    client = TestClient(app)
    token = create_access_token(email="hive@thiqos.com")
    return client, {"Authorization": f"Bearer {token}"}


def test_v3_projects_crud(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)

    empty = client.get("/api/v3/projects", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["success"] is True
    assert empty.json()["count"] == 0

    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "BalKutusu",
        "sector": "ecommerce",
        "domain": "www.balkutusu.com",
        "business_brief": "Türkiye geneli çalışan e-ticaret markası.",
        "design": {
            "wizard_version": 2,
            "brand_personality": ["premium", "guven_veren"],
            "design_dna": "luxury",
            "color_identity": "gold_luxury",
            "conversion_goal": "urun_sat",
            "creative_director_brief": "Lüks ve güven hissi vermeli.",
        },
        "deploy_mode": "hive_cloud",
    })
    assert create.status_code == 200
    body = create.json()
    assert body["success"] is True
    pid = body["project"]["id"]
    assert pid.startswith("prj-")
    assert body["project"]["status"] == "draft"
    assert body["project"]["sector"] == "ecommerce"
    assert body["project"]["design"]["wizard_version"] == 2
    assert body["project"]["design"]["design_dna"] == "luxury"
    assert body["project"]["site"]["engine"] == "astro"
    assert body["project"]["site"]["pages_count"] == 6
    assert len(body["project"]["pages"]) == 6
    assert body["project"]["pages"][0]["title"] == "Ana Sayfa"
    assert body["project"]["navigation"][0]["href"] == "/"
    assert body["project"]["theme"]["design_dna"] == "luxury"
    assert body["project"]["theme"]["color_identity"] == "gold_luxury"
    assert body["project"]["pages_count"] == 6

    get_one = client.get(f"/api/v3/projects/{pid}", headers=headers)
    assert get_one.status_code == 200
    assert get_one.json()["project"]["name"] == "BalKutusu"

    patch = client.patch(f"/api/v3/projects/{pid}", headers=headers, json={"status": "active"})
    assert patch.status_code == 200
    assert patch.json()["project"]["status"] == "active"

    listed = client.get("/api/v3/projects", headers=headers, params={"search": "balku"})
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    delete = client.delete(f"/api/v3/projects/{pid}", headers=headers)
    assert delete.status_code == 200
    assert client.get(f"/api/v3/projects/{pid}", headers=headers).status_code == 404


def test_v3_projects_health(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    r = client.get("/api/v3/projects/health", headers=headers)
    assert r.status_code == 200
    assert r.json()["module"] == "project_engine"
