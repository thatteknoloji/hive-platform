from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import astro_export_engine, project_engine as pe


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    monkeypatch.setattr(astro_export_engine, "EXPORT_ROOT", tmp_path / "generated_sites")
    panel_identity.bootstrap()
    from app.auth import create_access_token
    client = TestClient(app)
    token = create_access_token(email="hive@thiqos.com")
    return client, {"Authorization": f"Bearer {token}"}


def _create_project(client, headers):
    res = client.post("/api/v3/projects", headers=headers, json={
        "name": "Astro Export Hotel",
        "sector": "otel",
        "business_brief": "Karaburun'da butik otel.",
        "design": {
            "wizard_version": 2,
            "design_dna": "hotel_luxury",
            "color_identity": "gold_luxury",
            "conversion_goal": "rezervasyon",
        },
        "deploy_mode": "hive_cloud",
    })
    assert res.status_code == 200
    return res.json()["project"]["id"]


def test_export_astro_endpoint_success(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["project_id"] == pid
    assert data["files_count"] >= 12
    assert data["entry"] == "src/pages/index.astro"
    assert Path(data["export_path"]).is_dir()


def test_export_creates_package_json_and_index(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    root = Path(res.json()["export_path"])
    assert (root / "package.json").is_file()
    assert (root / "src" / "pages" / "index.astro").is_file()
    assert (root / "src" / "layouts" / "BaseLayout.astro").is_file()


def test_export_theme_css_variables(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    css = (Path(res.json()["export_path"]) / "src" / "styles" / "global.css").read_text(encoding="utf-8")
    assert "--hive-primary" in css
    assert "--hive-bg" in css
    assert "--hive-text" in css
    assert "--hive-accent" in css
    assert "#c9a962" in css


def test_export_hero_block_rendered(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    hero = (Path(res.json()["export_path"]) / "src" / "components" / "blocks" / "Hero.astro").read_text(encoding="utf-8")
    assert "primary_cta" in hero or "cta_label" in hero
    assert "eyebrow" in hero
    site_json = (Path(res.json()["export_path"]) / "src" / "data" / "site.json").read_text(encoding="utf-8")
    assert "Rezervasyon Yap" in site_json


def test_export_seo_title_in_layout(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    layout = (Path(res.json()["export_path"]) / "src" / "layouts" / "BaseLayout.astro").read_text(encoding="utf-8")
    index = (Path(res.json()["export_path"]) / "src" / "pages" / "index.astro").read_text(encoding="utf-8")
    assert '<title>' in layout or "title" in layout
    assert "meta name=\"description\"" in layout
    assert "canonical" in layout
    assert "application/ld+json" in layout
    assert "schema_type" in index or "schema" in index


def test_export_status_endpoint(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_project(client, headers)
    before = client.get(f"/api/v3/projects/{pid}/export/astro/status", headers=headers)
    assert before.status_code == 200
    assert before.json()["exported"] is False
    client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    after = client.get(f"/api/v3/projects/{pid}/export/astro/status", headers=headers)
    assert after.status_code == 200
    assert after.json()["exported"] is True
    assert after.json()["files_count"] >= 12


def test_export_fails_without_site(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pe.STATE_FILE.write_text(
        '{"projects": {"prj-legacy0001": {"id": "prj-legacy0001", "name": "Legacy", "sector": "otel", "status": "draft", "created_at": "x", "updated_at": "x"}}}',
        encoding="utf-8",
    )
    res = client.post("/api/v3/projects/prj-legacy0001/export/astro", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "no_site_skeleton"


def test_invalid_project_id_rejected(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/projects/../evil/export/astro", headers=headers)
    assert res.status_code in (400, 404, 422)
