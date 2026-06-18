"""HIVE Audit Engine V1 — merkezi denetim testleri."""

import json

import pytest

from app.moduller import hive_audit_engine as hae


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "hive_audit_engine_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(hae, "STATE_FILE", state)
    monkeypatch.setattr(hae, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": {**hae.DEFAULT_SETTINGS, "enabled": True},
        "issues": [],
        "reports": [],
        "scores": {},
        "last_run": "",
        "history": [],
    }), encoding="utf-8")
    yield


def _sample_issues():
    return [
        hae._make_issue("module", "warning", "Test module issue", affected_module="test_mod"),
        hae._make_issue("api", "critical", "Duplicate route", affected_file="main.py"),
        hae._make_issue("security", "warning", "Public endpoint", affected_file="main.py"),
        hae._make_issue("queue", "critical", "Stuck queue item: publisher_hub", affected_module="publisher_hub"),
    ]


def test_health(isolated_env):
    h = hae.health()
    assert h["success"] is True
    assert h["module"] == "hive_audit_engine"
    assert h["publishes"] is False


def test_run_audit(isolated_env, monkeypatch):
    monkeypatch.setattr(hae, "audit_modules", lambda: [_sample_issues()[0]])
    monkeypatch.setattr(hae, "audit_api", lambda: [_sample_issues()[1]])
    monkeypatch.setattr(hae, "audit_frontend", lambda: [])
    monkeypatch.setattr(hae, "audit_providers", lambda: [])
    monkeypatch.setattr(hae, "audit_states", lambda: [])
    monkeypatch.setattr(hae, "audit_queues", lambda: [_sample_issues()[3]])
    monkeypatch.setattr(hae, "audit_tests", lambda: [])
    monkeypatch.setattr(hae, "audit_security", lambda: [_sample_issues()[2]])

    res = hae.run_audit(persist=True)
    assert res["success"] is True
    assert res["scores"]["overall_audit_score"] >= 0
    assert res["report"]["total_issues"] == 4
    st = hae._load_state()
    assert st["last_run"]
    assert len(st["issues"]) == 4


def test_module_audit(isolated_env, monkeypatch):
    monkeypatch.setattr(hae, "_registered_modules", lambda: [{"id": "hive_audit_engine", "endpoint": "/api/hive-audit/health"}])
    monkeypatch.setattr(hae, "_nav_ids", lambda: set())
    monkeypatch.setattr(hae, "_parse_main_routes", lambda: [{"method": "GET", "path": "/api/hive-audit/health"}])
    monkeypatch.setattr(hae, "_test_files", lambda: {"hive_audit_engine": 5})
    monkeypatch.setattr(hae, "_state_files", lambda: [])
    issues = hae.audit_modules()
    assert isinstance(issues, list)


def test_api_audit(isolated_env, monkeypatch):
    monkeypatch.setattr(hae, "_parse_main_routes", lambda: [
        {"method": "GET", "path": "/api/test/health"},
        {"method": "GET", "path": "/api/test/health"},
    ])
    monkeypatch.setattr(hae, "_registered_modules", lambda: [])
    issues = hae.audit_api()
    assert any("Duplicate" in i["title"] for i in issues)


def test_frontend_route_audit(isolated_env, monkeypatch):
    monkeypatch.setattr(hae, "_nav_ids", lambda: {"hive_audit_engine", "missing_page"})
    monkeypatch.setattr(hae, "_route_map", lambda: {"hive_audit_engine": "/hive-audit-engine", "orphan_route": "/orphan"})
    monkeypatch.setattr(hae, "_app_gosterge_ids", lambda: {"hive_audit_engine"})
    issues = hae.audit_frontend()
    assert any(i.get("category") == "frontend" for i in issues)


def test_provider_audit(isolated_env, monkeypatch):
    mock_providers = {
        "providers": [
            {"provider": "tumblr", "label": "Tumblr", "status": "critical", "last_error": "oauth expired", "metadata": {"tokens": {"token_present": False}}},
            {"provider": "blogger", "label": "Blogger", "status": "healthy", "last_check": "2026-01-01 00:00:00 UTC", "metadata": {"tokens": {"token_present": True}}},
        ]
    }
    monkeypatch.setattr("app.moduller.provider_control_center.list_providers", lambda refresh=False: mock_providers)
    issues = hae.audit_providers()
    assert any("critical" in i["title"].lower() or "Tumblr" in i["title"] for i in issues)


def test_state_audit(isolated_env, tmp_path, monkeypatch):
    bad = tmp_path / "bad_state.json"
    bad.write_text("{broken", encoding="utf-8")
    good = tmp_path / "good_state.json"
    good.write_text(json.dumps({"settings": {}, "history": []}), encoding="utf-8")
    monkeypatch.setattr(hae, "APP_DIR", tmp_path)
    monkeypatch.setattr(hae, "_state_files", lambda: [])
    # direct call with empty - no crash
    issues = hae.audit_states()
    assert isinstance(issues, list)


def test_queue_audit(isolated_env, tmp_path, monkeypatch):
    pub_state = tmp_path / "publisher_hub_state.json"
    pub_state.write_text(json.dumps({
        "queue": [{"status": "failed", "title": "Test item", "updated_at": "2020-01-01 00:00:00 UTC"}],
        "drafts": [],
    }), encoding="utf-8")
    monkeypatch.setattr(hae, "APP_DIR", tmp_path)
    issues = hae.audit_queues()
    assert any("failed" in i["title"].lower() for i in issues)


def test_security_audit(isolated_env, monkeypatch):
    monkeypatch.setattr(hae, "_read_text", lambda path: "# no secrets here\n@app.get('/api/revenue-leads/track')\n")
    issues = hae.audit_security()
    assert any(i.get("category") == "security" for i in issues)


def test_issue_ack(isolated_env):
    issue = hae._make_issue("module", "warning", "Ack test")
    st = hae._load_state()
    st["issues"] = [issue]
    hae._save_state(st)
    res = hae.ack_issue(issue["issue_id"])
    assert res["success"] is True
    assert res["issue"]["status"] == "acknowledged"


def test_issue_resolve(isolated_env):
    issue = hae._make_issue("module", "critical", "Resolve test")
    st = hae._load_state()
    st["issues"] = [issue]
    hae._save_state(st)
    res = hae.resolve_issue(issue["issue_id"])
    assert res["success"] is True
    assert res["issue"]["status"] == "resolved"


def test_brain_hook(isolated_env, monkeypatch):
    events = []

    def capture(event_type, module, **kwargs):
        events.append({"event_type": event_type, "module": module})

    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "record_event", capture)
    monkeypatch.setattr(hae, "audit_modules", lambda: [])
    monkeypatch.setattr(hae, "audit_api", lambda: [])
    monkeypatch.setattr(hae, "audit_frontend", lambda: [])
    monkeypatch.setattr(hae, "audit_providers", lambda: [])
    monkeypatch.setattr(hae, "audit_states", lambda: [])
    monkeypatch.setattr(hae, "audit_queues", lambda: [])
    monkeypatch.setattr(hae, "audit_tests", lambda: [])
    monkeypatch.setattr(hae, "audit_security", lambda: [])

    hae.run_audit(persist=True)
    types = {e["event_type"] for e in events}
    assert "audit_started" in types
    assert "audit_completed" in types


def test_export_report(isolated_env, monkeypatch):
    monkeypatch.setattr(hae, "audit_modules", lambda: [])
    monkeypatch.setattr(hae, "audit_api", lambda: [])
    monkeypatch.setattr(hae, "audit_frontend", lambda: [])
    monkeypatch.setattr(hae, "audit_providers", lambda: [])
    monkeypatch.setattr(hae, "audit_states", lambda: [])
    monkeypatch.setattr(hae, "audit_queues", lambda: [])
    monkeypatch.setattr(hae, "audit_tests", lambda: [])
    monkeypatch.setattr(hae, "audit_security", lambda: [])
    hae.run_audit(persist=True)
    res = hae.export_report("overview")
    assert res["success"] is True
    assert res["path"].endswith(".json")


def test_mission_control_integration(isolated_env, monkeypatch):
    monkeypatch.setattr(hae, "audit_modules", lambda: [hae._make_issue("api", "critical", "MC test")])
    for fn in ("audit_api", "audit_frontend", "audit_providers", "audit_states", "audit_queues", "audit_tests", "audit_security"):
        monkeypatch.setattr(hae, fn, lambda: [])
    hae.run_audit(persist=True)
    mc = hae.mission_control_payload()
    assert "audit_score" in mc
    assert "critical_audit_issues" in mc


def test_executive_integration(isolated_env, monkeypatch):
    from app.moduller import executive_ai as ea
    monkeypatch.setattr(hae, "audit_modules", lambda: [hae._make_issue("security", "critical", "Exec test")])
    for fn in ("audit_api", "audit_frontend", "audit_providers", "audit_states", "audit_queues", "audit_tests", "audit_security"):
        monkeypatch.setattr(hae, fn, lambda: [])
    hae.run_audit(persist=True)
    risk = hae.executive_risk_payload()
    assert risk["audit_risk_score"] > 0

    mock_sources = {
        "brain": {}, "brain_timeline": {}, "opportunity": {}, "serp": {"critical_pressure_count": 0, "top_risks": []},
        "citation": {"citation_risks": 0}, "revenue": {}, "authority_factory": {}, "orchestrator": {},
        "publisher": {}, "support_network": {}, "rank": {}, "refresh": {}, "crawl_gap": {},
        "agent": {}, "agent_missions": {}, "mission_control": {"system_health": 70},
        "providers": {"provider_risk_score": 10}, "audit": {"audit_risk_score": 20},
    }
    monkeypatch.setattr(ea, "_collect_sources", lambda project_id="": mock_sources)
    scores = ea._score_from_sources(mock_sources)
    assert scores["risk_score"] >= 30
