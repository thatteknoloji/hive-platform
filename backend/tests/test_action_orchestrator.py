"""Action Orchestrator V1 testleri."""

import json

import pytest

from app.moduller import action_orchestrator as ao


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "action_orchestrator_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(ao, "STATE_FILE", state)
    monkeypatch.setattr(ao, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": {**ao.DEFAULT_SETTINGS, "enabled": True},
        "actions": [],
        "pipelines": [],
        "history": [],
        "stats": {"success_count": 0, "failure_count": 0, "completed_today": 0, "last_reset_date": ""},
    }), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state}


def test_health(isolated_env):
    h = ao.health()
    assert h["success"] is True
    assert h["module"] == "action_orchestrator"


def test_action_creation(isolated_env):
    r = ao.create_action(
        source_module="serp_defense_engine",
        action_type="add_faq",
        project_id="p1",
        keyword="test kw",
        priority="HIGH",
        estimated_gain=78,
    )
    assert r["success"] is True
    act = r["action"]
    assert act["action_id"].startswith("ao-")
    assert act["status"] == "queued"
    assert act["assigned_module"] == "question_intelligence_engine"
    assert act["estimated_gain"] == 78


def test_duplicate_action_prevention(isolated_env):
    ao.create_action(source_module="test", action_type="publish", title="Same", project_id="p1")
    r2 = ao.create_action(source_module="test", action_type="publish", title="Same", project_id="p1")
    assert r2["success"] is False
    assert "Duplicate" in r2["error"]


def test_queue_management(isolated_env):
    ao.create_action(source_module="a", action_type="add_faq", title="Q1")
    ao.create_action(source_module="b", action_type="publish", title="P1")
    listed = ao.list_actions(status="queued")
    assert listed["count"] == 2


def test_import_serp_pipeline(isolated_env):
    plan = {
        "plan_id": "sde-plan-test",
        "keyword": "Kuşadası gece hayatı",
        "project_id": "proj1",
        "one_click_defense": {
            "faqs_to_add": 3,
            "refreshes_needed": 2,
            "publishes_planned": 1,
        },
    }
    r = ao.import_plan("serp_defense_engine", {"plan": plan})
    assert r["success"] is True
    assert r["imported"] >= 2
    pipes = ao.list_pipelines()
    assert pipes["count"] >= 1


def test_import_autonomous_agent(isolated_env):
    plan = {
        "decisions": [{
            "decision_id": "d1",
            "recommended_action": "publish",
            "priority_score": 90,
            "project_id": "p1",
            "keyword": "kw",
        }],
    }
    r = ao.import_plan("autonomous_seo_agent", plan)
    assert r["success"] is True
    assert r["imported"] == 1


def test_status_transitions_plan_only(isolated_env):
    cr = ao.create_action(source_module="t", action_type="add_faq", title="FAQ task")
    aid = cr["action"]["action_id"]
    run = ao.run_action(aid)
    assert run["success"] is False
    assert "plan_only" in run["error"]


def test_status_transitions_semi_autonomous(isolated_env):
    ao.update_settings({"mode": "semi_autonomous"})
    cr = ao.create_action(source_module="t", action_type="add_faq", title="FAQ semi")
    aid = cr["action"]["action_id"]
    run = ao.run_action(aid)
    assert run["success"] is True
    assert run["status"] == "waiting_approval"


def test_status_transitions_autonomous(isolated_env, monkeypatch):
    ao.update_settings({"mode": "autonomous"})
    monkeypatch.setattr(ao, "_execute_action", lambda a, s: {"success": True, "delegated": True})
    cr = ao.create_action(source_module="t", action_type="add_faq", title="FAQ auto")
    aid = cr["action"]["action_id"]
    run = ao.run_action(aid)
    assert run["success"] is True
    assert run["action"]["status"] == "completed"


def test_cancel_action(isolated_env):
    cr = ao.create_action(source_module="t", action_type="deploy", title="Cancel me")
    aid = cr["action"]["action_id"]
    c = ao.cancel_action(aid)
    assert c["success"] is True
    assert c["action"]["status"] == "cancelled"


def test_settings_validation(isolated_env):
    bad = ao.update_settings({"mode": "invalid_mode"})
    assert bad["success"] is False
    good = ao.update_settings({"mode": "autonomous", "allow_publish": True})
    assert good["success"] is True
    assert good["settings"]["mode"] == "autonomous"


def test_mission_control_integration(isolated_env):
    ao.create_action(source_module="x", action_type="publish", title="Pending")
    ao.create_action(source_module="y", action_type="deploy", title="Fail me")
    dash = ao.build_dashboard()
    mcc = dash["mission_control"]
    assert "pending_actions" in mcc
    assert "running_actions" in mcc
    assert "failed_actions" in mcc
    assert "completed_today" in mcc
    assert mcc["pending_actions"] >= 1


def test_brain_integration(isolated_env):
    import app.moduller.hive_brain_engine as brain
    ao.create_action(source_module="brain_test", action_type="add_entity", title="Brain")
    events = brain._load_state().get("events") or []
    assert any(e.get("module") == "action_orchestrator" for e in events)


def test_pipeline_execution(isolated_env, monkeypatch):
    ao.update_settings({"mode": "autonomous"})
    monkeypatch.setattr(ao, "_execute_action", lambda a, s: {"success": True, "delegated": True})
    plan = {
        "plan_id": "pipe-test",
        "keyword": "kw",
        "one_click_defense": {"faqs_to_add": 2, "publishes_planned": 1},
    }
    imp = ao.import_plan("serp_defense", {"plan": plan})
    assert imp["imported"] >= 2
    for item in imp["actions"]:
        ao.run_action(item["action_id"], force=True)
    pipes = ao.list_pipelines()
    assert pipes["pipelines"][0]["steps_completed"] >= 1


def test_export_report(isolated_env):
    ao.create_action(source_module="e", action_type="publish", title="Export")
    r = ao.export_report("overview")
    assert r["success"] is True
    assert (isolated_env["reports"] / r["filename"]).exists()


def test_get_action(isolated_env):
    cr = ao.create_action(source_module="g", action_type="geo_page", title="Get me")
    g = ao.get_action(cr["action"]["action_id"])
    assert g["success"] is True
    assert g["action"]["title"] == "Get me"
