"""Entity Detail Page Generator testleri — Listing Hub'a ilan oluşturulmaz."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.moduller import entity_detail_generator as edg


SAMPLE_PLACE_JOB = {
    "id": "ps-job-1",
    "main_site_url": "https://www.balkutusu.com",
    "signals": {
        "entities": ["Ex Club", "Jimmy's Irish Bar", "Mezgit Restaurant", "Small Cafe X"],
        "categories": ["bar", "gece hayatı", "restoran"],
        "locations": ["Kuşadası", "Barlar Sokağı", "Marina"],
    },
    "parse": {
        "raw_text": """
        Kuşadası gece hayatı sektör analizi. Ex Club Barlar Sokağı'nda öne çıkan mekan.
        Website: https://exclub.example.com Instagram: instagram.com/exclub
        Adres: Barlar Sokağı No:12 Kuşadası
        Jimmy's Irish Bar Marina yakını canlı müzik pub.
        Mezgit Restaurant Kadınlar Denizi restoran deneyimi.
        Small Cafe X sadece isim geçiyor.
        """,
        "paragraphs": [],
        "headings": [],
        "tables": [],
    },
}


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "entity_detail_generator_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    state.write_text(json.dumps({"jobs": {}}), encoding="utf-8")
    monkeypatch.setattr(edg, "STATE_FILE", state)
    monkeypatch.setattr(edg, "REPORTS_DIR", reports)
    yield {"state": state, "reports": reports}


def _mock_place_job(monkeypatch):
    monkeypatch.setattr(
        edg, "_load_place_seo_job",
        lambda jid: dict(SAMPLE_PLACE_JOB) if jid == "ps-job-1" else None,
    )


def test_health(isolated_env):
    h = edg.health()
    assert h["success"] is True
    assert h["listing_hub_integration"] is False
    assert h["tier1_threshold"] == 70


def test_tier1_scoring(isolated_env):
    ent = edg._enrich_entity("Ex Club", SAMPLE_PLACE_JOB["parse"]["raw_text"], SAMPLE_PLACE_JOB["signals"])
    score = edg.score_tier1(ent, SAMPLE_PLACE_JOB["signals"])
    assert 0 <= score <= 100
    assert score >= 50
    assert ent.get("website")
    assert ent.get("instagram")
    assert ent.get("address")


def test_low_score_entity_not_auto_selected(isolated_env, monkeypatch):
    _mock_place_job(monkeypatch)
    result = edg.select_tier1("ps-job-1", threshold=95)
    assert result["success"] is True
    low = [e for e in result["entities"] if e["name"] == "Small Cafe X"][0]
    assert low["tier1_score"] < 95
    assert low["tier1_selected"] is False


def test_manual_override(isolated_env, monkeypatch):
    _mock_place_job(monkeypatch)
    sel = edg.select_tier1("ps-job-1", threshold=70)
    low_id = [e for e in sel["entities"] if e["name"] == "Small Cafe X"][0]["id"]
    upd = edg.update_manual_selection(sel["job_id"], {low_id: True})
    assert upd["success"] is True
    forced = [e for e in upd["entities"] if e["id"] == low_id][0]
    assert forced["tier1_selected"] is True
    assert forced["manual_override"] is True


def test_select_tier1_creates_job(isolated_env, monkeypatch):
    _mock_place_job(monkeypatch)
    result = edg.select_tier1("ps-job-1", threshold=70)
    assert result["success"] is True
    assert result["entity_count"] == 4
    assert result["tier1_selected"] >= 1
    assert result["listing_hub_called"] is False


@patch("app.moduller.page_hub.create_page")
@patch("app.moduller.entity_detail_generator._llm_generate_entity_content")
@patch("app.moduller.wordpress_api.wp_api")
@patch("app.moduller.rank_index_watcher.track_keyword")
def test_page_generation_payload(mock_track, mock_wp_api, mock_llm, mock_create, isolated_env, monkeypatch):
    _mock_place_job(monkeypatch)
    mock_wp = MagicMock()
    mock_wp.connected = True
    mock_wp_api.return_value = mock_wp
    mock_track.return_value = {"success": True}
    mock_create.return_value = {"success": True, "page": {"id": 1, "link": "https://www.balkutusu.com/rehber/ex-club-kusadasi/"}}
    mock_llm.return_value = (
        "<h2>Test</h2><p>" + " kelime " * 1300 + "</p>",
        [{"q": "Q?", "a": "A."}],
    )

    sel = edg.select_tier1("ps-job-1", threshold=70)
    jid = sel["job_id"]
    for e in sel["entities"]:
        if e["name"] == "Ex Club":
            e["tier1_selected"] = True
    edg._update_job(jid, entities=sel["entities"])

    result = edg.generate_pages(jid, publish_wordpress=True)
    assert result["success"] is True
    assert result["generated_count"] >= 1
    assert result["listing_hub_called"] is False
    mock_create.assert_called()
    call_kw = mock_create.call_args.kwargs
    assert "rehber/" in call_kw.get("slug", mock_create.call_args[0][2] if len(mock_create.call_args[0]) > 2 else "")


def test_no_listing_hub_call(isolated_env, monkeypatch):
    _mock_place_job(monkeypatch)
    with patch("app.moduller.listing_hub.create_listing") as mock_create:
        result = edg.select_tier1("ps-job-1")
        mock_create.assert_not_called()
    assert result["listing_hub_called"] is False


def test_default_video(isolated_env):
    watch, embed = edg._video_embed("")
    assert watch
    assert embed
    assert "youtube" in embed or "youtu" in watch


def test_map_fallback_with_address(isolated_env):
    url = edg._build_map_embed("Ex Club", "Barlar Sokağı No:12")
    assert url
    assert "maps" in url or "openstreetmap" in url


def test_map_fallback_name_only(isolated_env):
    url = edg._build_map_embed("Ex Club", "")
    assert url
    assert "Ex" in url or "kusadasi" in url.lower() or "maps" in url


def test_schema_generation(isolated_env):
    ent = {"name": "Ex Club", "slug": "rehber/ex-club-kusadasi", "category": "bar", "address": "Barlar Sokağı"}
    faq = [{"q": "Nerede?", "a": "Kuşadası."}]
    schemas = edg._build_schemas(ent, "https://www.balkutusu.com", faq)
    assert schemas["article"]["@type"] == "Article"
    assert schemas["faq"]["@type"] == "FAQPage"
    assert schemas["breadcrumb"]["@type"] == "BreadcrumbList"
    assert schemas["place"]["@type"] in ("BarOrPub", "LocalBusiness", "Place")


@patch("app.moduller.seo_quality_gate.seo_quality_gate.analyze_page")
def test_quality_gate_hook(mock_analyze, isolated_env, monkeypatch):
    _mock_place_job(monkeypatch)
    mock_analyze.return_value = {"seo_score": 85, "overall_score": 82, "pass": True}
    sel = edg.select_tier1("ps-job-1", threshold=70)
    jid = sel["job_id"]
    ent = sel["entities"][0]
    ent["tier1_selected"] = True
    ent["page"] = {"html": "<h1>Test</h1><p>" + "x " * 500 + "</p>"}
    edg._update_job(jid, entities=sel["entities"])

    gate = edg.run_quality_gate(jid)
    assert gate["success"] is True
    assert gate["deploy_allowed"] is True
    mock_analyze.assert_called()


@patch("app.moduller.astro_factory.generate_pages")
@patch("app.moduller.astro_factory._project_path")
@patch("app.moduller.astro_factory._get_project")
def test_astro_payload(mock_get, mock_path, mock_gen, isolated_env, monkeypatch, tmp_path):
    _mock_place_job(monkeypatch)
    mock_get.return_value = {"id": "astro1", "slug": "kusadasi-rehber"}
    mock_path.return_value = tmp_path / "site"
    mock_gen.return_value = {"success": True, "files_written": ["pages.json"]}

    sel = edg.select_tier1("ps-job-1", threshold=70)
    jid = sel["job_id"]
    for e in sel["entities"][:2]:
        e["tier1_selected"] = True
        e["page"] = {"html": "<h1>Test</h1>", "schemas": {"article": {}}}
    edg._update_job(jid, entities=sel["entities"], astro_project_id="astro1")

    res = edg.create_astro_pages(jid, project_id="astro1")
    assert res["success"] is True
    assert res["entity_pages_written"] == 2
    data_file = tmp_path / "site" / "src" / "data" / "entity_pages.json"
    assert data_file.exists()
    data = json.loads(data_file.read_text())
    assert len(data) == 2
    assert data[0].get("entity_name")


def test_export_report(isolated_env, monkeypatch):
    _mock_place_job(monkeypatch)
    sel = edg.select_tier1("ps-job-1")
    rep = edg.export_report(sel["job_id"])
    assert rep["success"] is True
    assert rep["report"]["listing_hub_called"] is False
    assert rep["report"]["entity_count"] == 4
