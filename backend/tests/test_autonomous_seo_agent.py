"""Autonomous SEO Agent V1 — karar katmanı testleri."""

import json

import pytest

from app.moduller import autonomous_seo_agent as asa


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "autonomous_seo_agent_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(asa, "STATE_FILE", state)
    monkeypatch.setattr(asa, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": {**asa.DEFAULT_SETTINGS, "enabled": True},
        "decisions": [],
        "missions": {"daily": [], "weekly": []},
        "action_plans": [],
        "audit_history": [],
        "stats": {"success_count": 0, "failure_count": 0},
    }), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state}


def test_health(isolated_env):
    h = asa.health()
    assert h["success"] is True
    assert h["module"] == "autonomous_seo_agent"
    assert h["mode"] == "plan_only"
    assert "defense" in h["agent_types"]


def test_threat_detection(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_collect_defense_signals", lambda pid: [{
        "keyword": "test kw",
        "recommended_action": "refresh",
        "reason": "CRITICAL pressure",
        "impact": 90,
        "confidence": 85,
        "risk": 20,
        "estimated_gain": 70,
        "source_module": "serp_defense_engine",
    }])
    monkeypatch.setattr(asa, "_collect_growth_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_content_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_authority_signals", lambda pid, nid: [])
    monkeypatch.setattr(asa, "_collect_publisher_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_memory_context", lambda pid="": {"success_actions": {}, "failure_actions": {}})

    res = asa.analyze_project("proj-1")
    assert res["success"] is True
    defense = res["by_agent"].get("defense") or []
    assert len(defense) >= 1
    assert defense[0]["recommended_action"] == "refresh"


def test_growth_prioritization(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_collect_defense_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_growth_signals", lambda pid: [
        {"keyword": "low", "recommended_action": "target_keyword", "reason": "low", "impact": 40, "confidence": 60, "risk": 30, "estimated_gain": 30, "source_module": "opportunity_engine"},
        {"keyword": "high", "recommended_action": "fill_gap", "reason": "high", "impact": 95, "confidence": 88, "risk": 20, "estimated_gain": 85, "source_module": "crawl_gap_engine"},
    ])
    monkeypatch.setattr(asa, "_collect_content_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_authority_signals", lambda pid, nid: [])
    monkeypatch.setattr(asa, "_collect_publisher_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_memory_context", lambda pid="": {"success_actions": {}, "failure_actions": {}})

    res = asa.analyze_project("proj-1")
    decisions = res["decisions"]
    assert decisions[0]["keyword"] == "high" or decisions[0]["priority_score"] >= decisions[-1]["priority_score"]


def test_authority_prioritization(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_collect_defense_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_growth_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_content_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_authority_signals", lambda pid, nid: [{
        "keyword": "auth kw",
        "recommended_action": "authority_boost",
        "reason": "idle authority site",
        "impact": 65,
        "confidence": 72,
        "risk": 30,
        "estimated_gain": 50,
        "source_module": "authority_mesh_engine",
    }])
    monkeypatch.setattr(asa, "_collect_publisher_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_memory_context", lambda pid="": {"success_actions": {}, "failure_actions": {}})

    res = asa.analyze_project("proj-1", network_id="net-1", agents=["authority"])
    assert res["success"] is True
    assert any(d["agent_type"] == "authority" for d in res["decisions"])


def test_refresh_prioritization(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_collect_defense_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_growth_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_content_signals", lambda pid: [{
        "keyword": "page kw",
        "recommended_action": "refresh",
        "reason": "CRITICAL refresh",
        "impact": 88,
        "confidence": 80,
        "risk": 15,
        "estimated_gain": 75,
        "source_module": "content_refresh_engine",
        "metadata": {"page_id": "p1"},
    }])
    monkeypatch.setattr(asa, "_collect_authority_signals", lambda pid, nid: [])
    monkeypatch.setattr(asa, "_collect_publisher_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_memory_context", lambda pid="": {"success_actions": {}, "failure_actions": {}})

    res = asa.analyze_project("proj-1", agents=["content"])
    assert any(d["recommended_action"] == "refresh" for d in res["decisions"])


def test_publisher_prioritization(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_collect_defense_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_growth_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_content_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_authority_signals", lambda pid, nid: [])
    monkeypatch.setattr(asa, "_collect_publisher_signals", lambda pid: [{
        "keyword": "pub kw",
        "recommended_action": "publish",
        "reason": "queue item",
        "impact": 55,
        "confidence": 70,
        "risk": 45,
        "estimated_gain": 40,
        "source_module": "publisher_hub",
    }])
    monkeypatch.setattr(asa, "_memory_context", lambda pid="": {"success_actions": {}, "failure_actions": {}})

    res = asa.analyze_project("proj-1", agents=["publisher"])
    assert any(d["recommended_action"] == "publish" for d in res["decisions"])


def test_mission_generation(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "analyze_project", lambda pid, nid="", **kw: {
        "success": True,
        "decisions": [
            {"decision_id": "d1", "recommended_action": "refresh", "priority_score": 80, "agent_type": "content", "reason": "r"},
            {"decision_id": "d2", "recommended_action": "refresh", "priority_score": 75, "agent_type": "content", "reason": "r"},
            {"decision_id": "d3", "recommended_action": "faq_expansion", "priority_score": 70, "agent_type": "defense", "reason": "r"},
        ],
        "by_agent": {},
    })
    daily = asa.generate_daily_mission("proj-1")
    assert daily["success"] is True
    assert daily["mission"]["type"] == "daily"
    assert len(daily["mission"]["items"]) >= 1

    weekly = asa.generate_weekly_mission("proj-1")
    assert weekly["success"] is True
    assert weekly["mission"]["type"] == "weekly"
    assert "sections" in weekly["mission"]


def test_decision_scoring(isolated_env):
    scores = asa.compute_decision_scores(impact=90, confidence=85, risk=20, estimated_gain=75)
    assert 0 <= scores["priority_score"] <= 100
    assert scores["impact_score"] == 90
    assert scores["confidence_score"] == 85


def test_brain_integration(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_collect_defense_signals", lambda pid: [{
        "keyword": "brain kw",
        "recommended_action": "refresh",
        "reason": "test",
        "impact": 80,
        "confidence": 85,
        "risk": 20,
        "estimated_gain": 60,
        "source_module": "serp_defense_engine",
    }])
    monkeypatch.setattr(asa, "_collect_growth_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_content_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_collect_authority_signals", lambda pid, nid: [])
    monkeypatch.setattr(asa, "_collect_publisher_signals", lambda pid: [])
    monkeypatch.setattr(asa, "_memory_context", lambda pid="": {"success_actions": {}, "failure_actions": {}})

    asa.analyze_project("proj-brain")
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    assert any(e.get("module") == "autonomous_seo_agent" or d.get("module") == "autonomous_seo_agent"
               for e in data.get("events") or [] for d in [e] + (data.get("decisions") or []))


def test_duplicate_decision_prevention(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_memory_context", lambda pid="": {"success_actions": {}, "failure_actions": {}})
    sig = {
        "keyword": "dup kw",
        "recommended_action": "refresh",
        "reason": "dup test",
        "impact": 70,
        "confidence": 80,
        "risk": 20,
        "estimated_gain": 50,
        "source_module": "test",
    }
    d1 = asa._make_decision("defense", "refresh", "dup test", project_id="p1", keyword="dup kw", scores=asa.compute_decision_scores(impact=70, confidence=80, risk=20, estimated_gain=50))
    d2 = asa._make_decision("defense", "refresh", "dup test", project_id="p1", keyword="dup kw", scores=asa.compute_decision_scores(impact=70, confidence=80, risk=20, estimated_gain=50))
    assert d1 is not None
    assert d2 is None


def test_settings_validation(isolated_env):
    with pytest.raises(ValueError):
        asa.update_settings({"mode": "invalid_mode"})
    s = asa.update_settings({"enabled": True, "min_confidence_score": 75})
    assert s["enabled"] is True
    assert s["min_confidence_score"] == 75
    assert s["allow_publish"] is False


def test_export_report(isolated_env):
    res = asa.export_report("overview")
    assert res["success"] is True
    assert __import__("pathlib").Path(res["path"]).exists()


def test_agent_disabled_by_default(tmp_path, monkeypatch):
    state = tmp_path / "agent_off.json"
    monkeypatch.setattr(asa, "STATE_FILE", state)
    state.write_text(json.dumps({"settings": dict(asa.DEFAULT_SETTINGS), "decisions": [], "missions": {"daily": [], "weekly": []}, "action_plans": [], "audit_history": [], "stats": {}}), encoding="utf-8")
    res = asa.analyze_project("p1")
    assert res["success"] is False
    assert res["error"] == "agent_disabled"


def test_dashboard(isolated_env, monkeypatch):
    monkeypatch.setattr(asa, "_integration_status", lambda: {"opportunity_engine": {"ok": True}})
    dash = asa.dashboard()
    assert dash["success"] is True
    assert dash["mode"] == "plan_only"
