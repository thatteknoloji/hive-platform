"""Entity & GEO Graph — gerçek filesystem fixture testleri."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.moduller import astro_factory as af
from app.moduller import entity_geo_graph as egg


def _write_project(gen_dir: Path, slug: str, pages: dict, faqs: list | None = None, blog: list | None = None):
    root = gen_dir / slug
    data = root / "src" / "data"
    public = root / "public"
    data.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    (data / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")
    (data / "faqs.json").write_text(json.dumps(faqs or [], ensure_ascii=False), encoding="utf-8")
    (data / "blog.json").write_text(json.dumps(blog or [], ensure_ascii=False), encoding="utf-8")
    (public / "sitemap.xml").write_text(
        '<?xml version="1.0"?><urlset><url><loc>https://test.example.com/</loc></url></urlset>',
        encoding="utf-8",
    )
    return root


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    gen_dir = tmp_path / "generated-sites"
    gen_dir.mkdir()
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    af_state = tmp_path / "astro_factory_state.json"
    egg_state = tmp_path / "entity_geo_graph_state.json"

    monkeypatch.setattr(af, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(af, "STATE_FILE", af_state)
    monkeypatch.setattr(egg, "GENERATED_DIR", gen_dir)
    monkeypatch.setattr(egg, "STATE_FILE", egg_state)
    monkeypatch.setattr(egg, "REPORTS_DIR", reports_dir)

    af_state.write_text(json.dumps({"projects": {}}), encoding="utf-8")
    egg_state.write_text(json.dumps({"graphs": {}}), encoding="utf-8")
    yield {"gen_dir": gen_dir, "reports_dir": reports_dir, "af_state": af_state, "egg_state": egg_state}


def _register_project(gen_dir, slug="geo-test", project_id="egraph01"):
    created = af.create_project({
        "site_name": "GEO Test Site",
        "slug": slug,
        "domain": "https://geotest.example.com",
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
    result = egg.health()
    assert result["success"] is True
    assert result["status"] == "ok"
    assert "nominatim_url" in result


def test_entity_extraction():
    text = (
        "<h1>Kuşadası Gece Hayatı Rehberi</h1>"
        "<p>Kuşadası Marina ve Kadınlar Denizi bölgesinde gece hayatı rehberi.</p>"
    )
    extracted = egg.extract_entities_from_text(
        text, title="Kuşadası Gece Hayatı", seed_keyword="kuşadası gece hayatı", location="Kuşadası",
    )
    assert "Kuşadası" in extracted["locations"] or any("kuşadası" in l.lower() for l in extracted["locations"])
    assert extracted["keywords"]


def test_build_graph_with_fixture(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    html = (
        "<h1>Kuşadası Gece Hayatı Rehberi</h1>"
        "<h2>Barlar ve Kulüpler</h2>"
        "<p>" + "Kuşadası Aydın bölgesinde gece hayatı. " * 30 + "</p>"
        '<a href="/blog">Blog</a>'
    )
    _write_project(
        gen_dir, slug,
        pages={
            "site_name": "GEO Test",
            "domain": "https://geotest.example.com",
            "seed_keyword": "kuşadası gece hayatı",
            "home": {
                "title": "Kuşadası Gece Hayatı — Rehber",
                "description": "Kuşadası gece hayatı yerel rehber",
                "content_html": html,
            },
            "geo": [{
                "title": "Kuşadası Barlar",
                "slug": "kusadasi-barlar",
                "keyword": "kuşadası barlar",
                "content_html": "<h1>Kuşadası Barlar</h1><p>Kuşadası barlar rehberi.</p>",
            }],
        },
        faqs=[{
            "title": "Kuşadası Gece Hayatı SSS",
            "slug": "kusadasi-gece-hayati-sss",
            "keyword": "kuşadası gece hayatı",
            "content_html": "<h3>Kuşadası gece hayatı nedir?</h3><p>Yerel eğlence rehberi.</p>",
        }],
    )
    with patch("app.moduller.entity_geo_graph._talon_keywords", return_value=["kuşadası barlar", "kuşadası marina"]):
        result = egg.build_project_graph(
            pid,
            domain="https://geotest.example.com",
            seed_keyword="kuşadası gece hayatı",
            location="Kuşadası",
        )
    assert result["success"] is True
    assert result["graph_id"]
    assert result["summary"]["node_count"] >= 5
    assert result["summary"]["edge_count"] >= 3
    assert "entity_strength_score" in result["summary"]
    entities = [n for n in result["nodes"] if n["type"] == "entity"]
    if entities:
        ent = entities[0]
        assert "entity_authority" in ent
        assert "entity_visibility" in ent
        assert "entity_gap" in ent
        assert "entity_strength" in ent


def test_internal_link_plan(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "home": {"title": "Ana", "content_html": "<h1>Kuşadası Gece Hayatı</h1><p>test</p>"},
            "geo": [{"title": "Barlar", "slug": "barlar", "keyword": "barlar", "content_html": "<h1>Barlar</h1>"}],
        },
    )
    with patch("app.moduller.entity_geo_graph._talon_keywords", return_value=[]):
        egg.build_project_graph(pid, seed_keyword="kuşadası gece hayatı", location="Kuşadası")
    plan = egg.internal_link_plan(pid, max_links_per_page=5)
    assert plan["success"] is True
    assert isinstance(plan["links"], list)


def test_missing_entities(isolated_env):
    with patch("app.moduller.entity_geo_graph.geo_expand") as mock_geo:
        mock_geo.return_value = {
            "success": True,
            "geo_entities": [{"name": "Güvercinada", "type": "landmark", "source": "test"}],
            "suggested_geo_pages": [{
                "title": "Güvercinada Gece Hayatı",
                "slug": "guvercinada-gece-hayati",
                "target_keyword": "güvercinada gece hayatı",
                "page_type": "geo_landing",
            }],
            "warnings": [],
        }
        with patch("app.moduller.entity_geo_graph._talon_keywords", return_value=[]):
            result = egg.missing_entities(location="Kuşadası", seed_keyword="gece hayatı")
    assert result["success"] is True
    assert result["missing_entities"]
    assert result["recommended_pages"]


def test_geo_expand_warning_on_provider_failure():
    with patch("app.moduller.entity_geo_graph.requests.get", side_effect=Exception("network down")):
        result = egg.geo_expand("Kuşadası", seed_keyword="gece hayatı")
    assert result["success"] is True
    assert result["warnings"]
    assert isinstance(result["geo_entities"], list)


def test_export_json_md(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    reports = isolated_env["reports_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(gen_dir, slug, pages={"home": {"title": "T", "content_html": "<h1>T</h1><p>x</p>"}})
    with patch("app.moduller.entity_geo_graph._talon_keywords", return_value=[]):
        built = egg.build_project_graph(pid, seed_keyword="test", location="Kuşadası")
    gid = built["graph_id"]
    j = egg.export_graph(gid, "json")
    m = egg.export_graph(gid, "md")
    assert j["success"] and m["success"]
    assert (reports / f"entity_geo_graph_{gid}.json").is_file()
    assert (reports / f"entity_geo_graph_{gid}.md").is_file()


def test_path_traversal_blocked(isolated_env):
    with pytest.raises(ValueError, match="Path traversal|Geçersiz"):
        egg._validate_project_path("../etc/passwd")


def test_private_url_blocked():
    assert egg._is_blocked_url("http://127.0.0.1/test") is True
    assert egg._is_blocked_url("http://localhost/page") is True
    result = egg.analyze_url("http://192.168.1.1/page")
    assert result["success"] is False


def test_topic_clusters(isolated_env):
    gen_dir = isolated_env["gen_dir"]
    pid, slug = _register_project(gen_dir)
    _write_project(
        gen_dir, slug,
        pages={
            "home": {"title": "Kuşadası Gece Hayatı Rehberi", "content_html": "<h1>Pillar</h1><p>content</p>"},
            "geo": [
                {"title": "Kuşadası Barlar", "slug": "barlar", "content_html": "<h1>Barlar</h1>"},
                {"title": "Kuşadası Beach Club", "slug": "beach", "content_html": "<h1>Beach</h1>"},
            ],
        },
    )
    with patch("app.moduller.entity_geo_graph._talon_keywords", return_value=[]):
        clusters = egg.topic_clusters(pid)
    assert clusters["success"] is True
    assert clusters.get("pillar")
    assert clusters.get("clusters")
