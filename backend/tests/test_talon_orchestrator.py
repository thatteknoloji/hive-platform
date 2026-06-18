"""Talon Orchestrator — birim testleri."""

import json
from unittest.mock import patch

import pytest

from app.moduller import talon_orchestrator as to


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    state_file = tmp_path / "talon_orchestrator_state.json"
    monkeypatch.setattr(to, "STATE_FILE", state_file)
    yield


def test_intent_classifier():
    assert to.intent_classifier("escort vip hizmet") == "commercial"
    assert to.intent_classifier("kuşadası gece hayatı nedir") == "informational"
    assert to.intent_classifier("en iyi kuşadası otelleri karşılaştır") == "comparison"
    assert to.intent_classifier("kuşadası escort fiyat") == "transactional"
    assert to.intent_classifier("kuşadası escort adres harita") == "navigational"
    assert to.intent_classifier("kuşadası mahalle merkez") == "local"


def test_page_type_recommender():
    assert to.page_type_recommender("kuşadası escort", "commercial", 0.6) == "astro_landing"
    assert to.page_type_recommender("nedir sss", "faq", 0.2) == "faq"
    assert to.page_type_recommender("x vs y", "comparison", 0.1) == "blog"
    assert to.page_type_recommender("arama terimi rehber", "informational", 0.1) == "blog"


def test_normalize_keyword_turkish():
    assert to.normalize_keyword("  Kuşadası   Gece  ") == "Kuşadası Gece"
    assert "ş" in to.normalize_keyword("kuşadası")
    assert "ı" in to.normalize_keyword("kuşadası")


def test_dedupe_keywords():
    items = ["Kuşadası Escort", "kuşadası escort", "Kuşadası  Escort", "aydın escort"]
    out = to.dedupe_keywords(items)
    assert len(out) == 2
    assert out[0] == "Kuşadası Escort"


def test_publish_priority_score():
    record = to.build_keyword_record("kuşadası gece hayatı", "Kuşadası")
    score = to.publish_priority_score(record)
    assert 0 <= score <= 100
    assert isinstance(score, int)

    low = to.build_keyword_record("x", "")
    low["recommended_page_type"] = "no_publish"
    assert to.publish_priority_score(low) < 50


def test_provider_missing_graceful_fallback(monkeypatch):
    monkeypatch.setattr(to.SearXNGProvider, "is_configured", staticmethod(lambda: False))
    monkeypatch.setattr(to.TavilyProvider, "is_configured", staticmethod(lambda: False))
    monkeypatch.setattr(to.ExaProvider, "is_configured", staticmethod(lambda: False))
    monkeypatch.setattr(to.AutocompleteProvider, "is_available", staticmethod(lambda: False))

    result = to.keyword_discovery("test keyword", "Kuşadası")
    assert result["success"] is False
    assert "provider" in result.get("error", "").lower() or "yapılandır" in result.get("error", "").lower()
    assert result.get("sources") is not None


def test_full_research_response_shape(monkeypatch):
    monkeypatch.setattr(to, "keyword_discovery", lambda s, l=None: {
        "success": True,
        "keywords": ["kuşadası gece hayatı", "kuşadası barlar"],
        "paa_questions": ["kuşadası gece hayatı nedir"],
        "sources": {"autocomplete": True},
        "errors": [],
    })
    monkeypatch.setattr(to, "geo_cluster_builder", lambda s, l: {
        "clusters": [{"pillar": "test", "topic": s}],
        "geo_pages": [{"title": "Kuşadası Merkez", "slug": "kusadasi-merkez", "keyword": "kuşadası merkez"}],
    })
    monkeypatch.setattr(to, "competitor_discovery", lambda k: {
        "competitors": [{"domain": "example.com", "appearances": 2}],
    })
    monkeypatch.setattr(to, "serp_gap_analysis", lambda k: {
        "success": True,
        "questions": ["kuşadası gece hayatı nerede"],
        "content_gaps": ["SSS fırsatı"],
    })

    result = to.full_research("kuşadası gece hayatı", "Kuşadası", limit=10)
    assert result["success"] is True
    assert result["seed_keyword"] == "kuşadası gece hayatı"
    assert isinstance(result["keywords"], list)
    assert len(result["keywords"]) >= 1
    assert "astro_factory_ready" in result
    assert "page_hub_ready" in result
    assert "sss_ready" in result
    assert "publisher_ready" in result
    assert "clusters" in result
    assert "geo_pages" in result
    assert "faq_questions" in result
    assert "id" in result

    kw = result["keywords"][0]
    for field in (
        "keyword", "location", "intent", "recommended_page_type",
        "opportunity_score", "geo_score", "difficulty_proxy",
        "competitors", "questions", "content_brief", "created_at",
    ):
        assert field in kw


def test_astro_factory_ready_field(monkeypatch):
    monkeypatch.setattr(to, "keyword_discovery", lambda s, l=None: {
        "success": True,
        "keywords": ["kuşadası escort vip"],
        "paa_questions": [],
        "sources": {"autocomplete": True},
        "errors": [],
    })
    monkeypatch.setattr(to, "geo_cluster_builder", lambda s, l: {"clusters": [], "geo_pages": []})
    monkeypatch.setattr(to, "competitor_discovery", lambda k: {"competitors": []})
    monkeypatch.setattr(to, "serp_gap_analysis", lambda k: {"success": False})

    result = to.full_research("kuşadası escort", "Kuşadası", limit=5)
    assert result["success"] is True
    assert isinstance(result["astro_factory_ready"], list)
    if result["astro_factory_ready"]:
        assert result["astro_factory_ready"][0].get("recommended_page_type") == "astro_landing"


def test_health():
    h = to.health()
    assert h["success"] is True
    assert "providers" in h


def test_state_persistence(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(to, "STATE_FILE", state_file)
    monkeypatch.setattr(to, "keyword_discovery", lambda s, l=None: {
        "success": True, "keywords": [s], "paa_questions": [], "sources": {"autocomplete": True}, "errors": [],
    })
    monkeypatch.setattr(to, "geo_cluster_builder", lambda s, l: {"clusters": [], "geo_pages": []})
    monkeypatch.setattr(to, "competitor_discovery", lambda k: {"competitors": []})
    monkeypatch.setattr(to, "serp_gap_analysis", lambda k: {"success": False})

    to.full_research("test", "Kuşadası", limit=5)
    assert state_file.exists()
    data = json.loads(state_file.read_text(encoding="utf-8"))
    assert len(data.get("history", [])) >= 1
