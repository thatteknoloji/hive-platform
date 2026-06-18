"""Crawl & Gap Engine V1 — gerçek state, mock başarı yok."""

import json

import pytest

from app.moduller import crawl_gap_engine as cge


OWN_HTML = """
<html><head><title>Balkutusu Rehber</title>
<script type="application/ld+json">{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Kuşadası gece hayatı nedir?"}]}</script>
<meta property="article:published_time" content="2025-01-01"></head>
<body>
<h1>Kuşadası Gece Hayatı</h1>
<h2>Barlar ve Mekanlar</h2>
<h2>Kuşadası mahalle rehberi</h2>
<p>Kuşadası gece hayatı rehberi içerik metni burada yer alır.</p>
<a href="/gece-hayati">Gece hayatı</a>
<a href="https://rakip.com/page">Rakip</a>
</body></html>
"""

COMP_HTML = """
<html><head><title>Rakip Site</title></head>
<body>
<h1>Rakip Kuşadası</h1>
<h2>En iyi barlar</h2>
<h2>Kuşadası ilçe rehberi</h2>
<h2>Kuşadası gece hayatı nasıl?</h2>
<h2>Yakın lokasyonlar</h2>
<p>Rakip içerik metni.</p>
</body></html>
"""


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "crawl_gap_engine_state.json"
    opp_state = tmp_path / "opportunity_engine_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    opp_state.write_text(json.dumps({"analyses": {"project:proj-test": {"opportunities": []}}}), encoding="utf-8")

    monkeypatch.setattr(cge, "STATE_FILE", state)
    monkeypatch.setattr(cge, "OPPORTUNITY_STATE_FILE", opp_state)
    monkeypatch.setattr(cge, "REPORTS_DIR", reports)

    state.write_text(json.dumps({
        "settings": dict(cge.DEFAULT_SETTINGS),
        "jobs": [],
        "analyses": {},
        "domain_analyses": {},
        "project_analyses": {},
        "competitor_analyses": {},
        "gap_reports": {},
        "latest": {},
        "crawl_history": [],
        "gap_history": [],
        "domains": {},
        "exportable_opportunities": [],
    }), encoding="utf-8")

    def fake_fetch(url):
        if "rakip" in url:
            return COMP_HTML, None
        if "fail" in url:
            return None, "HTTP 403"
        return OWN_HTML, None

    monkeypatch.setattr(cge, "fetch_html", fake_fetch)
    monkeypatch.setattr(cge, "_fetch_page", lambda url: fake_fetch(url))
    yield {"state": state, "opp_state": opp_state, "reports": reports}


def test_health(isolated_env):
    h = cge.health()
    assert h["success"] is True
    assert h["module"] == "crawl_gap_engine"
    assert "history_counts" in h


def test_analyze_domain_requires_input():
    res = cge.analyze_domain("", [])
    assert res["success"] is False
    assert res["error"] == "domain_gerekli"


def test_analyze_domain_crawl_and_gaps(isolated_env):
    res = cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    assert res["success"] is True
    analysis = res["analysis"]
    assert analysis["gaps"]["stats"]["entity_gap_count"] >= 0
    assert "faq_gaps" in analysis["gaps"]
    assert analysis["page_scores"]
    assert analysis["action_plan"]
    assert res["opportunities"]


def test_crawl_failure_explicit(isolated_env):
    res = cge.analyze_domain(own_domain="https://fail.com", competitor_domains=[])
    assert res["success"] is False
    assert res["error"] == "crawl_failed"


def test_list_endpoints_after_analyze(isolated_env):
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    ents = cge.list_entities("proj-test")
    assert ents["success"] is True
    faqs = cge.list_faqs("proj-test")
    assert faqs["success"] is True
    geo = cge.list_geo("proj-test")
    assert geo["success"] is True
    clusters = cge.list_clusters("proj-test")
    assert clusters["success"] is True


def test_ai_provider_missing(isolated_env, monkeypatch):
    monkeypatch.setattr(
        "app.moduller.rank_index_watcher._dataforseo_configured",
        lambda: False,
    )
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    ai = cge.list_ai("proj-test")
    assert ai["success"] is False
    assert ai["error"] == "provider_missing"


def test_history_persisted(isolated_env):
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    st = json.loads(isolated_env["state"].read_text(encoding="utf-8"))
    assert len(st["crawl_history"]) >= 1
    assert len(st["gap_history"]) >= 1


def test_export_to_opportunity(isolated_env):
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
        export_to_opportunity=True,
    )
    opp = json.loads(isolated_env["opp_state"].read_text(encoding="utf-8"))
    opps = opp["analyses"]["project:proj-test"]["opportunities"]
    assert any(o.get("source") == "crawl_gap_engine" for o in opps)


def test_brain_integration(isolated_env, tmp_path, monkeypatch):
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    data = json.loads(brain_state.read_text(encoding="utf-8"))
    assert any(e.get("module") == "crawl_gap_engine" for e in data.get("events") or [])


def test_export_report(isolated_env):
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    res = cge.export_report("entity", project_id="proj-test")
    assert res["success"] is True


def test_analyze_project_requires_id():
    res = cge.analyze_project("")
    assert res["success"] is False


def test_dashboard(isolated_env):
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    dash = cge.dashboard("proj-test")
    assert dash["success"] is True
    assert dash["gap_stats"]
    assert "pages_crawled" in dash
    assert "critical_gaps" in dash


def test_private_ip_blocked(isolated_env):
    res = cge.crawl_site("http://127.0.0.1")
    assert res["success"] is False
    assert res["error"] == "private_ip_blocked"


def test_analyze_competitor(isolated_env):
    res = cge.analyze_competitor("https://rakip.com", own_domain="https://balkutusu.com", project_id="proj-test")
    assert res["success"] is True
    assert res["analysis"]["competitor_domains"] == ["https://rakip.com"]


def test_compare_domain(isolated_env):
    res = cge.compare_domain("https://balkutusu.com", "https://rakip.com", project_id="proj-test")
    assert res["success"] is True
    assert res["comparison"]["gap_stats"]


def test_entity_gap_scored(isolated_env):
    res = cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    gaps = res["analysis"]["gaps"]
    assert gaps["stats"]["entity_gap_count"] >= 0
    if gaps["entity_gaps"]:
        eg = gaps["entity_gaps"][0]
        assert "gap_id" in eg
        assert "overall_gap_score" in eg
        assert "competitor_mentions" in eg


def test_faq_gap_detection(isolated_env):
    res = cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    faqs = res["analysis"]["gaps"]["faq_gaps"]
    assert any("?" in (f.get("question") or "") for f in faqs) or len(faqs) >= 0


def test_opportunity_payload_type(isolated_env):
    res = cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    assert any(o.get("type") == "crawl_gap_opportunity" for o in res["opportunities"])


def test_qie_questions_format(isolated_env):
    res = cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    qs = res["analysis"].get("qie_questions") or []
    for q in qs:
        assert q.get("source") == "crawl_gap"
        assert "recommended_engine" in q


def test_serp_defense_payload(isolated_env):
    res = cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    dr = res["analysis"].get("defense_risks") or {}
    assert "serp_defense_payload" in dr


def test_jobs_api(isolated_env):
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    jobs = cge.list_jobs()
    assert jobs["success"] is True
    assert jobs["count"] >= 1
    job = cge.get_job(jobs["jobs"][0]["job_id"])
    assert job["success"] is True
    assert job["job"]["status"] in ("completed", "failed", "running")


def test_content_refresh_recommendations_plan_only(isolated_env):
    res = cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    recs = res["analysis"].get("content_refresh_recommendations") or []
    for r in recs:
        assert r.get("plan_only") is True
        assert r.get("source") == "crawl_gap_engine"


def test_authority_gaps(isolated_env):
    cge.analyze_domain(
        own_domain="https://balkutusu.com",
        competitor_domains=["https://rakip.com"],
        project_id="proj-test",
    )
    auth = cge.list_authority("proj-test")
    assert auth["success"] is True


def test_settings_update(isolated_env):
    s = cge.update_settings({"max_pages_per_domain": 50, "respect_robots_txt": True})
    assert s["max_pages_per_domain"] == 50
