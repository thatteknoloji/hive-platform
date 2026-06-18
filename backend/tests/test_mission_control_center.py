"""Mission Control Center V1 testleri."""

import json

import pytest

from app.moduller import mission_control_center as mcc


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "mission_control_center_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(mcc, "STATE_FILE", state)
    monkeypatch.setattr(mcc, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": dict(mcc.DEFAULT_SETTINGS),
        "actions": [],
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state}


def _mock_sources(monkeypatch, **overrides):
    base = {
        "brain": {"success": True, "today_count": 3, "total_events": 10, "recent": [{"event_type": "test", "module": "x", "timestamp": "2026-01-01 10:00:00 UTC"}]},
        "brain_timeline": {"success": True, "timeline": []},
        "agent": {"success": True, "latest_daily_mission": None, "suggested_actions": [], "threats": []},
        "agent_missions": {"success": True, "daily": [], "weekly": []},
        "serp": {"success": True, "critical_pressure_count": 0, "top_risks": [], "weakest_fortresses": []},
        "opportunity": {"success": True, "top_opportunities": []},
        "crawl_gap": {"success": True, "critical_gaps": 0},
        "authority_mesh": {"success": True, "published_count": 2, "queued_tasks": 0, "login_required_tasks": 0, "browser_worker": {"available": True}},
        "support_network": {"success": True, "overall_network_score": 72, "gap_count": 0},
        "publisher": {"success": True, "published_count": 1, "queue_size": 0, "dashboard": {"queued": 0, "drafts": 0, "published": 1}},
        "refresh": {"success": True, "critical_pages": 0, "high_priority": 0, "queue_size": 0, "last_refresh_at": "2026-01-01"},
        "rank": {"success": True, "project_count": 1},
        "astro": {"success": True, "queued": 0, "quality_failed": 0},
        "github_pages": {"success": True, "provider_ready": False, "error": "provider_missing", "published_count": 0, "sites_count": 0},
        "google_sites": {"success": True, "provider_ready": False, "error": "provider_missing", "login_required_count": 0, "published_count": 0},
        "quality_gate": {"success": True},
    }
    base.update(overrides)
    monkeypatch.setattr(mcc, "_collect_sources", lambda **kwargs: base)
    monkeypatch.setattr(mcc, "_collect_sources_cached", lambda **kwargs: base)
    monkeypatch.setattr(mcc, "_rank_alerts_from_state", lambda: [])
    monkeypatch.setattr(mcc, "_publisher_failed_count", lambda: 0)
    return base


def test_health(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    h = mcc.health()
    assert h["success"] is True
    assert h["module"] == "mission_control_center"
    assert 0 <= h["system_health"] <= 100


def test_dashboard_aggregation(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    dash = mcc.build_dashboard(record_open=False)
    assert dash["success"] is True
    assert "system_health" in dash
    assert "critical_alerts" in dash
    assert "today_mission" in dash
    assert "next_best_actions" in dash
    assert "authority_status" in dash
    assert "publisher_status" in dash


def test_system_health_score(isolated_env, monkeypatch):
    sources = _mock_sources(monkeypatch, serp={"success": True, "critical_pressure_count": 3, "top_risks": [{"keyword": "kw"}]})
    health = mcc.compute_system_health(sources)
    assert 0 <= health["score"] <= 100
    assert len(health["components"]) == 8
    assert health["components"]["worker_health"] < 100


def test_critical_alerts(isolated_env, monkeypatch):
    sources = _mock_sources(monkeypatch, serp={
        "success": True, "critical_pressure_count": 2,
        "top_risks": [{"keyword": "test kw", "fortress_score": 40, "pressure_level": "CRITICAL"}],
    })
    alerts = mcc.build_critical_alerts(sources, mcc.get_settings())
    assert any(a["type"] == "serp_defense_critical" for a in alerts)


def test_today_mission_fallback(isolated_env, monkeypatch):
    sources = _mock_sources(monkeypatch, serp={
        "success": True, "top_risks": [{"keyword": "fallback kw", "pressure_level": "HIGH"}],
    }, opportunity={
        "success": True, "top_opportunities": [{"title": "Quick win", "opportunity_score": 85}],
    })
    items = mcc.build_today_mission(sources)
    assert len(items) >= 2
    assert any("fallback" in (i.get("title") or "").lower() or "serp" in (i.get("title") or "").lower() for i in items)


def test_next_best_actions(isolated_env, monkeypatch):
    sources = _mock_sources(monkeypatch, google_sites={
        "success": True, "provider_ready": False, "error": "provider_missing",
    })
    alerts = mcc.build_critical_alerts(sources, mcc.get_settings())
    actions = mcc.build_next_best_actions(sources, alerts, mcc.get_settings())
    assert len(actions) >= 1
    assert actions[0].get("deep_link")


def test_action_ack(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    res = mcc.acknowledge_action("mcc-act-test123")
    assert res["success"] is True
    assert res["status"] == "acknowledged"
    st = json.loads(isolated_env["state"].read_text(encoding="utf-8"))
    assert any(a.get("action_id") == "mcc-act-test123" for a in st.get("actions") or [])


def test_action_done(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    res = mcc.complete_action("mcc-act-done456")
    assert res["success"] is True
    assert res["status"] == "done"


def test_deep_links():
    assert mcc.DEEP_LINKS["serp_defense_engine"] == "serp_defense_engine"
    assert mcc.DEEP_LINKS["google_sites_worker"] == "authority_mesh_engine"
    item = mcc._mission_item("Test", "reason", "publisher_hub", "HIGH")
    assert item["deep_link"] == "publisher_hub"


def test_brain_hook(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    mcc.build_dashboard(record_open=True)
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    assert any(
        (e.get("metadata") or {}).get("mcc_event") == "mission_control_opened"
        for e in data.get("events") or []
    )


def test_export_report(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    res = mcc.export_report("overview")
    assert res["success"] is True
    assert __import__("pathlib").Path(res["path"]).exists()


def test_provider_missing_visible(isolated_env, monkeypatch):
    sources = _mock_sources(monkeypatch, google_sites={
        "success": True, "provider_ready": False, "error": "provider_missing — Playwright yapılandırın",
    })
    alerts = mcc.build_critical_alerts(sources, mcc.get_settings())
    assert any(a["type"] == "provider_missing" for a in alerts)
    dash = mcc.build_dashboard(record_open=False)
    assert dash["worker_status"]["google_sites"]["provider_ready"] is False


def test_missing_source_graceful_status(isolated_env, monkeypatch):
    sources = _mock_sources(monkeypatch, rank={})
    status = mcc.build_source_status(sources)
    assert status["rank"]["status"] == "not_configured"
    assert status["rank"]["status"] != "not_found"
    assert "Rank Watcher" in status["rank"]["message"]


def test_no_raw_not_found_in_payload(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    dash = mcc.build_dashboard(record_open=False)
    blob = json.dumps(dash).lower()
    assert "not found" not in blob
    assert '"not_found"' not in blob
    for entry in (dash.get("source_status") or {}).values():
        assert entry.get("status") in ("ok", "not_configured", "degraded")


def test_source_status_not_configured_rank(isolated_env, monkeypatch):
    sources = _mock_sources(monkeypatch, rank={"success": True, "project_count": 0})
    entry = mcc.build_source_status(sources)["rank"]
    assert entry == {
        "status": "not_configured",
        "source": "rank_index_watcher",
        "message": "Rank Watcher verisi henüz yok",
    }


API_HEADERS = {"X-API-Key": "supersifre123"}


@pytest.fixture
def api_client(isolated_env, monkeypatch):
    _mock_sources(monkeypatch)
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_http_health_endpoint(api_client):
    r = api_client.get("/api/mission-control/health", headers=API_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["module"] == "mission_control_center"
    assert "source_status" in body


def test_http_dashboard_endpoint(api_client):
    r = api_client.get("/api/mission-control/dashboard", headers=API_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "system_health" in body
    assert "source_status" in body
    assert "critical_alerts" in body


def test_http_alerts_endpoint(api_client):
    r = api_client.get("/api/mission-control/alerts", headers=API_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "alerts" in body


def test_http_actions_endpoint(api_client):
    r = api_client.get("/api/mission-control/actions", headers=API_HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "actions" in body


def test_http_dashboard_brain_event(isolated_env, api_client):
    r = api_client.get("/api/mission-control/dashboard", headers=API_HEADERS)
    assert r.status_code == 200
    data = json.loads(isolated_env["brain_state"].read_text(encoding="utf-8"))
    assert any(
        (e.get("metadata") or {}).get("mcc_event") == "mission_control_opened"
        for e in data.get("events") or []
    )
