from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import block_engine, project_engine as pe


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


def test_create_project_has_filled_blocks(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/projects", headers=headers, json={
        "name": "Test Shop",
        "sector": "ecommerce",
        "business_brief": "Türkiye geneli e-ticaret markası.",
        "design": {
            "wizard_version": 2,
            "design_dna": "marketplace",
            "color_identity": "sunset_orange",
            "conversion_goal": "urun_sat",
        },
        "deploy_mode": "hive_cloud",
    })
    assert res.status_code == 200
    project = res.json()["project"]
    assert block_engine.count_blocks(project["pages"]) > 0
    assert project["seo_score"] > 0
    assert project["geo_score"] > 0


def test_export_astro_creates_files(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Export Test",
        "sector": "blog",
        "business_brief": "Teknoloji blogu.",
        "design": {"design_dna": "editorial"},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    export = client.post(f"/api/v3/projects/{pid}/export-astro", headers=headers, json={"build": False})
    assert export.status_code == 200
    assert export.json()["success"] is True
    from pathlib import Path
    path = Path(export.json()["path"])
    assert (path / "src" / "data" / "pages.json").is_file()
    assert (path / "src" / "data" / "theme.json").is_file()


def test_creative_director_api(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/creative-director/suggest", headers=headers, json={
        "sector": "klinik",
        "business_brief": "İzmir merkezde diş kliniği.",
        "creative_brief": "Güven ve hijyen hissi.",
        "use_llm": False,
    })
    assert res.status_code == 200
    assert res.json()["suggestions"]["design_dna"] == "medical_clean"


def test_retro_seed_old_project(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    # simulate old project without site
    pe.STATE_FILE.write_text('{"projects": {"prj-old12345": {"id": "prj-old12345", "name": "Legacy", "sector": "otel", "status": "draft", "design": {}, "created_at": "x", "updated_at": "x"}}}', encoding="utf-8")
    res = client.post("/api/v3/projects/prj-old12345/retro-seed", headers=headers)
    assert res.status_code == 200
    project = res.json()["project"]
    assert project["site"]["site_id"]
    assert len(project["pages"]) == 7
