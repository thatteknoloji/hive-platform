"""Data Miner Engine V1 — unit tests."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.moduller import data_miner_engine as dm


SAMPLE_HTML = """
<html><head><title>Test Club</title>
<script type="application/ld+json">{"@type":"LocalBusiness","name":"Night Club","address":{"streetAddress":"Main St"}}</script>
</head><body>
<h1>Night Club Kuşadası</h1>
<p>Call us: info@test.com or +905321234567</p>
<h2>Sık Sorulan Sorular?</h2><p>We open at 22:00</p>
<nav><a href="/services">Hizmetler</a></nav>
</body></html>
"""

FAQ_SCHEMA_HTML = """
<html><head><script type="application/ld+json">
{"@type":"FAQPage","mainEntity":[{"@type":"Question","name":"Hours?","acceptedAnswer":{"@type":"Answer","text":"24/7"}}]}
</script></head><body><p>x@y.com</p></body></html>
"""


@pytest.fixture
def temp_state(monkeypatch):
    fd = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    fd.write(b'{"settings":{},"jobs":{},"datasets":[]}')
    fd.close()
    path = Path(fd.name)
    monkeypatch.setattr(dm, "STATE_FILE", path)
    yield path
    try:
        path.unlink()
    except OSError:
        pass


# ── Providers ─────────────────────────────────────────────────────────────────

def test_health_structure():
    h = dm.health()
    assert h["success"] is True
    assert h["module"] == "data_miner_engine"
    sg = h["providers"]["scrapegraphai"]
    assert "package_installed" in sg
    assert "available" in sg
    assert "reason" in sg or sg.get("reason") is None
    assert h["no_content_generation"] is True
    assert h["no_publishing"] is True


def test_scrapegraph_import_detection():
    assert isinstance(dm._scrapegraph_installed(), bool)


def test_scrapegraph_llm_missing_graceful(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_installed", lambda: True)
    monkeypatch.setattr(dm, "_scrapegraph_enabled", lambda: True)
    monkeypatch.setattr(dm, "_llm_configured", lambda: (False, "llm_provider_missing"))
    entry = dm._scrapegraph_health_entry()
    assert entry["package_installed"] is True
    assert entry["available"] is False
    assert entry["reason"] == "llm_provider_missing"


def test_fallback_to_beautifulsoup_when_scrapegraph_not_ready(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_ready", lambda: (False, "llm_provider_missing"))
    monkeypatch.setattr(dm, "_playwright_available", lambda: False)
    assert dm._resolve_current_provider() == "beautifulsoup"


def test_health_provider_payload_fields():
    h = dm.health()
    assert h["provider_chain"] == ["scrapegraphai", "playwright", "beautifulsoup"]
    sg = h["providers"]["scrapegraphai"]
    assert "llm_configured" in sg
    assert "ready" in sg


def test_settings_update_persists(temp_state):
    res = dm.update_settings({"engine_preference": "beautifulsoup"})
    assert res["success"] is True
    assert res["settings"]["engine_preference"] == "beautifulsoup"
    st = json.loads(temp_state.read_text())
    assert st["settings"]["engine_preference"] == "beautifulsoup"


def test_dashboard_provider_fields(temp_state):
    d = dm.dashboard()
    assert "active_extractor" in d
    assert "fallback_provider" in d
    assert "scrapegraphai_installed" in d


def test_firecrawl_provider_missing():
    with patch.dict("os.environ", {}, clear=True):
        res = dm._firecrawl_scrape("https://example.com")
    assert res["success"] is False
    assert res["error"] == "provider_missing"


def test_scrapegraph_extract_provider_missing_when_not_installed(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_installed", lambda: False)
    res = dm._scrapegraph_extract("https://example.com")
    assert res["success"] is False
    assert res["error"] == "provider_missing"


def test_beautifulsoup_available():
    assert dm._beautifulsoup_available() is True


# ── Extraction ────────────────────────────────────────────────────────────────

def test_extract_from_html_entities():
    data = dm.extract_from_html(SAMPLE_HTML, "https://example.com")
    assert len(data["entities"]) >= 1
    assert any("Night" in e.get("label", "") for e in data["entities"])


def test_extract_phones_emails():
    data = dm.extract_from_html(SAMPLE_HTML, "https://example.com")
    assert "info@test.com" in data["emails"]
    assert len(data["phones"]) >= 1


def test_extract_faq_from_schema():
    data = dm.extract_from_html(FAQ_SCHEMA_HTML, "https://faq.com")
    assert len(data["faqs"]) >= 1
    assert data["faqs"][0]["question"] == "Hours?"


def test_extract_schema_types():
    data = dm.extract_from_html(FAQ_SCHEMA_HTML, "https://faq.com")
    assert "FAQPage" in data["schema_types"]


def test_extract_categories():
    data = dm.extract_from_html(SAMPLE_HTML, "https://example.com")
    assert "Hizmetler" in data["categories"]


def test_build_result_model():
    ext = {"entities": [], "faqs": [], "schema_types": ["WebSite"], "phones": ["1"], "emails": [],
           "addresses": [], "categories": [], "services": [], "products": [], "links": [], "metadata": {}}
    r = dm.build_result("dm-abc", "beautifulsoup", ext)
    assert r["job_id"] == "dm-abc"
    assert r["source"] == "beautifulsoup"
    assert "phones" in r and "metadata" in r


def test_merge_extractions():
    a = {"entities": [{"label": "A", "type": "x", "source": "t"}], "faqs": [], "schema_types": ["A"],
         "phones": ["1"], "emails": [], "addresses": [], "categories": [], "services": [], "products": [], "links": [], "metadata": {}}
    b = {"entities": [{"label": "B", "type": "y", "source": "t"}], "faqs": [], "schema_types": ["B"],
         "phones": ["2"], "emails": [], "addresses": [], "categories": [], "services": [], "products": [], "links": [], "metadata": {}}
    m = dm._merge_extractions([a, b])
    assert len(m["entities"]) == 2
    assert set(m["phones"]) == {"1", "2"}


# ── Domain gaps ───────────────────────────────────────────────────────────────

def test_domain_gaps_schema_missing():
    ext = {"schema_types": ["WebSite"], "faqs": [], "entities": [], "metadata": {"pages": [{"word_count": 100}]}}
    gaps = dm._domain_gaps(ext)
    assert "entity_graph" in gaps
    assert len(gaps["schema_gap"]) >= 1
    assert any(g["gap"] == "thin_content" for g in gaps["content_gap"])


# ── Crawl URL ─────────────────────────────────────────────────────────────────

def test_crawl_url_success(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "fetch_page", lambda url, engine="auto": {
        "success": True, "provider": "beautifulsoup", "html": SAMPLE_HTML, "url": url,
    })
    monkeypatch.setattr(dm, "_read_entity_geo_hint", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_emit_brain", lambda *a, **k: None)
    res = dm.crawl_url("https://example.com")
    assert res["success"] is True
    assert res["job_id"]
    assert len(res.get("entities") or []) >= 0


def test_crawl_url_fetch_failed(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "fetch_page", lambda url, engine="auto": {
        "success": False, "provider": "beautifulsoup", "error": "fetch_failed", "url": url,
    })
    monkeypatch.setattr(dm, "_emit_brain", lambda *a, **k: None)
    res = dm.crawl_url("https://fail.com")
    assert res["success"] is False
    assert res["error"] == "fetch_failed"


def test_crawl_url_invalid():
    res = dm.crawl_url("")
    assert res["success"] is False


# ── Keyword crawl ─────────────────────────────────────────────────────────────

def test_crawl_keyword_provider_missing(monkeypatch):
    monkeypatch.setattr(dm, "_search_urls", lambda q, l: ([], "", "provider_missing"))
    res = dm.crawl_keyword("test query")
    assert res["success"] is False
    assert res["error"] == "provider_missing"


def test_crawl_keyword_success(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "_search_urls", lambda q, l: (["https://a.com"], "searxng", None))
    monkeypatch.setattr(dm, "fetch_page", lambda url, engine="auto": {
        "success": True, "provider": "beautifulsoup", "html": SAMPLE_HTML, "url": url,
    })
    monkeypatch.setattr(dm, "_emit_brain", lambda *a, **k: None)
    res = dm.crawl_keyword("kuşadası club", limit=1)
    assert res["success"] is True
    assert res["source"] == "searxng"


# ── Domain crawl ──────────────────────────────────────────────────────────────

def test_crawl_domain_success(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "fetch_page", lambda url, engine="auto": {
        "success": True, "provider": "beautifulsoup", "html": SAMPLE_HTML, "url": url,
    })
    monkeypatch.setattr(dm, "_emit_brain", lambda *a, **k: None)
    with patch("app.moduller.crawl_gap_engine.health", return_value={"success": True}):
        res = dm.crawl_domain("example.com", limit=2)
    assert res["success"] is True
    assert "gaps" in res


def test_crawl_domain_empty():
    assert dm.crawl_domain("")["success"] is False


# ── Jobs / settings / export ───────────────────────────────────────────────────

def test_jobs_and_results(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "fetch_page", lambda url, engine="auto": {
        "success": True, "provider": "beautifulsoup", "html": "<html><body>test@test.com</body></html>", "url": url,
    })
    monkeypatch.setattr(dm, "_read_entity_geo_hint", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_emit_brain", lambda *a, **k: None)
    crawled = dm.crawl_url("https://jobs.com")
    jid = crawled["job_id"]
    jobs = dm.list_jobs()
    assert jobs["total"] >= 1
    got = dm.get_results(jid)
    assert got["success"] is True
    assert got["result"]["job_id"] == jid


def test_get_results_not_found():
    assert dm.get_results("missing-id")["success"] is False


def test_settings_update(temp_state):
    res = dm.update_settings({"max_pages_per_job": 15})
    assert res["success"] is True
    assert dm.get_settings()["settings"]["max_pages_per_job"] == 15


def test_export_report(temp_state, monkeypatch, tmp_path):
    monkeypatch.setattr(dm, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(dm, "fetch_page", lambda url, engine="auto": {
        "success": True, "provider": "beautifulsoup", "html": SAMPLE_HTML, "url": url,
    })
    monkeypatch.setattr(dm, "_read_entity_geo_hint", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_emit_brain", lambda *a, **k: None)
    crawled = dm.crawl_url("https://export.com")
    out = dm.export_report(crawled["job_id"], "json")
    assert out["success"] is True
    assert "content" in out


def test_dashboard(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "hive_integrations", lambda: {"success": True, "read_only": True, "ready": True, "integrations": {}})
    d = dm.dashboard()
    assert d["success"] is True
    assert "total_jobs" in d


def test_hive_integrations_read_only(monkeypatch):
    monkeypatch.setattr(dm, "_INTEGRATION_CACHE", {"at": 0.0, "data": None})
    import app.moduller.opportunity_engine as oe
    import app.moduller.entity_geo_graph as egg
    import app.moduller.campaign_engine as ce
    import app.moduller.crawl_gap_engine as cge
    import app.moduller.hive_brain_engine as hbe
    monkeypatch.setattr(oe.opportunity_engine, "health", lambda: {"success": True})
    monkeypatch.setattr(egg.entity_geo_graph, "health", lambda: {"success": True})
    monkeypatch.setattr(ce, "health", lambda: {"success": True})
    monkeypatch.setattr(cge, "health", lambda: {"success": True})
    monkeypatch.setattr(hbe.hive_brain, "health", lambda: {"success": True})
    res = dm.hive_integrations()
    assert res["read_only"] is True
    assert "entity_geo_graph" in res["integrations"]
