from __future__ import annotations

from app.moduller import block_engine, block_seed, project_scores, creative_director, site_seed


def test_fill_blocks_creates_content():
    skeleton = site_seed.build_site_skeleton(
        sector="otel",
        design={"conversion_goal": "rezervasyon", "design_dna": "luxury"},
        project_name="Test Hotel",
    )
    project = {
        "name": "Test Hotel",
        "sector": "otel",
        "business_brief": "Karaburun'da lüks butik otel.",
        "design": {"creative_director_brief": "Lüks ve güven."},
        "theme": skeleton["theme"],
        "pages": skeleton["pages"],
    }
    stats = block_engine.fill_project_blocks(project, use_llm=False)
    assert stats["filled_blocks"] > 0
    home = project["pages"][0]
    assert home["sections"][0]["blocks"]
    hero = home["sections"][0]["blocks"][0]
    assert hero["type"] == "hero"
    assert "content" in hero
    assert hero["content"].get("title") or hero["content"].get("primary_cta")


def test_compute_scores_after_fill():
    skeleton = site_seed.build_site_skeleton(sector="ecommerce", project_name="Shop")
    project = {
        "name": "Shop",
        "sector": "ecommerce",
        "business_brief": "E-ticaret markası",
        "design": {"design_dna": "marketplace"},
        "theme": skeleton["theme"],
        "pages": skeleton["pages"],
        "navigation": skeleton["navigation"],
        "site": skeleton["site"],
    }
    block_engine.fill_project_blocks(project, use_llm=False)
    scores = project_scores.compute_scores(project)
    assert scores["seo_score"] > 0
    assert scores["geo_score"] > 0


def test_creative_director_rules():
    res = creative_director.suggest(
        sector="otel",
        business_brief="Karaburun'da deniz manzaralı lüks butik otel.",
        creative_brief="Misafir lüks ve güven hissetmeli.",
        use_llm=False,
    )
    s = res["suggestions"]
    assert s["design_dna"] == "hotel_luxury"
    assert "conversion_goal" in s
