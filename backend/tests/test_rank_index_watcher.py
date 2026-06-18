"""Rank & Index Watcher testleri — mock yok, gerçek state ve provider kontrolleri."""

import json
from pathlib import Path

import pytest

from app.moduller import rank_index_watcher as riw


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state_file = tmp_path / "rank_index_watcher_state.json"
    reports_dir = tmp_path / "reports"
    gen_dir = tmp_path / "generated-sites"
    astro_state = tmp_path / "astro_factory_state.json"
    seo_state = tmp_path / "seo_quality_gate_state.json"
    reports_dir.mkdir()
    gen_dir.mkdir()

    monkeypatch.setattr(riw, "STATE_FILE", state_file)
    monkeypatch.setattr(riw, "REPORTS_DIR", reports_dir)
    monkeypatch.setattr(riw, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(riw, "ASTRO_STATE", astro_state)
    monkeypatch.setattr(riw, "SEO_GATE_STATE", seo_state)
    monkeypatch.setattr(riw, "_gsc_oauth_configured", lambda: False)
    monkeypatch.setattr(riw, "_dataforseo_configured", lambda: False)

    state_file.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    astro_state.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    seo_state.write_text(json.dumps({"reports": {}}), encoding="utf-8")
    yield {
        "state_file": state_file,
        "reports_dir": reports_dir,
        "gen_dir": gen_dir,
        "astro_state": astro_state,
        "seo_state": seo_state,
    }


def test_health(isolated_env):
    result = riw.health()
    assert result["status"] == "ok"
    assert result["search_console"] is False
    assert result["rank_provider"] is False
    assert result["providers"] == []


def test_register_project_and_persistence(isolated_env):
    reg = riw.register_project("proj-abc", "https://kusadasigecehayati.com")
    assert reg["success"] is True
    assert reg["project"]["domain"] == "https://kusadasigecehayati.com"

    loaded = json.loads(isolated_env["state_file"].read_text(encoding="utf-8"))
    assert "proj-abc" in loaded["projects"]

    got = riw.get_project("proj-abc")
    assert got["success"] is True
    assert got["project"]["keywords"] == []


def test_register_invalid_project_id():
    with pytest.raises(ValueError):
        riw.register_project("../evil", "https://example.com")


def test_index_status_without_gsc():
    result = riw.index_status("https://example.com/page")
    assert result["success"] is False
    assert result["error"] == "search_console_not_configured"
    assert result["indexed"] is None


def test_track_keyword_provider_missing():
    result = riw.track_keyword("kuşadası gece hayatı", "kusadasigecehayati.com")
    assert result["success"] is False
    assert result["error"] == "provider_missing"


def test_ai_overview_provider_missing():
    result = riw.ai_overview("kuşadası gece hayatı")
    assert result["success"] is False
    assert result["error"] == "provider_missing"


def test_performance_without_gsc():
    result = riw.performance("https://kusadasigecehayati.com")
    assert result["success"] is False
    assert "search_console" in result["error"]


def test_decay_detector_needs_history(isolated_env):
    riw.register_project("p1", "https://example.com")
    result = riw.decay_detector("p1")
    assert result["success"] is True
    assert "note" in result


def test_decay_detector_with_history(isolated_env):
    riw.register_project("p1", "https://example.com")
    state = json.loads(isolated_env["state_file"].read_text(encoding="utf-8"))
    state["projects"]["p1"]["performance_history"] = [
        {"clicks": 50, "ctr": 0.02, "avg_position": 12.0, "checked_at": "t1"},
        {"clicks": 100, "ctr": 0.05, "avg_position": 8.0, "checked_at": "t0"},
    ]
    isolated_env["state_file"].write_text(json.dumps(state), encoding="utf-8")
    result = riw.decay_detector("p1")
    assert result["success"] is True
    types = {a["type"] for a in result["alerts"]}
    assert "traffic_drop" in types
    assert "ctr_drop" in types
    assert "rank_drop" in types


def test_opportunity_finder(isolated_env):
    riw.register_project("p1", "https://example.com")
    state = json.loads(isolated_env["state_file"].read_text(encoding="utf-8"))
    state["projects"]["p1"]["performance_history"] = [{
        "top_queries": [
            {"query": "kuşadası gece", "position": 9, "ctr": 0.005, "clicks": 2, "impressions": 400},
        ],
    }]
    state["projects"]["p1"]["seo_gate_flags"] = [
        {"slug": "home", "title": "Ana sayfa", "overall_score": 55},
    ]
    isolated_env["state_file"].write_text(json.dumps(state), encoding="utf-8")
    result = riw.opportunity_finder("p1")
    assert result["success"] is True
    assert len(result["opportunities"]) >= 2


def test_bulk_track_reads_astro_files(isolated_env):
    gen_dir: Path = isolated_env["gen_dir"]
    astro_state = isolated_env["astro_state"]
    slug = "test-site"
    data_dir = gen_dir / slug / "src" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "pages.json").write_text(json.dumps({
        "seed_keyword": "kuşadası gece hayatı",
        "home": {"title": "Kuşadası Gece", "description": "d", "content_html": "<p>x</p>"},
        "geo": [{"slug": "marina", "title": "Marina Gece", "keyword": "kuşadası marina", "content_html": "<p>y</p>"}],
    }), encoding="utf-8")
    (data_dir / "faqs.json").write_text("[]", encoding="utf-8")
    (data_dir / "blog.json").write_text("[]", encoding="utf-8")
    astro_state.write_text(json.dumps({
        "projects": {
            "astro-1": {
                "id": "astro-1",
                "slug": slug,
                "seed_keyword": "kuşadası gece hayatı",
                "domain": "https://test.example.com",
            }
        }
    }), encoding="utf-8")

    riw.register_project("astro-1", "https://test.example.com")
    result = riw.bulk_track("astro-1")
    assert result["success"] is True
    assert result["keywords_added"] >= 2


def test_export_json_and_md(isolated_env):
    riw.register_project("exp-1", "https://export.example.com")
    j = riw.export_report("exp-1", "json")
    assert j["success"] is True
    assert Path(j["absolute_path"]).is_file()

    m = riw.export_report("exp-1", "md")
    assert m["success"] is True
    assert m["path"].endswith(".md")


def test_export_path_traversal_blocked():
    with pytest.raises(ValueError):
        riw.export_report("../outside", "json")


def test_sitemap_status_real_http(monkeypatch):
    def fake_get(url, timeout=25):
        if url.endswith("robots.txt"):
            return 200, "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n", url
        if "sitemap.xml" in url:
            body = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                "<url><loc>https://example.com/</loc></url>"
                "<url><loc>https://example.com/blog</loc></url>"
                "</urlset>"
            )
            return 200, body, url
        return 404, "", url

    monkeypatch.setattr(riw, "_http_get", fake_get)
    result = riw.sitemap_status("https://example.com")
    assert result["success"] is True
    assert result["robots"]["exists"] is True
    assert result["url_count"] == 2
    assert result["indexed_ratio"] is None


def test_on_astro_project_created_hook(isolated_env):
    result = riw.on_astro_project_created("hook-1", "https://hook.example.com")
    assert result["success"] is True
    assert result["project"]["source"] == "astro_factory"


def test_research_v2_keyword_metrics():
    history = [
        {"position": 12, "at": "2026-06-10 12:00:00 UTC"},
        {"position": 8, "at": "2026-06-09 12:00:00 UTC"},
        {"position": 15, "at": "2026-06-08 12:00:00 UTC"},
    ]
    m = riw.compute_keyword_rank_metrics(history, last_position=12)
    assert "ranking_velocity" in m
    assert "keyword_strength_score" in m
    assert m["trend_direction"] in ("up", "down", "flat", "recovering", "decaying")
    assert 0 <= m["keyword_strength_score"] <= 100


def test_health_research_pack(isolated_env):
    h = riw.health()
    assert h.get("research_pack") == "v2"
