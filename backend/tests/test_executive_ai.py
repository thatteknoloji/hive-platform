"""Executive AI V1 — stratejik karar katmanı testleri."""

import json

import pytest

from app.moduller import executive_ai as ea


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "executive_ai_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(ea, "STATE_FILE", state)
    monkeypatch.setattr(ea, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    mock_sources = {
        "brain": {"success": True},
        "brain_timeline": {"timeline": []},
        "opportunity": {
            "success": True,
            "quick_wins": 3,
            "total_opportunities": 12,
            "top_opportunities": [
                {"title": "Kuşadası gece hayatı", "keyword": "kuşadası gece hayatı", "opportunity_score": 82, "estimated_gain": 75},
            ],
        },
        "serp": {
            "success": True,
            "critical_pressure_count": 1,
            "top_risks": [{"keyword": "test kw", "fortress_score": 42, "pressure_score": 70}],
        },
        "citation": {
            "success": True,
            "citation_health_score": 58,
            "citation_risks": 2,
            "low_citation_pages": 3,
            "ai_visibility_avg": 55,
            "top_opportunities": [{"title": "Citation: add_faq", "citation_opportunity_score": 72}],
        },
        "revenue": {
            "success": True,
            "today_leads": 4,
            "high_value_leads": 2,
            "revenue_opportunity": 400,
            "best_lead_source": {"source": "blogger", "domain": "blog.example.com"},
        },
        "authority_factory": {"success": True, "queued_batches": 2, "published_today": 1},
        "orchestrator": {"success": True, "action_success_rate": 78, "queued": 5, "mission_control": {"pending_actions": 5}},
        "publisher": {"success": True},
        "support_network": {"success": True, "sites_count": 4},
        "rank": {"success": True},
        "refresh": {"success": True, "critical_pages": 1},
        "crawl_gap": {"success": True, "quick_wins": 2},
        "agent": {
            "success": True,
            "suggested_actions": [{"recommended_action": "scale_content", "title": "Kuşadası gece hayatı"}],
        },
        "agent_missions": {"daily": [], "weekly": []},
        "mission_control": {"success": True, "system_health": 72},
    }

    monkeypatch.setattr(ea, "_collect_sources", lambda project_id="": mock_sources)
    state.write_text(json.dumps({
        "settings": {**ea.DEFAULT_SETTINGS, "enabled": True},
        "summaries": {},
        "priorities": [],
        "missions": {"daily": [], "weekly": [], "monthly": []},
        "reports": [],
        "forecasts": {},
        "history": [],
    }), encoding="utf-8")
    yield


def test_health(isolated_env):
    h = ea.health()
    assert h["success"] is True
    assert h["module"] == "executive_ai"
    assert h["produces_content"] is False


def test_executive_summary(isolated_env):
    res = ea.analyze_project("proj-1")
    assert res["success"] is True
    s = res["summary"]
    assert s["project_id"] == "proj-1"
    for key in ("health_score", "growth_score", "risk_score", "revenue_score", "citation_score", "authority_score", "execution_score", "overall_score"):
        assert key in s
    assert s["health_category"] in ea.HEALTH_CATEGORIES


def test_priority_engine(isolated_env):
    res = ea.analyze_project("proj-1")
    pri = res["priorities"]
    assert len(pri) >= 1
    assert "priority_score" in pri[0]
    assert pri[0]["source"] in ("opportunity", "serp_defense", "citation", "revenue", "authority_factory", "crawl_gap")


def test_top_actions(isolated_env):
    res = ea.analyze_project("proj-1")
    assert len(res["top_actions"]) >= 1
    assert res["top_actions"][0]["rank"] == 1


def test_mission_generation(isolated_env):
    res = ea.analyze_project("proj-1")
    m = res["missions"]
    assert len(m.get("daily") or []) >= 1
    assert len(m.get("weekly") or []) >= 0
    assert len(m.get("monthly") or []) >= 1


def test_ceo_reports(isolated_env):
    res = ea.analyze_project("proj-1")
    reports = res["ceo_reports"]
    assert "today" in reports
    assert "week" in reports
    assert "month" in reports
    assert reports["week"].get("headline") or reports["week"].get("top_opportunity")


def test_forecast_generation(isolated_env):
    res = ea.analyze_project("proj-1")
    fc = res["forecasts"]
    assert "revenue_forecast" in fc
    assert "citation_forecast" in fc
    assert "risk_forecast" in fc
    assert "authority_forecast" in fc


def test_revenue_integration(isolated_env):
    res = ea.analyze_project("proj-1")
    assert res["summary"]["revenue_score"] > 0
    assert res["ceo_reports"]["today"]["top_revenue_source"] != "—"


def test_citation_integration(isolated_env):
    res = ea.analyze_project("proj-1")
    assert res["summary"]["citation_score"] == 58
    assert "Citation" in str(res["ceo_reports"]["today"].get("top_risk") or res["ceo_reports"]["today"].get("risks"))


def test_authority_integration(isolated_env):
    res = ea.analyze_project("proj-1")
    assert res["summary"]["authority_score"] > 40
    assert "authority" in res["ceo_reports"]["today"]["authority_note"].lower() or "batch" in res["ceo_reports"]["today"]["authority_note"].lower()


def test_orchestrator_integration(isolated_env):
    res = ea.analyze_project("proj-1")
    assert res["summary"]["execution_score"] == 78


def test_agent_alignment(isolated_env):
    res = ea.analyze_project("proj-1")
    al = res["agent_alignment"]
    assert "alignment_pct" in al


def test_brain_hook(isolated_env):
    ea.analyze_project("proj-1")
    import app.moduller.hive_brain_engine as brain
    events = brain._load_state().get("events") or []
    types = {e.get("event_type") for e in events}
    assert "executive_report_created" in types


def test_mission_control_payload(isolated_env):
    ea.analyze_project("global")
    mc = ea.mission_control_payload()
    assert mc["success"] is True
    assert "executive_score" in mc
    assert "top_priority" in mc


def test_export_report(isolated_env):
    ea.analyze_project("proj-1")
    rep = ea.export_report("overview")
    assert rep["success"] is True
    assert rep["path"]


def test_list_priorities_and_missions(isolated_env):
    ea.analyze_project("proj-1")
    pri = ea.list_priorities()
    assert pri["success"] is True
    missions = ea.list_missions()
    assert missions["success"] is True
    assert "daily" in missions
