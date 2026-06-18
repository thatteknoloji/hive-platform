"""Entity Detail Page Generator — Tier 1 mekan/entity rehber sayfaları.

ÖNEMLİ: Bu modül Listing Hub ile entegre DEĞİLDİR ve asla ilan oluşturmaz.
Üretilen sayfalar entity rehber sayfasıdır (/rehber/{slug}).
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse

from app.moduller.storyforge_categories import _slugify

logger = logging.getLogger("hive.entity_detail_generator")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = Path(__file__).resolve().parent.parent / "entity_detail_generator_state.json"
REPORTS_DIR = ROOT / "reports"

TIER1_THRESHOLD = 70
MIN_WORD_TARGET = 1200
DUPLICATE_THRESHOLD = 0.82

IMPORTANT_REGIONS = (
    "barlar sokağı", "marina", "kadınlar denizi", "kaleiçi", "davutlar",
    "güzelçamlı", "long beach", "güvercinada", "merkez",
)

SECTOR_ANALYSIS_KEYWORDS = (
    "analiz", "sektör", "değerlendirme", "öne çıkan", "karşılaştırma",
    "rehber", "inceleme", "profil",
)

CATEGORY_VALUES = {
    "gece hayatı": 12, "bar": 12, "pub": 10, "kulüp": 11, "beach club": 11,
    "restoran": 10, "kafe": 9, "otel": 10, "canlı müzik": 9, "marina": 10, "plaj": 10,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("jobs", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"jobs": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_job(job_id: str) -> dict[str, Any] | None:
    return (_load_state().get("jobs") or {}).get(job_id)


def _update_job(job_id: str, **fields: Any) -> dict[str, Any]:
    state = _load_state()
    job = state["jobs"].setdefault(job_id, {"id": job_id})
    job.update(fields)
    job["updated_at"] = _now()
    state["jobs"][job_id] = job
    _save_state(state)
    return job


def _new_job_id() -> str:
    return f"edg-{uuid.uuid4().hex[:12]}"


def _entity_id(name: str) -> str:
    return f"ent-{_slugify(name)[:40] or uuid.uuid4().hex[:8]}"


def _default_video_url() -> str:
    from app.moduller.listing_hub import _default_video_url as lh_default
    return lh_default()


def _build_map_embed(name: str, address: str = "", city: str = "Kuşadası") -> str:
    from app.moduller.listing_hub import build_map_embed
    listing = {"address": address or f"{name}, {city}", "city": city, "district": city, "country": "Türkiye"}
    return build_map_embed(listing) or f"https://maps.google.com/maps?q={quote_plus(f'{name} {city}')}&output=embed"


def _video_embed(video_url: str = "") -> tuple[str, str]:
    from app.moduller.listing_hub import normalize_youtube_url
    url = (video_url or "").strip() or _default_video_url()
    return normalize_youtube_url(url)


def _load_place_seo_job(source_job_id: str) -> dict[str, Any] | None:
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    detail = place_seo_pipeline.get_job_detail(source_job_id)
    if not detail.get("success"):
        return None
    return detail.get("job")


def _corpus_from_place_job(place_job: dict[str, Any]) -> str:
    chunks: list[str] = []
    parsed = place_job.get("parse") or {}
    for key in ("raw_text", "paragraphs", "headings"):
        val = parsed.get(key)
        if isinstance(val, str):
            chunks.append(val)
        elif isinstance(val, list):
            chunks.extend(str(x) for x in val)
    for tbl in parsed.get("tables") or []:
        for row in tbl:
            chunks.extend(str(c) for c in row)
    return "\n".join(chunks)


def _extract_website(text: str) -> str:
    m = re.search(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", text, re.I)
    return m.group(0).rstrip(".,)") if m else ""


def _extract_instagram(text: str) -> str:
    m = re.search(r"(?:https?://)?(?:www\.)?instagram\.com/[A-Za-z0-9_.]+", text, re.I)
    return m.group(0) if m else ""


def _extract_address(text: str) -> str:
    patterns = [
        r"(?:adres|address)[:\s]+([^\n]{10,120})",
        r"((?:Mah\.|Mahalle|Cad\.|Cadde|Sok\.|Sokak|No:?\s*\d+)[^\n]{5,100})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).strip()
    return ""


def _guess_category(name: str, corpus: str, signals: dict[str, Any]) -> str:
    name_l = name.lower()
    corpus_l = corpus.lower()
    for cat in signals.get("categories") or []:
        if cat in name_l or cat in corpus_l:
            return cat
    hints = (
        ("club", "gece hayatı"), ("bar", "bar"), ("pub", "pub"), ("restaurant", "restoran"),
        ("restoran", "restoran"), ("hotel", "otel"), ("otel", "otel"), ("plaj", "plaj"),
        ("beach", "beach club"), ("kafe", "kafe"), ("cafe", "kafe"),
    )
    for hint, cat in hints:
        if hint in name_l:
            return cat
    cats = signals.get("categories") or []
    return cats[0] if cats else "gece hayatı"


def _guess_location(name: str, context: str, signals: dict[str, Any]) -> str:
    ctx = context.lower()
    for region in IMPORTANT_REGIONS:
        if region in ctx:
            return region.title() if region.islower() else region
    for loc in signals.get("locations") or []:
        if loc.lower() in ctx or loc.lower() in name.lower():
            return loc
    locs = signals.get("locations") or ["Kuşadası"]
    return locs[0]


def _entity_context(name: str, corpus: str, window: int = 400) -> str:
    idx = corpus.lower().find(name.lower())
    if idx < 0:
        return ""
    start = max(0, idx - window)
    end = min(len(corpus), idx + len(name) + window)
    return corpus[start:end]


def _entity_lines(name: str, corpus: str) -> str:
    lines = corpus.splitlines()
    for i, ln in enumerate(lines):
        if name.lower() in ln.lower():
            return "\n".join(lines[i : i + 3])
    paragraphs = re.split(r"\n\s*\n", corpus)
    for para in paragraphs:
        if name.lower() in para.lower():
            return para.strip()
    return _entity_context(name, corpus, window=180)


def _enrich_entity(name: str, corpus: str, signals: dict[str, Any]) -> dict[str, Any]:
    entity_block = _entity_lines(name, corpus)
    ctx = _entity_context(name, corpus)
    block_l = (ctx or entity_block).lower()
    return {
        "id": _entity_id(name),
        "name": name.strip(),
        "category": _guess_category(name, entity_block or ctx or name, signals),
        "location": _guess_location(name, entity_block or ctx or corpus, signals),
        "website": _extract_website(entity_block),
        "instagram": _extract_instagram(entity_block),
        "address": _extract_address(entity_block),
        "in_sector_analysis": bool(ctx) and any(k in block_l for k in SECTOR_ANALYSIS_KEYWORDS),
        "region_linked": bool(ctx) and any(r in block_l for r in IMPORTANT_REGIONS),
        "tier1_score": 0,
        "tier1_selected": False,
        "manual_override": False,
        "page_status": "pending",
        "quality_score": 0,
        "deploy_allowed": False,
        "slug": f"rehber/{_slugify(f'{name} kusadasi')}",
        "target_keywords": [
            f"{name} Kuşadası",
            f"{name} nerede",
        ],
    }


def score_tier1(entity: dict[str, Any], signals: dict[str, Any]) -> int:
    score = 0
    if entity.get("website"):
        score += 15
    if entity.get("instagram"):
        score += 10
    if entity.get("address"):
        score += 15
    cat = (entity.get("category") or "").lower()
    score += CATEGORY_VALUES.get(cat, 4)
    if entity.get("location") and entity["location"].lower() != "kuşadası":
        score += 10
    elif signals.get("locations"):
        score += 3
    if entity.get("in_sector_analysis"):
        score += 10
    if entity.get("region_linked"):
        score += 10
    if cat in (signals.get("categories") or []):
        score += 5
    score += min(6, len(signals.get("locations") or []) * 2)
    if entity.get("website") and entity.get("address"):
        score += 8
    if not entity.get("website") and not entity.get("instagram") and not entity.get("address"):
        score = min(score, 45)
    return min(100, score)


def _entities_from_place_job(place_job: dict[str, Any]) -> list[dict[str, Any]]:
    signals = place_job.get("signals") or {}
    corpus = _corpus_from_place_job(place_job)
    names = list(dict.fromkeys(signals.get("entities") or []))
    entities: list[dict[str, Any]] = []
    for name in names:
        ent = _enrich_entity(name, corpus, signals)
        ent["tier1_score"] = score_tier1(ent, signals)
        cat = ent.get("category") or "gece hayatı"
        ent["target_keywords"].append(f"{cat} Kuşadası")
        entities.append(ent)
    return entities


def _graph_context(entity: dict[str, Any], main_site_url: str) -> dict[str, Any]:
    try:
        from app.moduller.entity_geo_graph import entity_geo_graph
        loc = entity.get("location") or "Kuşadası"
        seed = entity.get("name", "")
        geo = entity_geo_graph.geo_expand(loc, radius_km=15, seed_keyword=seed)
        missing = entity_geo_graph.missing_entities(location=loc, seed_keyword=seed)
        links = entity_geo_graph.internal_link_plan("", max_links_per_page=5)
        return {
            "related_locations": [g.get("name", "") for g in (geo.get("geo_entities") or [])[:5]],
            "topic_clusters": [p.get("title", "") for p in (missing.get("recommended_pages") or [])[:5]],
            "internal_links": (links.get("links") or [])[:5],
            "main_site_url": main_site_url,
        }
    except Exception as exc:
        logger.warning("Entity graph context: %s", exc)
        return {"related_locations": [], "topic_clusters": [], "internal_links": [], "main_site_url": main_site_url}


def _is_duplicate_content(text: str, others: list[str], threshold: float = DUPLICATE_THRESHOLD) -> bool:
    t = (text or "").lower().strip()
    if len(t) < 80:
        return False
    for other in others:
        if SequenceMatcher(None, t, other.lower()).ratio() >= threshold:
            return True
    return False


def _word_count(html: str) -> int:
    plain = re.sub(r"<[^>]+>", " ", html or "")
    return len(re.findall(r"\w+", plain, re.UNICODE))


def _build_schemas(entity: dict[str, Any], main_site_url: str, faq_items: list[dict[str, str]]) -> dict[str, Any]:
    domain = main_site_url.rstrip("/") or "https://www.balkutusu.com"
    slug = entity.get("slug", "")
    page_url = f"{domain}/{slug.strip('/')}/"
    name = entity.get("name", "")
    title = f"{name} Kuşadası rehberi"
    cat = entity.get("category") or "Place"
    schema_type = "Hotel" if "otel" in cat else "Restaurant" if "restoran" in cat else "BarOrPub" if "bar" in cat else "Place"

    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "about": {"@type": "Place", "name": name, "address": entity.get("address") or f"{name}, Kuşadası"},
        "url": page_url,
    }
    place = {
        "@context": "https://schema.org",
        "@type": schema_type if schema_type != "Place" else "LocalBusiness",
        "name": name,
        "address": entity.get("address") or f"{name}, Kuşadası, Aydın",
        "url": entity.get("website") or page_url,
    }
    if entity.get("address"):
        place["address"] = {"@type": "PostalAddress", "streetAddress": entity["address"], "addressLocality": "Kuşadası", "addressRegion": "Aydın", "addressCountry": "TR"}
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ana Sayfa", "item": domain + "/"},
            {"@type": "ListItem", "position": 2, "name": "Rehber", "item": f"{domain}/rehber/"},
            {"@type": "ListItem", "position": 3, "name": title, "item": page_url},
        ],
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
            for q in faq_items[:6]
        ],
    }
    return {"article": article, "place": place, "breadcrumb": breadcrumb, "faq": faq_schema}


def _default_faq(entity: dict[str, Any]) -> list[dict[str, str]]:
    name = entity.get("name", "")
    loc = entity.get("location") or "Kuşadası"
    cat = entity.get("category") or "mekan"
    return [
        {"q": f"{name} nerede?", "a": f"{name}, Kuşadası {loc} bölgesinde konumlanır. Detaylı konum ipuçları sayfada yer alır."},
        {"q": f"{name} hangi deneyim için uygundur?", "a": f"{name}, Kuşadası {cat} deneyimi arayan ziyaretçiler için değerlendirilebilir."},
        {"q": f"{name} Kuşadası rehberi güvenilir mi?", "a": "Bu sayfa bölgesel rehber formatında hazırlanmıştır; resmi rezervasyon için işletmenin kendi kanallarını kullanın."},
    ]


def _llm_generate_entity_content(entity: dict[str, Any], graph_ctx: dict[str, Any], main_site_url: str, existing: list[str]) -> tuple[str, list[dict[str, str]]]:
    name = entity.get("name", "")
    loc = entity.get("location") or "Kuşadası"
    cat = entity.get("category") or "mekan"
    related = ", ".join(graph_ctx.get("related_locations") or []) or "Kuşadası merkez, Marina, Kadınlar Denizi"
    topics = ", ".join(graph_ctx.get("topic_clusters") or []) or f"{cat} rehberi"
    domain = urlparse(main_site_url).netloc or "balkutusu.com"

    prompt = (
        f"Kuşadası entity rehber sayfası yaz. Mekan: {name}\n"
        f"Kategori: {cat}\nBölge: {loc}\nAdres: {entity.get('address') or 'belirtilmemiş'}\n"
        f"Web: {entity.get('website') or 'yok'} | Instagram: {entity.get('instagram') or 'yok'}\n"
        f"İlişkili lokasyonlar: {related}\nTopic cluster: {topics}\n"
        f"Minimum 1200 kelime hedefle. Şablon giriş paragrafı kullanma — {name} için özgün yaz.\n"
        f"HTML bölümleri (h2 başlıklarıyla):\n"
        "1. Kısa answer box (div class=answer-box)\n"
        "2. Mekan/entity nedir?\n"
        "3. Kuşadası içindeki konumu ve önemi\n"
        "4. Hangi kategori/deneyim içinde değerlendirilir?\n"
        "5. Kimler için uygun?\n"
        "6. Bölge/GEO bağlamı\n"
        "7. Yakın bölge ve alternatif deneyimler\n"
        "8. Ulaşım/konum ipucu\n"
        "9. SSS (3 soru)\n"
        "10. Ana siteye doğal referans (link metni şablon olmasın)\n"
        "11. Kaynak/mention alanı\n"
        f"Ana site: {main_site_url} — doğal anchor ile 1 referans ver.\n"
        "Sadece HTML body içeriği döndür (html/head/body tag yok).\n"
        "SSS bölümünde her soru h3, cevap p olsun.\n"
    )
    faq_items = _default_faq(entity)
    html = ""
    engine = ""
    for attempt in range(3):
        try:
            from app.moduller import llm_router
            text, engine = llm_router.generate(prompt, max_tokens=3500, min_length=800)
            html = (text or "").strip()
            if html.startswith("```"):
                html = re.sub(r"^```(?:html)?\s*", "", html)
                html = re.sub(r"\s*```$", "", html)
            if _word_count(html) >= 400 and not _is_duplicate_content(html, existing):
                break
            prompt += f"\nDeneme {attempt + 2}: önceki metin çok kısa veya benzer — tamamen farklı açılış ve yapı kullan."
        except Exception as exc:
            logger.warning("LLM entity content: %s", exc)
            break

    if not html or _word_count(html) < 400:
        html = _fallback_entity_html(entity, graph_ctx, main_site_url, faq_items)
        engine = "fallback"

    return html, faq_items


def _fallback_entity_html(entity: dict[str, Any], graph_ctx: dict[str, Any], main_site_url: str, faq_items: list[dict[str, str]]) -> str:
    name = entity.get("name", "")
    loc = entity.get("location") or "Kuşadası"
    cat = entity.get("category") or "mekan"
    related = graph_ctx.get("related_locations") or ["Marina", "Barlar Sokağı"]
    parts = [
        f'<div class="answer-box"><p><strong>{name}</strong>, Kuşadası {loc} hattında {cat} deneyimi arayan ziyaretçilerin radarında olan bir entity rehber konusudur.</p></div>',
        f"<h2>{name} nedir?</h2><p>{name}, Kuşadası'nın {loc} çevresinde anılan ve bölgesel {cat} ekosisteminde referans gösterilen bir mekandır. "
        f"Bu sayfa ilan veya rezervasyon sayfası değil; ziyaretçinin karar vermesine yardımcı olacak derin rehber içeriğidir.</p>",
        f"<h2>Kuşadası içindeki konumu ve önemi</h2><p>{name}, {loc} bölgesinin akışına göre konumlanır. "
        f"Kuşadası'da {cat} arayan kullanıcılar için GEO sinyali güçlü bir çapa noktası oluşturur.</p>",
        f"<h2>Hangi kategori/deneyim?</h2><p>{cat.title()} kategorisinde değerlendirilir; gece hayatı, yeme-içme veya konaklama bağlamında "
        f"kullanıcı niyetine göre okunmalıdır.</p>",
        f"<h2>Kimler için uygun?</h2><p>Bölgeyi keşfetmek isteyen yerli ve yabancı ziyaretçiler, {cat} odaklı plan yapan gruplar ve "
        f"{loc} hattında alternatif arayanlar için uygundur.</p>",
        f"<h2>Bölge/GEO bağlamı</h2><p>{loc}, Kuşadası'nın {', '.join(related[:3])} ile bağlantılı micro-GEO ağında yer alır.</p>",
        f"<h2>Yakın bölge ve alternatifler</h2><p>Aynı bölgede {', '.join(related[:2])} ekseninde benzer deneyimler değerlendirilebilir.</p>",
        f"<h2>Ulaşım/konum ipucu</h2><p>{entity.get('address') or f'{name} için harita sorgusu: {name} Kuşadası'} — taksi, yürüyüş veya dolmuş hatları bölgeye göre değişir.</p>",
        "<h2>Sık sorulan sorular</h2>",
    ]
    for item in faq_items:
        parts.append(f"<h3>{item['q']}</h3><p>{item['a']}</p>")
    parts.append(
        f'<h2>Ana site referansı</h2><p>Kuşadası genel rehber ve güncel bölge içerikleri için '
        f'<a href="{main_site_url}">{urlparse(main_site_url).netloc or "ana site"}</a> üzerindeki otorite sayfalarına göz atın.</p>'
    )
    parts.append(f"<h2>Kaynak ve mention</h2><p>Bu rehber Place SEO Pipeline entity sinyalleri ve bölgesel kaynak taramasıyla üretilmiştir. İşletme: {name}.</p>")
    body = "\n".join(parts)
    while _word_count(body) < MIN_WORD_TARGET:
        body += (
            f"<p>{name} hakkında ek bağlam: Kuşadası {loc} bölgesinde {cat} deneyimi planlarken sezon, kalabalık ve "
            f"ulaşım faktörlerini birlikte değerlendirmek GEO uyumlu karar vermeyi kolaylaştırır.</p>"
        )
    return body


def _assemble_page_html(entity: dict[str, Any], body_html: str, faq_items: list[dict[str, str]], main_site_url: str) -> str:
    name = entity.get("name", "")
    title = f"{name} Kuşadası rehberi"
    watch, embed = _video_embed(entity.get("video_url", ""))
    map_url = _build_map_embed(name, entity.get("address", ""))
    schemas = _build_schemas(entity, main_site_url, faq_items)

    parts = [f"<h1>{title}</h1>", body_html]
    if embed:
        parts.append(f'<section class="entity-video"><iframe src="{embed}" title="{name} video" loading="lazy"></iframe></section>')
    if map_url:
        parts.append(f'<section class="entity-map"><iframe src="{map_url}" title="{name} harita" loading="lazy"></iframe></section>')
    for key in ("article", "place", "breadcrumb", "faq"):
        parts.append(f'<script type="application/ld+json">{json.dumps(schemas[key], ensure_ascii=False)}</script>')
    return "\n".join(parts)


def health() -> dict[str, Any]:
    wp_connected = False
    try:
        from app.moduller.wordpress_api import wp_api
        wp_connected = bool(wp_api().connected)
    except Exception:
        pass
    jobs = _load_state().get("jobs") or {}
    return {
        "success": True,
        "module": "entity_detail_generator",
        "publish_mode": "real",
        "wordpress_connected": wp_connected,
        "tier1_threshold": TIER1_THRESHOLD,
        "listing_hub_integration": False,
        "job_count": len(jobs),
    }


def list_jobs(limit: int = 20) -> dict[str, Any]:
    jobs = list((_load_state().get("jobs") or {}).values())
    jobs.sort(key=lambda j: j.get("updated_at") or j.get("created_at") or "", reverse=True)
    return {"success": True, "jobs": jobs[:limit]}


def get_job_detail(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    entities = job.get("entities") or []
    return {
        "success": True,
        "job": job,
        "summary": {
            "entity_count": len(entities),
            "tier1_candidates": sum(1 for e in entities if e.get("tier1_score", 0) >= TIER1_THRESHOLD),
            "tier1_selected": sum(1 for e in entities if e.get("tier1_selected")),
            "pages_generated": sum(1 for e in entities if e.get("page_status") == "generated"),
            "listing_hub_called": False,
        },
    }


def select_tier1(
    source_job_id: str,
    *,
    job_id: str = "",
    main_site_url: str = "https://www.balkutusu.com",
    threshold: int = TIER1_THRESHOLD,
    manual_selections: dict[str, bool] | None = None,
) -> dict[str, Any]:
    place_job = _load_place_seo_job(source_job_id.strip())
    if not place_job:
        return {"success": False, "error": "Place SEO Pipeline job bulunamadı veya sinyaller yok"}
    if not place_job.get("signals"):
        return {"success": False, "error": "Kaynak job'da sinyaller yok — önce Place SEO Pipeline extract-signals çalıştırın"}

    entities = _entities_from_place_job(place_job)
    manual = manual_selections or {}
    selected_count = 0
    for ent in entities:
        eid = ent["id"]
        if eid in manual:
            ent["tier1_selected"] = bool(manual[eid])
            ent["manual_override"] = True
        else:
            ent["tier1_selected"] = ent.get("tier1_score", 0) >= threshold
        if ent["tier1_selected"]:
            selected_count += 1

    jid = job_id.strip() or _new_job_id()
    job = _update_job(
        jid,
        id=jid,
        source_job_id=source_job_id.strip(),
        main_site_url=main_site_url.strip() or place_job.get("main_site_url", ""),
        status="tier1_selected",
        entities=entities,
        threshold=threshold,
        created_at=_now(),
        listing_hub_called=False,
    )
    return {
        "success": True,
        "job_id": jid,
        "entity_count": len(entities),
        "tier1_candidates": sum(1 for e in entities if e.get("tier1_score", 0) >= threshold),
        "tier1_selected": selected_count,
        "entities": entities,
        "listing_hub_called": False,
    }


def update_manual_selection(job_id: str, selections: dict[str, bool]) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    entities = job.get("entities") or []
    for ent in entities:
        if ent["id"] in selections:
            ent["tier1_selected"] = bool(selections[ent["id"]])
            ent["manual_override"] = True
    _update_job(job_id, entities=entities)
    return {
        "success": True,
        "job_id": job_id,
        "tier1_selected": sum(1 for e in entities if e.get("tier1_selected")),
        "entities": entities,
    }


def generate_pages(
    job_id: str,
    main_site_url: str = "",
    *,
    entity_ids: list[str] | None = None,
    publish_wordpress: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}

    url = (main_site_url or job.get("main_site_url") or "https://www.balkutusu.com").strip()
    entities = job.get("entities") or []
    targets = [e for e in entities if e.get("tier1_selected")]
    if entity_ids:
        ids = set(entity_ids)
        targets = [e for e in targets if e["id"] in ids]
    if not targets:
        return {"success": False, "error": "Tier 1 seçili entity yok"}

    wp = None
    if publish_wordpress:
        from app.moduller.wordpress_api import wp_api
        wp = wp_api()
        if not wp.connected:
            return {"success": False, "error": "WordPress bağlantısı yok"}

    existing_texts = [e.get("page", {}).get("html", "") for e in entities if e.get("page")]
    generated: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for ent in targets:
        graph_ctx = _graph_context(ent, url)
        body, faq_items = _llm_generate_entity_content(ent, graph_ctx, url, existing_texts)
        html = _assemble_page_html(ent, body, faq_items, url)
        wc = _word_count(html)
        existing_texts.append(html)

        page_data = {
            "html": html,
            "word_count": wc,
            "faq_items": faq_items,
            "schemas": _build_schemas(ent, url, faq_items),
            "graph_context": graph_ctx,
        }
        ent["page"] = page_data
        ent["page_status"] = "generated"
        ent["quality_score"] = 0
        ent["deploy_allowed"] = False

        entry = {"entity_id": ent["id"], "name": ent["name"], "slug": ent["slug"], "word_count": wc, "published": False}

        if publish_wordpress and wp:
            from app.moduller.page_hub import create_page
            title = f"{ent['name']} Kuşadası rehberi"
            res = create_page(
                "landing",
                title,
                slug=ent["slug"],
                content=html,
                keyword=ent["target_keywords"][0] if ent.get("target_keywords") else title,
                city=ent.get("location") or "Kuşadası",
                district="Kuşadası",
                status="publish",
                notify_index=True,
                force=force,
            )
            entry["published"] = bool(res.get("success"))
            entry["link"] = (res.get("page") or {}).get("link", "")
            if res.get("success"):
                ent["page_status"] = "published"
            else:
                ent["page_status"] = "failed"
                entry["error"] = res.get("error", "Yayınlanamadı")
                errors.append(entry)
        generated.append(entry)

        try:
            from app.moduller.rank_index_watcher import track_keyword
            domain = urlparse(url).netloc or "balkutusu.com"
            for kw in (ent.get("target_keywords") or [])[:3]:
                track_keyword(kw.lower(), domain, save=True)
        except Exception as exc:
            logger.warning("Rank watcher: %s", exc)

    _update_job(job_id, entities=entities, status="pages_generated", main_site_url=url, listing_hub_called=False)
    return {
        "success": len(generated) > 0,
        "job_id": job_id,
        "generated_count": len(generated),
        "published_count": sum(1 for g in generated if g.get("published")),
        "generated": generated,
        "errors": errors,
        "listing_hub_called": False,
    }


def create_astro_pages(job_id: str, project_id: str = "", main_site_url: str = "") -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}

    pid = (project_id or job.get("astro_project_id") or "").strip()
    if not pid:
        source = job.get("source_job_id", "")
        if source:
            place_job = _load_place_seo_job(source)
            if place_job:
                pid = (place_job.get("astro_project_id") or "").strip()
    if not pid:
        return {"success": False, "error": "Astro project_id gerekli — Place SEO astro veya project_id verin"}

    entities = [e for e in (job.get("entities") or []) if e.get("tier1_selected") and e.get("page")]
    if not entities:
        return {"success": False, "error": "Üretilmiş entity sayfası yok"}

    from app.moduller.astro_factory import _get_project, _project_path, generate_pages

    project = _get_project(pid)
    project_path = _project_path(project["slug"])
    data_dir = project_path / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    entity_pages = []
    for ent in entities:
        page = ent.get("page") or {}
        entity_pages.append({
            "slug": ent["slug"].replace("rehber/", ""),
            "title": f"{ent['name']} Kuşadası rehberi",
            "description": (page.get("html") or "")[:200],
            "content_html": page.get("html", ""),
            "schema": page.get("schemas", {}).get("article"),
            "keyword": (ent.get("target_keywords") or [""])[0],
            "location": ent.get("location", ""),
            "category": ent.get("category", ""),
            "entity_name": ent.get("name", ""),
        })

    (data_dir / "entity_pages.json").write_text(json.dumps(entity_pages, ensure_ascii=False, indent=2), encoding="utf-8")
    gen = generate_pages(pid)

    _update_job(job_id, astro_project_id=pid, status="astro_created", astro_entity_count=len(entity_pages))
    return {
        "success": True,
        "job_id": job_id,
        "project_id": pid,
        "entity_pages_written": len(entity_pages),
        "astro_files": gen.get("files_written", []),
        "data_path": str(data_dir / "entity_pages.json"),
        "listing_hub_called": False,
    }


def run_quality_gate(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}

    from app.moduller.seo_quality_gate import seo_quality_gate

    entities = job.get("entities") or []
    reports: list[dict[str, Any]] = []
    deploy_allowed = True

    for ent in entities:
        if not ent.get("tier1_selected") or not ent.get("page"):
            continue
        html = ent["page"].get("html", "")
        kw = (ent.get("target_keywords") or [ent.get("name", "")])[0]
        analysis = seo_quality_gate.analyze_page(
            html, kw,
            location=ent.get("location") or "Kuşadası",
            title=f"{ent.get('name')} Kuşadası rehberi",
        )
        score = analysis.get("overall_score") or analysis.get("seo_score") or 0
        passed = bool(analysis.get("pass")) and (analysis.get("seo_score") or 0) >= 70
        ent["quality_score"] = score
        ent["deploy_allowed"] = passed
        if not passed:
            deploy_allowed = False
        reports.append({
            "entity_id": ent["id"],
            "name": ent["name"],
            "quality_score": score,
            "deploy_allowed": passed,
            "analysis": analysis,
        })

    _update_job(job_id, status="gated", quality_gate={"reports": reports, "deploy_allowed": deploy_allowed})
    return {
        "success": True,
        "job_id": job_id,
        "deploy_allowed": deploy_allowed,
        "reports": reports,
        "listing_hub_called": False,
    }


def export_report(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"entity-detail-{job_id}.json"
    entities = job.get("entities") or []
    report = {
        "job_id": job_id,
        "source_job_id": job.get("source_job_id"),
        "exported_at": _now(),
        "entity_count": len(entities),
        "tier1_selected": sum(1 for e in entities if e.get("tier1_selected")),
        "pages_generated": sum(1 for e in entities if e.get("page_status") in ("generated", "published")),
        "quality_gate": job.get("quality_gate"),
        "listing_hub_called": False,
        "entities": [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "tier1_score": e.get("tier1_score"),
                "tier1_selected": e.get("tier1_selected"),
                "page_status": e.get("page_status"),
                "quality_score": e.get("quality_score"),
                "slug": e.get("slug"),
            }
            for e in entities
        ],
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "job_id": job_id, "report_path": str(path), "report": report}


entity_detail_generator = type("EntityDetailGenerator", (), {
    "health": staticmethod(health),
    "list_jobs": staticmethod(list_jobs),
    "get_job_detail": staticmethod(get_job_detail),
    "select_tier1": staticmethod(select_tier1),
    "update_manual_selection": staticmethod(update_manual_selection),
    "generate_pages": staticmethod(generate_pages),
    "create_astro_pages": staticmethod(create_astro_pages),
    "run_quality_gate": staticmethod(run_quality_gate),
    "export_report": staticmethod(export_report),
    "score_tier1": staticmethod(score_tier1),
})()
