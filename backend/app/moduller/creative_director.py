"""HIVE V3 Creative Director — brief'ten tasarım önerileri."""

from __future__ import annotations

import json
import re
from typing import Any

from app.moduller import llm_router

_BRIEF_KEYWORDS: list[tuple[list[str], dict[str, str]]] = [
    (["lüks", "luxury", "butik", "premium", "5 yıldız"], {
        "design_dna": "hotel_luxury",
        "color_identity": "gold_luxury",
        "font_style": "serif",
    }),
    (["klinik", "diş", "sağlık", "doktor", "hastane"], {
        "design_dna": "medical_clean",
        "color_identity": "ocean_blue",
        "font_style": "sans",
    }),
    (["e-ticaret", "ecommerce", "ürün", "mağaza", "satış"], {
        "design_dna": "marketplace",
        "color_identity": "sunset_orange",
        "font_style": "sans",
    }),
    (["emlak", "konut", "satılık", "kiralık"], {
        "design_dna": "corporate",
        "color_identity": "titanium_gray",
        "font_style": "sans",
    }),
    (["restoran", "menü", "yemek", "cafe"], {
        "design_dna": "bold",
        "color_identity": "sunset_orange",
        "font_style": "sans",
    }),
    (["blog", "yazar", "içerik"], {
        "design_dna": "editorial",
        "color_identity": "pure_white",
        "font_style": "serif",
    }),
]

_SECTOR_DEFAULTS: dict[str, dict[str, str]] = {
    "otel": {"design_dna": "hotel_luxury", "color_identity": "gold_luxury", "font_style": "serif"},
    "ecommerce": {"design_dna": "marketplace", "color_identity": "sunset_orange", "font_style": "sans"},
    "emlak": {"design_dna": "corporate", "color_identity": "titanium_gray", "font_style": "sans"},
    "klinik": {"design_dna": "medical_clean", "color_identity": "ocean_blue", "font_style": "sans"},
    "veteriner": {"design_dna": "medical_clean", "color_identity": "emerald_green", "font_style": "sans"},
    "restoran": {"design_dna": "bold", "color_identity": "sunset_orange", "font_style": "sans"},
    "rentacar": {"design_dna": "modern_startup", "color_identity": "midnight_black", "font_style": "sans"},
    "ilan": {"design_dna": "marketplace", "color_identity": "ocean_blue", "font_style": "sans"},
    "blog": {"design_dna": "editorial", "color_identity": "pure_white", "font_style": "serif"},
    "kurumsal": {"design_dna": "corporate", "color_identity": "titanium_gray", "font_style": "sans"},
    "ozel": {"design_dna": "modern_startup", "color_identity": "royal_purple", "font_style": "sans"},
}


def _rule_suggest(*, sector: str, business_brief: str, creative_brief: str) -> dict[str, Any]:
    text = f"{business_brief} {creative_brief}".lower()
    base = dict(_SECTOR_DEFAULTS.get(sector, _SECTOR_DEFAULTS["ozel"]))
    personalities: list[str] = []
    if any(w in text for w in ("güven", "profesyonel", "kurumsal")):
        personalities.append("guven_veren")
    if any(w in text for w in ("lüks", "premium", "butik")):
        personalities.extend(["premium", "ultra_luks"])
    if any(w in text for w in ("samimi", "sıcak", "yerel")):
        personalities.append("samimi")
    if any(w in text for w in ("modern", "genç", "dinamik")):
        personalities.append("modern")

    for keywords, overrides in _BRIEF_KEYWORDS:
        if any(k in text for k in keywords):
            base.update(overrides)
            break

    conversion_goal = "marka"
    if any(w in text for w in ("rezervasyon", "randevu")):
        conversion_goal = "rezervasyon"
    elif any(w in text for w in ("satış", "ürün", "e-ticaret")):
        conversion_goal = "urun_sat"
    elif any(w in text for w in ("lead", "teklif", "form")):
        conversion_goal = "lead_topla"
    elif any(w in text for w in ("whatsapp")):
        conversion_goal = "whatsapp"
    elif any(w in text for w in ("seo", "organik")):
        conversion_goal = "seo_dominasyon"
    elif any(w in text for w in ("yerel", "geo", "harita")):
        conversion_goal = "yerel_liderlik"

    hero_tone = creative_brief.strip() or business_brief.strip()[:200] or "Güven ve kalite hissi"
    return {
        "design_dna": base.get("design_dna", "modern_startup"),
        "color_identity": base.get("color_identity", "ocean_blue"),
        "font_style": base.get("font_style", "sans"),
        "brand_personality": list(dict.fromkeys(personalities))[:4] or ["guven_veren", "modern"],
        "conversion_goal": conversion_goal,
        "hero_tone": hero_tone,
        "cta_language": "Net ve güven veren CTA",
        "source": "rules",
    }


def suggest(
    *,
    sector: str,
    business_brief: str = "",
    creative_brief: str = "",
    use_llm: bool = True,
) -> dict[str, Any]:
    base = _rule_suggest(sector=sector, business_brief=business_brief, creative_brief=creative_brief)
    if not use_llm:
        return {"success": True, "suggestions": base}

    prompt = (
        f"Sektör: {sector}\nİş özeti: {business_brief}\nCreative brief: {creative_brief}\n\n"
        "JSON döndür: design_dna, color_identity, font_style (sans|serif), "
        "brand_personality (dizi), conversion_goal, hero_tone, cta_language.\n"
        "design_dna seçenekleri: luxury, premium, modern_startup, corporate, minimal, editorial, "
        "bold, dark_elite, hotel_luxury, fashion_elegant, marketplace, medical_clean, nightlife.\n"
        "color_identity: gold_luxury, midnight_black, emerald_green, ocean_blue, sunset_orange, "
        "royal_purple, titanium_gray, pure_white."
    )
    try:
        text, engine = llm_router.generate(
            prompt,
            system="HIVE Creative Director. Sadece geçerli JSON.",
            max_tokens=500,
        )
        if text:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                data = json.loads(m.group())
                merged = {**base, **{k: v for k, v in data.items() if v}}
                merged["source"] = f"llm:{engine}" if engine else "llm"
                return {"success": True, "suggestions": merged}
    except Exception:
        pass
    return {"success": True, "suggestions": base}
