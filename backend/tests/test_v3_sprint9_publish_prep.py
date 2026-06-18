from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import astro_build_runner, astro_export_engine, astro_publish_prep, project_engine as pe


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    monkeypatch.setattr(astro_export_engine, "EXPORT_ROOT", tmp_path / "generated_sites")
    monkeypatch.setattr(astro_publish_prep, "ARTIFACT_ROOT", tmp_path / "publish_artifacts")
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


def _create_built_project(client, headers):
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Prep Hotel",
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
        build = client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    assert build.status_code == 200
    return pid, Path(build.json()["dist_path"])


def test_prepare_blocked_without_build(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "No Build",
        "sector": "blog",
        "business_brief": "Blog",
        "design": {},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    res = client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "build_not_ready"


def test_prepare_blocked_when_build_not_built(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_built_project(client, headers)
    raw = pe.STATE_FILE.read_text(encoding="utf-8")
    import json
    state = json.loads(raw)
    state["projects"][pid]["metadata"]["astro_build"]["status"] = "build_failed"
    pe.STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    res = client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "build_not_ready"


def test_prepare_fails_when_dist_missing(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, dist_path = _create_built_project(client, headers)
    import shutil
    shutil.rmtree(dist_path)
    res = client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "dist_missing"


def test_prepare_fails_when_index_missing(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, dist_path = _create_built_project(client, headers)
    (dist_path / "index.html").unlink()
    res = client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "index_missing"


def test_prepare_success_creates_artifact(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, dist_path = _create_built_project(client, headers)
    res = client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["files_count"] >= 2
    assert data["total_size_bytes"] > 0
    assert data["entry"] == "index.html"
    artifact = Path(data["artifact_path"])
    assert artifact.is_dir()
    assert (artifact / "index.html").is_file()
    assert (artifact / "assets" / "app.css").is_file()
    status = client.get(f"/api/v3/projects/{pid}/publish/prepare/status", headers=headers)
    assert status.json()["status"] == "ready"
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    stored = project["metadata"]["astro_publish_artifact"]
    assert stored["files_count"] == data["files_count"]
    assert stored["total_size_bytes"] == data["total_size_bytes"]


def test_prepare_skips_symlinks(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, dist_path = _create_built_project(client, headers)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    try:
        os.symlink(outside, dist_path / "evil-link")
    except OSError:
        return  # skip on platforms without symlink support
    res = client.post(f"/api/v3/projects/{pid}/publish/prepare", headers=headers)
    assert res.status_code == 200
    artifact = Path(res.json()["artifact_path"])
    assert not (artifact / "evil-link").exists()


def test_path_traversal_project_id_blocked(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/projects/prj-evil../publish/prepare", headers=headers)
    assert res.status_code in (400, 404, 422)
