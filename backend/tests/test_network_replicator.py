"""Network Replicator testleri."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.moduller import network_replicator as nr


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    state = tmp_path / "network_replicator_state.json"
    state.write_text(json.dumps({"networks": {}, "blueprints": {}, "jobs": {}}), encoding="utf-8")
    monkeypatch.setattr(nr, "STATE_FILE", state)
    monkeypatch.setattr(nr, "REPORTS_DIR", tmp_path / "reports")
    yield {"state": state}


def test_health(isolated_env):
    h = nr.health()
    assert h["success"] is True
    assert "brand_hub" in h["domain_roles"]
    assert h["min_deploy_score"] == 85


def test_create_network(isolated_env):
    res = nr.create_network("balkutusu.com", "Balkutusu Network")
    assert res["success"] is True
    assert res["network"]["main_domain"] == "balkutusu.com"
    assert res["network"]["domains"][0]["role"] == "brand_hub"


def test_add_domain(isolated_env):
    net = nr.create_network("balkutusu.com")["network"]
    res = nr.add_domain(net["network_id"], "balkutusu.net", role="blog_hub")
    assert res["success"] is True
    assert len(res["network"]["domains"]) == 2


def test_assign_role_by_tld():
    assert nr._assign_role_for_domain("balkutusu.info", 0) == "faq_hub"
    assert nr._assign_role_for_domain("balkutusu.org", 0) == "entity_hub"


@patch("app.moduller.network_replicator.clone_site")
def test_clone_to_many(mock_clone, isolated_env):
    mock_clone.return_value = {"success": True, "target_project_id": "p1"}
    with patch.object(nr, "rewrite_content", return_value={"rewritten_fields": 3, "quality_gate": {"deploy_allowed": True}}):
        with patch.object(nr, "retheme_site", return_value={"style": "modern"}):
            with patch("app.moduller.astro_factory.generate_pages", return_value={"success": True}):
                with patch("app.moduller.astro_factory.build_astro_project", return_value={"success": True}):
                    res = nr.clone_to_many("src1", ["balkutusu.net", "balkutusu.org"], auto_build=True, auto_deploy=False)
    assert res["success"] is True
    assert res["cloned"] == 2
    assert mock_clone.call_count == 2


@patch("app.moduller.site_replicator._rewrite_data_files")
def test_rewrite_modes(mock_rw, isolated_env):
    mock_rw.return_value = 5
    with patch("app.moduller.astro_factory._get_project", return_value={"slug": "t", "site_name": "T"}):
        with patch("app.moduller.astro_factory._project_path", return_value=isolated_env["state"].parent / "site"):
            with patch.object(nr, "_quality_gate_project", return_value={"deploy_allowed": True}):
                for mode in ("light", "balanced", "heavy", "full_rebuild"):
                    res = nr.rewrite_content("p1", mode)
                    assert res["success"] is True
                    assert res["mode"] == mode


def test_retheme_modes(isolated_env, tmp_path):
    site = tmp_path / "site"
    css_dir = site / "src" / "styles"
    css_dir.mkdir(parents=True)
    (css_dir / "global.css").write_text("body{}", encoding="utf-8")
    with patch("app.moduller.astro_factory._get_project", return_value={"slug": "site", "site_name": "T"}):
        with patch("app.moduller.astro_factory._project_path", return_value=site):
            with patch("app.moduller.astro_factory._update_project"):
                for style in ("modern", "nightlife", "minimal"):
                    res = nr.retheme_site("p1", style)
                    assert res["success"] is True
                    assert res["style"] == style


@patch("app.moduller.site_replicator.analyze_competitor_blueprint")
def test_blueprint_analysis(mock_analyze, isolated_env):
    mock_analyze.return_value = {
        "success": True,
        "blueprint_id": "bp1",
        "blueprint": {
            "category_structure": ["A"],
            "internal_link_patterns": [],
            "schema_patterns": ["WebSite"],
            "content_gaps": ["gap1"],
            "heading_structure": [],
            "url_patterns": ["/geo/kusadasi"],
        },
        "compliance": {"copied_content": False, "blueprint_only": True},
    }
    res = nr.analyze_blueprint("https://example.com")
    assert res["success"] is True
    assert res["compliance"]["copied_content"] is False
    assert "category_tree" in res


@patch("app.moduller.cloudflare_pages_deploy.deploy_to_cloudflare")
def test_cloudflare_hook(mock_deploy, isolated_env):
    mock_deploy.return_value = {"success": True, "url": "https://x.pages.dev"}
    net = nr.create_network("balkutusu.com")["network"]
    net["domains"] = [{"domain": "balkutusu.net", "project_id": "p1", "build_status": "built"}]
    st = nr._load_state()
    st["networks"][net["network_id"]] = net
    nr._save_state(st)
    with patch.object(nr, "_quality_gate_project", return_value={"deploy_allowed": True}):
        with patch.object(nr, "_rank_notify"):
            res = nr.deploy_network(net["network_id"])
    assert res["success"] is True
    mock_deploy.assert_called()


@patch.object(nr, "_quality_gate_project")
def test_quality_gate_block(mock_gate, isolated_env):
    mock_gate.return_value = {"deploy_allowed": False, "reports": []}
    net = nr.create_network("balkutusu.com")["network"]
    net["domains"] = [{"domain": "balkutusu.net", "project_id": "p1"}]
    st = nr._load_state()
    st["networks"][net["network_id"]] = net
    nr._save_state(st)
    with patch("app.moduller.astro_factory.generate_pages"):
        with patch("app.moduller.astro_factory.build_astro_project"):
            res = nr.build_network(net["network_id"])
    assert res["success"] is True
    assert any(not r.get("success") for r in res["results"])


@patch("app.moduller.network_replicator._rank_notify")
@patch("app.moduller.site_replicator.clone_owned_site")
def test_clone_site(mock_clone, mock_rank, isolated_env):
    mock_clone.return_value = {"success": True, "summary": {"target_project_id": "new1"}}
    with patch.object(nr, "_update_domain_meta"):
        res = nr.clone_site("src1", "balkutusu.net", "Balkutusu Net")
    assert res["success"] is True
    assert res["target_project_id"] == "new1"


def test_export_report(isolated_env):
    net = nr.create_network("balkutusu.com")["network"]
    rep = nr.export_report(network_id=net["network_id"])
    assert rep["success"] is True


def test_domain_research_scores(isolated_env):
    scores = nr._domain_research_scores({
        "domain": "test.example.com",
        "project_id": "",
        "quality_score": 88,
        "last_publish": "2026-06-10",
        "build_status": "built",
    })
    assert "authority_score" in scores
    assert "content_freshness" in scores
    assert "entity_density" in scores
    assert "ai_visibility" in scores
    assert scores["content_freshness"] >= 78


def test_get_network_enriched_domains(isolated_env):
    net = nr.create_network("example.com")["network"]
    got = nr.get_network(net["network_id"])
    dom = got["network"]["domains"][0]
    assert "authority_score" in dom
    assert "entity_density" in dom
