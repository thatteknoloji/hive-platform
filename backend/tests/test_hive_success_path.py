"""HIVE Success Path V2 testleri."""

import json

import pytest

from app.moduller import hive_success_path as sp


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "hive_success_path_state.json"
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(sp, "STATE_FILE", state)
    monkeypatch.setattr(sp, "REPORTS_DIR", tmp_path / "reports")
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    for sid in sp.STEP_CHECKS:
        monkeypatch.setitem(sp.STEP_CHECKS, sid, lambda: False)

    monkeypatch.setattr(sp, "_wizard_completed", lambda: True)

    state.write_text(json.dumps({
        "settings": dict(sp.DEFAULT_SETTINGS),
        "manual_completed": [],
        "badges_earned": [],
        "path_started_at": "",
        "path_completed_at": "",
        "history": [],
    }), encoding="utf-8")
    yield


def test_health():
    h = sp.health()
    assert h["success"] is True
    assert h["module"] == "hive_success_path"
    assert h["completion_score"] == 0


def test_progress_calculation():
    p = sp.get_progress(recalculate=True)
    assert p["success"] is True
    assert p["completion_score"] == 0
    assert p["total_steps"] == 8
    assert len(p["steps"]) == 8
    assert len(p["steps_remaining"]) == 8


def test_step_completion_manual():
    r = sp.complete_step("provider_setup", manual=True)
    assert r["success"] is True
    assert "provider_setup" in r["steps_completed"]
    assert r["completion_score"] == 10


def test_progress_score_all_steps():
    for step in sp.SUCCESS_STEPS:
        sp.complete_step(step["step_id"], manual=True)
    p = sp.get_progress(recalculate=True)
    assert p["completion_score"] == 100
    assert len(p["steps_completed"]) == 8
    assert p["path_completed_at"]


def test_recommendation_generation():
    recs = sp.get_recommendations(limit=3)
    assert recs["success"] is True
    assert recs["count"] >= 1
    assert recs["recommendations"][0].get("module_id")


def test_academy_integration_in_steps():
    steps = sp.get_steps()
    assert steps["success"] is True
    first = steps["steps"][0]
    assert first.get("academy_guide") or first.get("instructions")


def test_mentor_integration():
    sp.complete_step("first_campaign", manual=True)
    ans = sp.mentor_success_answer()
    assert ans["success"] is True
    assert ans["intent"] == "success_path"
    assert ans["completion_score"] >= 15
    assert len(ans["steps"]) >= 1


def test_mission_control_payload():
    sp.complete_step("first_lead", manual=True)
    mc = sp.mission_control_payload()
    assert mc["success"] is True
    assert mc["completion_percent"] == 20
    assert mc["current_goal"]
    assert mc["next_action"]


def test_executive_activation():
    sp.complete_step("provider_setup", manual=True)
    sp.complete_step("first_project", manual=True)
    act = sp.executive_activation_payload()
    assert act["success"] is True
    assert act["activation_score"] == 20
    assert act["activation_category"] in ("Needs Onboarding", "On Track", "Activated")


def test_role_flows():
    sp.update_settings({"role": "local_seo"})
    steps = sp.get_steps()
    assert steps["role"] == "local_seo"
    order = [s["step_id"] for s in steps["steps"]]
    assert order[0] == "provider_setup"
    assert order[1] == "first_keyword"


def test_export_report():
    r = sp.export_report("overview")
    assert r["success"] is True
    assert r["path"]
    assert r["report"]["progress"]["completion_score"] == 0


def test_brain_hook_on_complete():
    import app.moduller.hive_brain_engine as brain
    sp.complete_step("first_campaign", manual=True)
    events = brain._load_state().get("events") or []
    types = [e.get("event_type") for e in events]
    assert "success_step_completed" in types or "module_action" in types


def test_settings_update():
    r = sp.update_settings({"role": "authority_builder", "user_id": "test-user"})
    assert r["success"] is True
    assert r["settings"]["role"] == "authority_builder"
    assert r["settings"]["user_id"] == "test-user"


def test_badges_earned():
    sp.complete_step("first_campaign", manual=True)
    p = sp.get_progress(recalculate=True)
    badge_ids = [b["id"] for b in p.get("badges") or []]
    assert "first_campaign" in badge_ids
