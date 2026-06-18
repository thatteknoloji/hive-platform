"""Production Readiness Engine V1 testleri."""

import json

import pytest

from app.moduller import production_readiness_engine as pre


MOCK_SOURCES = {
    "providers": {
        "provider_health_score": 85,
        "connected_providers": 4,
        "critical_providers": 0,
        "warning_providers": 1,
        "provider_alerts": [],
    },
    "audit": {
        "audit_score": 78,
        "critical_audit_issues": 0,
        "stuck_queues": 0,
        "provider_risks": 0,
        "last_run": "2026-01-01",
        "top_critical": [],
    },
    "mission_control": {"success": True, "system_health": 72, "generated_at": "now"},
    "executive": {"executive_score": 70},
    "success_path": {"completion_percent": 55},
    "orchestrator": {"mission_control": {"pending_actions": 2}, "queued": 2},
    "campaigns": {"total_campaigns": 2, "active_campaigns": 1},
    "revenue": {"today_leads": 1},
    "publisher": {"channels_connected": 2, "queue_size": 0, "dashboard": {"queued": 0}},
    "authority": {"factory_batches": 1, "batches_count": 1},
    "brain": {"success": True, "recent": [{"id": 1}]},
    "academy": {"progress_percent": 45},
}


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "production_readiness_engine_state.json"
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(pre, "STATE_FILE", state)
    monkeypatch.setattr(pre, "REPORTS_DIR", tmp_path / "reports")
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    monkeypatch.setattr(pre, "_collect_sources", lambda: dict(MOCK_SOURCES))

    state.write_text(json.dumps({
        "settings": dict(pre.DEFAULT_SETTINGS),
        "last_calculation": {},
        "last_launch_mode": "development",
        "history": [],
    }), encoding="utf-8")
    yield


def test_health():
    h = pre.health()
    assert h["success"] is True
    assert h["module"] == "production_readiness_engine"


def test_readiness_score():
    r = pre.calculate(persist=False)
    assert r["success"] is True
    assert 0 <= r["overall_score"] <= 100
    assert r["overall_readiness_score"] == r["overall_score"]
    assert "score_components" in r


def test_launch_mode_beta_range():
    r = pre.calculate(persist=False)
    assert r["launch_mode"] in ("development", "alpha", "beta", "production_ready", "enterprise_ready")


def test_blockers_critical_audit():
    sources = dict(MOCK_SOURCES)
    sources["audit"] = {
        **MOCK_SOURCES["audit"],
        "critical_audit_issues": 2,
        "top_critical": [{"title": "Critical route broken", "severity": "critical"}],
    }
    import app.moduller.production_readiness_engine as mod
    mod._collect_sources = lambda: sources  # type: ignore
    r = pre.calculate(persist=False)
    assert len(r["blockers"]) >= 1
    assert r["launch_mode"] != "production_ready" or r["blockers"]


def test_warnings_onboarding_low():
    sources = dict(MOCK_SOURCES)
    sources["success_path"] = {"completion_percent": 10}
    sources["academy"] = {"progress_percent": 10}
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(pre, "_collect_sources", lambda: sources)
    r = pre.calculate(persist=False)
    types = [w["type"] for w in r["warnings"]]
    assert "onboarding_low" in types or "documentation_low" in types
    monkeypatch.undo()


def test_mission_control_payload():
    pre.calculate(persist=True)
    mc = pre.mission_control_payload()
    assert mc["success"] is True
    assert "launch_mode" in mc
    assert "blockers_count" in mc


def test_executive_integration():
    ex = pre.executive_readiness_payload()
    assert ex["success"] is True
    assert "executive_readiness_score" in ex
    assert "executive_launch_recommendation" in ex


def test_brain_hook_on_calculate():
    import app.moduller.hive_brain_engine as brain
    pre.calculate(persist=True)
    events = brain._load_state().get("events") or []
    types = [e.get("event_type") for e in events]
    assert "readiness_calculated" in types


def test_export_report():
    r = pre.export_report("overview")
    assert r["success"] is True
    assert r["path"]
    assert r["report"]["readiness"]["overall_score"] >= 0


def test_get_blockers_warnings():
    b = pre.get_blockers()
    w = pre.get_warnings()
    assert b["success"] is True
    assert w["success"] is True
    assert "count" in b
    assert "count" in w


def test_settings_update():
    r = pre.update_settings({"min_production_score": 85})
    assert r["success"] is True
    assert r["settings"]["min_production_score"] == 85
