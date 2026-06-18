from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app import panel_identity
from app.moduller import block_engine, block_seed, project_engine as pe, site_seed


def _setup(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_EMAIL", "hive@thiqos.com")
    monkeypatch.setenv("HIVE_DEFAULT_ADMIN_PASSWORD", "hive123")
    monkeypatch.setenv("HIVE_JWT_SECRET", "test-secret-1234567890")
    monkeypatch.setattr(panel_identity, "STATE_FILE", tmp_path / "panel_identity_state.json")
    monkeypatch.setattr(pe, "STATE_FILE", tmp_path / "project_engine_state.json")
    panel_identity.bootstrap()
    from app.auth import create_access_token
    client = TestClient(app)
    token = create_access_token(email="hive@thiqos.com")
    return client, {"Authorization": f"Bearer {token}"}


def _seed_project(sector: str, name: str, brief: str, design: dict | None = None) -> dict:
    skeleton = site_seed.build_site_skeleton(
        sector=sector,
        design=design or {},
        project_name=name,
    )
    project = {
        "name": name,
        "sector": sector,
        "business_brief": brief,
        "design": design or {},
        "theme": skeleton["theme"],
        "pages": skeleton["pages"],
        "navigation": skeleton["navigation"],
        "site": skeleton["site"],
    }
    block_seed.seed_project_blocks(project)
    return project


def test_project_create_blocks_not_empty(tmp_path, monkeypatch):
    client, headers = _setup(tmp_path, monkeypatch)
    res = client.post("/api/v3/projects", headers=headers, json={
        "name": "Test Shop",
        "sector": "ecommerce",
        "business_brief": "Türkiye geneli e-ticaret markası.",
        "design": {
            "wizard_version": 2,
            "design_dna": "marketplace",
            "conversion_goal": "urun_sat",
        },
        "deploy_mode": "hive_cloud",
    })
    assert res.status_code == 200
    project = res.json()["project"]
    assert block_engine.count_blocks(project["pages"]) > 0
    for page in project["pages"]:
        for section in page.get("sections") or []:
            assert len(section.get("blocks") or []) >= 1


def test_hotel_homepage_hero_block(tmp_path, monkeypatch):
    project = _seed_project(
        "otel",
        "Pentera Evleri",
        "Karaburun'da deniz manzaralı butik otel.",
        {"conversion_goal": "rezervasyon", "design_dna": "hotel_luxury"},
    )
    home = project["pages"][0]
    hero = home["sections"][0]["blocks"][0]
    assert hero["type"] == "hero"
    assert "content" in hero
    assert hero["content"]["primary_cta"] == "Rezervasyon Yap"
    assert hero["content"]["secondary_cta"] == "Odaları İncele"
    assert "Karaburun" in hero["content"]["eyebrow"]
    assert hero["seo"]["target_keyword"]
    assert hero["geo"]["entity_type"] == "Hotel"


def test_ecommerce_cta_product_focused():
    project = _seed_project(
        "ecommerce",
        "ModaShop",
        "Online giyim mağazası.",
        {"conversion_goal": "urun_sat"},
    )
    home = project["pages"][0]
    hero = home["sections"][0]["blocks"][0]
    cta_section = home["sections"][1]["blocks"][0]
    assert hero["content"]["primary_cta"] == "Ürünleri İncele"
    assert cta_section["type"] == "cta"
    assert "Ürün" in cta_section["content"]["primary_cta"] or cta_section["content"]["primary_cta"] == "Ürünleri İncele"


def test_contact_page_has_form_and_map():
    project = _seed_project("otel", "Otel X", "İzmir merkezde otel.")
    contact = next(p for p in project["pages"] if p.get("type") == "contact")
    block_types = [b["type"] for s in contact["sections"] for b in s.get("blocks") or []]
    assert "contact_form" in block_types
    assert "map" in block_types


def test_seo_fields_populated():
    project = _seed_project("klinik", "Diş Kliniği", "İzmir merkezde diş kliniği.")
    for page in project["pages"]:
        seo = page.get("seo") or {}
        assert seo.get("title")
        assert seo.get("description")
        assert seo.get("target_keyword")
        assert seo.get("intent")
        assert seo.get("schema_type")
    home = project["pages"][0]
    assert home["seo"]["schema_type"] in ("MedicalClinic", "Hotel", "Organization", "WebPage")


def test_geo_fields_populated():
    project = _seed_project("emlak", "Emlak Pro", "Ankara merkezde emlak ofisi.")
    for page in project["pages"]:
        geo = page.get("geo") or {}
        assert geo.get("entity_type")
        assert "topic_cluster" in geo
        assert isinstance(geo.get("support_network_needed"), bool)
    block = project["pages"][0]["sections"][0]["blocks"][0]
    assert block.get("geo", {}).get("entity_type")


def test_unknown_sector_fallback():
    project = _seed_project("bilinmeyen_sektor", "Özel Marka", "Genel hizmet firması.")
    assert block_engine.count_blocks(project["pages"]) > 0
    hero = project["pages"][0]["sections"][0]["blocks"][0]
    assert hero["content"]["primary_cta"] == "Detayları İncele"
    assert project["pages"][0]["seo"]["schema_type"] == "Organization"


def test_block_schema_has_required_fields():
    project = _seed_project("blog", "Tech Blog", "Teknoloji haberleri.")
    blk = project["pages"][0]["sections"][0]["blocks"][0]
    for key in ("id", "type", "status", "content", "settings", "seo", "geo"):
        assert key in blk
