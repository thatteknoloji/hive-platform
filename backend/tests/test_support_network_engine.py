"""Support Network Engine V1 — gerçek entegrasyon testleri."""

import json

import pytest

from app.moduller import network_replicator as nr
from app.moduller import support_network_engine as sne


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    sne_state = tmp_path / "support_network_engine_state.json"
    nr_state = tmp_path / "network_replicator_state.json"
    reports = tmp_path / "reports"
    reports.mkdir()
    gate_state = tmp_path / "seo_quality_gate_state.json"
    gate_state.write_text(json.dumps({"reports": {}}), encoding="utf-8")

    monkeypatch.setattr(sne, "STATE_FILE", sne_state)
    monkeypatch.setattr(sne, "REPORTS_DIR", reports)
    monkeypatch.setattr(nr, "STATE_FILE", nr_state)
    monkeypatch.setattr(nr, "REPORTS_DIR", reports)

    sne_state.write_text(json.dumps({
        "settings": dict(sne.DEFAULT_SETTINGS),
        "domain_overrides": {},
        "link_plans": [],
        "keyword_registry": {},
        "jobs": {},
        "last_sync_at": "",
    }), encoding="utf-8")
    nr_state.write_text(json.dumps({"networks": {}, "blueprints": {}, "jobs": {}}), encoding="utf-8")
    yield {"sne_state": sne_state, "nr_state": nr_state, "reports": reports}


def _seed_network():
    net = nr.create_network("balkutusu.com", "Test Network")["network"]
    nr.add_domain(net["network_id"], "balkutusu.net", role="blog_hub")
    nr.add_domain(net["network_id"], "balkutusu.info", role="faq_hub")
    nr.add_domain(net["network_id"], "balkutusu.org", role="entity_hub")
    return net["network_id"]


def test_health_empty():
    h = sne.health()
    assert h["success"] is True
    assert h["enabled"] is True
    assert "money_sites" in h["network_groups"]
    assert "authority_hub" in h["roles"]


def test_list_domains_from_network_replicator(isolated_env):
    nid = _seed_network()
    res = sne.list_domains(nid)
    assert res["success"] is True
    assert res["count"] >= 4
    roles = {d["role"] for d in res["domains"]}
    assert "money_site" in roles or "brand_hub" in roles
    assert "blog_hub" in roles
    profile = res["domains"][0]
    for field in (
        "domain", "role", "project_id", "authority_score", "trust_score",
        "entity_score", "geo_score", "content_count", "indexed_pages",
        "ranking_keywords", "network_links", "status",
    ):
        assert field in profile


def test_authority_map(isolated_env):
    nid = _seed_network()
    res = sne.authority_map(nid)
    assert res["success"] is True
    assert "carrying_authority" in res
    assert "no_inbound_links" in res
    assert res["summary"]["total_domains"] >= 4


def test_authority_map_no_domains_error(isolated_env):
    res = sne.authority_map()
    assert res["success"] is False
    assert "error" in res


def test_keyword_distribution(isolated_env):
    nid = _seed_network()
    res = sne.keyword_distribution(nid)
    assert res["success"] is True
    assert "cannibalization_risks" in res
    assert "duplicate_keywords" in res


def test_network_health(isolated_env):
    nid = _seed_network()
    res = sne.network_health(nid)
    assert res["success"] is True
    assert 0 <= res["network_score"] <= 100
    for key in (
        "authority", "coverage", "content_freshness", "geo_coverage",
        "entity_coverage", "link_balance", "publish_activity", "index_coverage",
        "quality_gate_pass_rate",
    ):
        assert key in res["scores"]
    assert "overall_network_score" in res


def test_network_gaps(isolated_env):
    nid = _seed_network()
    res = sne.network_gaps(nid)
    assert res["success"] is True
    assert isinstance(res["gaps"], list)
    gap_types = {g["type"] for g in res["gaps"]}
    assert "missing_geo_hub" in gap_types or "missing_role" in gap_types


def test_link_strategy_plan_only(isolated_env):
    nid = _seed_network()
    res = sne.link_strategy(nid)
    assert res["success"] is True
    if res["count"] > 0:
        plan = res["plans"][0]
        assert plan["action"] == "plan_only"
        assert "from_domain" in plan
        assert "anchor_text" in plan


def test_suggest_role_integration():
    res = sne.suggest_role("example.info", 0)
    assert res["success"] is True
    assert res["suggested_role"] == "faq_hub"
    assert res["network_group"] == "faq_sites"


def test_sync_network(isolated_env):
    nid = _seed_network()
    res = sne.sync_network(nid)
    assert res["success"] is True
    assert res["job_id"]
    assert res["results"]["domains"]["count"] >= 4
    assert res["results"]["health"]["success"] is True


def test_export_report(isolated_env):
    nid = _seed_network()
    res = sne.export_report("authority", network_id=nid)
    assert res["success"] is True
    assert res["report_type"] == "authority"
    path = isolated_env["reports"] / res["path"].split("/")[-1]
    assert path.exists() or __import__("pathlib").Path(res["path"]).exists()


def test_settings_roundtrip(isolated_env):
    updated = sne.update_settings({"keyword_cannibalization_threshold": 0.9})
    assert updated["keyword_cannibalization_threshold"] == 0.9
    assert sne.get_settings()["keyword_cannibalization_threshold"] == 0.9


def test_discover_and_networks(isolated_env):
    nid = _seed_network()
    disc = sne.discover_network(nid)
    assert disc["success"] is True
    assert disc["domain_count"] >= 4
    nets = sne.list_networks_api()
    assert nets["success"] is True
    assert nets["count"] >= 1


def test_get_network_and_domain(isolated_env):
    nid = _seed_network()
    net = sne.get_network(nid)
    assert net["success"] is True
    assert net["domain_count"] >= 4
    dom = net["domains"][0]["domain"]
    detail = sne.get_domain(dom)
    assert detail["success"] is True
    assert detail["profile"]["domain"] == dom
    assert "quality_score" in detail["profile"]


def test_dashboard(isolated_env):
    _seed_network()
    dash = sne.dashboard()
    assert dash["success"] is True
    assert dash["domain_count"] >= 4


def test_growth_opportunities(isolated_env):
    _seed_network()
    res = sne.growth_opportunities()
    assert res["success"] is True
    assert "opportunities" in res


def test_publisher_channels_view(isolated_env):
    _seed_network()
    res = sne.publisher_channels_view()
    assert res["success"] is True
    assert "by_channel" in res
    assert "by_domain" in res


def test_health_integration_errors_explicit(isolated_env):
    h = sne.health()
    assert "integrations" in h
    assert "integration_errors" in h
    assert h["module"] == "support_network_engine"


def test_profile_fields_extended(isolated_env):
    nid = _seed_network()
    profile = sne.list_domains(nid)["domains"][0]
    for field in ("last_refresh_date", "quality_score", "supports_domain", "publish_channels"):
        assert field in profile
