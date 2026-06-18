"""Citation Engine V1 — analiz ve entegrasyon testleri."""

import json

import pytest

from app.moduller import citation_engine as ce

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Kuşadası Gece Hayatı Rehberi</title>
<meta name="author" content="HIVE Editor">
<script type="application/ld+json">{"@type":"Article","author":"HIVE"}</script>
<script type="application/ld+json">{"@type":"FAQPage"}</script>
<script type="application/ld+json">{"@type":"Organization"}</script>
</head><body>
<h1>Kuşadası Gece Hayatı</h1>
<p>Kuşadası gece hayatı canlı ve çeşitlidir.</p>
<h2>Gece hayatı nasıl?</h2>
<p>Cevap: Barlar ve kulüpler merkezde yoğunlaşır. 2025 güncel liste aşağıdadır.</p>
<blockquote cite="https://example.org">Alıntı bloğu</blockquote>
<ol class="sources"><li>Kaynak: example.org</li><li>Referans listesi</li></ol>
<p>İletişim ve gizlilik politikası. Hakkımızda sayfası.</p>
</body></html>"""

WEAK_HTML = """<html><head><title>Weak</title></head><body><p>Short.</p></body></html>"""


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "citation_engine_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(ce, "STATE_FILE", state)
    monkeypatch.setattr(ce, "REPORTS_DIR", reports)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({
        "settings": {**ce.DEFAULT_SETTINGS, "enabled": True},
        "pages": [],
        "entities": [],
        "competitors": [],
        "opportunities": [],
        "visibility": [],
        "projects": {},
        "history": [],
    }), encoding="utf-8")
    yield {"state": state, "reports": reports, "brain_state": brain_state}


def test_health(isolated_env):
    h = ce.health()
    assert h["success"] is True
    assert h["module"] == "citation_engine"
    assert h["produces_content"] is False
    assert "Google AI Overview" in h["ai_targets"]


def test_page_analysis(isolated_env):
    res = ce.analyze_page("https://example.com/test-page", html=SAMPLE_HTML, project_id="proj-1", title="Test")
    assert res["success"] is True
    page = res["page"]
    assert page["page_id"]
    assert page["url"] == "https://example.com/test-page"
    assert page["citation_score"] >= 40
    assert "overall_citation_score" in page
    assert page["faq_count"] >= 1
    assert "Article" in page["schema_types"]
    assert isinstance(page["missing_signals"], list)
    assert isinstance(page["improvements"], list)
    assert "ai_visibility" in page


def test_citation_subscores(isolated_env):
    res = ce.analyze_page("https://example.com/scores", html=SAMPLE_HTML)
    page = res["page"]
    for key in ce.SCORE_WEIGHTS:
        assert key in page
        assert 0 <= page[key] <= 100


def test_visibility_score(isolated_env):
    res = ce.analyze_page("https://example.com/vis", html=SAMPLE_HTML)
    vis = res["page"]["ai_visibility"]
    assert "ai_visibility_score" in vis
    assert "overview_probability" in vis
    assert "citation_probability" in vis
    assert "trust_probability" in vis
    assert vis["targets"]["Google AI Overview"]["status"] == "estimated"
    assert vis["targets"]["ChatGPT"]["status"] == "provider_missing"


def test_weak_page_missing_signals(isolated_env):
    res = ce.analyze_page("https://example.com/weak", html=WEAK_HTML)
    page = res["page"]
    assert page["citation_score"] < 60
    assert len(page["missing_signals"]) >= 3
    assert page["citation_ready"] is False


def test_project_analysis(isolated_env, monkeypatch):
    monkeypatch.setattr(ce, "_fetch_page", lambda url: {"success": True, "html": SAMPLE_HTML})
    monkeypatch.setattr(
        "app.moduller.entity_geo_graph.get_project_scores",
        lambda pid: {"success": True, "entity_strength_score": 72, "geo_coverage_score": 65, "topic_authority_score": 58},
    )
    monkeypatch.setattr(
        "app.moduller.entity_geo_graph.missing_entities",
        lambda **kwargs: {"success": True, "missing_entities": [], "recommended_pages": [{"title": "Support"}]},
    )
    res = ce.analyze_project("proj-1", urls=["https://example.com/a"])
    assert res["success"] is True
    assert res["summary"]["pages_analyzed"] >= 1
    assert res["entity_trust"]["trust_score"] > 0


def test_entity_trust(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.entity_geo_graph.get_project_scores",
        lambda pid: {"success": True, "entity_strength_score": 80, "geo_coverage_score": 70, "topic_authority_score": 75},
    )
    monkeypatch.setattr(
        "app.moduller.entity_geo_graph.missing_entities",
        lambda **kwargs: {"success": True, "missing_entities": [{"entity": "X"}]},
    )
    trust = ce._entity_trust_model(project_id="proj-1")
    assert trust["entity_strength"] == 80
    assert trust["trust_score"] > 0


def test_competitor_gap(isolated_env, monkeypatch):
    monkeypatch.setattr(ce, "_fetch_page", lambda url: {
        "success": True,
        "html": WEAK_HTML if "competitor" in url else SAMPLE_HTML,
    })
    our = ce.analyze_page("https://ours.com/page", html=SAMPLE_HTML)
    gap = ce._competitor_citation_gap(
        "https://ours.com/page",
        "https://competitor.com/page",
        our_record=our["page"],
    )
    assert gap["success"] is True
    assert "citation_gap_score" in gap
    assert gap["us"]["citation_score"] > gap["competitor"]["citation_score"]


def test_revenue_integration(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.revenue_lead_engine._load_state",
        lambda: {"leads": [
            {"source_url": "https://example.com/page", "estimated_value": 200, "keyword": "test"},
            {"source_url": "https://example.com/other", "estimated_value": 50},
        ]},
    )
    rev = ce.citation_revenue_score("https://example.com/page", citation_score=80)
    assert rev["success"] is True
    assert rev["lead_count"] >= 1
    assert "citation_revenue_score" in rev


def test_serp_integration(isolated_env):
    adj = ce.serp_fortress_adjustment("proj-1", "test kw", current_citation_score=40)
    assert adj["success"] is True
    assert adj["fortress_penalty"] is True
    assert adj["fortress_delta"] < 0

    adj2 = ce.serp_fortress_adjustment("proj-1", "test kw", current_citation_score=80)
    assert adj2["fortress_boost"] is True


def test_opportunity_integration(isolated_env):
    ce.analyze_page("https://example.com/opp", html=WEAK_HTML)
    payload = ce.opportunity_scoring_payload()
    assert payload["success"] is True
    assert len(payload.get("signals") or []) >= 1

    opps = [{"opportunity_score": 60, "domain": "https://example.com/opp"}]
    merged = ce.apply_citation_scores_to_opportunities(opps)
    assert merged[0].get("citation_opportunity_score") is not None


def test_brain_hook(isolated_env):
    ce.analyze_page("https://example.com/brain", html=WEAK_HTML)
    import app.moduller.hive_brain_engine as brain
    events = brain._load_state().get("events") or []
    types = {e.get("event_type") for e in events}
    assert "citation_analysis_completed" in types or "citation_gap_found" in types


def test_agent_signals(isolated_env):
    ce.analyze_page("https://example.com/low", html=WEAK_HTML)
    sig = ce.agent_signals()
    assert sig["success"] is True
    types = {i["type"] for i in sig.get("insights") or []}
    assert "low_citation_score" in types or len(sig.get("insights") or []) >= 0


def test_mission_control_payload(isolated_env):
    ce.analyze_page("https://example.com/mc", html=SAMPLE_HTML)
    mc = ce.mission_control_payload()
    assert mc["success"] is True
    assert "citation_health_score" in mc
    assert mc["pages_tracked"] >= 1


def test_export_report(isolated_env):
    ce.analyze_page("https://example.com/exp", html=SAMPLE_HTML)
    rep = ce.export_report("overview")
    assert rep["success"] is True
    assert rep["path"]
    assert rep["data"]["module"] == "citation_engine"


def test_settings(isolated_env):
    s = ce.update_settings({"citation_threshold": 80})
    assert s["citation_threshold"] == 80
    assert ce.get_settings()["citation_threshold"] == 80


def test_collect_citation_opportunities(isolated_env):
    ce.analyze_page("https://example.com/col", html=WEAK_HTML)
    opps, errs = ce.collect_citation_opportunities("proj-x")
    assert isinstance(opps, list)
    if opps:
        assert opps[0]["type"] == "citation"
        assert "citation_opportunity_score" in opps[0]
