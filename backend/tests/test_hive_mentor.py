"""HIVE Mentor V1 testleri."""

import json

import pytest

from app.moduller import hive_mentor as mentor


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "hive_mentor_state.json"
    brain_state = tmp_path / "hive_brain_state.json"
    brain_state.write_text(json.dumps({"events": [], "decisions": [], "settings": {}}), encoding="utf-8")

    monkeypatch.setattr(mentor, "STATE_FILE", state)
    import app.moduller.hive_brain_engine as brain
    monkeypatch.setattr(brain, "STATE_FILE", brain_state)

    state.write_text(json.dumps({"questions": [], "recommendation_history": []}), encoding="utf-8")
    yield


def test_health():
    h = mentor.health()
    assert h["success"] is True
    assert h["module"] == "hive_mentor"


def test_ask_keyword_growth_geo():
    r = mentor.ask("Kuşadası gece hayatında yükselmek istiyorum")
    assert r["success"] is True
    assert r["intent"] == "keyword_growth"
    modules = [s["module_id"] for s in r["steps"]]
    assert "opportunity_engine" in modules
    assert "crawl_gap_engine" in modules
    assert "authority_mesh_engine" in modules
    assert "publisher_hub" in modules


def test_ask_serp_defense():
    r = mentor.ask("SERP tehdidi var fortress düşüyor")
    assert r["success"] is True
    assert r["intent"] == "serp_defense"
    assert any(s["module_id"] == "serp_defense_engine" for s in r["steps"])


def test_ask_empty():
    r = mentor.ask("   ")
    assert r["success"] is False


def test_context_and_recommendations():
    mentor.ask("bugün ne yapmalıyım")
    ctx = mentor.get_context()
    assert ctx["questions_asked"] >= 1
    assert len(ctx.get("intent_catalog") or []) >= 10
    recs = mentor.get_recommendations()
    assert recs["success"] is True


def test_ask_google_sites():
    r = mentor.ask("Google Sites nasıl açılır")
    assert r["success"] is True
    assert r["intent"] == "google_sites_setup"
    assert r.get("tips")
    assert r.get("academy_guide") == "guide_google_sites"
    assert any(s["module_id"] == "authority_mesh_engine" for s in r["steps"])
