"""Site Replicator & Blueprint Engine testleri."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.moduller import site_replicator as sr


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "site_replicator_state.json"
    reports = tmp_path / "reports"
    gen = tmp_path / "generated-sites"
    gen.mkdir()
    reports.mkdir()
    state.write_text(json.dumps({"jobs": {}, "blueprints": {}}), encoding="utf-8")
    monkeypatch.setattr(sr, "STATE_FILE", state)
    monkeypatch.setattr(sr, "REPORTS_DIR", reports)
    monkeypatch.setattr(sr, "GENERATED_DIR", gen)
    yield {"state": state, "gen": gen, "reports": reports}


def test_health(isolated_env):
    h = sr.health()
    assert h["success"] is True
    assert h["compliance"]["competitor_content_copy"] is False


def test_path_traversal_guard():
    with pytest.raises(ValueError):
        sr._safe_slug("../etc/passwd")
    with pytest.raises(ValueError):
        sr._safe_project_path("../../outside")


def test_blocked_url_localhost():
    assert sr._is_blocked_url("http://localhost/test") is not None
    assert sr._is_blocked_url("http://127.0.0.1/") is not None


def test_canonical_domain_rewrite(isolated_env, tmp_path):
    project_path = tmp_path / "site"
    data_dir = project_path / "src" / "data"
    public = project_path / "public"
    data_dir.mkdir(parents=True)
    public.mkdir(parents=True)
    (data_dir / "pages.json").write_text(json.dumps({
        "site_name": "Old", "domain": "https://old.com", "main_site_url": "https://old.com", "geo": [],
    }), encoding="utf-8")
    (public / "sitemap.xml").write_text('<urlset><url><loc>https://old.com/page</loc></url></urlset>', encoding="utf-8")

    sr._update_domain_meta(project_path, "https://new.net", "New Site", "https://www.balkutusu.com")

    pages = json.loads((data_dir / "pages.json").read_text())
    assert pages["domain"] == "https://new.net"
    assert pages["site_name"] == "New Site"
    robots = (public / "robots.txt").read_text()
    assert "new.net" in robots
    sitemap = (public / "sitemap.xml").read_text()
    assert "old.com" not in sitemap
    assert "new.net" in sitemap


@patch("app.moduller.site_replicator._rewrite_text", side_effect=lambda t, *a, **k: t + " REWRITTEN")
def test_content_rewrite_required(mock_rw, isolated_env, tmp_path):
    data_dir = tmp_path / "src" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "faqs.json").write_text(json.dumps([{
        "slug": "f1", "title": "Q", "content_html": "<p>Original content here</p>",
    }]), encoding="utf-8")
    count = sr._rewrite_data_files(tmp_path, "Test Site", seed="s1")
    assert count >= 1
    data = json.loads((data_dir / "faqs.json").read_text())
    assert "REWRITTEN" in data[0]["content_html"]


@patch("app.moduller.site_replicator.requests.get")
def test_competitor_blueprint_no_copied_content(mock_get, isolated_env):
    mock_get.return_value = MagicMock(
        status_code=200,
        text="""
        <html><head><script type="application/ld+json">{"@type":"WebSite","name":"Comp"}</script></head>
        <body><nav><a href="/">Home</a></nav>
        <h1>Title</h1><h2>Category A</h2>
        <a href="/blog/post" class="btn-cta">CTA</a>
        </body></html>
        """,
        raise_for_status=lambda: None,
    )
    with patch.object(sr, "_fetch_robots_allowed", return_value=True):
        with patch.object(sr, "_is_blocked_url", return_value=None):
            result = sr.analyze_competitor_blueprint("https://example.com")

    assert result["success"] is True
    assert result["compliance"]["copied_content"] is False
    assert result["compliance"]["copied_assets"] is False
    assert result["compliance"]["blueprint_only"] is True
    assert "blueprint" in result
    assert len(result["blueprint"]["heading_structure"]) >= 1


@patch("app.moduller.site_replicator._copy_owned_site")
@patch("app.moduller.site_replicator._get_source_project")
@patch("app.moduller.site_replicator._run_quality_gate_on_project")
@patch("app.moduller.site_replicator._register_astro_project")
def test_owned_site_clone(mock_reg, mock_gate, mock_src, mock_copy, isolated_env, tmp_path):
    src_path = tmp_path / "source"
    src_path.mkdir()
    mock_src.return_value = ({"id": "src1", "slug": "source-site", "site_name": "Source"}, src_path)
    mock_gate.return_value = {"deploy_allowed": True, "reports": [], "passed_count": 1}
    mock_reg.return_value = None

    with patch.object(sr, "_safe_project_path", return_value=tmp_path / "target"):
        with patch.object(sr, "_update_domain_meta"):
            with patch.object(sr, "_rewrite_data_files", return_value=5):
                result = sr.clone_owned_site(
                    "src1", "balkutusu.net", "Balkutusu Rehber",
                    content_strategy="rewrite_all", auto_build=False, auto_deploy=False,
                )

    assert result["success"] is True
    assert result["summary"]["rewritten_fields"] == 5
    mock_copy.assert_called_once()


@patch("app.moduller.cloudflare_pages_deploy.deploy_to_cloudflare")
@patch("app.moduller.astro_factory.build_astro_project")
def test_cloudflare_deploy_hook(mock_build, mock_deploy, isolated_env):
    mock_build.return_value = {"success": True}
    mock_deploy.return_value = {"success": True, "url": "https://test.pages.dev"}
    with patch("app.moduller.astro_factory.generate_pages", return_value={"success": True}):
        with patch("app.moduller.astro_factory._get_project", return_value={"id": "p1", "domain": "https://test.com", "seed_keyword": "test"}):
            with patch.object(sr, "_notify_rank_watcher") as mock_rw:
                sr.build_project("p1")
                sr.deploy_cloudflare("p1")
    mock_deploy.assert_called_once_with("p1")


@patch("app.moduller.seo_quality_gate.seo_quality_gate.analyze_page")
def test_quality_gate_hook(mock_analyze, isolated_env, tmp_path):
    mock_analyze.return_value = {"pass": True, "seo_score": 90, "overall_score": 88}
    data_dir = tmp_path / "src" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "pages.json").write_text(json.dumps({
        "site_name": "T", "home": {"title": "H", "content_html": "<p>x</p>"},
        "geo": [{"title": "G", "content_html": "<p>y</p>", "keyword": "k"}],
    }), encoding="utf-8")
    gate = sr._run_quality_gate_on_project(tmp_path)
    assert gate["deploy_allowed"] is True
    mock_analyze.assert_called()


def test_no_asset_clone_in_competitor(isolated_env):
    assert sr.health()["compliance"]["competitor_asset_download"] is False


def test_export_report(isolated_env):
    job = sr._create_job("test", {"x": 1})
    rep = sr.export_report(job["job_id"])
    assert rep["success"] is True
    assert rep["report"]["job_id"] == job["job_id"]
