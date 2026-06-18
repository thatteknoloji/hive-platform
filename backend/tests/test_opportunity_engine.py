"""Opportunity Engine tests — mock provider yok, eksik provider açık hata."""

import pytest

from app.moduller import opportunity_engine as oe


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    state_file = tmp_path / "opportunity_engine_state.json"
    monkeypatch.setattr(oe, "STATE_FILE", state_file)
    monkeypatch.setattr(oe, "REPORTS_DIR", tmp_path / "reports")
    yield


def test_health():
    h = oe.health()
    assert h["success"] is True
    assert h["module"] == "opportunity_engine"
    assert "integrations" in h


def test_analyze_project_requires_id():
    res = oe.analyze_project("")
    assert res.get("success") is False
    assert res.get("error") == "project_id gerekli"


def test_analyze_project_provider_missing(monkeypatch):
    monkeypatch.setattr(oe, "_collect_keyword_opportunities", lambda pid: ([], ["Rank Watcher yok"]))
    monkeypatch.setattr(oe, "_collect_entity_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_geo_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_faq_opportunities", lambda *a, **k: ([], ["QIE yok"]))
    monkeypatch.setattr(oe, "_collect_authority_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_publisher_opportunities", lambda: ([], []))
    monkeypatch.setattr(oe, "_collect_ai_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_cluster_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_brain_hints", lambda *a, **k: ([], []))
    res = oe.analyze_project("test-proj")
    assert res.get("success") is False
    assert res.get("error") == "provider_missing"


def test_analyze_project_with_mock_opportunities(monkeypatch):
    sample = oe._make_opp(
        "keyword",
        "Test keyword opp",
        source="test",
        project_id="p1",
        keyword="test kw",
        scores=oe._score_opportunity(traffic=80, difficulty=20, gain=75, effort=25),
    )
    monkeypatch.setattr(oe, "_collect_keyword_opportunities", lambda pid: ([sample], []))
    monkeypatch.setattr(oe, "_collect_entity_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_geo_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_faq_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_authority_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_publisher_opportunities", lambda: ([], []))
    monkeypatch.setattr(oe, "_collect_ai_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_cluster_opportunities", lambda *a, **k: ([], []))
    monkeypatch.setattr(oe, "_collect_brain_hints", lambda *a, **k: ([], []))

    res = oe.analyze_project("p1")
    assert res["success"] is True
    assert res["opportunity_count"] >= 1
    assert res["opportunities"][0]["opportunity_score"] > 0
    assert res["opportunities"][0]["action_plan"]


def test_scoring_fields():
    scores = oe._score_opportunity(traffic=70, difficulty=30, gain=65, effort=25)
    for key in ("traffic_score", "difficulty_score", "authority_requirement", "estimated_gain", "implementation_effort", "opportunity_score"):
        assert key in scores
    assert scores["opportunity_score"] >= 50


def test_quick_wins(monkeypatch):
    high = oe._make_opp("keyword", "High", source="t", scores=oe._score_opportunity(traffic=90, difficulty=15, gain=85, effort=20))
    state = oe._load_state()
    state["analyses"]["latest"] = {"opportunities": [high]}
    oe._save_state(state)
    qw = oe.quick_wins()
    assert qw["success"] is True
    assert qw["counts"]["quick_wins"] >= 1


def test_one_click_plan_no_auto_apply(monkeypatch):
    sample = oe._make_opp("faq", "FAQ gap", source="qie", scores=oe._score_opportunity(traffic=60, difficulty=25, gain=70, effort=30))
    monkeypatch.setattr(oe, "analyze_project", lambda pid, **k: {
        "success": True,
        "opportunities": [sample],
        "opportunity_count": 1,
    })
    monkeypatch.setattr("app.moduller.hive_brain_engine.hive_brain.record_decision", lambda *a, **k: {"success": True})
    res = oe.generate_one_click_plan("p1")
    assert res["success"] is True
    assert "plan" in res
    assert res["plan"]["note"]
    assert "otomatik uygulama yapılmadı" in res["plan"]["note"].lower()
    assert res["plan"]["action_groups"]


def test_export_report(tmp_path):
    res = oe.export_report("", "overview")
    assert res["success"] is True
    assert res["path"]
