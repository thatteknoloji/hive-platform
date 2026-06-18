"""Mekan SEO Content Pipeline testleri — Listing Hub'a ilan oluşturulmaz."""

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from app.moduller import place_seo_pipeline as psp


def _minimal_docx(text: str) -> bytes:
    doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{psp.W_NS}">
  <w:body>
    <w:p><w:r><w:t>{text}</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Kuşadası Gece Hayatı</w:t></w:r></w:p>
    <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Ex Club</w:t></w:r></w:p></w:tc>
    <w:tc><w:p><w:r><w:t>Barlar Sokağı</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
  </w:body>
</w:document>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", doc_xml)
    return buf.getvalue()


SAMPLE_TEXT = """
Kuşadası gece hayatı rehberi. Ex Club, Jimmy's Irish Bar, Barlar Sokağı.
Kadınlar Denizi beach club deneyimi. Marina restoranları ve kafe kültürü.
Kuşadası gece hayatı nerede? Canlı müzik ve pub kültürü.
"""


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "place_seo_pipeline_state.json"
    uploads = tmp_path / "uploads" / "place-seo"
    reports = tmp_path / "reports"
    uploads.mkdir(parents=True)
    reports.mkdir()
    state.write_text(json.dumps({"jobs": {}, "uploads": {}}), encoding="utf-8")
    monkeypatch.setattr(psp, "STATE_FILE", state)
    monkeypatch.setattr(psp, "UPLOAD_DIR", uploads)
    monkeypatch.setattr(psp, "REPORTS_DIR", reports)
    yield {"state": state, "uploads": uploads, "reports": reports}


def test_health(isolated_env):
    h = psp.health()
    assert h["success"] is True
    assert h["listing_hub_integration"] is False


def test_docx_parse(isolated_env):
    parsed = psp.parse_docx(_minimal_docx(SAMPLE_TEXT))
    assert parsed["format"] == "docx"
    assert len(parsed["paragraphs"]) >= 1
    assert len(parsed["headings"]) >= 1
    assert len(parsed["tables"]) >= 1
    assert "Ex Club" in parsed["raw_text"]


def test_signal_extraction(isolated_env):
    parsed = psp.parse_txt(SAMPLE_TEXT)
    signals = psp.extract_signals(parsed, source_files=["test.txt"])
    assert signals["confidence"] > 0
    assert "kuşadası" in [l.lower() for l in signals["locations"]] or "Kuşadası" in signals["locations"]
    assert any("gece" in c for c in signals["categories"])
    assert len(signals["entities"]) >= 1
    assert len(signals["faq_candidates"]) >= 1


def test_normalize_signals():
    out = psp.normalize_signals({"categories": ["bar", "bar"], "confidence": 150})
    assert out["categories"] == ["bar"]
    assert out["confidence"] == 100


def test_category_page_plan(isolated_env):
    signals = psp.extract_signals(psp.parse_txt(SAMPLE_TEXT))
    plan = psp.generate_content_plan(signals, "https://www.balkutusu.com", job_id="j1")
    assert plan["success"] is True
    assert len(plan["plan"]["category_pages"]) >= 5
    assert plan["plan"]["summary"]["listing_hub_called"] is False


def test_geo_page_plan(isolated_env):
    signals = psp.extract_signals(psp.parse_txt(SAMPLE_TEXT))
    plan = psp.generate_content_plan(signals, "https://www.balkutusu.com")["plan"]
    assert len(plan["geo_pages"]) >= 1
    assert all("Kuşadası" in p["title"] or "kuşadası" in p["title"].lower() for p in plan["geo_pages"][:3])


def test_faq_plan(isolated_env):
    signals = psp.extract_signals(psp.parse_txt(SAMPLE_TEXT))
    plan = psp.generate_content_plan(signals, "https://www.balkutusu.com")["plan"]
    assert len(plan["faq_pages"]) >= 1


def test_link_policy_exact_anchor_forbidden(isolated_env):
    signals = psp.extract_signals(psp.parse_txt(SAMPLE_TEXT))
    plan = psp.generate_content_plan(signals, "https://www.balkutusu.com")["plan"]
    anchors = []
    for entry in plan["main_site_link_plan"]:
        for lk in entry["links"]:
            anchors.append(lk["anchor"].lower())
    assert len(anchors) == len(set(anchors))


def test_no_listing_created(isolated_env):
    """Pipeline Listing Hub create_listing çağırmamalı."""
    with patch("app.moduller.listing_hub.create_listing") as mock_create:
        mock_create.return_value = {"success": True}
        up = psp.upload_file("test.txt", SAMPLE_TEXT.encode())
        parsed = psp.parse_upload(upload_id=up["upload_id"])
        psp.extract_signals_for_job(parsed["job_id"])
        psp.generate_plan(parsed["job_id"], "https://www.balkutusu.com")
        psp.create_category_pages(parsed["job_id"], dry_run=True)
        psp.create_geo_pages(parsed["job_id"], dry_run=True)
        psp.create_faq_pages(parsed["job_id"], dry_run=True)
        mock_create.assert_not_called()


def test_no_mechanism_calls_listing_hub_module(isolated_env):
    import ast
    src = (psp.__file__ if hasattr(psp, "__file__") else "")
    from pathlib import Path
    code = Path(__file__).resolve().parents[1] / "app" / "moduller" / "place_seo_pipeline.py"
    tree = ast.parse(code.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(a.name for a in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert "app.moduller.listing_hub" not in imports


def test_upload_parse_flow(isolated_env):
    docx = _minimal_docx(SAMPLE_TEXT)
    up = psp.upload_file("kusadasi.docx", docx)
    res = psp.parse_upload(upload_id=up["upload_id"])
    assert res["success"] is True
    assert res["job_id"]
    sig = psp.extract_signals_for_job(res["job_id"])
    assert sig["signals"]["entities"]


def test_page_html_no_listing_table(isolated_env):
    html = psp._build_page_html(
        "Kuşadası Gece Hayatı", "Kuşadası", "gece hayatı",
        ["Ex Club", "Jimmy's Irish Bar"], ["canlı müzik"],
        "https://www.balkutusu.com", [],
    )
    assert "<table" not in html.lower()
    assert "katalog" in html.lower() or "rehber" in html.lower()
    assert "Ex Club" in html


@patch("app.moduller.seo_quality_gate.seo_quality_gate.analyze_page")
def test_quality_gate_hook(mock_analyze, isolated_env):
    mock_analyze.return_value = {"seo_score": 80, "geo_score": 75, "aeo_score": 70, "pass": True}
    up = psp.upload_file("t.txt", SAMPLE_TEXT.encode())
    jid = psp.parse_upload(upload_id=up["upload_id"])["job_id"]
    psp.extract_signals_for_job(jid)
    psp.generate_plan(jid, "https://www.balkutusu.com")
    gate = psp.run_quality_gate(jid)
    assert gate["success"] is True
    assert gate["deploy_allowed"] is True
    mock_analyze.assert_called()


@patch("app.moduller.astro_factory.generate_pages")
@patch("app.moduller.astro_factory.create_project")
@patch("app.moduller.astro_factory.generate_site_plan")
@patch("app.moduller.astro_factory._get_project")
@patch("app.moduller.astro_factory._project_path")
@patch("app.moduller.astro_factory._write_project_data")
@patch("app.moduller.astro_factory._update_project")
def test_astro_support_payload(
    mock_update, mock_write, mock_path, mock_get, mock_plan, mock_create, mock_gen_pages, isolated_env, tmp_path,
):
    mock_create.return_value = {"success": True, "project": {"id": "astro1", "slug": "kusadasi-rehber"}}
    mock_plan.return_value = {"success": True, "plan": {}}
    mock_get.return_value = {"id": "astro1", "slug": "kusadasi-rehber"}
    mock_path.return_value = tmp_path / "site"
    mock_gen_pages.return_value = {"success": True, "files_written": ["index.astro"]}

    up = psp.upload_file("t.txt", SAMPLE_TEXT.encode())
    jid = psp.parse_upload(upload_id=up["upload_id"])["job_id"]
    psp.extract_signals_for_job(jid)
    psp.generate_plan(jid, "https://www.balkutusu.com")
    res = psp.create_astro_support_site(jid)
    assert res["success"] is True
    assert res["listing_hub_called"] is False
    mock_create.assert_called_once()
    mock_write.assert_called_once()
    mock_gen_pages.assert_called_once()


@patch("app.moduller.rank_index_watcher.track_keyword")
@patch("app.moduller.place_seo_pipeline.create_astro_support_site")
@patch("app.moduller.place_seo_pipeline.run_quality_gate")
@patch("app.moduller.place_seo_pipeline.create_faq_pages")
@patch("app.moduller.place_seo_pipeline.create_geo_pages")
@patch("app.moduller.place_seo_pipeline.create_category_pages")
@patch("app.moduller.wordpress_api.wp_api")
def test_publish_all_to_wordpress(mock_wp_api, mock_cat, mock_geo, mock_faq, mock_gate, mock_astro, mock_track, isolated_env):
    mock_wp = MagicMock()
    mock_wp.connected = True
    mock_wp_api.return_value = mock_wp
    mock_track.return_value = {"keyword": "test", "position": 0}

    mock_gate.return_value = {"success": True, "deploy_allowed": True, "quality_gate": {}}
    page_entry = {"title": "T", "slug": "t", "published": True, "link": "https://www.balkutusu.com/t/"}
    mock_cat.return_value = {"success": True, "created": [page_entry], "published_count": 1, "previews": []}
    mock_geo.return_value = {"success": True, "created": [page_entry], "published_count": 1, "previews": []}
    mock_faq.return_value = {"success": True, "created": [page_entry], "published_count": 1, "previews": []}
    mock_astro.return_value = {"success": True, "project_id": "astro1"}

    up = psp.upload_file("t.txt", SAMPLE_TEXT.encode())
    jid = psp.parse_upload(upload_id=up["upload_id"])["job_id"]
    psp.extract_signals_for_job(jid)
    psp.generate_plan(jid, "https://www.balkutusu.com")

    result = psp.publish_all_to_wordpress(jid, "https://www.balkutusu.com", run_gate=True)
    assert result["success"] is True
    assert result["publish_report"]["total_published"] == 3
    assert result["publish_report"]["listing_hub_called"] is False
    mock_cat.assert_called_once()
    mock_geo.assert_called_once()
    mock_faq.assert_called_once()


def test_batch_upload_auto_pipeline(isolated_env):
    files = [
        ("a.txt", SAMPLE_TEXT.encode(), "text/plain"),
        ("b.txt", "Kuşadası marina restoran kafe\nEx Club bar\n".encode(), "text/plain"),
    ]
    result = psp.process_batch_upload(files, main_site_url="https://www.balkutusu.com", auto_pipeline=True)
    assert result["success"] is True
    assert result["file_count"] == 2
    assert result.get("signals")
    assert result.get("plan")
    job = psp.get_job_detail(result["job_id"])["job"]
    assert len(job.get("filenames") or []) == 2


def test_export_report(isolated_env):
    up = psp.upload_file("t.txt", SAMPLE_TEXT.encode())
    jid = psp.parse_upload(upload_id=up["upload_id"])["job_id"]
    psp.extract_signals_for_job(jid)
    psp.generate_plan(jid, "https://www.balkutusu.com")
    rep = psp.export_report(jid)
    assert rep["success"] is True
    assert rep["report"]["listing_hub_records_created"] == 0
