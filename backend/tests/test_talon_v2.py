"""Talon V2 provider testleri."""

from app.moduller.talon_stack.providers.people_also_ask_provider import PeopleAlsoAskProvider
from app.moduller.talon_stack.providers.base import provider_health
from app.moduller.talon_stack.services.talon_search_service import talon_search_service


def test_provider_health():
    h = provider_health()
    assert "searxng" in h
    assert "tavily" in h
    assert h["autocomplete"] == "available"


def test_talon_health_endpoint_shape():
    data = talon_search_service.health()
    assert data["talon"] == "ok"
    assert "providers" in data


def test_paa_generate():
    qs = PeopleAlsoAskProvider.generate_from_seed("kuşadası gece hayatı")
    assert len(qs) >= 5


def test_keyword_ideas_offline():
    result = talon_search_service.generate_keyword_ideas("kuşadası")
    assert "autocompleteKeywords" in result


def test_full_seo_research_structure():
    result = talon_search_service.full_seo_research("kuşadası bar")
    for key in ["seedKeyword", "serpResults", "autocompleteKeywords", "faqIdeas"]:
        assert key in result
