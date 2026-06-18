"""Question Intelligence Engine V2 — Search Intent Intelligence (SEO, GEO, AEO, PAA, Reddit)."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.question_intelligence_engine")

STATE_FILE = Path(__file__).resolve().parent.parent / "question_intelligence_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

_job_lock = threading.Lock()

CONTENT_TYPES = (
    "faq", "far", "comparison", "best_of", "problem_solution",
    "local_intent", "objection", "ai_overview",
    "people_also_ask", "autocomplete", "related_search",
    "reddit_intent", "decision", "entity_question", "location_question",
)

DEFAULT_REFRESH_FIELDS: dict[str, Any] = {
    "refresh_candidate": False,
    "intent_gap": 0,
    "question_gap": 0,
    "overview_gap": 0,
    "question_gap_score": 0,
    "intent_gap_score": 0,
    "paa_gap_score": 0,
    "autocomplete_gap_score": 0,
}

DEFAULT_ENTITIES = [
    "Ex Club", "Jimmy's Irish Bar", "Planet Yucca", "Joy Club", "Marina Bar",
]

DEFAULT_LOCATIONS = [
    "Kadınlar Denizi", "Marina", "Barlar Sokağı", "Kaleiçi", "Davutlar", "Güzelçamlı",
]

RELATED_LOCATION_PAIRS = [
    ("kuşadası beach club", ["didim beach club", "bodrum beach club", "çeşme beach club", "güzelçamlı beach club"]),
    ("kuşadası gece hayatı", ["bodrum gece hayatı", "didim gece hayatı", "izmir gece hayatı"]),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("jobs", {})
                data.setdefault("running_job", "")
                data.setdefault("last_generation_at", "")
                data.setdefault("outputs", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"jobs": {}, "running_job": "", "last_generation_at": "", "outputs": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _slugify(text: str) -> str:
    from app.moduller.sss_generator import _slugify as sss_slug
    return sss_slug(text)


def _llm(prompt: str, min_length: int = 150) -> tuple[str, str]:
    from app.moduller import llm_router
    return llm_router.generate(prompt, max_tokens=3500, min_length=min_length)


def _intent_for(keyword: str) -> str:
    try:
        from app.moduller.talon_orchestrator import intent_classifier
        return intent_classifier(keyword)
    except Exception:
        return "informational"


def _difficulty_for(keyword: str, question_type: str) -> str:
    words = len((keyword or "").split())
    if question_type in ("deep", "entity_question", "decision") or words >= 6:
        return "hard"
    if question_type in ("secondary", "follow_up", "comparison") or words >= 4:
        return "medium"
    return "easy"


def _compute_refresh_fields(
    keyword: str,
    content_html: str,
    content_type: str,
    *,
    related_questions: list[str] | None = None,
    autocomplete_suggestions: list[str] | None = None,
    entities: list[str] | None = None,
) -> dict[str, Any]:
    from app.moduller.seo_quality_gate import (
        _autocomplete_score,
        _faq_coverage_score,
        _intent_coverage_score,
        _overview_score,
        _paa_score,
        _question_coverage_score,
    )
    plain = re.sub(r"<[^>]+>", " ", content_html or "")
    faq_cov = _faq_coverage_score(content_html, expected_questions=8 if content_type == "faq" else 3)
    question_cov = _question_coverage_score(content_html, plain)
    intent_cov = _intent_coverage_score(keyword, plain)
    overview = _overview_score(plain, content_html)
    paa_cov = _paa_score(related_questions or [])
    auto_cov = _autocomplete_score(keyword, autocomplete_suggestions or [])
    intent_gap = max(0, 80 - intent_cov)
    question_gap = max(0, 70 - question_cov)
    overview_gap = max(0, 75 - overview)
    paa_gap = max(0, 75 - paa_cov)
    auto_gap = max(0, 70 - auto_cov)
    return {
        "refresh_candidate": any(g >= 40 for g in (intent_gap, question_gap, overview_gap, paa_gap, auto_gap)),
        "intent_gap": intent_gap,
        "question_gap": question_gap,
        "overview_gap": overview_gap,
        "question_gap_score": question_gap,
        "intent_gap_score": intent_gap,
        "paa_gap_score": paa_gap,
        "autocomplete_gap_score": auto_gap,
        "faq_coverage_score": faq_cov,
        "question_coverage_score": question_cov,
        "intent_coverage_score": intent_cov,
        "overview_score": overview,
        "paa_score": paa_cov,
        "autocomplete_score": auto_cov,
        "entity_question_score": _entity_question_score_plain(plain, entities or []),
    }


def _entity_question_score_plain(plain: str, entities: list[str]) -> int:
    try:
        from app.moduller.seo_quality_gate import _entity_question_score
        return _entity_question_score(plain, entities)
    except Exception:
        if not entities:
            return 40
        hits = sum(1 for e in entities if e.lower() in plain.lower())
        return min(100, int((hits / max(len(entities), 1)) * 100))


def _build_output(
    *,
    keyword: str,
    intent: str,
    content_type: str,
    title: str,
    slug: str,
    content_outline: list[str],
    entities: list[str],
    geo_signals: list[str],
    answer_blocks: list[dict[str, Any]],
    content_html: str = "",
    schema: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    intent_type: str = "",
    question_type: str = "",
    difficulty: str = "",
    entity: str = "",
    location: str = "",
    answer_block: str = "",
    related_questions: list[str] | None = None,
    autocomplete_suggestions: list[str] | None = None,
) -> dict[str, Any]:
    qt = question_type or content_type
    refresh = _compute_refresh_fields(
        keyword, content_html, content_type,
        related_questions=related_questions,
        autocomplete_suggestions=autocomplete_suggestions,
        entities=entities,
    )
    ab = answer_block or (answer_blocks[0].get("text", "") if answer_blocks else "")
    if not ab and content_html:
        ab = re.sub(r"<[^>]+>", " ", content_html)[:400].strip()
    item = {
        "keyword": keyword,
        "intent": intent,
        "intent_type": intent_type or intent,
        "question_type": qt,
        "difficulty": difficulty or _difficulty_for(keyword, qt),
        "entity": entity,
        "location": location,
        "type": content_type,
        "title": title,
        "slug": slug,
        "answer_block": ab,
        "related_questions": related_questions or [],
        "content_outline": content_outline,
        "entities": entities,
        "geo_signals": geo_signals,
        "answer_blocks": answer_blocks,
        "content_html": content_html,
        "schema": schema,
        "generated_at": _now(),
        "engine_version": "v2",
        **DEFAULT_REFRESH_FIELDS,
        **refresh,
    }
    if extra:
        item.update(extra)
    return item


def _extract_entities(text: str, keyword: str, location: str) -> list[str]:
    try:
        from app.moduller.entity_geo_graph import extract_entities_from_text
        res = extract_entities_from_text(text, title=keyword, seed_keyword=keyword, location=location)
        ents = list(res.get("entities") or []) + list(res.get("locations") or [])
        return list(dict.fromkeys(ents))[:20]
    except Exception:
        return [location] if location else []


def _geo_signals(location: str, category: str) -> list[str]:
    loc = location or "Kuşadası"
    cat = category or "gece hayatı"
    return [loc, f"{loc} {cat}", f"{loc} merkez", f"{loc} çevresi"]


def _new_job_id() -> str:
    return f"qie-{uuid.uuid4().hex[:12]}"


def _start_job(job_type: str, keyword: str) -> dict[str, Any]:
    with _job_lock:
        st = _load_state()
        jid = _new_job_id()
        job = {
            "job_id": jid,
            "type": job_type,
            "keyword": keyword,
            "status": "running",
            "started_at": _now(),
            "finished_at": "",
            "items": [],
            "errors": [],
        }
        st["jobs"][jid] = job
        st["running_job"] = jid
        _save_state(st)
        return job


def _finish_job(job_id: str, status: str, items: list[dict[str, Any]], errors: list[str] | None = None) -> dict[str, Any]:
    with _job_lock:
        st = _load_state()
        job = st["jobs"].get(job_id, {})
        job["status"] = status
        job["finished_at"] = _now()
        job["items"] = items
        job["errors"] = errors or []
        job["count"] = len(items)
        st["jobs"][job_id] = job
        st["running_job"] = ""
        st["last_generation_at"] = _now()
        st["outputs"] = (st.get("outputs") or [])[-100:] + items
        _save_state(st)
        return job


def _params(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "keyword": (payload.get("keyword") or "").strip(),
        "location": (payload.get("location") or "Kuşadası").strip(),
        "city": (payload.get("city") or "Aydın").strip(),
        "district": (payload.get("district") or payload.get("location") or "Kuşadası").strip(),
        "category": (payload.get("category") or "gece hayatı").strip(),
        "subcategory": (payload.get("subcategory") or payload.get("category") or "gece hayatı").strip(),
    }


def generate_faq(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    if not p["keyword"]:
        return {"success": False, "error": "keyword gerekli"}
    job = _start_job("faq", p["keyword"])
    try:
        from app.moduller.sss_generator import generate_sss_page, build_html
        page = generate_sss_page(
            p["city"], p["district"], p["category"], p["subcategory"], p["keyword"],
            secondary_keywords=payload.get("secondary_keywords", ""),
        )
        html = page.get("html") or build_html(page)
        intent = _intent_for(p["keyword"])
        entities = _extract_entities(html, p["keyword"], p["location"])
        outline = [f["question"] for f in (page.get("faqs") or [])[:12]]
        answers = [{"question": f["question"], "answer": f["answer"][:300]} for f in (page.get("faqs") or [])[:8]]
        item = _build_output(
            keyword=p["keyword"], intent=intent, content_type="faq",
            title=page.get("h1") or page.get("seo_title", ""),
            slug=page.get("slug") or _slugify(f"{p['keyword']}-sss"),
            content_outline=outline, entities=entities,
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=answers, content_html=html,
            schema=page.get("schema"),
            extra={"faq_count": len(page.get("faqs") or []), "engine": "sss_generator"},
        )
        items = [item]
        _integrate(payload, items)
        job = _finish_job(job["job_id"], "completed", items)
        return {"success": True, "job_id": job["job_id"], "items": items, "count": 1}
    except Exception as exc:
        _finish_job(job["job_id"], "failed", [], [str(exc)])
        return {"success": False, "error": str(exc)}


def _template_phrases(keyword: str, location: str, category: str, templates: list[str], count: int = 8) -> list[str]:
    loc = location or "Kuşadası"
    cat = category or "gece hayatı"
    phrases = [t.format(location=loc, keyword=keyword, category=cat) for t in templates]
    return list(dict.fromkeys(phrases))[:count]


FAR_TEMPLATES = [
    "{location} {category} fiyatları",
    "{location} {category} tavsiyeleri",
    "{location} marina restoranları",
    "{location} canlı müzik mekanları",
    "{location} beach club önerileri",
    "{keyword} rehberi",
    "{location} gece kulüpleri listesi",
    "{location} barlar sokağı mekanları",
]

COMPARISON_TEMPLATES = [
    "{location} mı Bodrum mu gece hayatı",
    "Ex Club mı Jimmy's mi",
    "Kadınlar Denizi mi Long Beach mi",
]

BESTOF_TEMPLATES = [
    "{location} En İyi 10 Bar",
    "{location} En İyi Beach Club",
    "{location} En İyi Balık Restoranları",
    "{location} En İyi Kahvaltı Mekanları",
]

PROBLEM_TEMPLATES = [
    "{location} gece nereye gidilir?",
    "{location} park sorunu nasıl çözülür?",
    "{location} uygun fiyatlı mekanlar hangileri?",
]

LOCAL_TEMPLATES = [
    "Yakınımdaki barlar {location}",
    "Marina yakınındaki restoranlar",
    "Kadınlar Denizi çevresi beach club önerileri",
    "{location} merkez gece kulüpleri",
]

OBJECTION_TEMPLATES = [
    "{location} gece hayatı pahalı mı?",
    "{location} gece hayatı güvenli mi?",
    "{location} gece hayatı aile için uygun mu?",
    "{location} mekanlarda rezervasyon gerekli mi?",
]


def _llm_article(
    title: str,
    keyword: str,
    location: str,
    article_type: str,
    structure_hint: str,
) -> tuple[str, list[str], list[dict[str, Any]], str]:
    prompt = f"""Konu: {title}
Anahtar kelime: {keyword}
Konum: {location}
İçerik tipi: {article_type}

{structure_hint}

Kurallar:
- Türkçe, SEO/GEO/AEO uyumlu
- Uydurma işletme adı verme
- HTML formatında (h1, h2, h3, p, ul, table)
- AI Overview için ilk paragrafta doğrudan cevap
- En az 800 kelime
"""
    raw, engine = _llm(prompt, min_length=400)
    if not raw or len(raw.strip()) < 200:
        raw = (
            f"<h1>{title}</h1>"
            f"<p><strong>{keyword}</strong> — {location} bölgesinde güncel 2026 rehber özeti.</p>"
            f"<h2>Özet</h2><p>{location} {keyword} hakkında yerel planlama ipuçları.</p>"
            f"<h2>Detaylar</h2><ul><li>Ulaşım ve sezon</li><li>Bütçe planlaması</li><li>Güvenlik</li></ul>"
        )
        engine = "rule_fallback"
    if not raw.strip().startswith("<"):
        raw = f"<div>{raw}</div>"
    outline = re.findall(r"<h[23]>([^<]+)</h[23]>", raw, re.I)[:10]
    blocks = [{"type": "summary", "text": re.sub(r"<[^>]+>", " ", raw)[:400]}]
    return raw, outline, blocks, engine


def generate_far(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    if not p["keyword"]:
        return {"success": False, "error": "keyword gerekli"}
    count = int(payload.get("count") or 6)
    job = _start_job("far", p["keyword"])
    phrases = _template_phrases(p["keyword"], p["location"], p["category"], FAR_TEMPLATES, count)
    items: list[dict[str, Any]] = []
    for phrase in phrases:
        html, outline, blocks, engine = _llm_article(
            phrase, phrase, p["location"], "far",
            "Arama niyeti odaklı makale. Soru formatı KULLANMA. Araştırma niyeti ifadeleri kullan.",
        )
        item = _build_output(
            keyword=phrase, intent="research", content_type="far",
            title=phrase.title(), slug=_slugify(phrase),
            content_outline=outline, entities=_extract_entities(html, phrase, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=blocks, content_html=html,
            extra={"engine": engine},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


def generate_comparisons(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("comparison", p["keyword"])
    titles = _template_phrases(p["keyword"], p["location"], p["category"], COMPARISON_TEMPLATES, int(payload.get("count") or 3))
    if p["keyword"] and p["keyword"] not in titles:
        titles.insert(0, p["keyword"])
    items: list[dict[str, Any]] = []
    for title in titles[: int(payload.get("count") or 3)]:
        html, outline, blocks, engine = _llm_article(
            title, title, p["location"], "comparison",
            "Karşılaştırma makalesi: HTML tablo, artılar listesi, eksiler listesi, karar özeti bölümü.",
        )
        pros = re.findall(r"<h2>Artılar</h2>\s*<ul>(.*?)</ul>", html, re.S | re.I)
        cons = re.findall(r"<h2>Eksiler</h2>\s*<ul>(.*?)</ul>", html, re.S | re.I)
        item = _build_output(
            keyword=title, intent="comparison", content_type="comparison",
            title=title, slug=_slugify(title),
            content_outline=outline, entities=_extract_entities(html, title, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=blocks + [{"type": "pros", "html": pros[0] if pros else ""}, {"type": "cons", "html": cons[0] if cons else ""}],
            content_html=html, extra={"engine": engine},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


def generate_bestof(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("best_of", p["keyword"])
    titles = _template_phrases(p["keyword"], p["location"], p["category"], BESTOF_TEMPLATES, int(payload.get("count") or 4))
    items: list[dict[str, Any]] = []
    for title in titles:
        html, outline, blocks, engine = _llm_article(
            title, title, p["location"], "best_of",
            "Liste makalesi: numaralı en iyi mekan/tip önerileri, her biri için kısa açıklama.",
        )
        item = _build_output(
            keyword=title, intent="best_of", content_type="best_of",
            title=title, slug=_slugify(title),
            content_outline=outline, entities=_extract_entities(html, title, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=blocks, content_html=html, extra={"engine": engine},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


def generate_problem_solution(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("problem_solution", p["keyword"])
    titles = _template_phrases(p["keyword"], p["location"], p["category"], PROBLEM_TEMPLATES, int(payload.get("count") or 3))
    items: list[dict[str, Any]] = []
    for title in titles:
        html, outline, blocks, engine = _llm_article(
            title, title, p["location"], "problem_solution",
            "Problem-çözüm formatı: sorunu tanımla, adım adım çözüm, pratik ipuçları.",
        )
        item = _build_output(
            keyword=title, intent="problem_solution", content_type="problem_solution",
            title=title, slug=_slugify(title),
            content_outline=outline, entities=_extract_entities(html, title, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=blocks, content_html=html, extra={"engine": engine},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


def generate_local_intent(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("local_intent", p["keyword"])
    titles = _template_phrases(p["keyword"], p["location"], p["category"], LOCAL_TEMPLATES, int(payload.get("count") or 4))
    items: list[dict[str, Any]] = []
    for title in titles:
        html, outline, blocks, engine = _llm_article(
            title, title, p["location"], "local_intent",
            "Yerel arama niyeti: yakınımdaki, çevresindeki, bölgesel ifadeler kullan.",
        )
        item = _build_output(
            keyword=title, intent="local", content_type="local_intent",
            title=title, slug=_slugify(title),
            content_outline=outline, entities=_extract_entities(html, title, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=blocks, content_html=html, extra={"engine": engine},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


def generate_objections(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("objection", p["keyword"])
    titles = _template_phrases(p["keyword"], p["location"], p["category"], OBJECTION_TEMPLATES, int(payload.get("count") or 4))
    items: list[dict[str, Any]] = []
    for title in titles:
        html, outline, blocks, engine = _llm_article(
            title, title, p["location"], "objection",
            "Karar aşaması itirazları: endişeyi kabul et, dengeli cevap ver, güven ver.",
        )
        item = _build_output(
            keyword=title, intent="objection", content_type="objection",
            title=title, slug=_slugify(title),
            content_outline=outline, entities=_extract_entities(html, title, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=blocks, content_html=html, extra={"engine": engine},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


def _word_limit(text: str, limit: int) -> str:
    words = text.split()
    return " ".join(words[:limit])


def generate_ai_overview(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    if not p["keyword"]:
        return {"success": False, "error": "keyword gerekli"}
    job = _start_job("ai_overview", p["keyword"])
    prompt = f"""Konu: {p['keyword']}
Konum: {p['location']}

AI Overview için içerik üret. JSON formatında döndür:
{{
  "short_answer": "40 kelime",
  "medium_answer": "60 kelime",
  "long_answer": "80 kelime",
  "bullet_points": ["madde1", "madde2", "madde3"],
  "overview_block": "alıntılanabilir özet paragraf",
  "citable_answer": "tek cümlelik kesin cevap"
}}
Sadece geçerli JSON döndür."""
    raw, engine = _llm(prompt, min_length=100)
    overview: dict[str, Any] = {}
    if raw:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                overview = json.loads(m.group())
            except json.JSONDecodeError:
                pass
    if not overview:
        base = f"{p['keyword']} {p['location']} bölgesinde güncel 2026 rehber bilgisi sunar."
        overview = {
            "short_answer": _word_limit(base, 40),
            "medium_answer": _word_limit(base + " Ulaşım, sezon ve bütçe planlaması önemlidir.", 60),
            "long_answer": _word_limit(base + " Yerel mekanlar, güvenlik ve rezervasyon konularında araştırma yapılmalıdır.", 80),
            "bullet_points": [f"{p['location']} merkez", "Sezon planlaması", "Bütçe ipuçları"],
            "overview_block": base,
            "citable_answer": f"{p['keyword']} için {p['location']} odaklı güncel rehber içerikleri mevcuttur.",
        }
        engine = "rule_fallback"

    html = (
        f"<h1>{p['keyword']}</h1>"
        f"<p class=\"ai-overview-short\"><strong>Özet:</strong> {overview.get('short_answer', '')}</p>"
        f"<p class=\"ai-overview-medium\">{overview.get('medium_answer', '')}</p>"
        f"<p class=\"ai-overview-long\">{overview.get('long_answer', '')}</p>"
        f"<h2>Öne Çıkanlar</h2><ul>{''.join(f'<li>{b}</li>' for b in (overview.get('bullet_points') or []))}</ul>"
        f"<blockquote>{overview.get('citable_answer', '')}</blockquote>"
        f"<div class=\"overview-block\">{overview.get('overview_block', '')}</div>"
    )
    answer_blocks = [
        {"type": "short_answer", "text": overview.get("short_answer", "")},
        {"type": "medium_answer", "text": overview.get("medium_answer", "")},
        {"type": "long_answer", "text": overview.get("long_answer", "")},
        {"type": "bullet_points", "items": overview.get("bullet_points", [])},
        {"type": "overview_block", "text": overview.get("overview_block", "")},
        {"type": "citable_answer", "text": overview.get("citable_answer", "")},
    ]
    item = _build_output(
        keyword=p["keyword"], intent="ai_overview", content_type="ai_overview",
        title=f"{p['keyword']} — AI Overview",
        slug=_slugify(f"{p['keyword']}-ai-overview"),
        content_outline=["short", "medium", "long", "bullets", "overview"],
        entities=_extract_entities(html, p["keyword"], p["location"]),
        geo_signals=_geo_signals(p["location"], p["category"]),
        answer_blocks=answer_blocks, content_html=html,
        extra={"overview": overview, "engine": engine},
    )
    items = [item]
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": 1, "overview": overview}


def _paa_chain(keyword: str, location: str) -> dict[str, list[str]]:
    loc = location or "Kuşadası"
    return {
        "primary": [f"{keyword} nasıl?", f"{keyword} nasıldır?"],
        "secondary": [
            f"{loc} en çok tercih edilen mekanlar hangileri?",
            f"{loc} gece hayatı pahalı mı?",
        ],
        "deep": [
            f"Yabancılar {loc} hangi mekanları tercih ediyor?",
            f"{loc} gece hayatında güvenlik nasıl?",
        ],
        "follow_up": [
            f"{loc} rezervasyon gerekli mi?",
            f"{loc} beach club fiyatları ne kadar?",
        ],
    }


def _build_faq_schema(questions: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in questions
        ],
    }


def _questions_to_html(title: str, qa_pairs: list[tuple[str, str]]) -> str:
    parts = [f"<h1>{title}</h1>"]
    for q, a in qa_pairs:
        parts.append(f"<h3>{q}</h3><p>{a}</p>")
    return "\n".join(parts)


def generate_people_also_ask(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    if not p["keyword"]:
        return {"success": False, "error": "keyword gerekli"}
    job = _start_job("people_also_ask", p["keyword"])
    chain = _paa_chain(p["keyword"], p["location"])
    all_q = chain["primary"] + chain["secondary"] + chain["deep"] + chain["follow_up"]
    qa_pairs: list[tuple[str, str]] = []
    for q in all_q:
        ans = f"{q.rstrip('?')} — {p['location']} bölgesinde güncel 2026 rehber bilgisi ve yerel planlama ipuçları."
        qa_pairs.append((q, ans))
    html = _questions_to_html(f"{p['keyword']} — People Also Ask", qa_pairs)
    schema = _build_faq_schema(qa_pairs)
    item = _build_output(
        keyword=p["keyword"], intent="informational", content_type="people_also_ask",
        intent_type="paa", question_type="primary",
        title=f"{p['keyword']} — People Also Ask",
        slug=_slugify(f"{p['keyword']}-paa"),
        location=p["location"],
        content_outline=all_q,
        entities=_extract_entities(html, p["keyword"], p["location"]),
        geo_signals=_geo_signals(p["location"], p["category"]),
        answer_blocks=[{"type": "paa_chain", "levels": chain}],
        content_html=html, schema=schema,
        related_questions=all_q,
        answer_block=qa_pairs[0][1] if qa_pairs else "",
        extra={"paa_levels": chain},
    )
    items = [item]
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": 1, "paa_levels": chain}


AUTOCOMPLETE_SUFFIXES = [
    "fiyatları", "tavsiye", "yorumları", "güvenli mi", "nerede",
    "nasıl", "en iyi", "2026", "rehberi", "mekanları",
]


def generate_autocomplete(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    if not p["keyword"]:
        return {"success": False, "error": "keyword gerekli"}
    job = _start_job("autocomplete", p["keyword"])
    base = p["keyword"].lower().strip()
    suggestions = [f"{base} {s}" for s in AUTOCOMPLETE_SUFFIXES]
    suggestions = list(dict.fromkeys(suggestions))[: int(payload.get("count") or 8)]
    items: list[dict[str, Any]] = []
    for sug in suggestions:
        html = f"<h1>{sug}</h1><p>{sug} hakkında {p['location']} odaklı autocomplete niyet özeti.</p>"
        item = _build_output(
            keyword=sug, intent="autocomplete", content_type="autocomplete",
            intent_type="autocomplete", question_type="suggestion",
            title=sug, slug=_slugify(sug), location=p["location"],
            content_outline=[sug], entities=[p["location"]],
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=[{"type": "suggestion", "text": sug}],
            content_html=html, answer_block=html,
            autocomplete_suggestions=suggestions,
            extra={"parent_keyword": base},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items), "suggestions": suggestions}


def generate_related_searches(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("related_search", p["keyword"])
    base_kw = (p["keyword"] or p["category"]).lower()
    related: list[str] = []
    for anchor, variants in RELATED_LOCATION_PAIRS:
        if anchor in base_kw or base_kw in anchor:
            related.extend(variants)
    if not related:
        related = [
            f"didim {p['category']}", f"bodrum {p['category']}",
            f"çeşme {p['category']}", f"güzelçamlı {p['category']}",
        ]
    related = list(dict.fromkeys(related))[: int(payload.get("count") or 5)]
    items: list[dict[str, Any]] = []
    for rel in related:
        html = f"<h1>{rel}</h1><p>{rel} ile ilişkili arama niyeti — {p['location']} karşılaştırmalı rehber.</p>"
        item = _build_output(
            keyword=rel, intent="related", content_type="related_search",
            intent_type="related_search", question_type="related",
            title=rel.title(), slug=_slugify(rel), location=p["location"],
            content_outline=[rel], entities=_extract_entities(html, rel, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=[{"type": "related", "text": rel}],
            content_html=html, related_questions=related,
            extra={"parent_keyword": p["keyword"]},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


REDDIT_INTENT_TEMPLATES: dict[str, list[str]] = {
    "deneyim": ["{location} gece hayatı deneyiminiz nasıldı?", "{location} beach club deneyimi nasıl?"],
    "tavsiye": ["{location} için mekan tavsiyesi?", "{location} bar önerisi arıyorum"],
    "şikayet": ["{location} gece hayatı hayal kırıklığı", "{location} fiyatlar abartılı mı?"],
    "karşılaştırma": ["{location} mı Bodrum mu?", "Ex Club mı Jimmy's mi daha iyi?"],
    "korku": ["{location} güvenli mi?", "{location} dolandırıcılık olur mu?"],
    "karar": ["{location} rezervasyon gerekli mi?", "VIP masa almaya değer mi?"],
}


def generate_reddit_intent(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("reddit_intent", p["keyword"])
    items: list[dict[str, Any]] = []
    for intent_cat, templates in REDDIT_INTENT_TEMPLATES.items():
        for tpl in templates[:1]:
            title = tpl.format(location=p["location"], keyword=p["keyword"])
            html = f"<h1>{title}</h1><p>Reddit tarzı {intent_cat} sorusu — {p['location']} topluluk deneyimi özeti.</p>"
            item = _build_output(
                keyword=title, intent="reddit", content_type="reddit_intent",
                intent_type=intent_cat, question_type="reddit",
                title=title, slug=_slugify(title), location=p["location"],
                content_outline=[title],
                entities=_extract_entities(html, title, p["location"]),
                geo_signals=_geo_signals(p["location"], p["category"]),
                answer_blocks=[{"type": intent_cat, "text": title}],
                content_html=html, answer_block=html,
            )
            items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


DECISION_TEMPLATES = [
    "En iyi beach club hangisi?",
    "VIP masa almaya değer mi?",
    "Rezervasyon gerekli mi?",
    "Hangi mekan daha uygun fiyatlı?",
    "Hafta içi mi hafta sonu mu tercih edilmeli?",
]


def generate_decision(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    job = _start_job("decision", p["keyword"])
    titles = [f"{p['location']} {t}" for t in DECISION_TEMPLATES[: int(payload.get("count") or 4)]]
    items: list[dict[str, Any]] = []
    for title in titles:
        html, outline, blocks, engine = _llm_article(
            title, title, p["location"], "decision",
            "Karar verme aşaması: seçenekleri karşılaştır, net öneri ver.",
        )
        item = _build_output(
            keyword=title, intent="decision", content_type="decision",
            intent_type="transactional", question_type="decision",
            title=title, slug=_slugify(title), location=p["location"],
            content_outline=outline, entities=_extract_entities(html, title, p["location"]),
            geo_signals=_geo_signals(p["location"], p["category"]),
            answer_blocks=blocks, content_html=html,
            extra={"engine": engine},
        )
        items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


ENTITY_QUESTION_TEMPLATES = [
    "{entity} giriş ücreti nedir?",
    "{entity} rezervasyon gerekli mi?",
    "{entity} çocuklu aileler için uygun mu?",
    "{entity} hangi günler açık?",
]


def generate_entity_questions(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    entities = payload.get("entities") or DEFAULT_ENTITIES
    job = _start_job("entity_question", p["keyword"])
    items: list[dict[str, Any]] = []
    for ent in entities[: int(payload.get("count") or 4)]:
        for tpl in ENTITY_QUESTION_TEMPLATES[:2]:
            title = tpl.format(entity=ent)
            ans = f"{title.rstrip('?')} — {ent} hakkında güncel bilgi için işletmeyle doğrudan iletişim önerilir."
            html = _questions_to_html(title, [(title, ans)])
            item = _build_output(
                keyword=title, intent="entity", content_type="entity_question",
                intent_type="entity", question_type="entity_question",
                title=title, slug=_slugify(title), entity=ent, location=p["location"],
                content_outline=[title], entities=[ent, p["location"]],
                geo_signals=_geo_signals(p["location"], p["category"]),
                answer_blocks=[{"type": "entity_q", "text": ans}],
                content_html=html, answer_block=ans,
                schema=_build_faq_schema([(title, ans)]),
            )
            items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


LOCATION_QUESTION_TEMPLATES = [
    "{loc} gece ne yapılır?",
    "{loc} çevresinde hangi restoranlar var?",
    "{loc} kaçta açılıyor?",
    "{loc} ulaşım nasıl?",
]


def generate_location_questions(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    locs = payload.get("locations") or DEFAULT_LOCATIONS
    job = _start_job("location_question", p["keyword"])
    items: list[dict[str, Any]] = []
    for loc in locs[: int(payload.get("count") or 4)]:
        for tpl in LOCATION_QUESTION_TEMPLATES[:2]:
            title = tpl.format(loc=loc)
            ans = f"{title.rstrip('?')} — {loc}, {p['location']} bölgesinde yerel rehber bilgisi."
            html = _questions_to_html(title, [(title, ans)])
            item = _build_output(
                keyword=title, intent="local", content_type="location_question",
                intent_type="geo", question_type="location_question",
                title=title, slug=_slugify(title), location=loc,
                content_outline=[title], entities=[loc],
                geo_signals=[loc, f"{loc} çevresi"],
                answer_blocks=[{"type": "location_q", "text": ans}],
                content_html=html, answer_block=ans,
                schema=_build_faq_schema([(title, ans)]),
            )
            items.append(item)
    _integrate(payload, items)
    job = _finish_job(job["job_id"], "completed", items)
    return {"success": True, "job_id": job["job_id"], "items": items, "count": len(items)}


def generate_all(payload: dict[str, Any]) -> dict[str, Any]:
    p = _params(payload)
    if not p["keyword"]:
        return {"success": False, "error": "keyword gerekli"}
    job = _start_job("generate_all", p["keyword"])
    all_items: list[dict[str, Any]] = []
    errors: list[str] = []
    generators = [
        ("faq", generate_faq),
        ("far", lambda pl: generate_far({**pl, "count": 4})),
        ("comparison", lambda pl: generate_comparisons({**pl, "count": 2})),
        ("best_of", lambda pl: generate_bestof({**pl, "count": 2})),
        ("problem_solution", lambda pl: generate_problem_solution({**pl, "count": 2})),
        ("local_intent", lambda pl: generate_local_intent({**pl, "count": 2})),
        ("objection", lambda pl: generate_objections({**pl, "count": 2})),
        ("ai_overview", generate_ai_overview),
        ("people_also_ask", generate_people_also_ask),
        ("autocomplete", lambda pl: generate_autocomplete({**pl, "count": 4})),
        ("related_search", lambda pl: generate_related_searches({**pl, "count": 3})),
        ("reddit_intent", generate_reddit_intent),
        ("decision", lambda pl: generate_decision({**pl, "count": 2})),
        ("entity_question", lambda pl: generate_entity_questions({**pl, "count": 2})),
        ("location_question", lambda pl: generate_location_questions({**pl, "count": 2})),
    ]
    inner_payload = {**payload, "write_astro": False, "push_entity_graph": False, "append_place_seo": False}
    for name, fn in generators:
        try:
            res = fn(inner_payload)
            if res.get("success"):
                all_items.extend(res.get("items") or [])
            else:
                errors.append(f"{name}: {res.get('error', 'fail')}")
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if payload.get("write_astro") and payload.get("project_id"):
        _write_to_astro(payload["project_id"].strip(), all_items)
    if payload.get("push_entity_graph", True):
        _push_to_entity_graph(all_items, p["keyword"], p["location"])
    if payload.get("append_place_seo"):
        _append_place_seo(all_items, p["keyword"], p["location"])
    job = _finish_job(job["job_id"], "completed" if all_items else "failed", all_items, errors)
    return {
        "success": bool(all_items),
        "job_id": job["job_id"],
        "items": all_items,
        "count": len(all_items),
        "errors": errors,
    }


def _integrate(payload: dict[str, Any], items: list[dict[str, Any]]) -> None:
    if payload.get("write_astro") and payload.get("project_id"):
        _write_to_astro(payload["project_id"].strip(), items)
    if payload.get("push_entity_graph", True):
        p = _params(payload)
        _push_to_entity_graph(items, p["keyword"], p["location"])
    if payload.get("append_place_seo"):
        p = _params(payload)
        _append_place_seo(items, p["keyword"], p["location"])


def _write_to_astro(project_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    from app.moduller.astro_factory import GENERATED_DIR, _get_project, _project_path, _write_project_data
    project = _get_project(project_id)
    path = _project_path(project["slug"])
    if not str(path.resolve()).startswith(str(GENERATED_DIR.resolve())):
        return {"success": False, "error": "generated-sites dışına yazma yasak"}
    data_dir = path / "src" / "data"
    pages_data = json.loads((data_dir / "pages.json").read_text(encoding="utf-8")) if (data_dir / "pages.json").exists() else {}
    faqs = json.loads((data_dir / "faqs.json").read_text(encoding="utf-8")) if (data_dir / "faqs.json").exists() else []
    blog = json.loads((data_dir / "blog.json").read_text(encoding="utf-8")) if (data_dir / "blog.json").exists() else []

    faq_types = {
        "faq", "problem_solution", "local_intent", "objection", "ai_overview",
        "people_also_ask", "reddit_intent", "decision", "entity_question", "location_question",
    }
    blog_types = {"far", "comparison", "best_of", "autocomplete", "related_search"}

    existing_faq_slugs = {f.get("slug") for f in faqs}
    existing_blog_slugs = {b.get("slug") for b in blog}

    for item in items:
        entry = {
            "slug": item["slug"],
            "title": item["title"],
            "description": (item.get("content_outline") or [""])[0][:155] if item.get("content_outline") else item["title"][:155],
            "content_html": item.get("content_html", ""),
            "schema": item.get("schema"),
            "keyword": item.get("keyword", ""),
            "updated_at": _now(),
        }
        if item["type"] in faq_types:
            if entry["slug"] not in existing_faq_slugs:
                faqs.append(entry)
                existing_faq_slugs.add(entry["slug"])
        elif item["type"] in blog_types:
            entry["topic"] = item.get("keyword", "")
            entry["ai_engine"] = item.get("engine", "qie")
            if entry["slug"] not in existing_blog_slugs:
                blog.append(entry)
                existing_blog_slugs.add(entry["slug"])

    home = pages_data.get("home") or {"title": project.get("site_name", ""), "description": "", "content_html": ""}
    geo = pages_data.get("geo") or []
    _write_project_data(path, project, home, geo, faqs, blog)
    return {"success": True, "faqs": len(faqs), "blog": len(blog)}


def _push_to_entity_graph(items: list[dict[str, Any]], keyword: str, location: str) -> dict[str, Any]:
    try:
        from app.moduller import entity_geo_graph as egg
        state = egg._load_state()
        graph_id = f"qie-{uuid.uuid4().hex[:10]}"
        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        def nid(ntype: str, label: str) -> str:
            return egg._node_id(ntype, label)

        nodes[nid("keyword", keyword)] = {
            "id": nid("keyword", keyword), "type": "keyword", "label": keyword, "score": 75,
            "metadata": {"source": "question_intelligence_engine"},
        }
        if location:
            nodes[nid("location", location)] = {
                "id": nid("location", location), "type": "location", "label": location, "score": 70,
            }
            edges.append({"source": nid("keyword", keyword), "target": nid("location", location), "type": "located_in", "weight": 0.9})

        for item in items:
            q_label = item.get("title") or item.get("keyword", "")
            qid = nid("question", q_label)
            nodes[qid] = {
                "id": qid, "type": "question", "label": q_label, "score": 65,
                "metadata": {
                    "content_type": item.get("type"),
                    "question_type": item.get("question_type"),
                    "intent_type": item.get("intent_type"),
                    "source": "question_intelligence_engine_v2",
                },
            }
            edges.append({"source": qid, "target": nid("keyword", keyword), "type": "targets", "weight": 0.85})
            if item.get("entity"):
                eid = nid("entity", item["entity"])
                nodes[eid] = {"id": eid, "type": "entity", "label": item["entity"], "score": 70, "metadata": {"source": "qie_v2"}}
                edges.append({"source": qid, "target": eid, "type": "answers", "weight": 0.9})
            for ent in item.get("entities") or []:
                eid = nid("entity", ent)
                if eid not in nodes:
                    nodes[eid] = {"id": eid, "type": "entity", "label": ent, "score": 60, "metadata": {"source": "qie"}}
                edges.append({"source": qid, "target": eid, "type": "mentions", "weight": 0.7})
            for rq in item.get("related_questions") or []:
                rqid = nid("question", rq)
                if rqid not in nodes:
                    nodes[rqid] = {"id": rqid, "type": "question", "label": rq, "score": 55, "metadata": {"paa_follow_up": True}}
                edges.append({"source": qid, "target": rqid, "type": "supports", "weight": 0.75})

        state.setdefault("graphs", {})[graph_id] = {
            "graph_id": graph_id,
            "nodes": list(nodes.values()),
            "edges": edges,
            "created_at": _now(),
            "source": "question_intelligence_engine",
        }
        egg._save_state(state)
        return {"success": True, "graph_id": graph_id, "nodes": len(nodes)}
    except Exception as exc:
        logger.warning("Entity graph push: %s", exc)
        return {"success": False, "error": str(exc)}


def _append_place_seo(items: list[dict[str, Any]], keyword: str, location: str) -> dict[str, Any]:
    try:
        faq_types = {"faq", "objection", "problem_solution", "people_also_ask", "entity_question", "location_question", "reddit_intent", "decision"}
        blog_types = {"far", "comparison", "best_of", "autocomplete", "related_search", "ai_overview"}
        geo_types = {"local_intent", "location_question"}
        entity_types = {"entity_question"}

        faq_candidates: list[str] = []
        blog_angles: list[str] = []
        geo_pages: list[str] = []
        category_pages: list[str] = []
        entity_list: list[str] = []

        for item in items:
            title = item.get("title", "")
            itype = item.get("type", "")
            if itype in faq_types:
                faq_candidates.append(title)
                faq_candidates.extend(item.get("related_questions") or [])
            if itype in blog_types:
                blog_angles.append(title or item.get("keyword", ""))
            if itype in geo_types:
                geo_pages.append(item.get("location") or title)
            if itype in entity_types and item.get("entity"):
                entity_list.append(item["entity"])
            if itype == "comparison":
                category_pages.append(title)

        signals = {
            "locations": list(dict.fromkeys([location] + geo_pages)) if location else geo_pages,
            "entities": list(dict.fromkeys(entity_list + [e for i in items for e in (i.get("entities") or [])])),
            "topics": list(dict.fromkeys([keyword] + category_pages)),
            "faq_candidates": list(dict.fromkeys(faq_candidates))[:40],
            "content_angles": list(dict.fromkeys(blog_angles + [f"{location} {keyword} rehberi"]))[:20],
            "geo_page_hints": list(dict.fromkeys(geo_pages))[:15],
            "category_hints": list(dict.fromkeys(category_pages))[:10],
            "confidence": 80,
            "source": "question_intelligence_engine_v2",
        }
        st_path = Path(__file__).resolve().parent.parent / "place_seo_pipeline_state.json"
        if st_path.exists():
            st = json.loads(st_path.read_text(encoding="utf-8"))
            jobs = st.get("jobs") or {}
            if jobs:
                last_id = sorted(jobs.keys())[-1]
                job = jobs[last_id]
                sig = job.get("signals") or {}
                sig["faq_candidates"] = list(dict.fromkeys((sig.get("faq_candidates") or []) + signals["faq_candidates"]))[:40]
                sig["content_angles"] = list(dict.fromkeys((sig.get("content_angles") or []) + signals["content_angles"]))[:25]
                sig["entities"] = list(dict.fromkeys((sig.get("entities") or []) + signals["entities"]))[:30]
                sig["qie_v2_plan"] = {
                    "faq": signals["faq_candidates"][:12],
                    "blog": signals["content_angles"][:10],
                    "geo": signals.get("geo_page_hints", [])[:8],
                    "entity": signals["entities"][:10],
                    "category": signals.get("category_hints", [])[:6],
                }
                job["signals"] = sig
                jobs[last_id] = job
                st["jobs"] = jobs
                st_path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "faq_candidates_added": len(faq_candidates), "signals": signals}
    except Exception as exc:
        logger.warning("Place SEO append: %s", exc)
        return {"success": False, "error": str(exc)}


def _items_to_markdown(items: list[dict[str, Any]], title: str = "Question Intelligence Export") -> str:
    lines = [f"# {title}", f"Exported: {_now()}", ""]
    for item in items:
        lines.append(f"## {item.get('title', '')}")
        lines.append(f"- **Type:** {item.get('question_type') or item.get('type')}")
        lines.append(f"- **Intent:** {item.get('intent_type') or item.get('intent')}")
        lines.append(f"- **Difficulty:** {item.get('difficulty', '')}")
        lines.append(f"- **Keyword:** {item.get('keyword', '')}")
        if item.get("entity"):
            lines.append(f"- **Entity:** {item['entity']}")
        if item.get("location"):
            lines.append(f"- **Location:** {item['location']}")
        if item.get("answer_block"):
            lines.append(f"\n> {item['answer_block'][:500]}\n")
        if item.get("related_questions"):
            lines.append("### Related Questions")
            for rq in item["related_questions"][:10]:
                lines.append(f"- {rq}")
        lines.append("")
    return "\n".join(lines)


def export_report(job_id: str = "", export_format: str = "json") -> dict[str, Any]:
    st = _load_state()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fmt = (export_format or "json").lower()
    if job_id:
        job = (st.get("jobs") or {}).get(job_id)
        if not job:
            return {"success": False, "error": "Job bulunamadı"}
        items = job.get("items") or []
        if fmt == "markdown":
            md = _items_to_markdown(items, title=f"QIE Job {job_id}")
            path = REPORTS_DIR / f"question-intelligence-{job_id}.md"
            path.write_text(md, encoding="utf-8")
            return {"success": True, "path": str(path), "job_id": job_id, "format": "markdown"}
        path = REPORTS_DIR / f"question-intelligence-{job_id}.json"
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "path": str(path), "job_id": job_id, "format": "json"}
    outputs = (st.get("outputs") or [])[-100:]
    if fmt == "markdown":
        md = _items_to_markdown(outputs)
        path = REPORTS_DIR / "question-intelligence-report.md"
        path.write_text(md, encoding="utf-8")
        return {"success": True, "path": str(path), "format": "markdown"}
    payload = {
        "exported_at": _now(),
        "engine_version": "v2",
        "jobs": list((st.get("jobs") or {}).values())[-30:],
        "outputs": outputs,
        "last_generation_at": st.get("last_generation_at", ""),
    }
    path = REPORTS_DIR / "question-intelligence-report.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path), "format": "json"}


def list_jobs(limit: int = 20) -> dict[str, Any]:
    jobs = list((_load_state().get("jobs") or {}).values())
    jobs.sort(key=lambda j: j.get("started_at", ""), reverse=True)
    return {"success": True, "jobs": jobs[:limit]}


def get_job_detail(job_id: str) -> dict[str, Any]:
    job = (_load_state().get("jobs") or {}).get(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    return {"success": True, "job": job}


def health() -> dict[str, Any]:
    st = _load_state()
    return {
        "success": True,
        "module": "question_intelligence_engine",
        "engine_version": "v2",
        "content_types": list(CONTENT_TYPES),
        "running_job": st.get("running_job", ""),
        "last_generation_at": st.get("last_generation_at", ""),
        "job_count": len(st.get("jobs") or {}),
        "output_count": len(st.get("outputs") or []),
    }


question_intelligence_engine = type("QuestionIntelligenceEngine", (), {
    "health": staticmethod(health),
    "generate_faq": staticmethod(generate_faq),
    "generate_far": staticmethod(generate_far),
    "generate_comparisons": staticmethod(generate_comparisons),
    "generate_bestof": staticmethod(generate_bestof),
    "generate_problem_solution": staticmethod(generate_problem_solution),
    "generate_local_intent": staticmethod(generate_local_intent),
    "generate_objections": staticmethod(generate_objections),
    "generate_ai_overview": staticmethod(generate_ai_overview),
    "generate_people_also_ask": staticmethod(generate_people_also_ask),
    "generate_autocomplete": staticmethod(generate_autocomplete),
    "generate_related_searches": staticmethod(generate_related_searches),
    "generate_reddit_intent": staticmethod(generate_reddit_intent),
    "generate_decision": staticmethod(generate_decision),
    "generate_entity_questions": staticmethod(generate_entity_questions),
    "generate_location_questions": staticmethod(generate_location_questions),
    "generate_all": staticmethod(generate_all),
    "export_report": staticmethod(export_report),
    "list_jobs": staticmethod(list_jobs),
    "get_job_detail": staticmethod(get_job_detail),
})()
