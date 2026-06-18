"""SERP Defense Engine V1 — gerçek entegrasyon testleri."""

import json

import pytest

from app.moduller import rank_index_watcher as riw
from app.moduller import serp_defense_engine as sde


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    sde_state = tmp_path / "serp_defense_engine_state.json"
    riw_state = tmp_path / "rank_index_watcher_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    gate_state = tmp_path / "seo_quality_gate_state.json"
    cre_state = tmp_path / "content_refresh_engine_state.json"
    qie_state = tmp_path / "question_intelligence_engine_state.json"
    gate_state.write_text(json.dumps({"reports": {}}), encoding="utf-8")
    cre_state.write_text(json.dumps({"candidates": {}}), encoding="utf-8")
    qie_state.write_text(json.dumps({"outputs": []}), encoding="utf-8")

    monkeypatch.setattr(sde, "STATE_FILE", sde_state)
    monkeypatch.setattr(sde, "REPORTS_DIR", reports)
    monkeypatch.setattr(riw, "STATE_FILE", riw_state)
    monkeypatch.setattr(riw, "REPORTS_DIR", reports)
    monkeypatch.setattr(riw, "_gsc_oauth_configured", lambda: False)
    monkeypatch.setattr(riw, "_dataforseo_configured", lambda: False)

    sde_state.write_text(json.dumps({
        "settings": dict(sde.DEFAULT_SETTINGS),
        "fortress_cache": {},
        "attack_surface_cache": {},
        "fortress_history": [],
        "attack_surface_history": [],
        "defense_plan_history": [],
        "pressure_history": [],
        "keyword_defense_history": [],
        "plans": [],
        "jobs": {},
        "last_analyze_at": "",
    }), encoding="utf-8")
    riw_state.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    yield {"sde_state": sde_state, "riw_state": riw_state, "reports": reports}


def _register_kw_project():
    riw.register_project("proj-test", "https://balkutusu.com")
    st = json.loads(riw.STATE_FILE.read_text(encoding="utf-8"))
    st["projects"]["proj-test"]["keywords"] = [{
        "keyword": "kuşadası gece hayatı",
        "added_at": "2026-01-01 00:00:00 UTC",
        "last_position": 8,
        "history": [
            {"position": 8, "at": "2026-06-10 00:00:00 UTC"},
            {"position": 5, "at": "2026-06-01 00:00:00 UTC"},
            {"position": 4, "at": "2026-05-01 00:00:00 UTC"},
        ],
        "ranking_decay_score": 0,
        "trend_direction": "flat",
        "keyword_strength_score": 70,
    }]
    riw.STATE_FILE.write_text(json.dumps(st), encoding="utf-8")


def test_health(isolated_env):
    h = sde.health()
    assert h["success"] is True
    assert h["module"] == "serp_defense_engine"
    assert "integrations" in h
    assert "search_console" in h["integrations"]
    assert h["integrations"]["search_console"]["ok"] is False


def test_analyze_keyword_requires_keyword():
    res = sde.analyze_keyword("")
    assert res["success"] is False


def test_analyze_keyword_with_rank_data(isolated_env):
    _register_kw_project()
    res = sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    assert res["success"] is True
    report = res["report"]
    assert report["keyword"] == "kuşadası gece hayatı"
    assert 0 <= report["fortress_score"] <= 100
    assert "attack_surface_score" in report
    assert "pressure_level" in report
    for key in sde.FORTRESS_WEIGHTS:
        assert key in report["components"]
    assert all(a.get("apply") == "plan_only" for a in report["recommended_actions"])


def test_ai_overview_provider_missing_explicit(isolated_env):
    _register_kw_project()
    res = sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    ai = res["report"]["ai_overview"]
    assert ai.get("success") is False
    assert ai.get("error") == "provider_missing"


def test_ctr_gsc_not_configured(isolated_env):
    _register_kw_project()
    res = sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    ctr = res["report"]["ctr_analysis"]
    assert ctr.get("success") is False
    assert ctr.get("error") == "search_console_not_configured"


def test_generate_plan_executable(isolated_env):
    _register_kw_project()
    res = sde.generate_plan(keyword="kuşadası gece hayatı", project_id="proj-test")
    assert res["success"] is True
    plan = res["plan"]
    assert plan["one_click_defense"]["auto_apply"] is True
    assert "Planı Uygula" in plan["one_click_defense"]["note"] or "uygulanabilir" in plan["one_click_defense"]["note"].lower()
    assert "modules_to_run" in plan["one_click_defense"]
    assert plan["estimated_quality_score"] >= 0


def test_fortress_list_cached(isolated_env):
    _register_kw_project()
    sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    fl = sde.fortress_list("proj-test")
    assert fl["success"] is True
    assert fl["count"] == 1


def test_attack_surface_and_pressure(isolated_env):
    _register_kw_project()
    sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    atk = sde.attack_surface_list("proj-test")
    assert atk["success"] is True
    pres = sde.pressure_overview("proj-test")
    assert pres["success"] is True
    assert "LOW" in pres["by_level"]


def test_export_report(isolated_env):
    _register_kw_project()
    sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    res = sde.export_report("fortress", project_id="proj-test")
    assert res["success"] is True
    assert isolated_env["reports"].joinpath(res["path"].split("/")[-1]).exists() or __import__(
        "pathlib"
    ).Path(res["path"]).exists()


def test_dashboard(isolated_env):
    _register_kw_project()
    sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    dash = sde.dashboard("proj-test")
    assert dash["success"] is True
    assert dash["keyword_count"] == 1


def test_history_persisted(isolated_env):
    _register_kw_project()
    sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    st = json.loads(isolated_env["sde_state"].read_text(encoding="utf-8"))
    assert len(st.get("fortress_history") or []) >= 1
    assert len(st.get("attack_surface_history") or []) >= 1
    assert len(st.get("pressure_history") or []) >= 1
    assert len(st.get("keyword_defense_history") or []) >= 1


def test_overall_fortress_and_strategy(isolated_env):
    _register_kw_project()
    res = sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    report = res["report"]
    assert report["overall_fortress_score"] == report["fortress_score"]
    assert "strategy_recommendation" in report
    assert report["strategy_recommendation"].get("decision") in ("defend", "grow", "balanced")


def test_brain_integration(isolated_env, tmp_path, monkeypatch):
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    _register_kw_project()
    sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    data = json.loads(brain_state.read_text(encoding="utf-8"))
    events = data.get("events") or []
    assert any(e.get("event_type") == "serp_defense_triggered" for e in events)
    assert any(e.get("module") == "serp_defense_engine" for e in events)


def test_opportunity_strategy_overlap(isolated_env, tmp_path, monkeypatch):
    opp_state = tmp_path / "opportunity_engine_state.json"
    opp_state.write_text(json.dumps({
        "settings": {},
        "analyses": {
            "project:proj-test": {
                "opportunities": [{
                    "type": "keyword",
                    "keyword": "kuşadası gece hayatı",
                    "opportunity_score": 82,
                    "estimated_gain": 90,
                }],
            },
        },
    }), encoding="utf-8")
    import app.moduller.opportunity_engine as opp
    monkeypatch.setattr(opp, "STATE_FILE", opp_state)

    _register_kw_project()
    res = sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    strat = res["report"]["strategy_recommendation"]
    assert strat.get("success") is True
    assert strat.get("overlap", {}).get("found") is True
    assert strat.get("decision") in ("defend", "grow", "balanced")


def test_defense_plan_history(isolated_env):
    _register_kw_project()
    sde.generate_plan(keyword="kuşadası gece hayatı", project_id="proj-test")
    st = json.loads(isolated_env["sde_state"].read_text(encoding="utf-8"))
    assert len(st.get("defense_plan_history") or []) >= 1
    plan = st["plans"][-1]
    oc = plan["one_click_defense"]
    assert "faqs_to_add" in oc
    assert "geo_sections_to_add" in oc
    assert "support_pages_needed" in oc
    assert oc["auto_apply"] is True


def test_health_history_counts(isolated_env):
    h = sde.health()
    assert "history_counts" in h
    assert "fortress_history" in h["history_counts"]
    assert "providers" in h
    assert h["providers"]["search_console"] is False
    assert h["providers"]["dataforseo"] is False


def test_refresh_live_data_gsc_not_configured(isolated_env):
    _register_kw_project()
    res = sde.refresh_live_data("proj-test", "kuşadası gece hayatı", "https://balkutusu.com")
    assert res["success"] is True
    assert res["live_refresh"]["gsc"]["success"] is False
    assert res["live_refresh"]["gsc"]["error"] == "search_console_not_configured"
    assert res["live_refresh"]["rank"]["skipped"] is True


def test_refresh_live_data_gsc_configured(isolated_env, monkeypatch):
    _register_kw_project()

    def _fake_sync(project_id, domain, days=28):
        snapshot = {
            "success": True,
            "domain": domain,
            "clicks": 10,
            "impressions": 500,
            "ctr": 0.02,
            "top_queries": [{
                "query": "kuşadası gece hayatı",
                "clicks": 5,
                "impressions": 200,
                "ctr": 0.025,
                "position": 6.2,
            }],
        }
        st = json.loads(isolated_env["riw_state"].read_text(encoding="utf-8"))
        proj = st["projects"].get(project_id)
        if proj:
            proj.setdefault("performance_history", []).insert(0, snapshot)
            isolated_env["riw_state"].write_text(json.dumps(st), encoding="utf-8")
        return snapshot

    monkeypatch.setattr(sde, "_gsc_configured", lambda: True)
    monkeypatch.setattr(sde, "_sync_live_gsc", _fake_sync)
    res = sde.refresh_live_data("proj-test", "kuşadası gece hayatı", "https://balkutusu.com", refresh_rank=False)
    assert res["live_refresh"]["gsc"]["success"] is True
    proj = json.loads(isolated_env["riw_state"].read_text(encoding="utf-8"))
    assert len(proj["projects"]["proj-test"].get("performance_history") or []) >= 1


def test_ctr_live_after_gsc_sync(isolated_env, monkeypatch):
    _register_kw_project()

    def _fake_sync(project_id, domain, days=28):
        snapshot = {
            "success": True,
            "top_queries": [{
                "query": "kuşadası gece hayatı",
                "clicks": 5,
                "impressions": 200,
                "ctr": 0.025,
                "position": 6.2,
            }],
        }
        st = json.loads(isolated_env["riw_state"].read_text(encoding="utf-8"))
        st["projects"][project_id].setdefault("performance_history", []).insert(0, snapshot)
        isolated_env["riw_state"].write_text(json.dumps(st), encoding="utf-8")
        return snapshot

    monkeypatch.setattr(sde, "_gsc_configured", lambda: True)
    monkeypatch.setattr(sde, "_sync_live_gsc", _fake_sync)
    res = sde.analyze_keyword("kuşadası gece hayatı", project_id="proj-test")
    ctr = res["report"]["ctr_analysis"]
    assert ctr.get("success") is True
    assert ctr.get("ctr") == 0.025
    assert ctr.get("source") == "search_console"


def test_execute_plan_support_network(isolated_env, monkeypatch):
    _register_kw_project()
    st = json.loads(isolated_env["sde_state"].read_text(encoding="utf-8"))
    st["plans"] = [{
        "plan_id": "plan-sne-test",
        "project_id": "proj-test",
        "keyword": "kuşadası gece hayatı",
        "actions": [{"action": "support_network_boost", "keyword": "kuşadası gece hayatı", "priority": "medium"}],
        "one_click_defense": {"auto_apply": True},
    }]
    isolated_env["sde_state"].write_text(json.dumps(st), encoding="utf-8")

    import app.moduller.support_network_engine as sne
    monkeypatch.setattr(sne, "sync_network", lambda network_id="": {
        "success": True,
        "job_id": "sne-test",
        "results": {"domains": {"count": 2}},
    })

    exec_res = sde.execute_defense_plan(plan_id="plan-sne-test")
    assert exec_res["success"] is True
    assert exec_res["execution"]["status"] in ("completed", "partial")
    steps = exec_res["execution"]["steps"]
    assert any(s.get("action") == "support_network_boost" and s.get("success") for s in steps)
    st = json.loads(isolated_env["sde_state"].read_text(encoding="utf-8"))
    assert len(st.get("execution_history") or []) >= 1


def test_execute_plan_add_faq(isolated_env, monkeypatch):
    _register_kw_project()
    st = json.loads(isolated_env["sde_state"].read_text(encoding="utf-8"))
    st["plans"] = [{
        "plan_id": "plan-faq-test",
        "project_id": "proj-test",
        "keyword": "kuşadası gece hayatı",
        "actions": [{"action": "add_faq", "keyword": "kuşadası gece hayatı", "priority": "high"}],
        "one_click_defense": {"auto_apply": True},
    }]
    isolated_env["sde_state"].write_text(json.dumps(st), encoding="utf-8")

    import app.moduller.question_intelligence_engine as qie
    import app.moduller.publisher_hub as pub

    monkeypatch.setattr(qie, "generate_faq", lambda payload: {
        "success": True,
        "items": [{
            "title": "SSS Test",
            "keyword": payload["keyword"],
            "content_html": "<h1>SSS</h1><p>Test</p>",
            "content_type": "faq",
        }],
    })
    monkeypatch.setattr(pub, "enqueue", lambda item, **kw: {
        "success": True,
        "publish_id": "pub-1",
        "status": "queued",
    })
    monkeypatch.setattr(pub, "publish_item", lambda publish_id, **kw: {
        "success": True,
        "status": "published",
    })

    exec_res = sde.execute_defense_plan(plan_id="plan-faq-test")
    assert exec_res["success"] is True
    step = exec_res["execution"]["steps"][0]
    assert step["action"] == "add_faq"
    assert step["success"] is True
    assert step["publish"]["count"] == 1


def test_execute_plan_disabled(isolated_env, monkeypatch):
    _register_kw_project()
    sde.update_settings({"auto_apply_enabled": False})
    gen = sde.generate_plan(keyword="kuşadası gece hayatı", project_id="proj-test")
    res = sde.execute_defense_plan(plan_id=gen["plan"]["plan_id"])
    assert res["success"] is False
    assert res["error"] == "auto_apply_disabled"
    sde.update_settings({"auto_apply_enabled": True})
