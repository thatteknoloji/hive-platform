"""HIVE Brain / Memory Engine tests."""

import pytest

from app.moduller.hive_brain_engine import (
    hive_brain,
    record_event,
    record_decision,
    get_timeline,
    get_project_story,
    EVENT_TYPES,
)


@pytest.fixture(autouse=True)
def isolated_brain_state(tmp_path, monkeypatch):
    state_file = tmp_path / "hive_brain_state.json"
    monkeypatch.setattr("app.moduller.hive_brain_engine.STATE_FILE", state_file)
    monkeypatch.setattr("app.moduller.hive_brain_engine.REPORTS_DIR", tmp_path / "reports")
    yield


def test_health_empty():
    h = hive_brain.health()
    assert h["success"] is True
    assert h["module"] == "hive_brain_engine"
    assert h["events_count"] == 0


def test_record_event_schema():
    res = record_event(
        "project_created",
        "astro_factory",
        project_id="proj-test-1",
        domain="balkutusu.com",
        keyword="kuşadası otel",
        status="ok",
        result={"summary": "Proje oluşturuldu"},
    )
    assert res["success"] is True
    ev = res["event"]
    assert ev["event_id"].startswith("evt-")
    assert ev["event_type"] == "project_created"
    assert ev["module"] == "astro_factory"
    assert ev["project_id"] == "proj-test-1"
    assert ev["summary"]


def test_project_memory_and_story():
    record_event("project_created", "astro_factory", project_id="p1", status="ok")
    record_event("content_generated", "astro_factory", project_id="p1", status="ok", result={"count": 42})
    record_event("deploy_completed", "astro_auto_publisher", project_id="p1", domain="balkutusu.net", status="ok")

    mem = hive_brain.get_project_memory("p1")
    assert mem["success"] is True
    assert mem["memory"]["last_actions"]
    assert len(mem["recent_event_details"]) >= 3

    story = get_project_story("p1")
    assert story["success"] is True
    assert "p1" in story["story"]
    assert story["event_count"] >= 3


def test_domain_and_keyword_memory():
    record_event("deploy_completed", "network_replicator", domain="balkutusu.net", status="ok")
    record_event("rank_drop", "rank_index_watcher", keyword="kuşadası gece", result={"position": 12}, status="ok")

    dom = hive_brain.get_domain_memory("balkutusu.net")
    assert dom["success"] is True
    assert dom["memory"]["deploy_history"]

    kw = hive_brain.get_keyword_memory("kuşadası gece")
    assert kw["success"] is True
    assert kw["memory"]["position_history"]


def test_decision_memory():
    record_decision(
        "serp_defense_engine",
        "FAQ sayfası ekle",
        reason="CTR düşüşü",
        project_id="p2",
        keyword="test kw",
        applied=None,
    )
    decs = hive_brain.list_decisions()
    assert decs["count"] >= 1
    assert decs["decisions"][0]["recommendation"] == "FAQ sayfası ekle"


def test_timeline():
    record_event("content_published", "publisher_hub", project_id="p3", status="ok")
    tl = get_timeline(days=7)
    assert tl["success"] is True
    assert tl["days"] >= 1
    assert tl["timeline"][0]["highlights"]


def test_event_types_defined():
    assert "serp_defense_triggered" in EVENT_TYPES
    assert "quality_gate_pass" in EVENT_TYPES


def test_list_events_filter():
    record_event("network_created", "network_replicator", domain="balkutusu.org", status="ok")
    record_event("faq_created", "question_intelligence_engine", project_id="p4", status="ok")
    ev = hive_brain.list_events(limit=10, event_type="network_created")
    assert all(e["event_type"] == "network_created" for e in ev["events"])


def test_dashboard_empty_state():
    dash = hive_brain.dashboard()
    assert dash["success"] is True
    assert dash["status"] == "empty"
    assert dash["next_action"]["path"] == "/hive-brain"


def test_list_projects_empty():
    res = hive_brain.list_projects()
    assert res["success"] is True
    assert res["status"] == "empty"
    assert res["projects"] == []


def test_list_projects_with_data():
    record_event("project_created", "astro_factory", project_id="proj-a", status="ok")
    res = hive_brain.list_projects()
    assert res["success"] is True
    assert res["count"] >= 1
    assert any(p["project_id"] == "proj-a" for p in res["projects"])
