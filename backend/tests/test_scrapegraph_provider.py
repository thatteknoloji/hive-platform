"""ScrapeGraphAI provider — Data Miner integration tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.moduller import data_miner_engine as dm


SG_RAW = {
    "entities": [{"label": "Night Club", "type": "LocalBusiness"}],
    "faqs": [{"question": "Hours?", "answer": "24/7"}],
    "phones": ["+905321234567"],
    "emails": ["info@club.com"],
    "addresses": ["Main St 1"],
    "schema_types": ["LocalBusiness", "FAQPage"],
    "services": ["VIP"],
    "products": ["Ticket"],
}


def test_scrapegraph_installed_after_pip():
    assert dm._scrapegraph_installed() is True


def test_health_scrapegraph_package_installed():
    h = dm.health()
    sg = h["providers"]["scrapegraphai"]
    assert sg["package_installed"] is True
    assert "available" in sg
    assert "reason" in sg or sg.get("reason") is None


def test_health_payload_has_provider_chain():
    h = dm.health()
    assert h["provider_chain"] == ["scrapegraphai", "playwright", "beautifulsoup"]
    assert "playwright" in h["providers"]
    assert "beautifulsoup" in h["providers"]


def test_scrapegraph_not_installed_returns_provider_missing(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_installed", lambda: False)
    ok, reason = dm._scrapegraph_available()
    assert ok is False
    assert reason == "provider_missing"


def test_scrapegraph_ready_requires_llm(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_installed", lambda: True)
    monkeypatch.setattr(dm, "_scrapegraph_enabled", lambda: True)
    monkeypatch.setattr(dm, "_llm_configured", lambda: (False, "llm_provider_missing"))
    ready, reason = dm._scrapegraph_ready()
    assert ready is False
    assert reason == "llm_provider_missing"


def test_map_scrapegraph_raw_full_model():
    mapped = dm.map_scrapegraph_raw(SG_RAW, "https://club.com")
    assert mapped["phones"] == ["+905321234567"]
    assert mapped["emails"] == ["info@club.com"]
    assert len(mapped["entities"]) == 1
    assert mapped["faqs"][0]["question"] == "Hours?"
    assert "LocalBusiness" in mapped["schema_types"]
    assert mapped["services"] == ["VIP"]
    assert mapped["products"] == ["Ticket"]


def test_map_scrapegraph_raw_string_entities():
    raw = {"entities": ["Acme Corp"], "phones": ["123"]}
    mapped = dm.map_scrapegraph_raw(raw, "https://acme.com")
    assert mapped["entities"][0]["label"] == "Acme Corp"
    assert mapped["phones"] == ["123"]


def test_fetch_page_auto_fallback_to_bs4(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_ready", lambda: (False, "llm_provider_missing"))
    monkeypatch.setattr(dm, "_playwright_fetch", lambda u: (None, "skip"))
    monkeypatch.setattr(dm, "fetch_html", lambda u: ("<html><body>x@y.com</body></html>", None))
    res = dm.fetch_page("https://fallback.com", engine="auto")
    assert res["success"] is True
    assert res["provider"] == "beautifulsoup"


def test_fetch_page_auto_uses_scrapegraph_when_ready(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_ready", lambda: (True, "ok"))
    monkeypatch.setattr(dm, "_scrapegraph_extract", lambda url, prompt="": {
        "success": True, "provider": "scrapegraphai", "raw": SG_RAW, "url": url,
    })
    res = dm.fetch_page("https://sg.com", engine="auto")
    assert res["success"] is True
    assert res["provider"] == "scrapegraphai"
    assert res["structured"]["phones"] == ["+905321234567"]


def test_fetch_page_scrapegraph_explicit_failure_no_fake_success(monkeypatch):
    monkeypatch.setattr(dm, "_scrapegraph_ready", lambda: (True, "ok"))
    monkeypatch.setattr(dm, "_scrapegraph_extract", lambda url, prompt="": {
        "success": False, "provider": "scrapegraphai", "error": "api_error",
    })
    res = dm.fetch_page("https://fail.com", engine="scrapegraphai")
    assert res["success"] is False
    assert res["error"] == "api_error"


def test_crawl_url_scrapegraph_extraction(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "fetch_page", lambda url, engine="auto": {
        "success": True,
        "provider": "scrapegraphai",
        "structured": SG_RAW,
        "url": url,
    })
    monkeypatch.setattr(dm, "_read_entity_geo_hint", lambda *a, **k: None)
    monkeypatch.setattr(dm, "_emit_brain", lambda *a, **k: None)
    res = dm.crawl_url("https://club.com")
    assert res["success"] is True
    assert res["phones"] == ["+905321234567"]
    assert res["source"] == "scrapegraphai"
    assert len(res["entities"]) >= 1


def test_dashboard_provider_fields(temp_state, monkeypatch):
    monkeypatch.setattr(dm, "hive_integrations", lambda: {"success": True, "read_only": True, "ready": True, "integrations": {}})
    d = dm.dashboard()
    assert "current_provider" in d
    assert "scrapegraphai_available" in d
    assert "playwright_available" in d
    assert "beautifulsoup_available" in d
    assert d["scrapegraphai_available"] is True


@pytest.fixture
def temp_state(monkeypatch):
    import json
    import tempfile
    from pathlib import Path
    fd = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    fd.write(b'{"settings":{"engine_preference":"auto"},"jobs":{},"datasets":[]}')
    fd.close()
    path = Path(fd.name)
    monkeypatch.setattr(dm, "STATE_FILE", path)
    yield path
    try:
        path.unlink()
    except OSError:
        pass
