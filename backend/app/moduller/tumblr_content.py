"""Tumblr otomatik içerik — SEO/GEO uyumlu üretim + yayın."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from app import config
from app.moduller.modul_base import simdi
from app.moduller.tumblr_api import post_to_tumblr, _resolve_blog_name

logger = logging.getLogger("hive.tumblr.content")

SYSTEM_PROMPT = """Sen BalKutusu.com için Tumblr'da yayınlanacak SEO ve GEO uyumlu blog yazıları üreten bir içerik motorusun.

Görev: Verilen konu, şehir ve yerel bağlam ile Tumblr'a uygun kısa-orta uzunlukta (350-550 kelime) özgün yazı üret.

Kurallar:
- Türkçe yaz, doğal ve bilgilendirici ton.
- Yerel GEO sinyalleri kullan: mahalle, ilçe, semt, ulaşım, sezon, gece hayatı vb.
- Anahtar kelimeyi başlık, ilk paragraf ve bir H2'de geçir.
- Abartılı vaat yok: "en iyi", "garanti", "kesin" kullanma.
- Uydurma telefon, adres, fiyat verme.
- Son paragrafta site linkini doğal şekilde geçir.
- HTML kullan: <h2>, <p>, <ul><li> — sadece bu etiketler.
- Tumblr etiketleri: 8-12 adet, virgülle ayrılmış, küçük harf tercih.

Çıktı formatı (aynen bu başlıklar):
BAŞLIK: (60 karakter max)
ETİKETLER: etiket1, etiket2, etiket3
İÇERİK:
<p>...</p>"""


def _ollama_generate(prompt: str) -> tuple[str, bool]:
    from app.moduller import llm_router
    text, engine = llm_router.generate(prompt, system=SYSTEM_PROMPT, max_tokens=2000, min_length=80)
    if not text:
        logger.warning("Tumblr içerik: AI motoru yanıt vermedi")
    return text, bool(text and engine)


def _talon_context(topic: str, city: str) -> dict[str, Any]:
    seed = f"{city} {topic}".strip()
    ctx: dict[str, Any] = {
        "local_keywords": [],
        "geo_places": [],
        "faq_ideas": [],
    }
    try:
        from app.moduller.talon_stack.services.talon_search_service import talon_search_service

        geo = talon_search_service.geo_seo_research(seed, {})
        ctx["geo_places"] = [
            (p.get("title") or "")[:80]
            for p in (geo.get("recommendedPages") or [])[:8]
            if p.get("title")
        ]
        ctx["local_keywords"] = (geo.get("localKeywords") or [])[:12]

        faq = talon_search_service.generate_faq_ideas(seed, {})
        ctx["faq_ideas"] = (faq.get("peopleAlsoAskQuestions") or [])[:6]
    except Exception as e:
        logger.debug("Talon context atlandı: %s", e)
    return ctx


def _parse_generated(raw: str) -> dict[str, Any]:
    title = ""
    tags: list[str] = []
    content = ""

    m_title = re.search(r"BAŞLIK:\s*(.+)", raw, re.I)
    if m_title:
        title = m_title.group(1).strip()[:120]

    m_tags = re.search(r"ETİKETLER:\s*(.+)", raw, re.I)
    if m_tags:
        tags = [t.strip() for t in m_tags.group(1).split(",") if t.strip()][:15]

    m_body = re.search(r"İÇERİK:\s*(.+)", raw, re.S | re.I)
    if m_body:
        content = m_body.group(1).strip()
    elif "<p>" in raw or "<h2>" in raw:
        content = raw.strip()

    if content and not content.startswith("<"):
        content = f"<p>{content}</p>"

    return {"title": title, "tags": tags, "content": content}


def _fallback_content(
    topic: str,
    city: str,
    district: str,
    site_url: str,
    ctx: dict[str, Any],
    extra_keywords: list[str],
) -> dict[str, Any]:
    loc = f"{district}, {city}".strip(", ") if district else city
    places = ctx.get("geo_places") or [
        "Kuşadası Merkez", "Kadınlar Denizi", "Marina", "Atatürk Bulvarı",
    ]
    kws = list(dict.fromkeys(
        [topic, city, district, f"{city} gece hayatı", f"{city} rehber"]
        + extra_keywords
        + (ctx.get("local_keywords") or [])[:5]
    ))
    kws = [k for k in kws if k][:12]

    title = f"{topic} — {loc} rehberi"[:60]
    place_txt = ", ".join(places[:4])
    faq = (ctx.get("faq_ideas") or ["Nerede bulunur?", "Ne zaman gidilir?"])[0]

    content = f"""<p>{loc} bölgesinde <strong>{topic}</strong> arayanlar için hazırlanan bu rehber, yerel GEO sinyalleri ve güncel arama niyetlerine göre derlendi. {city} ve çevresinde plan yaparken semt bazlı düşünmek önemlidir.</p>
<h2>{topic} ve {city} bölgesi</h2>
<p>Öne çıkan lokasyonlar: {place_txt}. Ulaşım, sezon ve gece planı yaparken bu noktaları referans alabilirsiniz. {faq} sorusu da sık aranan başlıklar arasında.</p>
<h2>Pratik öneriler</h2>
<ul>
<li>Randevu ve buluşma noktasını önceden netleştirin.</li>
<li>Yoğun sezonda erken planlama yapın.</li>
<li>Güvenilir kaynaklardan bilgi alın; acele karar vermeyin.</li>
</ul>
<p>Daha fazla yerel içerik ve güncel rehberler için <a href="{site_url}">balkutusu.com</a> ana portalını ziyaret edebilirsiniz.</p>"""

    return {
        "title": title,
        "content": content,
        "tags": kws,
        "ai_ollama": False,
        "mode": "template+talon",
    }


def generate_tumblr_content(
    topic: str,
    city: str = "Kuşadası",
    district: str = "",
    site_url: str = "",
    extra_keywords: list[str] | None = None,
) -> dict[str, Any]:
    topic = (topic or "").strip()
    if not topic:
        return {"success": False, "error": "Konu/topic gerekli"}

    city = (city or "Kuşadası").strip()
    district = (district or "").strip()
    site_url = (site_url or config.get("WP_URL") or "https://www.balkutusu.com").strip().rstrip("/")
    extra = [k.strip() for k in (extra_keywords or []) if k and str(k).strip()]

    ctx = _talon_context(topic, city)
    loc = f"{district}, {city}".strip(", ") if district else city

    prompt = f"""Konu: {topic}
Şehir: {city}
İlçe/Semt: {district or "belirtilmedi"}
Site linki: {site_url}
Yan anahtar kelimeler: {", ".join(extra) if extra else "yok"}
Yerel GEO noktaları: {", ".join(ctx.get("geo_places") or []) or "Kuşadası merkez, marina, sahil"}
Yerel anahtar kelimeler: {", ".join(ctx.get("local_keywords") or [])}
SSS fikirleri: {"; ".join(ctx.get("faq_ideas") or [])}

{loc} odağında Tumblr yazısı üret. BAŞLIK, ETİKETLER ve İÇERİK formatına uy."""

    raw, ai_used = _ollama_generate(prompt)
    if ai_used and raw:
        parsed = _parse_generated(raw)
        if parsed.get("content"):
            result = {
                "success": True,
                "title": parsed["title"] or f"{loc} {topic}"[:60],
                "content": parsed["content"],
                "tags": parsed["tags"] or extra or [topic, city, "kusadasi", "rehber"],
                "ai_ollama": True,
                "mode": "ollama+talon",
                "talon_context": ctx,
                "generated_at": simdi(),
            }
            if site_url not in result["content"]:
                result["content"] += f'\n<p><a href="{site_url}">balkutusu.com</a></p>'
            return result

    fb = _fallback_content(topic, city, district, site_url, ctx, extra)
    return {
        "success": True,
        **fb,
        "talon_context": ctx,
        "generated_at": simdi(),
    }


def auto_publish(
    topic: str,
    city: str = "Kuşadası",
    district: str = "",
    site_url: str = "",
    extra_keywords: list[str] | None = None,
    blog_name: str = "",
    state: str = "published",
) -> dict[str, Any]:
    generated = generate_tumblr_content(
        topic=topic,
        city=city,
        district=district,
        site_url=site_url,
        extra_keywords=extra_keywords,
    )
    if not generated.get("success"):
        return generated

    blog = _resolve_blog_name(blog_name or config.get("TUMBLR_DEFAULT_BLOG") or "")
    try:
        resp = post_to_tumblr(
            blog_name=blog,
            content=generated["content"],
            title=generated["title"],
            tags=generated.get("tags") or [],
            state=state,
        )
        post_id = (resp.get("response") or {}).get("id")
        return {
            "success": True,
            "published": True,
            "post_id": post_id,
            "blog_name": blog,
            "title": generated["title"],
            "tags": generated.get("tags"),
            "mode": generated.get("mode"),
            "ai_ollama": generated.get("ai_ollama", False),
            "content_preview": generated["content"][:400],
            "response": resp,
        }
    except Exception as e:
        return {
            "success": False,
            "published": False,
            "error": str(e),
            "generated": generated,
        }
