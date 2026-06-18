"""SEO Quality Gate — gerçek dosya analizi testleri."""

import json
from pathlib import Path

import pytest

from app.moduller import astro_factory as af
from app.moduller import seo_quality_gate as qg


def _write_project(gen_dir: Path, slug: str, pages: dict, faqs: list | None = None, blog: list | None = None,
                   robots: str | None = None, sitemap: str | None = None, dist_html: str | None = None):
    root = gen_dir / slug
    data = root / "src" / "data"
    public = root / "public"
    data.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    (data / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    (data / "faqs.json").write_text(json.dumps(faqs or [], ensure_ascii=False), encoding="utf-8")
    (data / "blog.json").write_text(json.dumps(blog or [], ensure_ascii=False), encoding="utf-8")
    if robots is not None:
        (public / "robots.txt").write_text(robots, encoding="utf-8")
    if sitemap is not None:
        (public / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    if dist_html is not None:
        dist = root / "dist"
        dist.mkdir(parents=True)
        (dist / "index.html").write_text(dist_html, encoding="utf-8")
    return root


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    gen_dir = tmp_path / "generated-sites"
    gen_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    af_state = tmp_path / "astro_factory_state.json"
    qg_state = tmp_path / "seo_quality_gate_state.json"

    monkeypatch.setattr(af, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(af, "STATE_FILE", af_state)
    monkeypatch.setattr(qg, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(qg, "STATE_FILE", qg_state)
    monkeypatch.setattr(qg, "REPORTS_DIR", reports_dir)

    af_state.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    qg_state.write_text(json.dumps({"reports": {}}), encoding="utf-8")
    yield {"gen_dir": gen_dir, "reports_dir": reports_dir, "af_state": af_state}


def _register_project(gen_dir, slug="test-site", project_id="proj001"):
    created = af.create_project({
        "site_name": "Test Gate Site",
        "slug": slug,
        "domain": "https://testgate.example.com",
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


def test_health(isolated_env):
    result = qg.health()
    assert result["success"] is True
    assert result["status"] == "ok"
    assert "thresholds" in result


def test_analyze_project_good_score(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    long_html = (
        "<h1>Kuşadası Gece Hayatı Rehberi</h1>"
        "<h2>Gece Hayatı Nedir?</h2>"
        "<p>" + "Kuşadası Aydın bölgesinde gece hayatı rehberi. " * 40 + "</p>"
        '<a href="/blog">Blog</a> <a href="https://www.balkutusu.com">Kaynak</a>'
        '<img alt="Kuşadası gece" src="/img.jpg" />'
    )
    _write_project(
        gen_dir, slug,
        pages={
            "site_name": "Test",
            "domain": "https://testgate.example.com",
            "main_site_url": "https://www.balkutusu.com",
            "home": {
                "title": "Kuşadası Gece Hayatı — Yerel Rehber",
                "description": "Kuşadası gece hayatı hakkında kapsamlı yerel rehber bilgileri ve öneriler.",
                "content_html": long_html,
            },
            "geo": [],
        },
        robots="User-agent: *\nAllow: /\nSitemap: https://testgate.example.com/sitemap.xml",
        sitemap='<?xml version="1.0"?><urlset><url><loc>https://testgate.example.com/</loc></url></urlset>',
        dist_html=(
            "<html><head><title>Test</title>"
            '<link rel="canonical" href="https://testgate.example.com/" />'
            "</head><body><h1>Test</h1></body></html>"
        ),
    )
    result = qg.analyze_project(pid, target_keyword="kuşadası gece hayatı", strict_mode=True)
    assert result["success"] is True
    assert result["overall_score"] >= 65
    assert result["status"] in ("pass", "warning")
    assert result["report_id"]
    assert len(result["pages"]) >= 1


def test_thin_content_detected(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "domain": "https://testgate.example.com",
            "home": {
                "title": "Kısa",
                "description": "Kısa açıklama",
                "content_html": "<h1>Test</h1><p>Kısa.</p>",
            },
            "geo": [],
        },
        robots="Allow: /",
        sitemap="<urlset></urlset>",
    )
    result = qg.analyze_project(pid, strict_mode=True)
    codes = [i["code"] for i in result.get("critical_issues", []) + result.get("warnings", [])]
    assert "THIN_CONTENT" in codes or any(
        i.get("code") == "THIN_CONTENT" for p in result["pages"] for i in p.get("issues", [])
    )


def test_missing_title(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "domain": "https://testgate.example.com",
            "home": {"title": "", "description": "desc", "content_html": "<h1>X</h1><p>" + "kelime " * 200 + "</p>"},
            "geo": [],
        },
        robots="Allow: /",
        sitemap="<urlset></urlset>",
    )
    result = qg.analyze_project(pid)
    assert any(i["code"] == "MISSING_TITLE" for p in result["pages"] for i in p.get("issues", []))


def test_missing_sitemap(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "domain": "https://testgate.example.com",
            "home": {
                "title": "Başlık yeterince uzun",
                "description": "Açıklama metni burada yer alıyor ve yeterince uzun olmalı.",
                "content_html": "<h1>Başlık</h1><p>" + "içerik " * 180 + "</p>",
            },
            "geo": [],
        },
        robots="User-agent: *\nAllow: /",
    )
    sitemap_file = gen_dir / slug / "public" / "sitemap.xml"
    if sitemap_file.is_file():
        sitemap_file.unlink()
    result = qg.analyze_project(pid)
    assert any(i["code"] == "MISSING_SITEMAP" for i in result.get("warnings", []))


def test_score_calculation():
    issues = [
        {"severity": "critical", "penalty": 10},
        {"severity": "warning", "penalty": 3},
        {"severity": "info", "penalty": 1},
    ]
    score = qg._calculate_score(issues)
    assert score == 86
    assert qg._calculate_score([{"severity": "critical", "penalty": 10}] * 11) == 0


def test_export_json_and_md(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    reports_dir = isolated_env["reports_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "domain": "https://testgate.example.com",
            "home": {
                "title": "Export Test Sayfası",
                "description": "Export test için meta açıklama metni.",
                "content_html": "<h1>Export</h1><p>" + "test " * 160 + "</p>",
            },
            "geo": [],
        },
        robots="Allow: /",
        sitemap="<urlset><url><loc>https://testgate.example.com/</loc></url></urlset>",
    )
    analyzed = qg.analyze_project(pid)
    rid = analyzed["report_id"]

    j = qg.export_report(rid, "json")
    assert j["success"] is True
    assert Path(j["path"]).exists()

    m = qg.export_report(rid, "md")
    assert m["success"] is True
    assert Path(m["path"]).suffix == ".md"
    assert "SEO GEO AEO Quality Gate" in m["content"]
    assert "seo_score" in analyzed or analyzed.get("seo_score") is not None
    assert "geo_score" in analyzed
    assert "aeo_score" in analyzed
    assert "readiness" in analyzed
    assert (reports_dir / f"{rid}.md").is_file()


def test_path_traversal_blocked(isolated_env):
    with pytest.raises(ValueError):
        qg._validate_project_path("../../etc/passwd")


def test_localhost_url_blocked():
    result = qg.analyze_url("http://localhost:4000/test")
    assert result["success"] is False
    assert "engellendi" in result.get("error", "").lower() or "localhost" in result.get("error", "").lower()


def test_list_and_get_report(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "domain": "https://testgate.example.com",
            "home": {
                "title": "Liste test",
                "description": "Meta",
                "content_html": "<h1>L</h1><p>" + "x " * 170 + "</p>",
            },
            "geo": [],
        },
        robots="ok",
        sitemap="<urlset/>",
    )
    analyzed = qg.analyze_project(pid)
    listed = qg.list_reports()
    assert listed["count"] >= 1
    got = qg.get_report(analyzed["report_id"])
    assert got["success"] is True
    assert got["report"]["report_id"] == analyzed["report_id"]


def test_fix_suggestions_rule_based(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "domain": "https://testgate.example.com",
            "home": {"title": "", "description": "", "content_html": "<p>k</p>"},
            "geo": [],
        },
    )
    analyzed = qg.analyze_project(pid)
    fixes = qg.fix_suggestions(analyzed["report_id"], use_llm=False)
    assert fixes["success"] is True
    assert fixes["count"] >= 1
    assert any(s.get("source") == "rule" for s in fixes["suggestions"])


def test_research_v2_page_scores(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "domain": "https://testgate.example.com",
            "home": {
                "title": "Kuşadası Gece Hayatı Rehberi",
                "description": "Rehber",
                "content_html": (
                    "<h1>Kuşadası Gece Hayatı</h1>"
                    "<h2>Kuşadası gece hayatı nedir?</h2>"
                    "<p>Kuşadası gece hayatı Kuşadası'da bar ve kulüplerden oluşur. "
                    "2026 sezonunda 50+ mekan aktiftir. Sonuç olarak gece hayatı canlıdır.</p>"
                ),
            },
            "geo": [],
        },
        robots="User-agent: *\nAllow: /",
        sitemap='<?xml version="1.0"?><urlset><url><loc>https://x.com/</loc></url></urlset>',
    )
    analyzed = qg.analyze_project(pid)
    assert analyzed.get("research_pack") == "v2"
    assert "citation_score" in analyzed
    assert "answerability_score" in analyzed
    assert "overview_probability_score" in analyzed
    assert "llm_visibility_score" in analyzed
    assert analyzed["pages"][0].get("citation_score") is not None


def test_research_citation_score_helper():
    plain = "Kuşadası gece hayatı 2026 rehberi. 50 mekan listelendi."
    score = qg._research_citation_score(plain, f"<p>{plain}</p>")
    assert 0 < score <= 100
