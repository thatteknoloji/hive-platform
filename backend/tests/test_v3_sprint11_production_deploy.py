from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import (
    astro_build_runner,
    astro_export_engine,
    astro_publish_prep,
    hive_cloud_deploy,
    hive_production_deploy,
    project_engine as pe,
)


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    monkeypatch.setattr(astro_export_engine, "EXPORT_ROOT", tmp_path / "generated_sites")
    monkeypatch.setattr(astro_publish_prep, "ARTIFACT_ROOT", tmp_path / "publish_artifacts")
    monkeypatch.setattr(hive_cloud_deploy, "PUBLIC_ROOT", tmp_path / "public_sites")
    panel_identity.bootstrap()
    from app.auth import create_access_token
    client = TestClient(app)
    token = create_access_token(email="hive@thiqos.com")
    return client, {"Authorization": f"Bearer {token}"}


def _success_runner(cmd: list[str], cwd: Path, timeout: int) -> dict:
    if cmd[:2] == ["npm", "run"]:
        dist = cwd / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
    return {
        "cmd": " ".join(cmd),
        "exit_code": 0,
        "duration_ms": 1,
        "stdout_tail": "",
        "stderr_tail": "",
        "timed_out": False,
    }


def _create_deployed_project(client, headers):
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Prod Hotel",
        "sector": "otel",
        "business_brief": "Test.",
        "design": {"design_dna": "hotel_luxury"},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    client.get(f"/api/v3/projects/{pid}/publish-gate", headers=headers)
    with patch.object(astro_build_runner, "_default_cmd_runner", _success_runner):
        client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    deploy = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    assert deploy.status_code == 200
    return pid


def test_domain_bind_success(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    res = client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "penteraevleri.com", "include_www": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["domain"] == "penteraevleri.com"
    assert data["www_domain"] == "www.penteraevleri.com"
    assert data["status"] == "configured"
    assert data["ssl_status"] == "pending"
    status = client.get(f"/api/v3/projects/{pid}/domain/status", headers=headers)
    assert status.json()["domain"] == "penteraevleri.com"
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    assert project["metadata"]["domain_binding"]["domain"] == "penteraevleri.com"
    assert project["domain"] == "penteraevleri.com"


def test_domain_bind_strips_http_https(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    res = client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "https://PenteraEvleri.com", "include_www": False},
    )
    assert res.status_code == 200
    assert res.json()["domain"] == "penteraevleri.com"
    assert res.json()["www_domain"] == ""


def test_domain_bind_rejects_path(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    res = client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "example.com/foo", "include_www": True},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "path_not_allowed"


def test_domain_bind_rejects_invalid(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    res = client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "not a domain!", "include_www": True},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "invalid_domain"


def test_domain_bind_rejects_empty(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    res = client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "  ", "include_www": True},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "empty_domain"


def test_production_plan_requires_local_deploy(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "No Deploy",
        "sector": "blog",
        "business_brief": "Blog",
        "design": {},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "example.com", "include_www": True},
    )
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/plan", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "local_deploy_required"


def test_production_plan_requires_domain_binding(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/plan", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "domain_binding_required"


def test_production_plan_success(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "penteraevleri.com", "include_www": True},
    )
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/plan", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "planned"
    assert data["domain"] == "penteraevleri.com"
    assert data["production_path"] == "/var/www/hive-sites/penteraevleri.com"
    assert data["nginx_config_path"] == "/etc/nginx/sites-available/penteraevleri.com"
    assert data["live_url"] == "https://penteraevleri.com"
    assert data["source_path"]
    status = client.get(f"/api/v3/projects/{pid}/deploy/production/status", headers=headers)
    assert status.json()["status"] == "planned"
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    stored = project["metadata"]["hive_production_deploy"]
    assert stored["production_path"] == data["production_path"]


def test_nginx_preview_contains_domain_and_root(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_deployed_project(client, headers)
    client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "penteraevleri.com", "include_www": True},
    )
    client.post(f"/api/v3/projects/{pid}/deploy/production/plan", headers=headers)
    res = client.get(f"/api/v3/projects/{pid}/deploy/production/nginx-preview", headers=headers)
    assert res.status_code == 200
    cfg = res.json()["config"]
    assert "penteraevleri.com" in cfg
    assert "www.penteraevleri.com" in cfg
    assert "root /var/www/hive-sites/penteraevleri.com" in cfg
    assert "try_files $uri $uri/ /index.html" in cfg
    assert "ssl_certificate" in cfg


def test_sanitize_domain_unit():
    assert hive_production_deploy.sanitize_domain("https://Example.COM") == "example.com"
    assert hive_production_deploy.sanitize_domain("http://foo.bar.co.uk") == "foo.bar.co.uk"


def test_path_traversal_project_id_blocked(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post(
        "/api/v3/projects/prj-evil../domain/bind",
        headers=headers,
        json={"domain": "example.com", "include_www": True},
    )
    assert res.status_code in (400, 404, 422)
