from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import astro_build_runner, astro_export_engine, project_engine as pe


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


def _create_export_validate_gate(client, headers):
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "Build Hotel",
        "sector": "otel",
        "business_brief": "Test otel.",
        "design": {"design_dna": "hotel_luxury", "conversion_goal": "rezervasyon"},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    export = client.post(f"/api/v3/projects/{pid}/export/astro", headers=headers)
    export_path = Path(export.json()["export_path"])
    client.post(f"/api/v3/projects/{pid}/export/astro/validate", headers=headers)
    client.get(f"/api/v3/projects/{pid}/publish-gate", headers=headers)
    return pid, export_path


def _success_runner(cmd: list[str], cwd: Path, timeout: int) -> dict:
    if cmd[:2] == ["npm", "run"]:
        dist = cwd / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    return {
        "cmd": " ".join(cmd),
        "exit_code": 0,
        "duration_ms": 42,
        "stdout_tail": "ok",
        "stderr_tail": "",
        "timed_out": False,
    }


def test_build_blocked_when_gate_false(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    create = client.post("/api/v3/projects", headers=headers, json={
        "name": "No Gate",
        "sector": "blog",
        "business_brief": "Blog",
        "design": {},
        "deploy_mode": "hive_cloud",
    })
    pid = create.json()["project"]["id"]
    calls: list[list[str]] = []

    def runner(cmd, cwd, timeout):
        calls.append(cmd)
        return _success_runner(cmd, cwd, timeout)

    with patch.object(astro_build_runner, "_default_cmd_runner", runner):
        res = client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "publish_gate_blocked"
    assert calls == []


def test_build_runs_npm_when_gate_true(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_export_validate_gate(client, headers)
    calls: list[list[str]] = []

    def runner(cmd, cwd, timeout):
        calls.append(list(cmd))
        return _success_runner(cmd, cwd, timeout)

    with patch.object(astro_build_runner, "_default_cmd_runner", runner):
        res = client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "built"
    assert [c[:2] for c in calls] == [["npm", "install"], ["npm", "run"]]


def test_build_failed_on_npm_install(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_export_validate_gate(client, headers)

    def runner(cmd, cwd, timeout):
        if cmd[:2] == ["npm", "install"]:
            return {
                "cmd": "npm install",
                "exit_code": 1,
                "duration_ms": 10,
                "stdout_tail": "",
                "stderr_tail": "install error",
                "timed_out": False,
            }
        return _success_runner(cmd, cwd, timeout)

    with patch.object(astro_build_runner, "_default_cmd_runner", runner):
        res = client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "npm_install_failed"
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    assert project["metadata"]["astro_build"]["status"] == "build_failed"


def test_build_failed_on_npm_run_build(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_export_validate_gate(client, headers)

    def runner(cmd, cwd, timeout):
        if cmd[:2] == ["npm", "run"]:
            return {
                "cmd": "npm run build",
                "exit_code": 1,
                "duration_ms": 20,
                "stdout_tail": "",
                "stderr_tail": "build error",
                "timed_out": False,
            }
        return {"cmd": "npm install", "exit_code": 0, "duration_ms": 5, "stdout_tail": "", "stderr_tail": "", "timed_out": False}

    with patch.object(astro_build_runner, "_default_cmd_runner", runner):
        res = client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "npm_build_failed"


def test_build_timeout_handled(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, _ = _create_export_validate_gate(client, headers)

    def runner(cmd, cwd, timeout):
        return {
            "cmd": " ".join(cmd),
            "exit_code": -1,
            "duration_ms": timeout * 1000,
            "stdout_tail": "",
            "stderr_tail": "timed out",
            "timed_out": True,
        }

    with patch.object(astro_build_runner, "_default_cmd_runner", runner):
        res = client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    assert res.status_code == 400
    assert res.json()["detail"] == "npm_install_timeout"


def test_build_success_writes_metadata(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    pid, export_path = _create_export_validate_gate(client, headers)

    with patch.object(astro_build_runner, "_default_cmd_runner", _success_runner):
        res = client.post(f"/api/v3/projects/{pid}/export/astro/build", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["dist_path"] == str(export_path / "dist")
    assert len(data["commands"]) == 2
    project = client.get(f"/api/v3/projects/{pid}", headers=headers).json()["project"]
    stored = project["metadata"]["astro_build"]
    assert stored["status"] == "built"
    assert stored["dist_path"] == data["dist_path"]
    status = client.get(f"/api/v3/projects/{pid}/export/astro/build/status", headers=headers)
    assert status.json()["status"] == "built"


def test_path_traversal_project_id_blocked(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/projects/prj-evil../export/astro/build", headers=headers)
    assert res.status_code in (400, 404, 422)


def test_runner_unit_gate_and_dist(tmp_path, monkeypatch):
    monkeypatch.setattr(astro_export_engine, "EXPORT_ROOT", tmp_path / "generated_sites")
    export_root = tmp_path / "generated_sites" / "prj-unitest01"
    export_root.mkdir(parents=True)
    (export_root / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    project = {
        "id": "prj-unitest01",
        "metadata": {
            "astro_export": {"export_path": str(export_root)},
        },
    }
    gate_open = {"can_publish": True, "reasons": []}
    with patch.object(astro_build_runner, "_default_cmd_runner", _success_runner):
        result = astro_build_runner.run_build("prj-unitest01", project, gate=gate_open)
    assert result["success"] is True
    assert (export_root / "dist" / "index.html").is_file()
