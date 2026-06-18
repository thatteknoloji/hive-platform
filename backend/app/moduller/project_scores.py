"""HIVE V3 — skeleton tabanlı SEO / GEO skor hesaplama."""

from __future__ import annotations

from typing import Any

from app.moduller.block_engine import count_blocks


def compute_scores(project: dict[str, Any]) -> dict[str, int]:
    pages = project.get("pages") or []
    site = project.get("site") or {}
    theme = project.get("theme") or {}
    design = project.get("design") or {}
    navigation = project.get("navigation") or []

    page_count = len(pages) or int(site.get("pages_count") or 0)
    block_count = count_blocks(pages)
    section_count = sum(len(p.get("sections") or []) for p in pages)

    seo = 0
    # sayfa çeşitliliği
    seo += min(25, page_count * 3)
    # seo meta doluluğu
    seo_meta = sum(
        1 for p in pages
        if (p.get("seo") or {}).get("title") and (p.get("seo") or {}).get("description")
    )
    seo += min(20, seo_meta * 3)
    seo_kw = sum(1 for p in pages if (p.get("seo") or {}).get("target_keyword"))
    seo += min(10, seo_kw * 2)
    # blok içerik
    seo += min(30, block_count * 2)
    # navigation
    seo += min(10, len(navigation))
    # theme / design dna
    if theme.get("design_dna") or design.get("design_dna"):
        seo += 10
    if design.get("creative_director_brief"):
        seo += 5
    seo = min(100, seo)

    geo = 0
    types = {p.get("type") for p in pages}
    if "contact" in types:
        geo += 15
    if "faq" in types or any(p.get("slug") == "sss" for p in pages):
        geo += 15
    if "location" in types or project.get("sector") in ("otel", "emlak", "restoran", "rentacar", "klinik"):
        geo += 20
    if design.get("conversion_goal") in ("geo_dominasyon", "yerel_liderlik", "rezervasyon"):
        geo += 15
    if block_count >= page_count * 2:
        geo += 20
    geo_fields = sum(1 for p in pages if (p.get("geo") or {}).get("entity_type"))
    geo += min(15, geo_fields * 2)
    if theme.get("color_identity"):
        geo += 10
    geo = min(100, geo)

    return {"seo_score": seo, "geo_score": geo}
