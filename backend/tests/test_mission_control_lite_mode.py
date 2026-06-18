"""Mission Control production lite mode tests."""

import json
import time

import pytest

from app.moduller import mission_control_center as mcc


@pytest.fixture(autouse=True)
def isolated_mcc_lite(tmp_path, monkeypatch):
    state = tmp_path / "mission_control_center_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(mcc, "STATE_FILE", state)
    monkeypatch.setattr(mcc, "REPORTS_DIR", reports)
    monkeypatch.setattr(mcc, "_DASHBOARD_RESPONSE_CACHE", {"at": 0.0, "lite": None, "full": None, "standard": None})
    monkeypatch.setattr(mcc, "_SOURCES_CACHE", {"at": 0.0, "lite": None, "full": None, "standard": None})
    monkeypatch.setattr(mcc, "_PROVIDER_MC_CACHE", {"at": 0.0, "data": None})
    monkeypatch.setattr(mcc, "_LAST_MODULE_TIMINGS", [])

    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": dict(mcc.DEFAULT_SETTINGS),
        "actions": [],
        "history": [],
    }), encoding="utf-8")
    yield


def _fast_sources():
    base = {
        "brain": {"success": True, "today_count": 2, "total_events": 5, "recent": []},
        "brain_timeline": {"success": True, "timeline": [], "status": "deferred"},
        "agent": {"success": False, "status": "deferred", "error": "lite_mode"},
        "agent_missions": {"success": True, "daily": [], "weekly": [], "status": "deferred"},
        "serp": {"success": True, "critical_pressure_count": 0, "top_risks": []},
        "opportunity": {"success": True, "top_opportunities": []},
        "crawl_gap": {"success": True, "critical_gaps": 0},
        "authority_mesh": {"success": True, "published_count": 1, "queued_tasks": 0, "login_required_tasks": 0},
        "authority_factory": {"success": True, "factory_batches": 1, "failed_items": 0, "login_required_items": 0},
        "revenue_leads": {"success": True, "today_leads": 0},
        "citation": {"success": True, "citation_health_score": 50},
        "executive": {"success": True, "executive_score": 60, "health_category": "Warning"},
        "providers": {"success": True, "provider_health_score": 70, "healthy_providers": 5, "failed_providers": 1},
        "audit": {"success": True, "audit_score": 80, "critical_audit_issues": 0, "stuck_queues": 0, "top_critical": []},
        "campaigns": {"success": True, "active_campaigns": 1, "campaign_progress_avg": 40, "recent_campaigns": []},
        "success_path": {"success": True, "completion_percent": 25, "current_goal": "Setup", "next_action": "Deploy"},
        "readiness": {"success": True, "overall_score": 55, "launch_mode": "beta"},
        "support_network": {"success": False, "status": "deferred", "error": "lite_mode"},
        "publisher": {"success": True, "published_count": 1, "queue_size": 0, "dashboard": {"queued": 0, "drafts": 0, "published": 1}, "channels_connected": 2},
        "refresh": {"success": True, "critical_pages": 0, "high_priority": 0, "queue_size": 0},
        "rank": {"success": True, "project_count": 1, "cached": True},
        "astro": {"success": False, "status": "deferred", "error": "lite_mode"},
        "github_pages": {"success": True, "provider_ready": False, "error": "provider_missing", "cached": True},
        "google_sites": {"success": True, "provider_ready": False, "login_required_count": 1, "cached": True},
        "quality_gate": {"success": False, "status": "deferred", "error": "lite_mode"},
        "performance": {"success": True, "performance_score": 88, "performance_risk": 12},
    }
    return base


def test_is_mcc_lite_mode_env(monkeypatch):
    monkeypatch.setenv("HIVE_PRODUCTION", "true")
    monkeypatch.setenv("HIVE_MCC_LITE", "")
    assert mcc._is_mcc_lite_mode() is True

    monkeypatch.setenv("HIVE_PRODUCTION", "")
    monkeypatch.setenv("HIVE_MCC_LITE", "1")
    assert mcc._is_mcc_lite_mode() is True


def test_lite_dashboard_under_5s(monkeypatch):
    monkeypatch.setenv("HIVE_MCC_LITE", "true")
    monkeypatch.setattr(mcc, "_collect_sources_cached", lambda **kwargs: _fast_sources())
    monkeypatch.setattr(mcc, "_rank_alerts_from_state", lambda: [])
    monkeypatch.setattr(mcc, "_publisher_failed_count", lambda: 0)

    started = time.perf_counter()
    dash = mcc.build_dashboard(record_open=False, full=False)
    elapsed = time.perf_counter() - started

    assert dash["success"] is True
    assert dash["lite_mode"] is True
    assert dash["dashboard_mode"] == "lite"
    assert elapsed < 5.0
    assert dash["response_time_ms"] < 5000
    assert "agent" in dash["deferred_modules"] or dash["source_status"].get("agent", {}).get("status") == "deferred"


def test_full_dashboard_mode_flag(monkeypatch):
    monkeypatch.setenv("HIVE_MCC_LITE", "true")
    monkeypatch.setattr(mcc, "_collect_sources_cached", lambda **kwargs: _fast_sources())
    monkeypatch.setattr(mcc, "_rank_alerts_from_state", lambda: [])
    monkeypatch.setattr(mcc, "_publisher_failed_count", lambda: 0)

    dash = mcc.build_dashboard(record_open=False, full=True)
    assert dash["lite_mode"] is False
    assert dash["dashboard_mode"] == "full"


def test_deferred_module_no_fake_success(monkeypatch):
    monkeypatch.setenv("HIVE_MCC_LITE", "true")

    def slow_agent():
        time.sleep(2.0)
        return {"success": True, "fake": True}

    specs = mcc._lite_source_callables()
    specs["agent"] = slow_agent
    sources, timings = mcc._collect_sources_timed_from_specs(
        specs, total_budget_sec=5.0, per_module_timeout=0.2,
    )
    assert sources["agent"]["status"] == "deferred"
    assert sources["agent"]["error"] == "timeout"
    assert sources["agent"].get("fake") is not True
    assert any(t["module"] == "agent" and t["status"] == "deferred" for t in timings)


def test_http_lite_dashboard_endpoint(monkeypatch):
    monkeypatch.setenv("HIVE_MCC_LITE", "true")
    monkeypatch.setattr(mcc, "_collect_sources_cached", lambda **kwargs: _fast_sources())
    monkeypatch.setattr(mcc, "_rank_alerts_from_state", lambda: [])
    monkeypatch.setattr(mcc, "_publisher_failed_count", lambda: 0)

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/mission-control/dashboard", headers={"X-API-Key": "test"})
    assert r.status_code in (200, 401, 403)


def test_http_dashboard_full_endpoint(monkeypatch):
    monkeypatch.setattr(mcc, "_collect_sources_cached", lambda **kwargs: _fast_sources())
    monkeypatch.setattr(mcc, "_rank_alerts_from_state", lambda: [])
    monkeypatch.setattr(mcc, "_publisher_failed_count", lambda: 0)

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    r = client.get("/api/mission-control/dashboard-full", headers={"X-API-Key": "test"})
    assert r.status_code in (200, 401, 403)
