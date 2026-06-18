"""First Run Wizard V1 testleri."""

import json

import pytest

from app.moduller import first_run_wizard as wizard


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "first_run_wizard_state.json"
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(wizard, "STATE_FILE", state)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    for sid in wizard.STEP_CHECKS:
        monkeypatch.setitem(wizard.STEP_CHECKS, sid, lambda: False)

    state.write_text(json.dumps({
        "manual_completed": [],
        "wizard_completed_at": "",
        "history": [],
    }), encoding="utf-8")
    yield


def test_health():
    h = wizard.health()
    assert h["success"] is True
    assert h["module"] == "first_run_wizard"


def test_status_eight_steps():
    s = wizard.get_status()
    assert s["success"] is True
    assert s["total_steps"] == 8
    assert len(s["steps"]) == 8
    assert s["progress_percent"] == 0
    assert s["progress_bucket"] == 0


def test_complete_step_manual():
    r = wizard.complete_step("wordpress", manual=True)
    assert r["success"] is True
    assert r["completed_count"] >= 1
    s = wizard.get_status()
    wp = next(x for x in s["steps"] if x["step_id"] == "wordpress")
    assert wp["completed"] is True


def test_progress_buckets():
    for sid in ["wordpress", "github", "blogger", "astro_project"]:
        wizard.complete_step(sid, manual=True)
    s = wizard.get_status()
    assert s["progress_bucket"] in (25, 50, 75, 100)
    assert s["completed_count"] == 4


def test_wizard_complete_all_steps():
    for step in wizard.WIZARD_STEPS:
        wizard.complete_step(step["step_id"], manual=True)
    s = wizard.get_status()
    assert s["wizard_completed"] is True
    assert s["progress_percent"] == 100
    assert s["progress_bucket"] == 100


def test_reset():
    wizard.complete_step("wordpress", manual=True)
    r = wizard.reset_wizard()
    assert r["success"] is True
    assert r["completed_count"] == 0


def test_invalid_step():
    r = wizard.complete_step("invalid_step", manual=True)
    assert r["success"] is False


def test_step_detail_enrichment():
    s = wizard.get_status()
    assert s["success"] is True
    wp = next(x for x in s["steps"] if x["step_id"] == "wordpress")
    assert wp.get("instructions")
    assert wp.get("env_vars")
    assert wp.get("status") in ("done", "pending", "connect_required")
