from __future__ import annotations

from app.moduller import site_seed


def test_hotel_sector_pages():
    pages = site_seed.get_sector_page_blueprints("otel")
    titles = [p["title"] for p in pages]
    assert "Ana Sayfa" in titles
    assert "Odalar" in titles
    assert "SSS" in titles
    assert len(pages) == 7


def test_ecommerce_sector_pages():
    pages = site_seed.get_sector_page_blueprints("ecommerce")
    titles = [p["title"] for p in pages]
    assert "Kategoriler" in titles
    assert "Ürünler" in titles
    assert len(pages) == 6


def test_build_site_skeleton_navigation():
    skeleton = site_seed.build_site_skeleton(
        sector="otel",
        design={
            "design_dna": "luxury",
            "color_identity": "gold_luxury",
            "brand_personality": ["premium"],
            "conversion_goal": "rezervasyon",
        },
        project_name="Karaburun Hotel",
    )
    assert skeleton["site"]["engine"] == "astro"
    assert skeleton["site"]["status"] == "draft"
    assert skeleton["site"]["pages_count"] == 7
    assert len(skeleton["pages"]) == 7
    assert skeleton["navigation"][0] == {"label": "Ana Sayfa", "href": "/"}
    assert skeleton["navigation"][1]["href"] == "/odalar"

    home = skeleton["pages"][0]
    assert home["type"] == "homepage"
    assert home["status"] == "draft"
    assert len(home["sections"]) >= 2
    assert home["sections"][0]["type"] == "hero"


def test_theme_from_wizard_design():
    theme = site_seed.build_theme({
        "design_dna": "luxury",
        "color_identity": "gold_luxury",
        "custom_color": "#c9a962",
        "brand_personality": ["ultra_luks", "premium"],
        "conversion_goal": "rezervasyon",
    })
    assert theme["design_dna"] == "luxury"
    assert theme["color_identity"] == "gold_luxury"
    assert theme["custom_color"] == "#c9a962"
    assert theme["brand_personality"] == ["ultra_luks", "premium"]
    assert theme["conversion_goal"] == "rezervasyon"
    assert theme["font_style"] == "serif"
    assert theme["radius"] == "premium"
    assert theme["spacing"] == "comfortable"


def test_unknown_sector_falls_back_to_ozel():
    from app.moduller import sector_packs
    pages = site_seed.get_sector_page_blueprints("unknown_sector")
    assert len(pages) == len(sector_packs.get_default_pages("ozel"))
