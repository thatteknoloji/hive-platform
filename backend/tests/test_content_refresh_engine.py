"""Content Refresh Engine — gerçek dosya ve entegrasyon testleri."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.moduller import astro_factory as af
from app.moduller import content_refresh_engine as cre


def _write_project(gen_dir: Path, slug: str, pages: dict, faqs: list | None = None):
    root = gen_dir / slug
    data = root / "src" / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    (data / "faqs.json").write_text(json.dumps(faqs or [], ensure_ascii=False), encoding="utf-8")
    (data / "blog.json").write_text("[]", encoding="utf-8")
    return root


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    gen_dir = tmp_path / "generated-sites"
    gen_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    af_state = tmp_path / "astro_factory_state.json"
    cre_state = tmp_path / "content_refresh_engine_state.json"
    gate_state = tmp_path / "seo_quality_gate_state.json"

    monkeypatch.setattr(af, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(af, "STATE_FILE", af_state)
    monkeypatch.setattr(cre, "STATE_FILE", cre_state)
    monkeypatch.setattr(cre, "REPORTS_DIR", reports_dir)

    af_state.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    cre_state.write_text(json.dumps({
        "settings": dict(cre.DEFAULT_SETTINGS),
        "candidates": {},
        "plans": {},
        "queue": [],
        "jobs": {},
        "running_job": "",
    }), encoding="utf-8")
    gate_state.write_text(json.dumps({"reports": {}}), encoding="utf-8")
    yield {"gen_dir": gen_dir, "reports_dir": reports_dir, "af_state": af_state, "cre_state": cre_state}


def _register_project(gen_dir, slug="refresh-site", project_id="cre-proj-1"):
    created = af.create_project({
        "site_name": "Refresh Test Site",
        "slug": slug,
        "domain": "https://refresh.example.com",
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
    return project_id, slug


def _sample_pages():
    return {
        "seed_keyword": "kuşadası gece hayatı",
        "home": {
            "title": "Kuşadası Gece Hayatı Rehberi",
            "content_html": "<h1>Kuşadası Gece Hayatı</h1><p>2024 özet rehber.</p>",
            "updated_at": "2024-01-01 00:00:00 UTC",
        },
        "geo": [],
    }


def _high_decay_signals():
    return {
        **cre.DEFAULT_SIGNALS,
        "refresh_priority": 92,
        "ranking_decay_score": 50,
        "ctr_decay_score": 30,
        "entity_loss_score": 30,
        "citation_loss_score": 25,
        "ai_visibility_loss_score": 25,
        "refresh_needed": True,
        "priority_label": "CRITICAL",
    }


def _mock_contexts(monkeypatch):
    monkeypatch.setattr(cre, "_entity_graph_summary", lambda pid: {
        "orphan_entities": ["Ex Club"],
        "missing_pages": ["kuşadası beach club"],
        "pillar_pages": ["Kuşadası Gece Hayatı"],
        "cluster_pages": ["faq-1"],
    })
    monkeypatch.setattr(cre, "_qie_gaps_for_keyword", lambda kw: {
        "question_gap_score": 35,
        "paa_gap_score": 30,
        "autocomplete_gap_score": 25,
    })
    monkeypatch.setattr(cre, "_rank_context", lambda pid: {
        "keywords": {"kuşadası gece hayatı": {
            "ranking_decay_score": 50,
            "trend_direction": "decaying",
            "last_position": 12,
            "keyword_strength_score": 40,
        }},
        "performance": {"ctr": 0.01},
        "ctr_drop": 0.03,
    })
    monkeypatch.setattr(cre, "_entity_context", lambda pid: {
        "entity_strength_score": 40,
        "missing_pages": ["/faq-1"],
    })
    monkeypatch.setattr(cre, "_gate_context", lambda pid: {
        "overall_score": 70,
        "citation_score": 60,
        "llm_visibility_score": 50,
        "authority_score": 65,
        "pages": [{"slug": "home", "score": 70, "citation_score": 60, "llm_visibility_score": 50}],
    })


@pytest.fixture
def project_setup(isolated_env, monkeypatch):
    pid, slug = _register_project(isolated_env["gen_dir"])
    _write_project(isolated_env["gen_dir"], slug, _sample_pages(), faqs=[
        {"slug": "faq-1", "title": "Kuşadası gece hayatı nedir?", "content_html": "<p>Eski cevap</p>",
         "keyword": "kuşadası gece hayatı", "updated_at": "2024-01-01 00:00:00 UTC"},
    ])
    _mock_contexts(monkeypatch)
    cre.update_settings({"priority_threshold": 40})
    return pid, slug


def test_health(isolated_env):
    h = cre.health()
    assert h["success"] is True
    assert h["settings"]["enabled"] is False
    assert "dashboard" in h


def test_scan(project_setup):
    pid, _ = project_setup
    res = cre.scan(pid)
    assert res["success"] is True
    assert res["pages_scanned"] >= 1
    assert any(c.get("refresh_needed") for c in res["candidates"])
    assert "refresh_priority" in res["candidates"][0]


def _high_decay_page_id(scan_res):
    cand = next(
        (c for c in scan_res["candidates"] if c.get("ranking_decay_score", 0) >= 30),
        scan_res["candidates"][0],
    )
    return cand["page_id"]


def test_analyze_page(project_setup):
    pid, _ = project_setup
    scan = cre.scan(pid)
    page_id = _high_decay_page_id(scan)
    res = cre.analyze_page(pid, page_id)
    assert res["success"] is True
    assert "signals" in res
    assert "questions" in res
    assert res["questions"]["ranking_loss"] is True


def test_refresh_plan(project_setup):
    pid, _ = project_setup
    res = cre.create_refresh_plan(pid)
    assert res["success"] is True
    assert res["count"] >= 1
    plan = res["plans"][0]
    assert plan["actions"]
    assert plan["priority"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def test_queue(project_setup):
    pid, _ = project_setup
    cre.create_refresh_plan(pid)
    res = cre.queue_pages(pid)
    assert res["success"] is True
    assert res["queued"] >= 1
    q = cre.get_queue()
    assert q["count"] >= 1
    item = q["queue"][0]
    assert item["status"] == "queued"
    assert item["priority"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def test_process_and_refresh_page(project_setup, monkeypatch, isolated_env):
    pid, slug = project_setup
    good_html = "<h1>Kuşadası Gece Hayatı</h1><p>2026 güncel rehber.</p>" * 20

    monkeypatch.setattr(
        "app.moduller.llm_router.generate",
        lambda *a, **k: (good_html, "test_llm"),
    )
    monkeypatch.setattr(cre, "_quality_check", lambda page, html: {
        "passed": True, "score": 90, "analysis": {"overall_score": 90, "pass": True},
    })

    cre.queue_pages(pid)
    proc = cre.process_queue(pid, auto_publish=False)
    assert proc["success"] is True
    assert proc["summary"]["pages_refreshed"] >= 1

    pages_path = isolated_env["gen_dir"] / slug / "src" / "data" / "pages.json"
    data = json.loads(pages_path.read_text(encoding="utf-8"))
    assert "2026" in data["home"]["content_html"]


def test_quality_gate_fail(project_setup, monkeypatch):
    pid, _ = project_setup
    cre.queue_pages(pid)
    page_id = cre.get_queue()["queue"][0]["page_id"]

    calls = {"n": 0}

    def gate(page, html):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"passed": True, "score": 88, "analysis": {"overall_score": 88, "pass": True}}
        return {"passed": False, "score": 60, "analysis": {"overall_score": 60, "pass": False}}

    monkeypatch.setattr(cre, "_quality_check", gate)
    monkeypatch.setattr("app.moduller.llm_router.generate", lambda *a, **k: ("<p>zayıf</p>", "test"))

    res = cre.refresh_page(pid, page_id, auto_publish=False)
    assert res["success"] is False
    assert "Quality Gate fail" in res["error"]


def test_auto_publisher_hook(project_setup, monkeypatch):
    pid, _ = project_setup
    page_id = cre.scan(pid)["candidates"][0]["page_id"]
    published = {}

    def fake_queue(project_id, items, **kw):
        published["items"] = items
        return {"success": True, "queued": len(items)}

    monkeypatch.setattr("app.moduller.astro_auto_publisher.queue_missing", fake_queue)
    monkeypatch.setattr("app.moduller.astro_auto_publisher.process_queue", lambda *a, **k: {"success": True, "built": True})
    monkeypatch.setattr(cre, "_quality_check", lambda p, h: {"passed": True, "score": 91, "analysis": {}})
    monkeypatch.setattr("app.moduller.llm_router.generate", lambda *a, **k: ("<h1>Güncel</h1>" * 30, "llm"))

    res = cre.refresh_page(pid, page_id, auto_publish=True, auto_deploy=False)
    assert res["success"] is True
    assert published["items"][0]["source"] == "content_refresh_engine"


def test_rank_watcher_comparison(project_setup, monkeypatch):
    pid, _ = project_setup
    page_id = _high_decay_page_id(cre.scan(pid))
    monkeypatch.setattr(cre, "_quality_check", lambda p, h: {"passed": True, "score": 90, "analysis": {}})
    monkeypatch.setattr("app.moduller.llm_router.generate", lambda *a, **k: ("<h1>Güncel</h1>" * 30, "llm"))

    res = cre.refresh_page(pid, page_id, auto_publish=False)
    assert res["success"] is True
    cmp = res["comparison"]
    assert "before" in cmp and "after" in cmp
    assert "improvement_score" in cmp
    assert cmp["before"]["rank"]["decay_score"] == 50


def test_entity_graph_update(project_setup, monkeypatch):
    pid, _ = project_setup
    page_id = cre.scan(pid)["candidates"][0]["page_id"]
    called = {}

    def fake_build(project_id):
        called["project_id"] = project_id
        return {"success": True}

    monkeypatch.setattr("app.moduller.entity_geo_graph.build_project_graph", fake_build)
    monkeypatch.setattr(cre, "_quality_check", lambda p, h: {"passed": True, "score": 90, "analysis": {}})
    monkeypatch.setattr("app.moduller.llm_router.generate", lambda *a, **k: ("<h1>Güncel</h1>" * 30, "llm"))

    cre.refresh_page(pid, page_id, auto_publish=False)
    assert called["project_id"] == pid


def test_network_replicator_update(project_setup, monkeypatch):
    pid, _ = project_setup
    page_id = cre.scan(pid)["candidates"][0]["page_id"]
    monkeypatch.setattr(cre, "_quality_check", lambda p, h: {"passed": True, "score": 90, "analysis": {}})
    monkeypatch.setattr("app.moduller.llm_router.generate", lambda *a, **k: ("<h1>Güncel</h1>" * 30, "llm"))
    monkeypatch.setattr(
        "app.moduller.network_replicator.list_networks",
        lambda: {"networks": [{
            "network_id": "net-1",
            "domains": [
                {"project_id": pid, "domain": "main.example.com"},
                {"project_id": "cre-proj-2", "domain": "variant.example.com"},
            ],
        }]},
    )
    queued = []

    def fake_queue_pages(project_id, page_ids=None):
        queued.append(project_id)
        return {"success": True, "queued": 1}

    monkeypatch.setattr(cre, "queue_pages", fake_queue_pages)

    res = cre.refresh_page(pid, page_id, auto_publish=False)
    assert res["success"] is True
    assert "cre-proj-2" in queued


def test_analyze_project(project_setup):
    pid, _ = project_setup
    res = cre.analyze_project(pid)
    assert res["success"] is True
    assert res["pages_scanned"] >= 1
    assert "page_analyses" in res
    assert res["refresh_needed_count"] >= 1


def test_entity_refresh_analysis(project_setup):
    pid, _ = project_setup
    scan = cre.scan(pid)
    page_id = _high_decay_page_id(scan)
    res = cre.analyze_page(pid, page_id)
    assert res["success"] is True
    assert "entity_refresh" in res
    assert res["entity_refresh"].get("expansion_recommended") is True


def test_geo_refresh_analysis(project_setup):
    pid, _ = project_setup
    scan = cre.scan(pid)
    page_id = _high_decay_page_id(scan)
    res = cre.analyze_page(pid, page_id)
    assert res["success"] is True
    assert len(res.get("geo_opportunities") or []) >= 1


def test_qie_integration_on_refresh(project_setup, monkeypatch):
    pid, _ = project_setup
    page_id = _high_decay_page_id(cre.scan(pid))
    monkeypatch.setattr(cre, "_quality_check", lambda p, h: {"passed": True, "score": 90, "analysis": {}})
    monkeypatch.setattr("app.moduller.llm_router.generate", lambda *a, **k: ("<h1>Güncel</h1>" * 30, "llm"))
    monkeypatch.setattr(cre, "_inject_qie_blocks", lambda page, actions, project: '<section class="paa">PAA block</section>')
    monkeypatch.setattr(cre, "_inject_ai_overview", lambda html, kw, loc: html + '<div class="ai-overview">overview</div>')

    st = json.loads(cre.STATE_FILE.read_text(encoding="utf-8"))
    st["queue"] = [{
        "queue_id": "crq-test",
        "project_id": pid,
        "page_id": page_id,
        "priority": "CRITICAL",
        "actions": ["add_paa_questions", "add_ai_overview_block"],
        "status": "queued",
    }]
    cre.STATE_FILE.write_text(json.dumps(st), encoding="utf-8")

    res = cre.refresh_page(pid, page_id, auto_publish=False)
    assert res["success"] is True
    assert res.get("qie_integrated") is True


def test_export_report(project_setup):
    pid, _ = project_setup
    cre.scan(pid)
    res = cre.export_report(project_id=pid)
    assert res["success"] is True
    assert Path(res["path"]).is_file()

    st = json.loads(cre.STATE_FILE.read_text(encoding="utf-8"))
    job_id = "cre-test-job-1"
    st["jobs"][job_id] = {
        "job_id": job_id,
        "type": "process",
        "project_id": pid,
        "status": "completed",
        "summary": {"pages_refreshed": 1, "quality_passed": 1},
    }
    cre.STATE_FILE.write_text(json.dumps(st), encoding="utf-8")
    job_res = cre.export_report(job_id=job_id)
    assert job_res["success"] is True
