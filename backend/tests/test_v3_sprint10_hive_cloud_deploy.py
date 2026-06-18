from __future__ import annotations

import json
import os
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
        (dist / "assets").mkdir(exist_ok=True)
        (dist / "assets" / "app.css").write_text("body{}", encoding="utf-8")
    return {
        "cmd": " ".join(cmd),
        "exit_code": 0,
        "duration_ms": 1,
        "stdout_tail": "",
        "stderr_tail": "",
        "timed_out": False,
    }


def _create_ready_artifact(client, headers):
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Deploy Hotel",
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
    prep = client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    assert prep.status_code == 200
    assert prep.json()["status"] == "ready"
    return pid


def test_deploy_blocked_without_artifact(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "No Artifact",
        "sector": "blog",
        "business_brief": "Blog",
        "design": {},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    res = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "artifact_not_ready"


def test_deploy_blocked_when_artifact_not_ready(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_ready_artifact(client, headers)
    state = json.loads(pe.STATE_FILE.read_text(encoding="utf-8"))
    state["projects"][pid]["metadata"]["astro_publish_artifact"]["status"] = "prep_failed"
    pe.STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    res = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "artifact_not_ready"


def test_deploy_success_creates_public_site(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_ready_artifact(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "deployed"
    assert data["live_url"] == f"/sites/{pid}/"
    assert data["files_count"] >= 2
    assert data["total_size_bytes"] > 0
    deploy_dir = Path(data["deploy_path"])
    assert deploy_dir.is_dir()
    assert (deploy_dir / "index.html").is_file()
    assert (deploy_dir / "assets" / "app.css").is_file()
    status = client.get(f"/api/v3/projects/{pid}/deploy/hive-cloud/status", headers=headers)
    assert status.json()["status"] == "deployed"
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    stored = project["metadata"]["hive_cloud_deploy"]
    assert stored["live_url"] == data["live_url"]
    assert stored["files_count"] == data["files_count"]


def test_deploy_live_url_format(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_ready_artifact(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    assert res.json()["live_url"] == hive_cloud_deploy.live_url_for(pid)


def test_deploy_cleans_old_deploy(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_ready_artifact(client, headers)
    deploy_dir = tmp_path / "public_sites" / pid
    deploy_dir.mkdir(parents=True)
    (deploy_dir / "stale.html").write_text("old", encoding="utf-8")
    res = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    assert res.status_code == 200
    assert not (deploy_dir / "stale.html").exists()
    assert (deploy_dir / "index.html").is_file()


def test_deploy_skips_symlinks(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_ready_artifact(client, headers)
    artifact = tmp_path / "publish_artifacts" / pid
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    try:
        os.symlink(outside, artifact / "evil-link")
    except OSError:
        return
    res = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    assert res.status_code == 200
    deploy_dir = Path(res.json()["deploy_path"])
    assert not (deploy_dir / "evil-link").exists()


def test_path_traversal_project_id_blocked(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/projects/prj-evil../deploy/hive-cloud", headers=headers)
    assert res.status_code in (400, 404, 422)


def test_static_sites_route_registered():
    found = False
    for route in app.routes:
        path = getattr(route, "path", None)
        if path == "/sites":
            found = True
            break
    assert found


def test_static_sites_serve_index(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid = _create_ready_artifact(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/deploy/hive-cloud", headers=headers)
    deploy_dir = Path(res.json()["deploy_path"])
    real_public = Path(__file__).resolve().parents[1] / "app" / "public_sites" / pid
    real_public.parent.mkdir(parents=True, exist_ok=True)
    if real_public.exists():
        import shutil
        shutil.rmtree(real_public)
    import shutil
    shutil.copytree(deploy_dir, real_public)
    try:
        page = client.get(f"/sites/{pid}/")
        assert page.status_code == 200
        assert "ok" in page.text
    finally:
        shutil.rmtree(real_public, ignore_errors=True)
