"""Campaign Engine V1 — kampanya planlayıcı testleri."""

import json

import pytest

from app.moduller import campaign_engine as ce


MOCK_SOURCES = {
    "opportunity": {"success": True, "quick_wins": 4, "total_opportunities": 15, "top_opportunities": []},
    "serp": {"success": True, "critical_pressure_count": 1, "top_risks": [{"keyword": "test"}]},
    "citation": {"success": True, "citation_health_score": 58, "citation_risks": 18, "low_citation_pages": 3},
    "revenue": {"success": True, "today_leads": 3, "high_value_leads": 2, "revenue_opportunity": 400},
    "authority_factory": {"success": True, "queued_batches": 2, "published_today": 1},
    "support_network": {"success": True, "sites_count": 4},
    "crawl_gap": {"success": True, "faq_gaps": 20, "entity_gaps": 8, "critical_gaps": 5},
    "rank": {"success": True, "project_count": 2},
    "executive": {"success": True, "top_priority": {"keyword": "kuşadası gece hayatı", "title": "Kuşadası"}},
}


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "campaign_engine_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(ce, "STATE_FILE", state)
    monkeypatch.setattr(ce, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)
    monkeypatch.setattr(ce, "collect_sources", lambda **kwargs: dict(MOCK_SOURCES))
    def _mock_safe_read(module, func, *args, default=None, **kwargs):
        if module == "authority_factory":
            import importlib
            mod = importlib.import_module(f"app.moduller.{module}")
            fn = getattr(mod, func)
            return fn(*args, **kwargs)
        return default if default is not None else {}

    monkeypatch.setattr(ce, "_safe_read", _mock_safe_read)

    state.write_text(json.dumps({
        "settings": {**ce.DEFAULT_SETTINGS, "enabled": True},
        "campaigns": [],
        "tasks": [],
        "history": [],
    }), encoding="utf-8")
    yield


def test_health(isolated_env):
    h = ce.health()
    assert h["success"] is True
    assert h["module"] == "campaign_engine"
    assert h["publishes"] is False


def test_create_campaign(isolated_env):
    res = ce.create_campaign(target_keyword="kuşadası gece hayatı", goal="ranking", priority="high")
    assert res["success"] is True
    c = res["campaign"]
    assert c["campaign_id"].startswith("camp-")
    assert c["target_keyword"] == "kuşadası gece hayatı"
    assert c["status"] == "planned"
    assert c["goal"] == "ranking"


def test_create_campaign_requires_keyword(isolated_env):
    res = ce.create_campaign(target_keyword="")
    assert res["success"] is False


def test_generate_plan(isolated_env):
    created = ce.create_campaign(target_keyword="kuşadası gece hayatı", goal="lead_generation")
    cid = created["campaign"]["campaign_id"]
    plan = ce.generate_plan(cid)
    assert plan["success"] is True
    assert plan["task_count"] > 0
    bp = plan["blueprint"]["counts"]
    assert bp.get("pillar", 0) >= 1
    assert bp.get("faq", 0) >= 50
    assert bp.get("cluster", 0) >= 12
    camp = plan["campaign"]
    assert camp["status"] == "active"
    assert camp["weekly_blueprint"]
    assert camp["scores"]["overall"] >= 0


def test_blueprint_full_domination(isolated_env):
    bp = ce.compute_blueprint(keyword="test kw", goal="ranking", campaign_type="full_domination", sources=MOCK_SOURCES)
    counts = bp["counts"]
    assert counts["cluster"] >= 12
    assert counts["authority_source"] >= 10


def test_authority_integration(isolated_env, monkeypatch):
    batch_result = {"success": True, "batch": {"batch_id": "af-test123"}}

    def mock_safe(mod, func, *a, default=None, **kw):
        if mod == "authority_factory":
            return batch_result
        return default if default is not None else {"success": True}

    monkeypatch.setattr(ce, "_safe_read", mock_safe)
    created = ce.create_campaign(target_keyword="authority kw", goal="authority")
    cid = created["campaign"]["campaign_id"]
    ce.generate_plan(cid)
    res = ce.create_authority_batch(cid)
    assert res["success"] is True


def test_citation_integration(isolated_env):
    created = ce.create_campaign(target_keyword="cite kw", goal="citation")
    cid = created["campaign"]["campaign_id"]
    plan = ce.generate_plan(cid)
    cite_tasks = [t for t in plan["tasks"] if "citation" in (t.get("module") or "") or "citation" in (t.get("item_type") or "")]
    assert len(cite_tasks) >= 1


def test_revenue_integration(isolated_env):
    created = ce.create_campaign(target_keyword="lead kw", goal="lead_generation")
    cid = created["campaign"]["campaign_id"]
    plan = ce.generate_plan(cid)
    rev_tasks = [t for t in plan["tasks"] if t.get("module") == "revenue_lead_engine" or t.get("item_type") == "revenue"]
    assert len(rev_tasks) >= 1


def test_orchestrator_integration(isolated_env, monkeypatch):
    action_ids = []

    def mock_safe(mod, func, *a, default=None, **kw):
        if mod == "action_orchestrator" and func == "create_action":
            aid = f"ao-{len(action_ids)}"
            action_ids.append(aid)
            return {"success": True, "action": {"action_id": aid}}
        return default if default is not None else MOCK_SOURCES

    monkeypatch.setattr(ce, "_safe_read", mock_safe)
    created = ce.create_campaign(target_keyword="orch kw")
    cid = created["campaign"]["campaign_id"]
    ce.generate_plan(cid)
    res = ce.send_to_orchestrator(cid)
    assert res["success"] is True
    assert res["imported"] > 0


def test_brain_hook(isolated_env, monkeypatch):
    events = []

    def capture(event_type, module, **kwargs):
        events.append(event_type)

    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "record_event", capture)

    created = ce.create_campaign(target_keyword="brain kw")
    assert "campaign_created" in events
    ce.generate_plan(created["campaign"]["campaign_id"])
    assert "campaign_started" in events


def test_mission_control_payload(isolated_env):
    created = ce.create_campaign(target_keyword="mc kw", priority="critical")
    ce.generate_plan(created["campaign"]["campaign_id"])
    mc = ce.mission_control_payload()
    assert mc["success"] is True
    assert "active_campaigns" in mc
    assert "campaign_progress_avg" in mc
    assert "campaign_roi_estimate" in mc
    assert "top_campaign" in mc


def test_executive_alignment(isolated_env, monkeypatch):
    created = ce.create_campaign(target_keyword="kuşadası gece hayatı")
    ce.generate_plan(created["campaign"]["campaign_id"])

    def mock_exec(mod, func, *a, default=None, **kw):
        if mod == "executive_ai":
            return MOCK_SOURCES["executive"]
        return default if default is not None else {}

    monkeypatch.setattr(ce, "_safe_read", mock_exec)
    align = ce.executive_alignment_payload()
    assert align["success"] is True
    assert align.get("best_match") is not None


def test_export_report(isolated_env):
    created = ce.create_campaign(target_keyword="export kw")
    ce.generate_plan(created["campaign"]["campaign_id"])
    res = ce.export_report("overview")
    assert res["success"] is True
    assert res["path"].endswith(".json")


def test_list_and_get_campaign(isolated_env):
    created = ce.create_campaign(target_keyword="list kw", name="List Test")
    cid = created["campaign"]["campaign_id"]
    lst = ce.list_campaigns()
    assert lst["count"] >= 1
    one = ce.get_campaign(cid)
    assert one["success"] is True
    assert one["campaign"]["name"] == "List Test"


def test_campaign_scores(isolated_env):
    created = ce.create_campaign(target_keyword="score kw")
    cid = created["campaign"]["campaign_id"]
    plan = ce.generate_plan(cid)
    scores = plan["campaign"]["scores"]
    for key in ("ranking", "authority", "citation", "revenue", "execution", "risk", "overall"):
        assert key in scores
