"""
HIVE V3 Block Seed Engine — deterministic sector-aware block + page SEO/GEO seeding.
No AI calls; templates are stable and field names are AI-replaceable later.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

# --- Sector schema & entity maps ---

_SECTOR_SCHEMA: dict[str, str] = {
    "otel": "Hotel",
    "ecommerce": "Organization",
    "emlak": "RealEstateAgent",
    "klinik": "MedicalClinic",
    "veteriner": "VeterinaryCare",
    "restoran": "Restaurant",
    "kurumsal": "Organization",
    "blog": "BlogPosting",
    "ilan": "ItemList",
    "rentacar": "AutoRental",
    "ozel": "Organization",
}

_SECTOR_SCHEMA_ALT: dict[str, str] = {
    "otel": "LodgingBusiness",
    "ecommerce": "Product",
    "emlak": "Offer",
    "ilan": "WebSite",
}

_PAGE_SCHEMA_OVERRIDE: dict[str, str] = {
    "blog": "BlogPosting",
    "faq": "FAQPage",
    "legal": "WebPage",
    "contact": "ContactPage",
}

_SECTOR_ENTITY: dict[str, str] = {
    "otel": "Hotel",
    "ecommerce": "Organization",
    "emlak": "RealEstateAgent",
    "klinik": "MedicalClinic",
    "veteriner": "VeterinaryCare",
    "restoran": "Restaurant",
    "kurumsal": "Organization",
    "blog": "Blog",
    "ilan": "WebSite",
    "rentacar": "AutoRental",
    "ozel": "Organization",
}

_SECTOR_DISPLAY: dict[str, str] = {
    "otel": "konaklama",
    "ecommerce": "e-ticaret",
    "emlak": "emlak",
    "klinik": "sağlık",
    "veteriner": "veteriner",
    "restoran": "restoran",
    "kurumsal": "kurumsal",
    "blog": "blog",
    "ilan": "ilan",
    "rentacar": "araç kiralama",
    "ozel": "hizmet",
}

_SECTOR_VALUE: dict[str, str] = {
    "otel": "konforlu odalar ve unutulmaz bir konaklama",
    "ecommerce": "güvenilir alışveriş ve hızlı teslimat",
    "emlak": "doğru adres ve güvenilir danışmanlık",
    "klinik": "uzman kadro ve güvenilir sağlık hizmeti",
    "veteriner": "sevgi dolu pet bakımı ve profesyonel tedavi",
    "restoran": "lezzetli menü ve sıcak atmosfer",
    "kurumsal": "kurumsal güven ve uzmanlık",
    "blog": "kaliteli içerik ve uzman görüşler",
    "ilan": "hızlı arama ve güvenilir ilanlar",
    "rentacar": "güvenli ve konforlu araç kiralama",
    "ozel": "profesyonel dijital deneyim",
}

_INTENT_BY_PAGE: dict[str, str] = {
    "homepage": "commercial",
    "landing": "commercial",
    "category": "commercial",
    "product": "transactional",
    "blog": "informational",
    "faq": "informational",
    "legal": "informational",
    "contact": "navigational",
    "about": "informational",
}

# CTA triples: (primary, secondary, tertiary) by sector + conversion_goal key
_CTA_BY_SECTOR_GOAL: dict[tuple[str, str], tuple[str, str, str]] = {
    ("otel", "rezervasyon"): ("Rezervasyon Yap", "Odaları İncele", "Müsaitlik Sor"),
    ("otel", "marka"): ("Rezervasyon Yap", "Odaları İncele", "Müsaitlik Sor"),
    ("ecommerce", "urun_sat"): ("Ürünleri İncele", "Sepete Git", "Kampanyaları Gör"),
    ("ecommerce", "marka"): ("Ürünleri İncele", "Sepete Git", "Kampanyaları Gör"),
    ("klinik", "lead_topla"): ("Randevu Al", "Doktorlarla Tanış", "Bilgi Al"),
    ("klinik", "rezervasyon"): ("Randevu Al", "Doktorlarla Tanış", "Bilgi Al"),
    ("veteriner", "lead_topla"): ("Randevu Al", "Hizmetlerimiz", "Bilgi Al"),
    ("rentacar", "lead_topla"): ("Araçları İncele", "Hemen Teklif Al", "Müsait Araç Sor"),
    ("rentacar", "rezervasyon"): ("Araçları İncele", "Hemen Teklif Al", "Müsait Araç Sor"),
    ("ilan", "lead_topla"): ("İlanları Gör", "Ücretsiz İlan Ver", "Kategorileri İncele"),
    ("ilan", "marka"): ("İlanları Gör", "Ücretsiz İlan Ver", "Kategorileri İncele"),
}

_CTA_FALLBACK = ("Detayları İncele", "İletişime Geç", "Daha Fazla Bilgi")

_GEO_CLUSTER_SECTORS = frozenset({"otel", "emlak", "klinik", "restoran", "rentacar", "veteriner"})


def _new_id(prefix: str = "block") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _extract_location_hint(brief: str) -> str:
    if not brief:
        return ""
    m = re.search(
        r"([\wçğıöşüÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ\s-]{1,40}?)"
        r"(?:'?(?:da|de|ta|te)|\s+merkez(?:de|de)?|\s+ilçesinde)",
        brief,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    m2 = re.search(r"\b([A-ZÇĞİÖŞÜ][a-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğıöşü]+)?)\b", brief)
    if m2:
        return m2.group(1).strip()
    return ""


def _brief_snippet(brief: str, limit: int = 160) -> str:
    text = (brief or "").strip()
    if not text:
        return ""
    sentence = re.split(r"[.!?]\s+", text)[0].strip()
    return (sentence or text)[:limit]


def _cta_triple(sector: str, conversion_goal: str) -> tuple[str, str, str]:
    goal = conversion_goal or "marka"
    key = (sector, goal)
    if key in _CTA_BY_SECTOR_GOAL:
        return _CTA_BY_SECTOR_GOAL[key]
    if sector == "otel":
        return _CTA_BY_SECTOR_GOAL[("otel", "rezervasyon")]
    if sector == "ecommerce":
        return _CTA_BY_SECTOR_GOAL[("ecommerce", "urun_sat")]
    if sector == "klinik":
        return _CTA_BY_SECTOR_GOAL[("klinik", "lead_topla")]
    if sector == "rentacar":
        return _CTA_BY_SECTOR_GOAL[("rentacar", "lead_topla")]
    if sector == "ilan":
        return _CTA_BY_SECTOR_GOAL[("ilan", "lead_topla")]
    return _CTA_FALLBACK


def _visual_style(design_dna: str, sector: str) -> str:
    if design_dna:
        return design_dna
    defaults = {
        "otel": "hotel_luxury",
        "ecommerce": "marketplace",
        "klinik": "medical_clean",
        "emlak": "real_estate_modern",
        "restoran": "restaurant_warm",
    }
    return defaults.get(sector, "standard")


def _build_context(project: dict[str, Any]) -> dict[str, Any]:
    design = project.get("design") or {}
    theme = project.get("theme") or {}
    brief = (project.get("business_brief") or "").strip()
    sector = (project.get("sector") or "ozel").strip()
    conversion_goal = theme.get("conversion_goal") or design.get("conversion_goal") or "marka"
    design_dna = theme.get("design_dna") or design.get("design_dna") or ""
    creative_brief = (design.get("creative_director_brief") or "").strip()
    location = _extract_location_hint(brief)
    primary, secondary, tertiary = _cta_triple(sector, conversion_goal)
    return {
        "project_name": (project.get("name") or "Site").strip(),
        "sector": sector,
        "business_brief": brief,
        "brief_snippet": _brief_snippet(brief),
        "creative_brief": creative_brief,
        "conversion_goal": conversion_goal,
        "design_dna": design_dna,
        "location_hint": location,
        "ctas": {"primary": primary, "secondary": secondary, "tertiary": tertiary},
        "sector_display": _SECTOR_DISPLAY.get(sector, "hizmet"),
        "sector_value": _SECTOR_VALUE.get(sector, _SECTOR_VALUE["ozel"]),
        "visual_style": _visual_style(design_dna, sector),
    }


def _block_geo(ctx: dict[str, Any], *, block_type: str) -> dict[str, Any]:
    return {
        "entity_type": _SECTOR_ENTITY.get(ctx["sector"], "Organization"),
        "location_hint": ctx["location_hint"],
        "topic_cluster": f"{ctx['sector']}_{block_type}",
        "support_network_needed": ctx["sector"] in _GEO_CLUSTER_SECTORS,
    }


def _block_seo(ctx: dict[str, Any], *, keyword: str, intent: str = "commercial") -> dict[str, Any]:
    return {
        "target_keyword": keyword,
        "intent": intent,
    }


def _target_keyword(ctx: dict[str, Any], page_title: str, page_type: str) -> str:
    loc = ctx["location_hint"]
    name = ctx["project_name"]
    sector = ctx["sector_display"]
    if page_type == "homepage":
        if loc:
            return f"{loc.lower()} {sector}"
        return f"{name.lower()} {sector}"
    if loc:
        return f"{loc.lower()} {page_title.lower()}"
    return f"{name.lower()} {page_title.lower()}"


def _schema_type(sector: str, page_type: str) -> str:
    if page_type in _PAGE_SCHEMA_OVERRIDE:
        return _PAGE_SCHEMA_OVERRIDE[page_type]
    if page_type in ("category", "product"):
        return _SECTOR_SCHEMA_ALT.get(sector, _SECTOR_SCHEMA.get(sector, "WebPage"))
    return _SECTOR_SCHEMA.get(sector, "Organization")


def _page_intent(page_type: str, sector: str) -> str:
    if page_type in _INTENT_BY_PAGE:
        return _INTENT_BY_PAGE[page_type]
    if sector == "ecommerce":
        return "commercial"
    return "informational"


def seed_page_metadata(page: dict[str, Any], ctx: dict[str, Any]) -> None:
    page_type = page.get("type", "page")
    title = page.get("title", "")
    keyword = _target_keyword(ctx, title, page_type)
    snippet = ctx["brief_snippet"] or ctx["sector_value"]

    seo = page.setdefault("seo", {})
    if not seo.get("title"):
        seo["title"] = ctx["project_name"] if page_type == "homepage" else f"{title} | {ctx['project_name']}"
    seo["description"] = seo.get("description") or f"{ctx['project_name']} — {snippet}"
    seo["target_keyword"] = keyword
    seo["intent"] = _page_intent(page_type, ctx["sector"])
    seo["schema_type"] = _schema_type(ctx["sector"], page_type)
    seo.setdefault("index", True)

    geo = page.setdefault("geo", {})
    geo["entity_type"] = _SECTOR_ENTITY.get(ctx["sector"], "Organization")
    geo["location_hint"] = ctx["location_hint"]
    geo["topic_cluster"] = f"{ctx['sector']}_{page_type}"
    geo["support_network_needed"] = ctx["sector"] in _GEO_CLUSTER_SECTORS


def _hero_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    page_type = page.get("type", "page")
    page_title = page.get("title", "")
    loc = ctx["location_hint"]
    ctas = ctx["ctas"]
    eyebrow = (
        f"{loc}'da özel bir deneyim" if loc
        else (ctx["creative_brief"][:72] if ctx["creative_brief"] else f"{ctx['sector_display'].title()} odaklı hizmet")
    )
    if page_type == "homepage":
        title = f"{ctx['project_name']} ile {ctx['sector_value']}"
    else:
        title = f"{page_title} — {ctx['project_name']}"
    subtitle = ctx["brief_snippet"] or ctx["sector_value"]
    keyword = _target_keyword(ctx, page_title, page_type)
    return {
        "id": _new_id("block"),
        "type": "hero",
        "status": "draft",
        "content": {
            "eyebrow": eyebrow,
            "title": title,
            "subtitle": subtitle,
            "primary_cta": ctas["primary"],
            "secondary_cta": ctas["secondary"],
        },
        "settings": {
            "layout": "full_bleed" if page_type == "homepage" else "contained",
            "visual_style": ctx["visual_style"],
            "media_type": "image",
        },
        "seo": _block_seo(ctx, keyword=keyword),
        "geo": _block_geo(ctx, block_type="hero"),
    }


def _cta_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    ctas = ctx["ctas"]
    keyword = _target_keyword(ctx, page.get("title", ""), page.get("type", "page"))
    return {
        "id": _new_id("block"),
        "type": "cta",
        "status": "draft",
        "content": {
            "title": "Hemen başlayın",
            "body": ctx["brief_snippet"] or f"{ctx['project_name']} ile {ctx['sector_value']}.",
            "primary_cta": ctas["primary"],
            "secondary_cta": ctas["tertiary"],
        },
        "settings": {"layout": "band", "visual_style": ctx["visual_style"]},
        "seo": _block_seo(ctx, keyword=keyword),
        "geo": _block_geo(ctx, block_type="cta"),
    }


def _content_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    page_title = page.get("title", "")
    keyword = _target_keyword(ctx, page_title, page.get("type", "page"))
    return {
        "id": _new_id("block"),
        "type": "content",
        "status": "draft",
        "content": {
            "title": page_title,
            "body": ctx["brief_snippet"] or f"{ctx['project_name']} hakkında detaylı bilgi.",
        },
        "settings": {"layout": "prose", "visual_style": ctx["visual_style"]},
        "seo": _block_seo(ctx, keyword=keyword, intent="informational"),
        "geo": _block_geo(ctx, block_type="content"),
    }


def _faq_preview_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    keyword = _target_keyword(ctx, "sss", "faq")
    return {
        "id": _new_id("block"),
        "type": "faq_preview",
        "status": "draft",
        "content": {
            "title": "Sık sorulan sorular",
            "items": [
                {
                    "question": f"{ctx['project_name']} nasıl rezervasyon yapılır?",
                    "answer": ctx["brief_snippet"] or f"{ctx['project_name']} web sitesi veya iletişim kanalları üzerinden ulaşabilirsiniz.",
                },
                {
                    "question": "İletişim bilgilerine nasıl ulaşırım?",
                    "answer": "İletişim sayfamızdan form doldurarak veya doğrudan arayarak bize ulaşabilirsiniz.",
                },
            ],
        },
        "settings": {"layout": "accordion", "max_items": 3},
        "seo": _block_seo(ctx, keyword=keyword, intent="informational"),
        "geo": _block_geo(ctx, block_type="faq_preview"),
    }


def _faq_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    keyword = _target_keyword(ctx, "sss", "faq")
    return {
        "id": _new_id("block"),
        "type": "faq",
        "status": "draft",
        "content": {
            "title": "Sık sorulan sorular",
            "items": [
                {
                    "question": f"{ctx['project_name']} nedir?",
                    "answer": ctx["brief_snippet"] or f"{ctx['project_name']}, {ctx['sector_value']} sunan bir markadır.",
                },
                {
                    "question": "Nasıl iletişime geçebilirim?",
                    "answer": "İletişim sayfamızdan form doldurarak veya CTA butonlarından bize ulaşabilirsiniz.",
                },
                {
                    "question": f"Hangi {ctx['sector_display']} hizmetleri sunuluyor?",
                    "answer": ctx["sector_value"].capitalize() + ".",
                },
            ],
        },
        "settings": {"layout": "accordion"},
        "seo": _block_seo(ctx, keyword=keyword, intent="informational"),
        "geo": _block_geo(ctx, block_type="faq"),
    }


def _blog_list_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    keyword = _target_keyword(ctx, "blog", "blog")
    return {
        "id": _new_id("block"),
        "type": "blog_list",
        "status": "draft",
        "content": {
            "title": "Son yazılar",
            "empty_message": "Yakında yeni içerikler eklenecek.",
        },
        "settings": {"layout": "grid", "columns": 3},
        "seo": _block_seo(ctx, keyword=keyword, intent="informational"),
        "geo": _block_geo(ctx, block_type="blog_list"),
    }


def _contact_form_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    ctas = ctx["ctas"]
    keyword = _target_keyword(ctx, "iletisim", "contact")
    return {
        "id": _new_id("block"),
        "type": "contact_form",
        "status": "draft",
        "content": {
            "title": "Bize ulaşın",
            "fields": ["name", "email", "phone", "message"],
            "submit_label": ctas["primary"],
        },
        "settings": {"layout": "split", "visual_style": ctx["visual_style"]},
        "seo": _block_seo(ctx, keyword=keyword, intent="navigational"),
        "geo": _block_geo(ctx, block_type="contact_form"),
    }


def _map_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    loc = ctx["location_hint"] or ctx["project_name"]
    keyword = _target_keyword(ctx, "konum", "contact")
    return {
        "id": _new_id("block"),
        "type": "map",
        "status": "draft",
        "content": {
            "title": "Konum",
            "location_label": loc,
            "map_provider": "openstreetmap",
        },
        "settings": {"layout": "full_width", "height": "medium"},
        "seo": _block_seo(ctx, keyword=keyword, intent="local"),
        "geo": {
            **_block_geo(ctx, block_type="map"),
            "location_hint": loc,
        },
    }


def _gallery_block(ctx: dict[str, Any], page: dict[str, Any]) -> dict[str, Any]:
    keyword = _target_keyword(ctx, page.get("title", "galeri"), page.get("type", "page"))
    return {
        "id": _new_id("block"),
        "type": "gallery",
        "status": "draft",
        "content": {
            "title": page.get("title", "Galeri"),
            "caption": ctx["brief_snippet"] or f"{ctx['project_name']} görsel galerisi.",
        },
        "settings": {"layout": "masonry", "columns": 3},
        "seo": _block_seo(ctx, keyword=keyword),
        "geo": _block_geo(ctx, block_type="gallery"),
    }


_SECTION_BUILDERS: dict[str, Any] = {
    "hero": _hero_block,
    "cta": _cta_block,
    "content": _content_block,
    "faq_preview": _faq_preview_block,
    "faq": _faq_block,
    "blog_list": _blog_list_block,
    "form": _contact_form_block,
    "contact_form": _contact_form_block,
    "map": _map_block,
    "gallery": _gallery_block,
}


def blocks_for_section(
    section_type: str,
    *,
    page: dict[str, Any],
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    page_type = page.get("type", "page")

    if page_type == "legal" and section_type in ("content", "hero"):
        return [_content_block(ctx, page)]

    builder = _SECTION_BUILDERS.get(section_type)
    if builder:
        return [builder(ctx, page)]

    # Unknown section — hero + content fallback
    if section_type not in ("hero",):
        return [_content_block(ctx, page)]
    return [_hero_block(ctx, page)]


def seed_project_blocks(project: dict[str, Any]) -> dict[str, Any]:
    """Fill empty section blocks and page SEO/GEO metadata. Mutates project in place."""
    ctx = _build_context(project)
    pages = project.get("pages") or []
    filled_sections = 0
    filled_blocks = 0

    for page in pages:
        seed_page_metadata(page, ctx)
        for section in page.get("sections") or []:
            if section.get("blocks"):
                continue
            stype = section.get("type", "content")
            blocks = blocks_for_section(stype, page=page, ctx=ctx)
            section["blocks"] = blocks
            section["status"] = "draft"
            filled_sections += 1
            filled_blocks += len(blocks)

    return {
        "filled_sections": filled_sections,
        "filled_blocks": filled_blocks,
        "llm_used": False,
    }
