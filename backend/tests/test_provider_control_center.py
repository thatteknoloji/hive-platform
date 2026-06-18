"""Provider Control Center V1 — gözlem ve raporlama testleri."""

import json

import pytest

from app.moduller import provider_control_center as pcc


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "provider_control_center_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(pcc, "STATE_FILE", state)
    monkeypatch.setattr(pcc, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    def mock_probe(provider_id: str):
        base = {
            "connected": provider_id in ("blogger", "openrouter"),
            "configured": provider_id != "google_sites",
            "status": "healthy" if provider_id == "blogger" else ("not_configured" if provider_id == "google_sites" else "warning"),
            "last_error": "" if provider_id == "blogger" else "missing token",
            "metadata": {
                "module": "mock",
                "tokens": {
                    "tokens_masked": [pcc.mask_token("sk-test-secret-abcd")],
                    "token_present": provider_id != "google_sites",
                },
                "last_action": {"action": "publish", "status": "published", "at": "2026-06-10 12:00:00 UTC"},
            },
            "quota": {"published": 2},
        }
        if provider_id == "tumblr":
            base["status"] = "critical"
            base["connected"] = False
            base["last_error"] = "oauth expired"
        return base

    monkeypatch.setattr(pcc, "PROBE_MAP", {pid: (lambda pid=pid: mock_probe(pid)) for pid in pcc.PROVIDER_IDS})

    state.write_text(json.dumps({
        "settings": {**pcc.DEFAULT_SETTINGS, "enabled": True},
        "providers": {},
        "alerts": [],
        "recent_activity": [],
        "history": [],
        "last_full_check": "",
    }), encoding="utf-8")
    yield


def test_health(isolated_env):
    h = pcc.health()
    assert h["success"] is True
    assert h["module"] == "provider_control_center"
    assert h["publishes"] is False
    assert h["providers_total"] == len(pcc.PROVIDER_IDS)


def test_provider_discovery(isolated_env):
    res = pcc.check_all_providers(persist=True)
    assert res["success"] is True
    assert res["count"] == len(pcc.PROVIDER_IDS)
    lst = pcc.list_providers()
    assert lst["count"] == len(pcc.PROVIDER_IDS)
    names = {p["provider"] for p in lst["providers"]}
    assert "github_pages" in names
    assert "openrouter" in names


def test_token_masking(isolated_env):
    assert pcc.mask_token("sk-live-abcdefghijklmnop") == "********mnop"
    assert pcc.mask_token("ab") == "********ab"
    assert pcc.mask_token("") == ""
    res = pcc.check_provider("blogger", persist=True)
    tokens = res["provider"]["metadata"]["tokens"]["tokens_masked"]
    assert tokens
    assert "********" in tokens[0]
    assert "sk-test" not in tokens[0]


def test_error_detection(isolated_env):
    res = pcc.check_provider("tumblr", persist=True)
    assert res["provider"]["status"] == "critical"
    assert "oauth" in res["provider"]["last_error"]
    dash = pcc.dashboard()
    assert any(e.get("provider") == "tumblr" for e in dash.get("errors", []))


def test_mission_control_integration(isolated_env):
    pcc.check_all_providers(persist=True)
    mc = pcc.mission_control_payload()
    assert mc["success"] is True
    assert "provider_health_score" in mc
    assert "connected_providers" in mc
    assert "failed_providers" in mc
    assert "provider_alerts" in mc


def test_executive_integration(isolated_env):
    pcc.check_all_providers(persist=True)
    risk = pcc.executive_risk_payload()
    assert risk["success"] is True
    assert risk["provider_risk_score"] > 0
    assert "critical_providers" in risk


def test_brain_hook(isolated_env, monkeypatch):
    events = []

    def capture(event_type, module, **kwargs):
        events.append({"event_type": event_type, "module": module, **kwargs})

    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "record_event", capture)

    pcc.check_provider("blogger", persist=True)
    assert any(e["event_type"] == "provider_connected" for e in events)

    st = pcc._load_state()
    st["providers"]["blogger"] = {**st["providers"]["blogger"], "connected": False, "status": "critical", "last_error": "down"}
    pcc._save_state(st)
    pcc.check_provider("blogger", persist=True)
    assert any(e["event_type"] in ("provider_disconnected", "provider_error_detected", "provider_health_restored") for e in events)


def test_report_export(isolated_env):
    pcc.check_all_providers(persist=True)
    res = pcc.export_report("overview")
    assert res["success"] is True
    assert res["path"]
    path = res["path"]
    assert path.endswith(".json")
    data = json.loads(open(path, encoding="utf-8").read())
    assert data.get("success") is True or "providers" in data


def test_get_provider(isolated_env):
    res = pcc.get_provider("openrouter", refresh=True)
    assert res["success"] is True
    assert res["provider"]["provider"] == "openrouter"


def test_settings(isolated_env):
    updated = pcc.update_settings({"auto_check_interval_minutes": 15})
    assert updated["auto_check_interval_minutes"] == 15
    assert pcc.get_settings()["auto_check_interval_minutes"] == 15


def test_executive_ai_risk_includes_providers(isolated_env, monkeypatch):
    from app.moduller import executive_ai as ea

    mock_sources = {
        "brain": {"success": True},
        "brain_timeline": {"timeline": []},
        "opportunity": {"quick_wins": 1, "total_opportunities": 5},
        "serp": {"critical_pressure_count": 0, "top_risks": []},
        "citation": {"citation_risks": 0, "citation_health_score": 60},
        "revenue": {"today_leads": 1, "high_value_leads": 0, "revenue_opportunity": 100},
        "authority_factory": {"published_today": 0, "queued_batches": 0},
        "orchestrator": {"action_success_rate": 70},
        "publisher": {},
        "support_network": {"sites_count": 1},
        "rank": {},
        "refresh": {"critical_pages": 0},
        "crawl_gap": {},
        "agent": {},
        "agent_missions": {},
        "mission_control": {"system_health": 65},
        "providers": {"provider_risk_score": 24, "critical_providers": ["tumblr"]},
    }
    monkeypatch.setattr(ea, "_collect_sources", lambda project_id="": mock_sources)
    scores = ea._score_from_sources(mock_sources)
    assert scores["risk_score"] >= 24
