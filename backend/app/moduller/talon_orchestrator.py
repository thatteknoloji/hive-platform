"""Talon Orchestrator — HIVE merkezi SEO karar motoru."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.moduller.talon_stack.providers import (
    AutocompleteProvider,
    ExaProvider,
    PeopleAlsoAskProvider,
    SearXNGProvider,
    TavilyProvider,
    provider_health,
)
from app.moduller.talon_stack.services.talon_search_service import talon_search_service

logger = logging.getLogger("hive.talon.orchestrator")

STATE_FILE = Path(__file__).resolve().parent.parent / "talon_orchestrator_state.json"
REQUEST_TIMEOUT = 20

INTENTS = (
    "informational", "commercial", "local", "navigational",
    "transactional", "faq", "comparison",
)
PAGE_TYPES = (
    "astro_landing", "wordpress_page", "faq", "blog",
    "category", "support_network", "no_publish",
)

_INFO_PATTERNS = ("nedir", "nasıl", "ne zaman", "kimdir", "rehber", "hakkında", "neden")
_TX_PATTERNS = ("fiyat", "ücret", "rezervasyon", "satın", "sipariş", "book")
_LOCAL_PATTERNS = ("kuşadası", "aydın", "mahalle", "bölge", "yakın", "lokasyon", "merkez")
_FAQ_PATTERNS = ("?", "sss", "soru", "mi ", "mı ", "mu ", "mü ")
_CMP_PATTERNS = ("vs", "karşılaştır", "en iyi", "alternatif", "fark")
_NAV_PATTERNS = ("adres", "harita", "nerede", "yol tarifi", "konum")
_COMM_PATTERNS = ("escort", "vip", "hizmet", "model", "gece hayatı", "otel")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def normalize_keyword(keyword: str) -> str:
    return re.sub(r"\s+", " ", (keyword or "").strip())


def dedupe_keywords(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in keywords:
        kw = normalize_keyword(raw)
        if not kw:
            continue
        key = _norm_key(kw)
        if key in seen:
            continue
        seen.add(key)
        out.append(kw)
    return out


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"history": []}


def _save_research(record: dict[str, Any]) -> str:
    state = _load_state()
    rid = record.get("id") or str(uuid.uuid4())[:12]
    record["id"] = rid
    history = state.setdefault("history", [])
    history.insert(0, record)
    state["history"] = history[:25]
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return rid


def health() -> dict[str, Any]:
    providers = provider_health()
    configured = sum(1 for v in providers.values() if v in ("configured", "available"))
    return {
        "success": True,
        "status": "ok",
        "providers": providers,
        "providers_configured": configured,
        "ready": configured > 0,
    }


def keyword_discovery(seed_keyword: str, location: str | None = None) -> dict[str, Any]:
    seed = normalize_keyword(seed_keyword)
    if not seed:
        return {"success": False, "error": "seed_keyword gerekli"}

    loc = normalize_keyword(location or "")
    query = f"{loc} {seed}".strip() if loc and loc.lower() not in seed.lower() else seed

    sources: dict[str, Any] = {}
    errors: list[str] = []
    collected: list[str] = [seed]

    if SearXNGProvider.is_configured():
        try:
            for r in SearXNGProvider.search(query, 8):
                t = (r.get("title") or "").strip()
                if t:
                    collected.append(t)
            sources["searxng"] = True
        except Exception as e:
            errors.append(f"searxng: {e}")
            sources["searxng"] = False
    else:
        sources["searxng"] = False

    if TavilyProvider.is_configured():
        try:
            for r in TavilyProvider.search(query, 8):
                for field in ("title", "snippet"):
                    val = (r.get(field) or "").strip()
                    if val and len(val) < 120:
                        collected.append(val)
            sources["tavily"] = True
        except Exception as e:
            errors.append(f"tavily: {e}")
            sources["tavily"] = False
    else:
        sources["tavily"] = False

    if ExaProvider.is_configured():
        try:
            for r in ExaProvider.search(query, 8):
                t = (r.get("title") or "").strip()
                if t:
                    collected.append(t)
            sources["exa"] = True
        except Exception as e:
            errors.append(f"exa: {e}")
            sources["exa"] = False
    else:
        sources["exa"] = False

    if AutocompleteProvider.is_available():
        try:
            for r in AutocompleteProvider.expand_seed(query):
                kw = (r.get("keyword") or "").strip()
                if kw:
                    collected.append(kw)
            sources["autocomplete"] = True
        except Exception as e:
            errors.append(f"autocomplete: {e}")
            sources["autocomplete"] = False
    else:
        sources["autocomplete"] = False

    serp_for_paa: list[dict] = []
    if sources.get("searxng") or sources.get("tavily") or sources.get("exa"):
        serp = talon_search_service.search_web(query, {"num_results": 8})
        serp_for_paa = serp.get("results", [])

    paa_items: list[str] = []
    if serp_for_paa:
        try:
            snippets = [
                r.get("snippet") or r.get("title") or ""
                for r in serp_for_paa
                if isinstance(r, dict)
            ]
            paa = PeopleAlsoAskProvider.extract_from_snippets(query, snippets)
            for item in paa:
                q = (item.get("answer") or item.get("snippet") or item.get("title") or "").strip()
                if q:
                    paa_items.append(q)
                    collected.append(q.rstrip("?"))
            sources["paa"] = bool(paa_items)
        except Exception as e:
            errors.append(f"paa: {e}")
            sources["paa"] = False
    else:
        sources["paa"] = False

    keywords = dedupe_keywords(collected)
    primary_ok = any(sources.get(p) for p in ("searxng", "tavily", "exa", "autocomplete"))
    if not primary_ok:
        return {
            "success": False,
            "error": "Hiçbir Talon arama provider yapılandırılmamış",
            "sources": sources,
            "errors": errors,
            "keywords": [seed] if seed else [],
        }

    return {
        "success": True,
        "seed_keyword": seed,
        "location": loc,
        "query": query,
        "keywords": keywords,
        "count": len(keywords),
        "paa_questions": dedupe_keywords(paa_items),
        "sources": sources,
        "errors": errors,
    }


def intent_classifier(keyword: str) -> str:
    kw = _norm_key(keyword)
    if any(p in kw for p in _FAQ_PATTERNS):
        return "faq"
    if any(p in kw for p in _CMP_PATTERNS):
        return "comparison"
    if any(p in kw for p in _TX_PATTERNS):
        return "transactional"
    if any(p in kw for p in _NAV_PATTERNS):
        return "navigational"
    if any(p in kw for p in _INFO_PATTERNS):
        return "informational"
    if any(p in kw for p in _LOCAL_PATTERNS):
        return "local"
    if any(p in kw for p in _COMM_PATTERNS):
        return "commercial"
    return "informational"


def _geo_score(keyword: str, location: str) -> float:
    kw = _norm_key(keyword)
    loc = _norm_key(location)
    score = 0.0
    if loc and loc in kw:
        score += 0.5
    if any(p in kw for p in _LOCAL_PATTERNS):
        score += 0.3
    if len(kw.split()) >= 3:
        score += 0.1
    return min(1.0, score)


def page_type_recommender(keyword: str, intent: str, geo_score: float) -> str:
    if intent == "faq":
        return "faq"
    if intent == "comparison":
        return "blog"
    if intent == "navigational":
        return "wordpress_page"
    if intent == "transactional":
        return "wordpress_page"
    if intent == "commercial" and geo_score >= 0.4:
        return "astro_landing"
    if intent == "local" and geo_score >= 0.5:
        return "astro_landing"
    if intent == "local":
        return "wordpress_page"
    if intent == "commercial":
        return "category"
    if geo_score >= 0.6:
        return "astro_landing"
    if len(keyword.split()) >= 5:
        return "support_network"
    if intent == "informational":
        return "blog"
    return "wordpress_page"


def geo_cluster_builder(seed_keyword: str, location: str) -> dict[str, Any]:
    loc_query = normalize_keyword(location or seed_keyword)
    geo = talon_search_service.geo_seo_research(
        f"{loc_query} {seed_keyword}".strip(),
        {"mahalleler": []},
    )
    clusters: list[dict[str, Any]] = []
    geo_pages: list[dict[str, Any]] = []
    for page in geo.get("recommendedPages", []):
        entry = {
            "title": page.get("title", ""),
            "slug": page.get("slug", ""),
            "location": page.get("location", {}),
            "keyword": f"{page.get('title', '')} {seed_keyword}".strip(),
        }
        geo_pages.append(entry)
        clusters.append({
            "pillar": entry.get("slug", ""),
            "topic": seed_keyword,
            "location": location,
        })
    return {
        "success": True,
        "seed_keyword": seed_keyword,
        "location": location,
        "geo_entities": geo.get("geoEntities", []),
        "clusters": clusters,
        "geo_pages": geo_pages,
        "local_keywords": geo.get("localKeywords", []),
        "provider_used": bool(geo.get("geoEntities")),
    }


def competitor_discovery(keyword: str) -> dict[str, Any]:
    comp = talon_search_service.find_competitors(keyword, {"num_results": 10})
    serp = talon_search_service.search_web(keyword, {"num_results": 10})
    by_domain: dict[str, dict[str, Any]] = {}

    for r in serp.get("results", []):
        dom = _domain(r.get("url") or "")
        if not dom:
            continue
        row = by_domain.setdefault(dom, {
            "domain": dom,
            "titles": [],
            "snippets": [],
            "urls": [],
            "appearances": 0,
        })
        row["appearances"] += 1
        if r.get("title"):
            row["titles"].append(r["title"])
        if r.get("snippet"):
            row["snippets"].append(r["snippet"])
        if r.get("url"):
            row["urls"].append(r["url"])

    for c in comp.get("competitors", []):
        dom = c.get("domain", "")
        if dom and dom not in by_domain:
            by_domain[dom] = {
                "domain": dom,
                "titles": [],
                "snippets": [],
                "urls": [],
                "appearances": c.get("appearances", 1),
            }

    competitors = sorted(by_domain.values(), key=lambda x: -x["appearances"])[:20]
    return {
        "success": True,
        "keyword": keyword,
        "competitors": competitors,
        "count": len(competitors),
    }


def serp_gap_analysis(keyword: str) -> dict[str, Any]:
    serp = talon_search_service.search_web(keyword, {"num_results": 10})
    results = serp.get("results", [])[:10]
    if not results:
        return {
            "success": False,
            "error": "SERP sonucu yok — provider yapılandırmasını kontrol edin",
            "keyword": keyword,
        }

    titles = [(r.get("title") or "").strip() for r in results if r.get("title")]
    snippets = [(r.get("snippet") or "").strip() for r in results if r.get("snippet")]
    questions: list[str] = []
    try:
        paa = PeopleAlsoAskProvider.extract_from_serp_results(keyword, results)
        for item in paa:
            q = (item.get("answer") or item.get("snippet") or "").strip()
            if q:
                questions.append(q)
    except Exception:
        pass

    topics: list[str] = []
    for t in titles:
        topics.extend(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", t.lower()))
    topic_freq: dict[str, int] = {}
    for t in topics:
        if len(t) > 3:
            topic_freq[t] = topic_freq.get(t, 0) + 1
    common_topics = sorted(topic_freq, key=topic_freq.get, reverse=True)[:12]

    gaps: list[str] = []
    kw_low = _norm_key(keyword)
    if "fiyat" not in kw_low and not any("fiyat" in _norm_key(t) for t in titles):
        gaps.append(f"{keyword} fiyat rehberi eksik")
    if "güvenli" not in kw_low and not any("güven" in _norm_key(s) for s in snippets):
        gaps.append(f"{keyword} güvenlik / güvenilirlik içeriği açık")
    if len(questions) < 3:
        gaps.append("SSS / People Also Ask kapsamı zayıf — SSS sayfası fırsatı")

    return {
        "success": True,
        "keyword": keyword,
        "serp_count": len(results),
        "titles": titles,
        "questions": dedupe_keywords(questions),
        "common_topics": common_topics,
        "content_gaps": gaps,
        "opportunities": gaps + questions[:5],
    }


def content_brief_generator(
    keyword: str,
    location: str = "",
    intent: str = "",
    page_type: str = "",
) -> dict[str, Any]:
    kw = normalize_keyword(keyword)
    loc = normalize_keyword(location)
    intent_val = intent or intent_classifier(kw)
    geo = _geo_score(kw, loc)
    page = page_type or page_type_recommender(kw, intent_val, geo)

    gap = serp_gap_analysis(kw)
    questions = gap.get("questions", []) if gap.get("success") else []
    comp = competitor_discovery(kw)
    domains = [c["domain"] for c in comp.get("competitors", [])[:5]]

    title_base = kw.title()[:70]
    loc_part = f"{loc} " if loc else ""
    brief = {
        "keyword": kw,
        "intent": intent_val,
        "recommended_page_type": page,
        "title_options": [
            f"{loc_part}{title_base} Rehberi",
            f"{title_base} — {loc or 'Kuşadası'} 2026",
            f"{title_base} Hakkında Bilmeniz Gerekenler",
        ],
        "h1": f"{loc_part}{title_base}",
        "h2_outline": [
            f"{kw.title()} Nedir?",
            f"{loc or 'Bölge'} Hakkında Genel Bilgi",
            "Öne Çıkan Mekanlar ve Deneyimler",
            "Sık Sorulan Sorular",
            "Sonuç ve Öneriler",
        ],
        "faq_questions": questions[:8] or [f"{kw} nedir?", f"{kw} nerede?", f"{kw} fiyatları"],
        "entities": [loc] if loc else ["Kuşadası", "Aydın"],
        "internal_link_targets": ["anasayfa", "kategori", "sss", "blog"],
        "external_source_suggestions": domains,
        "schema_recommendations": (
            ["FAQPage"] if page == "faq"
            else ["Article"] if page == "blog"
            else ["WebPage", "LocalBusiness"] if page == "astro_landing"
            else ["WebPage"]
        ),
        "content_gaps": gap.get("content_gaps", []),
    }
    return {"success": True, "content_brief": brief}


def publish_priority_score(record: dict[str, Any]) -> int:
    kw = record.get("keyword", "")
    intent = record.get("intent", "")
    geo = float(record.get("geo_score", 0))
    diff = float(record.get("difficulty_proxy", 0.5))
    competitors = len(record.get("competitors", []))
    questions = len(record.get("questions", []))
    page_type = record.get("recommended_page_type", "")

    score = 40.0
    score += geo * 25
    if intent in ("local", "commercial", "transactional"):
        score += 12
    if intent == "faq":
        score += 8
    if questions >= 3:
        score += 10
    if len(kw.split()) >= 4:
        score += 8
    if page_type in ("astro_landing", "wordpress_page", "faq"):
        score += 10
    if page_type == "no_publish":
        score -= 30
    score -= min(20, competitors * 2)
    score -= diff * 15
    return max(0, min(100, int(round(score))))


def _difficulty_proxy(competitor_count: int, serp_count: int) -> float:
    if serp_count == 0:
        return 0.5
    return min(1.0, (competitor_count / max(serp_count, 1)) * 0.6 + 0.2)


def build_keyword_record(
    keyword: str,
    location: str,
    *,
    competitors: list[dict] | None = None,
    questions: list[str] | None = None,
    related: list[str] | None = None,
    sources: list[str] | None = None,
    content_brief: dict | None = None,
) -> dict[str, Any]:
    kw = normalize_keyword(keyword)
    intent = intent_classifier(kw)
    geo = _geo_score(kw, location)
    page_type = page_type_recommender(kw, intent, geo)
    comp_list = competitors or []
    diff = _difficulty_proxy(len(comp_list), 10)
    record: dict[str, Any] = {
        "keyword": kw,
        "location": location,
        "intent": intent,
        "recommended_page_type": page_type,
        "geo_score": round(geo, 3),
        "difficulty_proxy": round(diff, 3),
        "competitors": comp_list[:5],
        "questions": questions or [],
        "related_keywords": related or [],
        "content_brief": content_brief or {},
        "sources": sources or [],
        "created_at": _now(),
    }
    record["opportunity_score"] = publish_priority_score(record)
    if record["opportunity_score"] < 25:
        record["recommended_page_type"] = "no_publish"
    return record


def full_research(seed_keyword: str, location: str = "", limit: int = 50) -> dict[str, Any]:
    seed = normalize_keyword(seed_keyword)
    loc = normalize_keyword(location or "Kuşadası")
    if not seed:
        return {"success": False, "error": "seed_keyword gerekli"}

    limit = max(5, min(limit, 100))
    discovery = keyword_discovery(seed, loc)
    if not discovery.get("success"):
        return discovery

    geo_data = geo_cluster_builder(seed, loc)
    comp_seed = competitor_discovery(f"{loc} {seed}".strip())
    gap_seed = serp_gap_analysis(f"{loc} {seed}".strip())

    keywords_raw = discovery.get("keywords", [])[:limit]
    paa_all = discovery.get("paa_questions", [])
    if gap_seed.get("success"):
        paa_all = dedupe_keywords(paa_all + gap_seed.get("questions", []))

    keyword_records: list[dict[str, Any]] = []
    for kw in keywords_raw:
        brief_res = content_brief_generator(kw, loc)
        brief = brief_res.get("content_brief", {})
        record = build_keyword_record(
            kw,
            loc,
            competitors=comp_seed.get("competitors", [])[:3],
            questions=[q for q in paa_all if _norm_key(kw) in _norm_key(q) or _norm_key(q) in _norm_key(kw)][:5] or paa_all[:3],
            related=keywords_raw[:8],
            sources=[k for k, v in (discovery.get("sources") or {}).items() if v],
            content_brief=brief,
        )
        keyword_records.append(record)

    keyword_records.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

    astro_ready = [r for r in keyword_records if r["recommended_page_type"] == "astro_landing" and r["opportunity_score"] >= 30]
    page_hub_ready = [r for r in keyword_records if r["recommended_page_type"] in ("wordpress_page", "category", "blog") and r["opportunity_score"] >= 25]
    sss_ready = [r for r in keyword_records if r["recommended_page_type"] == "faq" or r["intent"] == "faq"]
    publisher_ready = [r for r in keyword_records if r["recommended_page_type"] in ("support_network", "blog") and r["opportunity_score"] >= 35]

    result = {
        "success": True,
        "seed_keyword": seed,
        "location": loc,
        "keywords": keyword_records,
        "clusters": geo_data.get("clusters", []),
        "competitors": comp_seed.get("competitors", []),
        "faq_questions": paa_all[:30],
        "geo_pages": geo_data.get("geo_pages", []),
        "recommended_pages": [
            {
                "keyword": r["keyword"],
                "page_type": r["recommended_page_type"],
                "opportunity_score": r["opportunity_score"],
                "intent": r["intent"],
            }
            for r in keyword_records[:20]
        ],
        "astro_factory_ready": astro_ready[:15],
        "page_hub_ready": page_hub_ready[:20],
        "sss_ready": sss_ready[:20],
        "publisher_ready": publisher_ready[:15],
        "providers": discovery.get("sources", {}),
        "provider_errors": discovery.get("errors", []),
        "serp_gaps": gap_seed.get("content_gaps", []) if gap_seed.get("success") else [],
        "created_at": _now(),
    }
    result["id"] = _save_research(result)
    return result


def list_history(limit: int = 20) -> dict[str, Any]:
    history = _load_state().get("history", [])[:limit]
    return {"success": True, "history": history, "count": len(history)}


def get_scored_keyword_queue(seed_keyword: str, location: str = "", limit: int = 30) -> dict[str, Any]:
    """Page Hub / Category Hub için skorlu keyword kuyruğu."""
    res = full_research(seed_keyword, location, limit=limit)
    if not res.get("success"):
        return res
    queue = [
        {
            "keyword": r["keyword"],
            "opportunity_score": r["opportunity_score"],
            "intent": r["intent"],
            "recommended_page_type": r["recommended_page_type"],
            "content_brief": r.get("content_brief", {}),
        }
        for r in res.get("page_hub_ready", [])[:limit]
    ]
    return {
        "success": True,
        "keywords": [q["keyword"] for q in queue],
        "queue": queue,
        "total": len(queue),
        "research_id": res.get("id"),
    }


def get_sss_keyword_pool(main_keyword: str, location: str = "", count: int = 50) -> dict[str, Any]:
    """SSS Automation için Talon soru + keyword havuzu."""
    res = full_research(main_keyword, location, limit=min(count, 60))
    if not res.get("success"):
        return res
    keywords: list[str] = []
    for r in res.get("sss_ready", []):
        keywords.append(r["keyword"])
    for q in res.get("faq_questions", []):
        qn = normalize_keyword(q.rstrip("?"))
        if qn and qn not in keywords:
            keywords.append(qn)
    return {
        "success": True,
        "keywords": keywords[:count],
        "faq_questions": res.get("faq_questions", [])[:count],
        "research_id": res.get("id"),
    }


def get_astro_plan_data(seed_keyword: str, location: str = "", page_count: int = 10) -> dict[str, Any]:
    """Astro Factory plan üretimi için Talon verisi."""
    res = full_research(seed_keyword, location, limit=max(page_count, 15))
    if not res.get("success"):
        return res
    return {
        "success": True,
        "seed_keyword": seed_keyword,
        "location": location,
        "keywords": [r["keyword"] for r in res.get("keywords", [])],
        "astro_factory_ready": res.get("astro_factory_ready", []),
        "geo_pages": res.get("geo_pages", []),
        "faq_questions": res.get("faq_questions", []),
        "clusters": res.get("clusters", []),
        "competitors": res.get("competitors", []),
        "research_id": res.get("id"),
        "talon_meta": {
            "providers": res.get("providers", {}),
            "provider_errors": res.get("provider_errors", []),
            "keyword_count": len(res.get("keywords", [])),
        },
    }


talon_orchestrator = type("TalonOrchestrator", (), {
    "health": staticmethod(health),
    "keyword_discovery": staticmethod(keyword_discovery),
    "intent_classifier": staticmethod(intent_classifier),
    "page_type_recommender": staticmethod(page_type_recommender),
    "geo_cluster_builder": staticmethod(geo_cluster_builder),
    "competitor_discovery": staticmethod(competitor_discovery),
    "serp_gap_analysis": staticmethod(serp_gap_analysis),
    "content_brief_generator": staticmethod(content_brief_generator),
    "publish_priority_score": staticmethod(publish_priority_score),
    "full_research": staticmethod(full_research),
    "list_history": staticmethod(list_history),
    "get_scored_keyword_queue": staticmethod(get_scored_keyword_queue),
    "get_sss_keyword_pool": staticmethod(get_sss_keyword_pool),
    "get_astro_plan_data": staticmethod(get_astro_plan_data),
    "normalize_keyword": staticmethod(normalize_keyword),
    "dedupe_keywords": staticmethod(dedupe_keywords),
    "build_keyword_record": staticmethod(build_keyword_record),
})()
