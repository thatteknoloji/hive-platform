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


def _create_and_export(client, headers):
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Validate Hotel",
        "sector": "otel",
        "business_brief": "Karaburun'da butik otel.",
        "design": {"design_dna": "hotel_luxury", "color_identity": "gold_luxury", "conversion_goal": "rezervasyon"},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    export = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    assert export.status_code == 200
    return pid, Path(export.json()["export_path"])


def test_validate_without_export_returns_error(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "No Export",
        "sector": "blog",
        "business_brief": "Blog.",
        "design": {},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    res = client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "no_export"


def test_validate_after_export_success(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_and_export(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["valid"] is True
    assert data["errors_count"] == 0
    assert len(data["checks"]) >= 12
    assert data["project_id"] == pid


def test_validate_fails_when_package_json_missing(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, export_path = _create_and_export(client, headers)
    (export_path / "package.json").unlink()
    res = client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert data["errors_count"] > 0
    names = [c["name"] for c in data["checks"]]
    assert "package_json_exists" in names


def test_validate_fails_when_site_json_invalid(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, export_path = _create_and_export(client, headers)
    (export_path / "src" / "data" / "site.json").write_text("{broken", encoding="utf-8")
    res = client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert any(c["name"] == "site_json_parseable" and not c["ok"] for c in data["checks"])


def test_validation_persisted_to_project_storage(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_and_export(client, headers)
    client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    stored = project["metadata"]["astro_export_validation"]
    assert stored["valid"] is True
    assert stored["errors_count"] == 0
    assert stored["checks_count"] >= 12
    assert stored["validated_at"]


def test_validate_status_endpoint(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_and_export(client, headers)
    before = client.get(f"/api/v3/projects/{pid}/export/astro/validate/status", headers=headers)
    assert before.status_code == 200
    assert before.json()["validated"] is False
    client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    after = client.get(f"/api/v3/projects/{pid}/export/astro/validate/status", headers=headers)
    assert after.status_code == 200
    assert after.json()["validated"] is True
    assert after.json()["valid"] is True


def test_validate_checks_list_populated(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_and_export(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    checks = res.json()["checks"]
    expected = {
        "package_json_exists",
        "astro_config_exists",
        "index_astro_exists",
        "global_css_hive_primary",
        "base_layout_title_render",
        "page_renderer_content_fallback",
    }
    names = {c["name"] for c in checks}
    assert expected.issubset(names)
    for check in checks:
        assert "name" in check
        assert "ok" in check
        assert "severity" in check
