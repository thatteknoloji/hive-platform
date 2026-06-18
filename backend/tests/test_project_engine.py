from __future__ import annotations

from pathlib import Path

import pytest

from app.moduller import project_engine as pe


@pytest.fixture()
def engine_state(tmp_path, monkeypatch):
    path = tmp_path / "project_engine_state.json"
    monkeypatch.setattr(pe, "STATE_FILE", path)
    return path


def test_project_engine_crud(engine_state):
    created = pe.create_project(
        name="BalKutusu",
        sector="ecommerce",
        domain="www.balkutusu.com",
        business_brief="E-ticaret",
        design={"layout": "grid"},
        deploy_mode="hive_cloud",
    )
    assert created["success"] is True
    pid = created["project"]["id"]
    assert pid.startswith("prj-")

    got = pe.get_project(pid)
    assert got and got["project"]["name"] == "BalKutusu"

    listed = pe.list_projects(search="balku")
    assert listed["count"] == 1

    updated = pe.update_project(pid, {"status": "active"})
    assert updated["project"]["status"] == "active"

    deleted = pe.delete_project(pid)
    assert deleted["success"] is True
    assert pe.get_project(pid) is None


def test_project_engine_persists(engine_state: Path):
    pe.create_project(name="Persist", sector="blog")
    assert engine_state.exists()
    pe.STATE_FILE = engine_state
    again = pe.list_projects()
    assert again["count"] == 1
