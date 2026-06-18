from __future__ import annotations

import json
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
    hive_production_apply,
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


def _create_planned_project(client, headers):
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Apply Hotel",
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
    client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    client.post(
        f"/api/v3/projects/{pid}/domain/bind",
        headers=headers,
        json={"domain": "penteraevleri.com", "include_www": True},
    )
    plan = client.post(f"/api/v3/projects/{pid}/deploy/production/plan", headers=headers)
    assert plan.status_code == 200
    return pid


def test_apply_script_blocked_without_plan(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "No Plan",
        "sector": "blog",
        "business_brief": "Blog",
        "design": {},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/apply-script", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "production_plan_required"


def test_apply_script_success_contains_paths_and_domain(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_planned_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/apply-script", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "script_ready"
    assert data["domain"] == "penteraevleri.com"
    assert data["requires_root"] is True
    assert "manual_steps" in data
    script = data["script"]
    assert "penteraevleri.com" in script
    assert "/var/www/hive-sites/penteraevleri.com" in script
    assert "public_sites" in script
    assert "nginx -t" in script
    assert "systemctl reload nginx" in script
    status = client.get(f"/api/v3/projects/{pid}/deploy/production/apply-script/status", headers=headers)
    assert status.json()["status"] == "script_ready"
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    assert project["metadata"]["hive_production_apply_script"]["status"] == "script_ready"


def test_apply_script_certbot_commented(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_planned_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/apply-script", headers=headers)
    script = res.json()["script"]
    assert "# certbot --nginx" in script
    assert "-d penteraevleri.com" in script
    assert "-d www.penteraevleri.com" in script


def test_apply_script_invalid_domain_rejected(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_planned_project(client, headers)
    state = json.loads(pe.STATE_FILE.read_text(encoding="utf-8"))
    state["projects"][pid]["metadata"]["hive_production_deploy"]["domain"] = "not valid!"
    pe.STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/apply-script", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "invalid_domain"


def test_apply_script_invalid_source_path_rejected(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_planned_project(client, headers)
    state = json.loads(pe.STATE_FILE.read_text(encoding="utf-8"))
    state["projects"][pid]["metadata"]["hive_production_deploy"]["source_path"] = "/etc/passwd"
    pe.STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/apply-script", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "invalid_source_path"


def test_apply_script_invalid_production_path_rejected(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_planned_project(client, headers)
    state = json.loads(pe.STATE_FILE.read_text(encoding="utf-8"))
    state["projects"][pid]["metadata"]["hive_production_deploy"]["production_path"] = "/var/www/evil"
    pe.STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    res = client.post(f"/api/v3/projects/{pid}/deploy/production/apply-script", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "invalid_production_path"


def test_apply_script_path_traversal_project_id_blocked(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post(
        "/api/v3/projects/prj-evil../deploy/production/apply-script",
        headers=headers,
    )
    assert res.status_code in (400, 404, 422)


def test_generate_apply_script_unit():
    script = hive_production_apply.generate_apply_script(
        domain="example.com",
        www_domain="www.example.com",
        source_path="/opt/hive/backend/app/public_sites/prj-abc123",
        target_path="/var/www/hive-sites/example.com",
        nginx_available="/etc/nginx/sites-available/example.com",
        nginx_enabled="/etc/nginx/sites-enabled/example.com",
    )
    assert script.startswith("#!/usr/bin/env bash")
    assert "set -euo pipefail" in script
    assert "rsync -a --delete" in script
    assert "chown -R www-data:www-data" in script
    assert "NGINXEOF" in script
