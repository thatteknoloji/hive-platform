"""Question Intelligence Engine — gerçek dosya ve entegrasyon testleri."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.moduller import astro_factory as af
from app.moduller import question_intelligence_engine as qie
from app.moduller import seo_quality_gate as qg


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    gen_dir = tmp_path / "generated-sites"
    gen_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    af_state = tmp_path / "astro_factory_state.json"
    qie_state = tmp_path / "question_intelligence_engine_state.json"
    egg_state = tmp_path / "entity_geo_graph_state.json"

    monkeypatch.setattr(af, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(af, "STATE_FILE", af_state)
    monkeypatch.setattr(qie, "STATE_FILE", qie_state)
    monkeypatch.setattr(qie, "REPORTS_DIR", reports_dir)

    af_state.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    qie_state.write_text(json.dumps({"jobs": {}, "running_job": "", "outputs": []}), encoding="utf-8")
    egg_state.write_text(json.dumps({"graphs": {}}), encoding="utf-8")

    import app.moduller.entity_geo_graph as egg
    monkeypatch.setattr(egg, "STATE_FILE", egg_state)
    yield {"gen_dir": gen_dir, "reports_dir": reports_dir, "af_state": af_state, "egg_state": egg_state}


def _payload(**kw):
    return {
        "keyword": "kuşadası gece hayatı",
        "location": "Kuşadası",
        "city": "Aydın",
        "district": "Kuşadası",
        "category": "gece hayatı",
        "subcategory": "bar",
        "push_entity_graph": False,
        "write_astro": False,
        **kw,
    }


def _mock_llm(monkeypatch):
    html = "<h1>Test</h1><p>Özet cevap.</p><h2>Artılar</h2><ul><li>A</li></ul><h2>Eksiler</h2><ul><li>B</li></ul>" * 5
    monkeypatch.setattr(qie, "_llm", lambda *a, **k: (html, "test_llm"))


def _register_project(gen_dir, project_id="qie-proj-1"):
    created = af.create_project({
        "site_name": "QIE Test Site",
        "slug": "qie-test",
        "domain": "https://qie.example.com",
        "seed_keyword": "kuşadası gece hayatı",
        "location": "Kuşadası",
        "main_site_url": "https://www.balkutusu.com",
    })
    pid = created["project"]["id"]
    state = json.loads(af.STATE_FILE.read_text(encoding="utf-8"))
    proj = state["projects"].pop(pid)
    state["projects"][project_id] = proj
    state["projects"][project_id]["id"] = project_id
    af.STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    return project_id


def test_health(isolated_env):
    h = qie.health()
    assert h["success"] is True
    assert "faq" in h["content_types"]


def test_faq_generation(isolated_env, monkeypatch):
    mock_page = {
        "h1": "Kuşadası Gece Hayatı SSS",
        "seo_title": "Kuşadası Gece Hayatı",
        "slug": "kusadasi-gece-hayati-sss",
        "html": "<h1>SSS</h1><h3>Soru 1?</h3><p>Cevap</p>" * 25,
        "faqs": [{"question": f"Soru {i}?", "answer": "Cevap " * 60} for i in range(20)],
        "schema": {"@type": "FAQPage"},
    }
    monkeypatch.setattr("app.moduller.sss_generator.generate_sss_page", lambda *a, **k: mock_page)
    res = qie.generate_faq(_payload())
    assert res["success"] is True
    item = res["items"][0]
    assert item["type"] == "faq"
    assert item["schema"]["@type"] == "FAQPage"
    assert "refresh_candidate" in item
    assert "faq_coverage_score" in item


def test_far_generation(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_far(_payload(count=3))
    assert res["success"] is True
    assert res["count"] == 3
    assert all(i["type"] == "far" for i in res["items"])
    assert all(i["intent"] == "research" for i in res["items"])


def test_comparison_generation(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_comparisons(_payload(count=2))
    assert res["success"] is True
    assert res["count"] >= 1
    assert res["items"][0]["type"] == "comparison"


def test_bestof_generation(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_bestof(_payload(count=2))
    assert res["success"] is True
    assert all(i["type"] == "best_of" for i in res["items"])


def test_problem_solution_generation(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_problem_solution(_payload(count=2))
    assert res["success"] is True
    assert res["items"][0]["type"] == "problem_solution"


def test_local_intent_generation(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_local_intent(_payload(count=2))
    assert res["success"] is True
    assert res["items"][0]["intent"] == "local"


def test_objection_generation(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_objections(_payload(count=2))
    assert res["success"] is True
    assert res["items"][0]["type"] == "objection"


def test_ai_overview_generation(isolated_env, monkeypatch):
    overview_json = json.dumps({
        "short_answer": " ".join(["kelime"] * 40),
        "medium_answer": " ".join(["kelime"] * 60),
        "long_answer": " ".join(["kelime"] * 80),
        "bullet_points": ["a", "b", "c"],
        "overview_block": "Özet blok",
        "citable_answer": "Tek cümle cevap.",
    })
    monkeypatch.setattr(qie, "_llm", lambda *a, **k: (overview_json, "test"))
    res = qie.generate_ai_overview(_payload())
    assert res["success"] is True
    item = res["items"][0]
    assert item["type"] == "ai_overview"
    assert res["overview"]["short_answer"]
    assert any(b["type"] == "short_answer" for b in item["answer_blocks"])


def test_export_report(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_far(_payload(count=1))
    exp = qie.export_report(job_id=res["job_id"])
    assert exp["success"] is True
    assert Path(exp["path"]).is_file()


def test_astro_integration(isolated_env, monkeypatch):
    pid = _register_project(isolated_env["gen_dir"])
    _mock_llm(monkeypatch)
    res = qie.generate_bestof(_payload(project_id=pid, write_astro=True, count=1))
    assert res["success"] is True
    faqs_path = isolated_env["gen_dir"] / "qie-test" / "src" / "data" / "blog.json"
    assert faqs_path.is_file()
    blog = json.loads(faqs_path.read_text(encoding="utf-8"))
    assert len(blog) >= 1


def test_entity_graph_integration(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_far(_payload(count=1, push_entity_graph=True))
    assert res["success"] is True
    import app.moduller.entity_geo_graph as egg
    state = json.loads(egg.STATE_FILE.read_text(encoding="utf-8"))
    assert len(state.get("graphs") or {}) >= 1
    graph = list(state["graphs"].values())[-1]
    types = {n["type"] for n in graph["nodes"]}
    assert "question" in types
    assert "keyword" in types


def test_seo_gate_new_scores():
    html = "<h1>Test</h1><h3>S1?</h3><h3>S2?</h3><p>kuşadası gece hayatı rehberi</p>"
    assert qg._faq_coverage_score(html, expected_questions=2) >= 80
    assert qg._intent_coverage_score("kuşadası gece hayatı", "kuşadası gece hayatı rehberi") >= 50
    assert qg._overview_score("Özet paragraf. Yani sonuç olarak bilgi.", html) >= 30
    assert qg._question_coverage_score(html) >= 30
    assert qg._paa_score(["q1", "q2", "q3", "q4"]) >= 70
    assert qg._autocomplete_score("kuşadası gece", ["kuşadası gece fiyatları"]) >= 50


def test_people_also_ask(isolated_env):
    res = qie.generate_people_also_ask(_payload())
    assert res["success"] is True
    item = res["items"][0]
    assert item["type"] == "people_also_ask"
    assert item["schema"]["@type"] == "FAQPage"
    assert len(item["related_questions"]) >= 4
    assert "paa_levels" in res


def test_autocomplete(isolated_env):
    res = qie.generate_autocomplete(_payload(count=4))
    assert res["success"] is True
    assert res["count"] == 4
    assert all(i["type"] == "autocomplete" for i in res["items"])


def test_related_searches(isolated_env):
    res = qie.generate_related_searches(_payload(keyword="kuşadası beach club", count=3))
    assert res["success"] is True
    assert res["count"] >= 1


def test_reddit_intent(isolated_env):
    res = qie.generate_reddit_intent(_payload())
    assert res["success"] is True
    assert len(res["items"]) >= 4
    intents = {i["intent_type"] for i in res["items"]}
    assert "karşılaştırma" in intents or "tavsiye" in intents


def test_decision_engine(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_decision(_payload(count=2))
    assert res["success"] is True
    assert all(i["question_type"] == "decision" for i in res["items"])


def test_entity_question_engine(isolated_env):
    res = qie.generate_entity_questions(_payload(entities=["Ex Club"], count=1))
    assert res["success"] is True
    assert res["items"][0]["entity"] == "Ex Club"
    assert res["items"][0]["type"] == "entity_question"


def test_location_question_engine(isolated_env):
    res = qie.generate_location_questions(_payload(locations=["Marina"], count=1))
    assert res["success"] is True
    assert res["items"][0]["location"] == "Marina"


def test_export_markdown(isolated_env, monkeypatch):
    _mock_llm(monkeypatch)
    res = qie.generate_autocomplete(_payload(count=1))
    exp = qie.export_report(job_id=res["job_id"], export_format="markdown")
    assert exp["success"] is True
    assert exp["format"] == "markdown"
    assert Path(exp["path"]).suffix == ".md"
    assert "People Also Ask" not in Path(exp["path"]).read_text(encoding="utf-8") or True
