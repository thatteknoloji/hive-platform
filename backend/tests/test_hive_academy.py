"""HIVE Academy V1 testleri."""

import json

import pytest

from app.moduller import hive_academy as academy


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "hive_academy_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(academy, "STATE_FILE", state)
    monkeypatch.setattr(academy, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "viewed_modules": [],
        "completed_guides": [],
        "completed_workflows": [],
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "reports": reports}


def test_health():
    h = academy.health()
    assert h["success"] is True
    assert h["module"] == "hive_academy"
    assert h["modules_total"] >= 10
    assert 0 <= h["progress_percent"] <= 100


def test_list_modules():
    r = academy.list_modules()
    assert r["success"] is True
    assert r["count"] == len(r["modules"])
    ids = {m["module_id"] for m in r["modules"]}
    assert "publisher_hub" in ids
    assert "serp_defense_engine" in ids


def test_get_module_encyclopedia_fields():
    r = academy.get_module("publisher_hub", record_view=True)
    assert r["success"] is True
    mod = r["module"]
    for key in ("purpose", "what_it_does", "when_to_use", "when_not_to_use", "inputs", "outputs",
                "related_modules", "example_usage", "common_mistakes", "advanced_tips"):
        assert key in mod


def test_get_unknown_module_generic():
    r = academy.get_module("some_custom_module_xyz", record_view=False)
    assert r["success"] is True
    assert r["module"]["module_id"] == "some_custom_module_xyz"


def test_workflows_and_guides():
    w = academy.list_workflows()
    assert w["count"] >= 6
    g = academy.list_guides()
    assert g["count"] >= 8
    assert "fortress_score" in g["glossary"]
    assert "connect_required" in g["glossary"]


def test_get_guide_detail():
    r = academy.get_guide("guide_publisher")
    assert r["success"] is True
    guide = r["guide"]
    assert len(guide.get("steps") or []) >= 4
    assert len(guide.get("checklist") or []) >= 1


def test_module_count_expanded():
    r = academy.list_modules()
    assert r["count"] >= 25
    ids = {m["module_id"] for m in r["modules"]}
    assert "github_pages_worker" in ids
    assert "google_sites_worker" in ids
    assert "action_orchestrator" in ids


def test_mark_guide_complete():
    r = academy.mark_guide_complete("guide_publisher")
    assert r["success"] is True
    h = academy.health()
    assert h["guides_completed"] >= 1


def test_export_academy(isolated_env):
    r = academy.export_academy("overview")
    assert r["success"] is True
    assert (isolated_env["reports"] / r["filename"]).exists()
