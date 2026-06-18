"""SEO GEO AEO Quality Gate — klasik SEO, GEO, AEO/AI Overview, entity ve topical authority analizi."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.moduller.astro_factory import GENERATED_DIR, _get_project, _project_path, _safe_slug

logger = logging.getLogger("hive.seo_quality_gate")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
REPORTS_DIR = ROOT / "reports"
URL_TIMEOUT = 15

SEVERITY_PENALTY = {"critical": 10, "warning": 3, "info": 1}
RISK_SEVERITY_WEIGHT = {"critical": 25, "warning": 12, "info": 4}
PASS_THRESHOLD = 85
WARNING_THRESHOLD = 70
FAIL_THRESHOLD = 70
GEO_DEPLOY_MIN = 70
AEO_PUBLISHER_MIN = 70
RISK_FAIL_THRESHOLD = 60
MIN_WORDS = 150
TITLE_MAX = 70
META_DESC_MAX = 160
KEYWORD_STUFFING_RATIO = 0.03
ANSWER_BOX_MIN_WORDS = 40
ANSWER_BOX_MAX_WORDS = 60

MODULE_NAME = "SEO GEO AEO Quality Gate"

SEO_CATEGORIES = frozenset({"meta", "headings", "content", "links", "images", "technical"})
GEO_CATEGORIES = frozenset({"geo"})
AEO_CATEGORIES = frozenset({"aeo"})
ENTITY_CATEGORIES = frozenset({"entity"})
AUTHORITY_CATEGORIES = frozenset({"authority", "freshness"})
RISK_CATEGORIES = frozenset({"risk"})

NEIGHBOR_REGIONS = (
    "güzelçamlı", "selçuk", "izmir", "davutlar", "söke", "didim", "pamucak", "kadınlar denizi",
)
LOCAL_SUBHEADING_KEYWORDS = (
    "fiyat", "ücret", "ulaşım", "nasıl gidilir", "güven", "güvenli", "saat", "ne zaman",
    "mekan", "otel", "bar", "restoran", "ulaşım", "park", "harita", "adres",
)
AEO_QUESTION_CHECKS = (
    ("nedir", "AEO_MISSING_NEDIR", "Nedir sorusuna doğrudan cevap yok"),
    ("nasıl", "AEO_MISSING_NASIL", "Nasıl sorusuna doğrudan cevap yok"),
    ("nerede", "AEO_MISSING_NEREDE", "Nerede sorusuna doğrudan cevap yok"),
    ("ne kadar", "AEO_MISSING_PRICE", "Fiyat/ne kadar cevabı yok"),
    ("fiyat", "AEO_MISSING_PRICE", "Fiyat bilgisi yok"),
    ("en iyi", "AEO_MISSING_BEST", "En iyi seçenek cevabı yok"),
)
SERVICE_KEYWORDS = ("escort", "hizmet", "otel", "bar", "restoran", "tur", "rehber", "gece hayatı")
COMPETITOR_HINTS = ("booking", "tripadvisor", "otelleri.com", "tatil", "alternatif")

_BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"reports": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _status_from_score(score: int, risk_score: int = 0) -> str:
    if risk_score > RISK_FAIL_THRESHOLD:
        return "fail"
    if score < FAIL_THRESHOLD:
        return "fail"
    if score >= PASS_THRESHOLD:
        return "pass"
    if score >= WARNING_THRESHOLD:
        return "warning"
    return "fail"


def _issues_in_categories(issues: list[dict[str, Any]], categories: frozenset[str]) -> list[dict[str, Any]]:
    return [i for i in issues if i.get("category") in categories]


def _dimension_score(issues: list[dict[str, Any]], categories: frozenset[str]) -> int:
    return _calculate_score(_issues_in_categories(issues, categories))


def _calculate_risk_score(issues: list[dict[str, Any]]) -> int:
    score = 0
    for iss in _issues_in_categories(issues, RISK_CATEGORIES):
        score += RISK_SEVERITY_WEIGHT.get(iss.get("severity", "info"), 5)
    return min(100, score)


def _research_citation_score(plain: str, html: str = "") -> int:
    """Agentic SEO / CPS-inspired: declarative openings, fact density, quotable blocks."""
    if not plain.strip():
        return 15
    score = 45
    paras = _paragraphs_from_html(html or f"<p>{plain}</p>")
    first = paras[0] if paras else plain[:400]
    first_sent = re.split(r"[.!?]+", first)[0].strip()
    if first_sent and len(first_sent.split()) <= 28:
        score += 18
    facts = len(re.findall(r"\b\d{4}\b|\b\d+%|\b\d+\s*(tl|usd|km)\b", plain, re.I))
    score += min(22, facts * 4)
    if html and re.search(r"<h[23][^>]*>[^<]*\?", html, re.I):
        score += 10
    atomic = sum(1 for p in paras if 25 <= len(p.split()) <= 80)
    score += min(15, atomic * 5)
    return max(0, min(100, score))


def _research_answerability_score(plain: str, html: str = "") -> int:
    """Direct-answer + FAQ / Q-shaped structure for AEO."""
    if not plain.strip():
        return 10
    score = 40
    if re.search(r"\b(nasıl|nedir|ne zaman|nerede|kaç|kim)\b", plain, re.I):
        score += 12
    if html:
        faq_blocks = len(re.findall(r"<h[23][^>]*>.*\?", html, re.I))
        score += min(25, faq_blocks * 8)
    if re.search(r"\b(cevap|sonuç|özet)\b", plain, re.I):
        score += 8
    short_answers = sum(1 for p in _paragraphs_from_html(html or plain) if 20 <= len(p.split()) <= 60)
    score += min(20, short_answers * 6)
    return max(0, min(100, score))


def _question_coverage_score(html: str, plain: str = "") -> int:
    """QIE V2 — question density (H3, ?, soru kelimeleri)."""
    if not html.strip() and not plain.strip():
        return 0
    text = plain or re.sub(r"<[^>]+>", " ", html)
    h3 = len(re.findall(r"<h3[^>]*>", html, re.I))
    qmarks = text.count("?")
    q_words = len(re.findall(r"\b(nasıl|nedir|nerede|hangi|mi|mı|mu|mü)\b", text, re.I))
    score = min(40, h3 * 8) + min(30, qmarks * 10) + min(30, q_words * 5)
    return max(0, min(100, score))


def _entity_names_from_payload(entities: Any) -> list[str]:
    if isinstance(entities, list):
        return [str(e) for e in entities]
    if isinstance(entities, dict):
        names: list[str] = []
        if entities.get("primary"):
            names.append(str(entities["primary"]))
        for key in ("secondary", "category", "brand", "services"):
            names.extend(str(x) for x in (entities.get(key) or []))
        return names
    return []


def _entity_question_score(plain: str, entities: list[str]) -> int:
    """QIE V2 — entity mentions in question content."""
    if not plain.strip():
        return 20
    if not entities:
        return 45
    hits = sum(1 for e in entities if e and e.lower() in plain.lower())
    return max(0, min(100, int((hits / max(len(entities), 1)) * 90 + 10)))


def _paa_score(related_questions: list[str]) -> int:
    """QIE V2 — People Also Ask chain depth."""
    n = len(related_questions or [])
    if n == 0:
        return 15
    if n >= 8:
        return 95
    if n >= 4:
        return 75
    return 50


def _autocomplete_score(keyword: str, suggestions: list[str]) -> int:
    """QIE V2 — autocomplete variation coverage."""
    if not keyword.strip():
        return 10
    if not suggestions:
        return 25
    base = keyword.lower().strip()
    hits = sum(1 for s in suggestions if base in (s or "").lower())
    return max(0, min(100, int((hits / max(len(suggestions), 1)) * 100)))


def _faq_coverage_score(html: str, expected_questions: int = 5) -> int:
    """Question Intelligence — FAQ/H3 coverage vs expected question count."""
    if not html.strip():
        return 0
    h3_count = len(re.findall(r"<h3[^>]*>", html, re.I))
    faq_schema = len(re.findall(r'"@type"\s*:\s*"Question"', html, re.I))
    found = max(h3_count, faq_schema)
    if expected_questions <= 0:
        return min(100, found * 15)
    ratio = found / expected_questions
    return max(0, min(100, int(ratio * 100)))


def _intent_coverage_score(keyword: str, plain: str) -> int:
    """Question Intelligence — keyword intent signals in content."""
    if not keyword.strip() or not plain.strip():
        return 30
    kw_parts = [p for p in re.split(r"\s+", keyword.lower()) if len(p) > 2]
    if not kw_parts:
        return 40
    text = plain.lower()
    hits = sum(1 for p in kw_parts if p in text)
    score = int((hits / len(kw_parts)) * 55)
    try:
        from app.moduller.talon_orchestrator import intent_classifier
        intent = intent_classifier(keyword)
        intent_markers = {
            "faq": ["nedir", "nasıl", "mi", "mı", "soru"],
            "comparison": ["karşılaştır", "mı", "mi", "fark", "artı", "eksi"],
            "transactional": ["fiyat", "ücret", "rezervasyon", "satın"],
            "navigational": ["nerede", "adres", "yakın", "merkez"],
        }
        for marker in intent_markers.get(intent, []):
            if marker in text:
                score += 8
    except Exception:
        pass
    return max(0, min(100, score))


def _overview_score(plain: str, html: str = "") -> int:
    """Question Intelligence — AI Overview readiness (alias of overview probability)."""
    return _research_overview_probability(plain, html)


def _research_overview_probability(plain: str, html: str = "") -> int:
    """Semantic containment + atomic answer blocks for AI Overview."""
    if not plain.strip():
        return 10
    score = 38
    paras = _paragraphs_from_html(html or f"<p>{plain}</p>")
    contained = sum(1 for p in paras if 3 <= len(re.split(r"[.!?]+", p)) <= 6 and len(p.split()) >= 35)
    score += min(30, contained * 10)
    if re.search(r"\b(örneğin|yani|sonuç olarak|bu nedenle)\b", plain, re.I):
        score += 8
    lists = len(re.findall(r"<[ou]l>", html or "", re.I))
    score += min(12, lists * 4)
    return max(0, min(100, score))


def _research_llm_visibility(html: str, plain: str) -> int:
    """Agentic SEO-inspired: parseable structure for LLM extraction."""
    if not plain.strip():
        return 10
    score = 42
    soup = _parse_html(html or f"<p>{plain}</p>")
    h2 = len(soup.find_all("h2"))
    h3 = len(soup.find_all("h3"))
    score += min(20, h2 * 5 + h3 * 3)
    if soup.find("h1"):
        score += 8
    lists = len(soup.find_all(["ul", "ol"]))
    score += min(12, lists * 4)
    if len(plain.split()) <= 2500:
        score += 8
    return max(0, min(100, score))


def _research_competitive_gap_score(pages: list[dict[str, Any]], keyword: str) -> int:
    """SEOctopus-inspired: thin coverage vs keyword intent."""
    if not pages or not keyword:
        return 50
    kw = keyword.lower()
    covering = sum(
        1 for p in pages
        if kw in (p.get("title") or "").lower() or kw in _strip_html(p.get("content_html", "")).lower()
    )
    if covering >= 3:
        return 75
    if covering == 0:
        return 25
    return 50


def _compute_overall_score(
    seo_score: int,
    geo_score: int,
    aeo_score: int,
    entity_score: int,
    authority_score: int,
    risk_score: int,
    citation_score: int = 0,
    llm_visibility_score: int = 0,
) -> int:
    cite = citation_score if citation_score else int((aeo_score + authority_score) / 2 * 0.5)
    llm = llm_visibility_score if llm_visibility_score else int((aeo_score + seo_score) / 2 * 0.5)
    base = int(
        seo_score * 0.25
        + geo_score * 0.20
        + aeo_score * 0.20
        + entity_score * 0.15
        + authority_score * 0.10
        + cite * 0.05
        + llm * 0.05
    )
    if risk_score > RISK_FAIL_THRESHOLD:
        return min(base, FAIL_THRESHOLD - 1)
    if risk_score > 40:
        base = max(0, base - int((risk_score - 40) * 0.3))
    return max(0, min(100, base))


def _compute_deploy_gate(scores: dict[str, int]) -> dict[str, Any]:
    overall = scores["overall_score"]
    risk = scores["risk_score"]
    geo = scores["geo_score"]
    aeo = scores["aeo_score"]
    status = _status_from_score(overall, risk)
    return {
        "status": status,
        "deploy_allowed": status == "pass",
        "geo_deploy_allowed": geo >= GEO_DEPLOY_MIN,
        "publisher_hub_allowed": aeo >= AEO_PUBLISHER_MIN,
        "support_network_allowed": (
            overall >= PASS_THRESHOLD and aeo >= AEO_PUBLISHER_MIN and risk <= 40
        ),
    }


def _compute_readiness(scores: dict[str, int]) -> dict[str, bool]:
    return {
        "google_search_ready": scores["seo_score"] >= 80 and scores["risk_score"] <= 50,
        "geo_local_ready": scores["geo_score"] >= GEO_DEPLOY_MIN,
        "ai_overview_ready": scores["aeo_score"] >= AEO_PUBLISHER_MIN,
        "support_network_ready": (
            scores["overall_score"] >= PASS_THRESHOLD
            and scores["aeo_score"] >= AEO_PUBLISHER_MIN
            and scores["risk_score"] <= 40
        ),
    }


def _paragraphs_from_html(html: str) -> list[str]:
    soup = _parse_html(html)
    return [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(strip=True)]


def _has_location_context(plain: str, location: str) -> bool:
    if not location:
        return False
    loc = location.lower()
    text = plain.lower()
    if loc not in text:
        return False
    for sent in re.split(r"[.!?]+", text):
        if loc in sent and len(sent.split()) >= 6:
            return True
    return False


def _extract_entities(
    page: dict[str, Any],
    keyword: str,
    location: str,
    plain: str,
    main_site: str,
) -> dict[str, Any]:
    soup = _parse_html(page.get("content_html", ""))
    plain_low = plain.lower()
    secondary = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]
    category_hits = [w for w in ("gece hayatı", "eğlence", "turizm", "otel", "restoran") if w in plain_low]
    brand: list[str] = []
    if main_site:
        dom = urlparse(main_site if "://" in main_site else f"https://{main_site}").netloc
        if dom:
            brand.append(dom.replace("www.", ""))
    if "balkutusu" in plain_low:
        brand.append("balkutusu.com")
    competitors = [c for c in COMPETITOR_HINTS if c in plain_low]
    services = [s for s in SERVICE_KEYWORDS if s in plain_low]
    entities = {
        "primary": keyword or page.get("title", ""),
        "secondary": secondary[:8],
        "location": location,
        "category": category_hits,
        "brand": list(dict.fromkeys(brand)),
        "competitor": competitors,
        "service": services,
    }
    return entities


def _entity_coverage_score(entities: dict[str, Any]) -> int:
    checks = [
        bool(entities.get("primary")),
        len(entities.get("secondary") or []) >= 1,
        bool(entities.get("location")),
        len(entities.get("category") or []) >= 1,
        len(entities.get("brand") or []) >= 1,
        len(entities.get("service") or []) >= 1,
        len(entities.get("competitor") or []) >= 1,
    ]
    present = sum(1 for c in checks if c)
    return int(round(present / len(checks) * 100))


def _analyze_geo_extended(
    page: dict[str, Any],
    location: str,
    plain: str,
    soup: BeautifulSoup,
    schema_str: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    page_id = page.get("slug") or "home"
    page_type = page.get("type", "")
    plain_low = plain.lower()
    loc = (location or "").lower()

    if page_type in ("geo", "home", "faq") and loc:
        if loc in plain_low and not _has_location_context(plain, location):
            issues.append(_issue(
                "GEO_KEYWORD_ONLY", "Lokasyon yalnızca keyword gibi geçiyor, bağlamsal cümle yok",
                "warning", page=page_id, category="geo",
            ))
        if not _has_location_context(plain, location):
            issues.append(_issue(
                "GEO_NO_CONTEXT", "Lokasyon entity bağlamı zayıf",
                "warning", page=page_id, category="geo",
            ))
        if not any(n in plain_low for n in NEIGHBOR_REGIONS):
            issues.append(_issue(
                "GEO_MISSING_NEIGHBOR", "Yakın bölge/komşu lokasyon referansı yok",
                "info", page=page_id, category="geo",
            ))
        entity_markers = ("mekan", "otel", "bar", "marina", "sahil", "merkez", "meydan")
        if not any(m in plain_low for m in entity_markers):
            issues.append(_issue(
                "GEO_NO_ENTITY_LIST", "Yerel mekan/bölge entity listesi zayıf",
                "warning", page=page_id, category="geo",
            ))
        missing_subs = [k for k in LOCAL_SUBHEADING_KEYWORDS[:10] if k not in plain_low]
        if len(missing_subs) >= 7:
            issues.append(_issue(
                "GEO_MISSING_SUBHEADINGS",
                "Yerel alt başlıklar eksik (fiyat, ulaşım, güvenlik, saat vb.)",
                "warning", page=page_id, category="geo",
            ))
        if page_type == "geo" and "place" not in schema_str and "localbusiness" not in schema_str:
            issues.append(_issue(
                "GEO_MISSING_PLACE_SCHEMA", "Place / LocalBusiness schema eksik",
                "warning", page=page_id, category="geo",
            ))
        if "breadcrumb" not in schema_str and page_type in ("geo", "blog"):
            issues.append(_issue(
                "GEO_MISSING_BREADCRUMB", "Breadcrumb schema eksik",
                "info", page=page_id, category="geo",
            ))
    return issues


def _analyze_aeo(page: dict[str, Any], plain: str, soup: BeautifulSoup) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    page_id = page.get("slug") or "home"
    plain_low = plain.lower()

    short_answers = [
        p for p in _paragraphs_from_html(page.get("content_html", ""))
        if ANSWER_BOX_MIN_WORDS <= _word_count(p) <= ANSWER_BOX_MAX_WORDS + 20
    ]
    if not short_answers:
        issues.append(_issue(
            "AEO_NO_ANSWER_BOX", "40-60 kelimelik net cevap kutusu (answer box) yok",
            "warning", page=page_id, category="aeo",
        ))

    for pattern, code, msg in AEO_QUESTION_CHECKS:
        if pattern not in plain_low:
            issues.append(_issue(code, msg, "info", page=page_id, category="aeo"))

    if page.get("type") == "faq":
        if "?" not in plain and "cevap" not in plain_low:
            issues.append(_issue(
                "AEO_FAQ_NOT_DIRECT", "SSS cevapları doğrudan/alıntılanabilir formatta değil",
                "warning", page=page_id, category="aeo",
            ))

    declarative = [s.strip() for s in re.split(r"[.!?]+", plain) if 8 <= len(s.split()) <= 25]
    if len(declarative) < 2:
        issues.append(_issue(
            "AEO_NO_CITABLE", "Kaynak gösterilebilir net bildirim cümleleri az",
            "info", page=page_id, category="aeo",
        ))

    has_structure = bool(soup.find_all(["ul", "ol", "table"]))
    if not has_structure and _word_count(plain) > 120:
        issues.append(_issue(
            "AEO_NO_LIST_STRUCTURE", "Liste, tablo veya madde yapısı yok",
            "info", page=page_id, category="aeo",
        ))

    vague_markers = ("belki", "sanırım", "gibi", "vb.", "vs.")
    vague_count = sum(plain_low.count(v) for v in vague_markers)
    if vague_count >= 4:
        issues.append(_issue(
            "AEO_NOT_AI_FRIENDLY", "İçerik AI cevabı için fazla belirsiz",
            "warning", page=page_id, category="aeo",
        ))

    return issues


def _analyze_entity_issues(
    entities: dict[str, Any],
    page_id: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    cov = _entity_coverage_score(entities)
    if not entities.get("primary"):
        issues.append(_issue("ENTITY_NO_PRIMARY", "Ana entity tanımlı değil", "warning", page=page_id, category="entity"))
    if not entities.get("location"):
        issues.append(_issue("ENTITY_NO_LOCATION", "Lokasyon entity eksik", "warning", page=page_id, category="entity"))
    if not entities.get("service"):
        issues.append(_issue("ENTITY_NO_SERVICE", "Hizmet entity eksik", "info", page=page_id, category="entity"))
    if cov < 50:
        issues.append(_issue(
            "ENTITY_LOW_COVERAGE", f"Entity coverage düşük ({cov}/100)",
            "warning", page=page_id, category="entity",
        ))
    return issues


def _analyze_trust_freshness(
    page: dict[str, Any],
    plain: str,
    soup: BeautifulSoup,
    main_site: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    page_id = page.get("slug") or "home"
    plain_low = plain.lower()
    year = str(datetime.now(timezone.utc).year)

    trust_markers = ("yazar", "kurum", "editör", "kaynak", "iletişim", "hakkımızda", "güncelleme")
    if not any(t in plain_low for t in trust_markers) and main_site not in plain:
        issues.append(_issue(
            "TRUST_NO_SIGNAL", "Yazar/kurum/kaynak güven sinyali zayıf",
            "info", page=page_id, category="authority",
        ))
    if year not in plain and "2026" not in plain and "2025" not in plain:
        issues.append(_issue(
            "FRESH_NO_YEAR", f"Güncel yıl ({year}) referansı yok",
            "info", page=page_id, category="freshness",
        ))
    variable_kw = ("fiyat", "saat", "ücret", "açık", "kapanış")
    if any(k in plain_low for k in variable_kw) and "güncel" not in plain_low and "son güncelleme" not in plain_low:
        issues.append(_issue(
            "FRESH_NO_VARIABLE_NOTE", "Değişken bilgi (fiyat/saat) için güncellik notu yok",
            "info", page=page_id, category="freshness",
        ))
    if "son güncelleme" not in plain_low and "güncellendi" not in plain_low:
        issues.append(_issue(
            "FRESH_NO_UPDATE_DATE", "Son güncelleme tarihi belirtilmemiş",
            "info", page=page_id, category="freshness",
        ))
    if _word_count(plain) < 80:
        issues.append(_issue(
            "TRUST_LOW_VALUE", "İçerik kullanıcıya düşük fayda sağlıyor (çok kısa)",
            "warning", page=page_id, category="authority",
        ))
    return issues


def _analyze_topical_authority(
    pages: list[dict[str, Any]],
    plan: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    slugs = {p.get("slug") or "home" for p in pages}
    geo_count = sum(1 for p in pages if p.get("type") == "geo")
    blog_count = sum(1 for p in pages if p.get("type") == "blog")
    faq_count = sum(1 for p in pages if p.get("type") == "faq")
    internal_links = 0
    for page in pages:
        soup = _parse_html(page.get("content_html", ""))
        internal_links += sum(
            1 for a in soup.find_all("a", href=True)
            if not a["href"].startswith("http")
        )

    if geo_count + blog_count + faq_count < 2:
        issues.append(_issue(
            "TOPICAL_WEAK_CLUSTER", "Konu kümesinde yeterli destek sayfası yok",
            "warning", category="authority",
        ))
    clusters = (plan or {}).get("content_clusters") or []
    if not clusters and geo_count >= 2:
        issues.append(_issue(
            "TOPICAL_NO_PILLAR", "Pillar/cluster yapısı tanımlı değil",
            "info", category="authority",
        ))
    if internal_links < max(3, len(pages)):
        issues.append(_issue(
            "TOPICAL_WEAK_INTERNAL", "İç link ağı zayıf",
            "warning", category="authority",
        ))
    if geo_count >= 1 and blog_count == 0 and faq_count == 0:
        issues.append(_issue(
            "TOPICAL_ORPHAN_GEO", "GEO sayfaları cluster/blog/SSS desteği olmadan kalmış",
            "warning", category="authority",
        ))

    for page in pages:
        soup = _parse_html(page.get("content_html", ""))
        links = [a.get("href", "") for a in soup.find_all("a", href=True) if not a["href"].startswith("http")]
        if page.get("type") != "home" and len(links) == 0:
            pid = page.get("slug") or "home"
            issues.append(_issue(
                "TOPICAL_ORPHAN_PAGE", "Sayfa iç link ağından izole",
                "info", page=pid, category="authority",
            ))
    return issues


def _extended_risk_checks(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    geo_pages = [p for p in pages if p.get("type") == "geo"]
    if len(geo_pages) >= 3:
        bodies = [_strip_html(p.get("content_html", ""))[:300] for p in geo_pages]
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                if _similarity(bodies[i], bodies[j]) > 0.9:
                    issues.append(_issue(
                        "GEO_COPY_VARIANT", "Sadece lokasyon değiştirilmiş kopya GEO sayfa riski",
                        "critical", category="risk",
                    ))
                    return issues
    for page in pages:
        plain = _strip_html(page.get("content_html", ""))
        if _word_count(plain) < 40 and page.get("type") == "geo":
            issues.append(_issue(
                "PROGRAMMATIC_THIN", "Yapay/boş programmatic GEO sayfa riski",
                "critical", page=page.get("slug") or "home", category="risk",
            ))
            break
    return issues


def _issue(
    code: str,
    message: str,
    severity: str,
    *,
    page: str = "",
    category: str = "",
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "severity": severity,
        "page": page,
        "category": category,
        "penalty": SEVERITY_PENALTY.get(severity, 0),
    }


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or "", re.UNICODE))


def _strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "html.parser")


def _keyword_density(text: str, keyword: str) -> float:
    if not keyword or not text:
        return 0.0
    words = re.findall(r"\w+", text.lower(), re.UNICODE)
    if not words:
        return 0.0
    kw_parts = keyword.lower().split()
    if len(kw_parts) == 1:
        hits = sum(1 for w in words if w == kw_parts[0])
        return hits / len(words)
    kw = keyword.lower()
    return text.lower().count(kw) / max(len(words), 1)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _safe_read(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning("Dosya okunamadı %s: %s", path, e)
        return ""


def _safe_read_json(path: Path, default: Any) -> Any:
    raw = _safe_read(path)
    if not raw.strip():
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _validate_project_path(slug: str) -> Path:
    safe = _safe_slug(slug)
    base = GENERATED_DIR.resolve()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    target = (GENERATED_DIR / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal engellendi")
    return target


def _is_blocked_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        return host in _BLOCKED_HOSTS or host.endswith(".localhost")
    except Exception:
        return True


def _collect_pages_from_data(
    pages_data: dict[str, Any],
    faqs_data: list[Any],
    blog_data: list[Any],
) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    home = pages_data.get("home") or {}
    if home:
        pages.append({
            "slug": "",
            "type": "home",
            "title": home.get("title", ""),
            "description": home.get("description", ""),
            "content_html": home.get("content_html", ""),
            "schema": home.get("schema"),
            "keyword": pages_data.get("seed_keyword", ""),
        })
    for item in pages_data.get("geo") or []:
        if isinstance(item, dict):
            pages.append({
                "slug": item.get("slug", ""),
                "type": "geo",
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "content_html": item.get("content_html", ""),
                "schema": item.get("schema"),
                "keyword": item.get("keyword", ""),
            })
    for item in faqs_data or []:
        if isinstance(item, dict):
            pages.append({
                "slug": item.get("slug", ""),
                "type": "faq",
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "content_html": item.get("content_html", ""),
                "schema": item.get("schema"),
                "keyword": item.get("keyword", ""),
            })
    for item in blog_data or []:
        if isinstance(item, dict):
            pages.append({
                "slug": item.get("slug", ""),
                "type": "blog",
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "content_html": item.get("content_html", ""),
                "schema": item.get("schema"),
                "keyword": item.get("topic") or item.get("keyword", ""),
            })
    return pages


def _analyze_page_content(
    page: dict[str, Any],
    *,
    target_keyword: str,
    location: str,
    domain: str,
    strict_mode: bool,
    talon_brief: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    slug = page.get("slug") or "home"
    page_id = slug or "home"
    title = (page.get("title") or "").strip()
    description = (page.get("description") or "").strip()
    html = page.get("content_html") or ""
    page_type = page.get("type", "page")
    plain = _strip_html(html)
    soup = _parse_html(html)
    words = _word_count(plain)

    if not title:
        issues.append(_issue("MISSING_TITLE", "Sayfa başlığı (title) eksik", "critical", page=page_id, category="meta"))
    elif len(title) > TITLE_MAX:
        issues.append(_issue(
            "TITLE_TOO_LONG", f"Title {len(title)} karakter (önerilen ≤{TITLE_MAX})", "warning",
            page=page_id, category="meta",
        ))
    elif len(title) < 10:
        issues.append(_issue("TITLE_TOO_SHORT", f"Title çok kısa ({len(title)} karakter)", "info", page=page_id, category="meta"))

    if not description:
        issues.append(_issue("MISSING_META_DESCRIPTION", "Meta description eksik", "warning", page=page_id, category="meta"))
    elif len(description) > META_DESC_MAX:
        issues.append(_issue(
            "META_DESCRIPTION_TOO_LONG",
            f"Meta description {len(description)} karakter (önerilen ≤{META_DESC_MAX})",
            "warning", page=page_id, category="meta",
        ))

    h1s = soup.find_all("h1")
    if not h1s:
        issues.append(_issue("MISSING_H1", "H1 etiketi yok", "critical", page=page_id, category="headings"))
    elif len(h1s) > 1:
        issues.append(_issue("MULTIPLE_H1", f"Birden fazla H1 ({len(h1s)})", "warning", page=page_id, category="headings"))

    h2s = soup.find_all("h2")
    if not h2s and words > 80:
        issues.append(_issue("MISSING_H2", "H2 yapısı yok", "info", page=page_id, category="headings"))

    min_words = 50 if strict_mode else MIN_WORDS
    if words < min_words:
        sev = "critical" if strict_mode and words < 30 else "warning"
        issues.append(_issue(
            "THIN_CONTENT", f"İçerik çok ince ({words} kelime, min {min_words})", sev,
            page=page_id, category="content",
        ))

    if target_keyword:
        kw_low = target_keyword.lower()
        if kw_low not in plain.lower() and kw_low not in title.lower():
            issues.append(_issue(
                "KEYWORD_NOT_FOUND", f"Hedef keyword içerikte yok: {target_keyword}",
                "warning" if not strict_mode else "critical", page=page_id, category="content",
            ))
        density = _keyword_density(plain, target_keyword)
        if density > KEYWORD_STUFFING_RATIO:
            issues.append(_issue(
                "KEYWORD_STUFFING",
                f"Keyword yoğunluğu yüksek ({density:.1%})",
                "warning", page=page_id, category="content",
            ))

    internal = [a.get("href", "") for a in soup.find_all("a", href=True) if not a["href"].startswith("http")]
    external = [a.get("href", "") for a in soup.find_all("a", href=True) if a["href"].startswith("http")]
    if not internal and page_type != "home":
        issues.append(_issue("NO_INTERNAL_LINKS", "İç link yok", "info", page=page_id, category="links"))
    if not external and page_type in ("geo", "blog"):
        issues.append(_issue("NO_EXTERNAL_LINKS", "Dış kaynak linki yok", "info", page=page_id, category="links"))
    for href in internal:
        if href.startswith("#") or href in ("/", ""):
            continue
        if ".." in href or href.startswith("//"):
            issues.append(_issue(
                "BROKEN_RELATIVE_LINK", f"Şüpheli relative link: {href}",
                "warning", page=page_id, category="links",
            ))

    imgs = soup.find_all("img")
    for img in imgs:
        alt = (img.get("alt") or "").strip()
        if not alt:
            issues.append(_issue("MISSING_ALT", "Görsel alt text eksik", "warning", page=page_id, category="images"))
            break

    schema = page.get("schema")
    schema_str = json.dumps(schema, ensure_ascii=False).lower() if schema else ""
    if page_type == "faq" and "faqpage" not in schema_str and "faq" not in plain.lower():
        issues.append(_issue("MISSING_FAQ_SCHEMA", "FAQ schema veya SSS yapısı eksik", "warning", page=page_id, category="schema"))
    if page_type == "blog" and "article" not in schema_str:
        issues.append(_issue("MISSING_ARTICLE_SCHEMA", "Article schema eksik", "info", page=page_id, category="schema"))
    if page_type == "geo" and "localbusiness" not in schema_str:
        issues.append(_issue("MISSING_LOCAL_BUSINESS", "LocalBusiness schema eksik", "info", page=page_id, category="schema"))

    loc_low = (location or "").lower()
    plain_low = plain.lower()
    if loc_low and loc_low not in plain_low and loc_low not in title.lower():
        issues.append(_issue(
            "MISSING_DISTRICT", f"Lokasyon adı içerikte yok: {location}",
            "warning", page=page_id, category="geo",
        ))
    if "aydın" not in plain_low and "aydin" not in plain_low and page_type in ("geo", "home"):
        issues.append(_issue("MISSING_CITY", "Şehir adı (Aydın) içerikte geçmiyor", "info", page=page_id, category="geo"))

    if talon_brief:
        for h2 in (talon_brief.get("h2_outline") or [])[:2]:
            if h2 and h2.lower() not in plain_low:
                issues.append(_issue(
                    "MISSING_BRIEF_SECTION", f"Talon brief bölümü eksik: {h2}",
                    "info", page=page_id, category="content",
                ))
                break

    return issues


def _analyze_page_full(
    page: dict[str, Any],
    *,
    target_keyword: str,
    location: str,
    domain: str,
    main_site: str,
    strict_mode: bool,
    talon_brief: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    issues = _analyze_page_content(
        page,
        target_keyword=target_keyword,
        location=location,
        domain=domain,
        strict_mode=strict_mode,
        talon_brief=talon_brief,
    )
    html = page.get("content_html") or ""
    plain = _strip_html(html)
    soup = _parse_html(html)
    schema = page.get("schema")
    schema_str = json.dumps(schema, ensure_ascii=False).lower() if schema else ""

    issues.extend(_analyze_geo_extended(page, location, plain, soup, schema_str))
    issues.extend(_analyze_aeo(page, plain, soup))
    entities = _extract_entities(page, target_keyword or page.get("keyword", ""), location, plain, main_site)
    issues.extend(_analyze_entity_issues(entities, page.get("slug") or "home"))
    issues.extend(_analyze_trust_freshness(page, plain, soup, main_site))
    return issues, entities


def _analyze_dist_html(
    html_path: Path,
    domain: str,
    strict_mode: bool,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    page_id = html_path.name

    raw = _safe_read(html_path)
    if not raw:
        return issues

    soup = BeautifulSoup(raw, "html.parser")
    title_tag = soup.find("title")
    if not title_tag or not title_tag.get_text(strip=True):
        issues.append(_issue("DIST_MISSING_TITLE", f"dist HTML title eksik: {page_id}", "critical", page=page_id, category="technical"))

    canonical = soup.find("link", rel="canonical")
    if not canonical or not canonical.get("href"):
        issues.append(_issue("MISSING_CANONICAL", f"Canonical link eksik: {page_id}", "warning", page=page_id, category="meta"))
    elif domain:
        href = canonical.get("href", "")
        dom = domain.replace("https://", "").replace("http://", "").rstrip("/")
        if dom and dom not in href:
            sev = "critical" if strict_mode else "warning"
            issues.append(_issue(
                "CANONICAL_DOMAIN_MISMATCH",
                f"Canonical domain uyuşmuyor: {href}",
                sev, page=page_id, category="meta",
            ))

    robots = soup.find("meta", attrs={"name": re.compile(r"robots", re.I)})
    if robots and "noindex" in (robots.get("content") or "").lower():
        issues.append(_issue("NOINDEX_DETECTED", f"noindex bulundu: {page_id}", "critical", page=page_id, category="technical"))

    return issues


def _site_level_checks(
    project_path: Path,
    domain: str,
    pages: list[dict[str, Any]],
    strict_mode: bool,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    robots_path = project_path / "public" / "robots.txt"
    if not robots_path.is_file():
        issues.append(_issue("MISSING_ROBOTS_TXT", "public/robots.txt bulunamadı", "critical", category="technical"))
    else:
        robots = _safe_read(robots_path)
        if "sitemap" not in robots.lower():
            issues.append(_issue("ROBOTS_NO_SITEMAP", "robots.txt içinde Sitemap satırı yok", "info", category="technical"))

    sitemap_path = project_path / "public" / "sitemap.xml"
    if not sitemap_path.is_file():
        issues.append(_issue("MISSING_SITEMAP", "public/sitemap.xml bulunamadı", "warning", category="technical"))
    else:
        sitemap = _safe_read(sitemap_path)
        if domain:
            dom = domain.replace("https://", "").replace("http://", "").rstrip("/")
            if dom and dom not in sitemap and "example.com" in sitemap:
                issues.append(_issue(
                    "SITEMAP_DOMAIN_MISMATCH",
                    "sitemap.xml hâlâ example.com domain kullanıyor",
                    "warning", category="technical",
                ))

    intros: list[str] = []
    paragraphs: list[str] = []
    for page in pages:
        plain = _strip_html(page.get("content_html", ""))
        paras = [p.strip() for p in plain.split("\n") if len(p.strip()) > 40]
        if paras:
            intros.append(paras[0][:200])
            paragraphs.extend(paras)

    para_counts = Counter(paragraphs)
    for para, count in para_counts.items():
        if count > 1 and len(para) > 60:
            issues.append(_issue(
                "DUPLICATE_PARAGRAPH",
                f"Aynı paragraf {count} sayfada tekrarlanıyor",
                "warning", category="risk",
            ))
            break

    intro_groups = [i for i in intros if i]
    if len(intro_groups) >= 3:
        similar_pairs = 0
        for i in range(len(intro_groups)):
            for j in range(i + 1, len(intro_groups)):
                if _similarity(intro_groups[i], intro_groups[j]) > 0.85:
                    similar_pairs += 1
        if similar_pairs >= 2:
            issues.append(_issue(
                "SAME_INTRO_PARAGRAPH",
                "Birden fazla sayfada benzer giriş paragrafı (doorway riski)",
                "warning", category="risk",
            ))

    geo_pages = [p for p in pages if p.get("type") == "geo"]
    if len(geo_pages) >= 5:
        titles = [p.get("title", "") for p in geo_pages]
        if len(set(titles)) < len(titles) * 0.6:
            issues.append(_issue("DOORWAY_RISK", "Çok sayıda benzer GEO sayfası — doorway riski", "critical", category="risk"))

    anchors: list[str] = []
    for page in pages:
        soup = _parse_html(page.get("content_html", ""))
        anchors.extend(a.get_text(strip=True).lower() for a in soup.find_all("a") if a.get_text(strip=True))
    anchor_counts = Counter(anchors)
    for anchor, count in anchor_counts.items():
        if count >= 8 and len(anchor) > 3:
            issues.append(_issue(
                "ANCHOR_SPAM",
                f"Aynı anchor çok tekrarlanıyor: '{anchor}' ({count}x)",
                "warning", category="risk",
            ))
            break

    titles = [p.get("title", "").strip().lower() for p in pages if p.get("title")]
    title_counts = Counter(titles)
    for t, count in title_counts.items():
        if count > 1:
            issues.append(_issue("DUPLICATE_PAGE", f"Aynı title {count} sayfada: {t}", "critical", category="content"))
            break

    dist = project_path / "dist"
    if dist.is_dir():
        for html_file in dist.rglob("*.html"):
            if html_file.is_file():
                issues.extend(_analyze_dist_html(html_file, domain, strict_mode))

    issues.extend(_extended_risk_checks(pages))
    return issues


def _calculate_score(all_issues: list[dict[str, Any]]) -> int:
    score = 100
    for iss in all_issues:
        score -= iss.get("penalty", SEVERITY_PENALTY.get(iss.get("severity", "info"), 0))
    return max(0, min(100, score))


def _page_score(issues: list[dict[str, Any]]) -> int:
    return _calculate_score(issues)


def _get_talon_brief(keyword: str, location: str) -> dict[str, Any] | None:
    if not keyword:
        return None
    try:
        from app.moduller.talon_orchestrator import content_brief_generator, intent_classifier
        intent = intent_classifier(keyword)
        res = content_brief_generator(keyword, location, intent)
        return res.get("content_brief")
    except Exception as e:
        logger.debug("Talon brief alınamadı: %s", e)
        return None


def analyze_project(
    project_id: str,
    target_keyword: str = "",
    main_site_url: str = "",
    strict_mode: bool = True,
) -> dict[str, Any]:
    project = _get_project(project_id)
    slug = project.get("slug", "")
    project_path = _validate_project_path(slug)

    if not project_path.is_dir():
        return {"success": False, "error": f"Proje dizini yok: generated-sites/{slug}"}

    pages_data = _safe_read_json(project_path / "src" / "data" / "pages.json", {})
    faqs_data = _safe_read_json(project_path / "src" / "data" / "faqs.json", [])
    blog_data = _safe_read_json(project_path / "src" / "data" / "blog.json", [])

    domain = (pages_data.get("domain") or project.get("domain") or "").strip()
    location = project.get("location", "Kuşadası")
    keyword = (target_keyword or project.get("seed_keyword") or "").strip()
    main_site = (main_site_url or pages_data.get("main_site_url") or project.get("main_site_url") or "").strip()

    talon_brief = _get_talon_brief(keyword, location) if keyword else None
    plan = project.get("plan") or {}

    pages = _collect_pages_from_data(pages_data, faqs_data, blog_data)
    if not pages:
        return {"success": False, "error": "Analiz edilecek sayfa verisi yok (pages.json boş)"}

    all_issues: list[dict[str, Any]] = []
    page_reports: list[dict[str, Any]] = []
    all_entities: list[dict[str, Any]] = []

    for page in pages:
        brief = talon_brief if page.get("keyword") == keyword or not page.get("keyword") else None
        page_issues, entities = _analyze_page_full(
            page,
            target_keyword=keyword,
            location=location,
            domain=domain,
            main_site=main_site,
            strict_mode=strict_mode,
            talon_brief=brief,
        )
        all_issues.extend(page_issues)
        all_entities.append(entities)
        plain = _strip_html(page.get("content_html", ""))
        html = page.get("content_html", "")
        entity_cov = _entity_coverage_score(entities)
        page_reports.append({
            "slug": page.get("slug") or "home",
            "type": page.get("type"),
            "title": page.get("title", ""),
            "score": _page_score(page_issues),
            "seo_score": _dimension_score(page_issues, SEO_CATEGORIES),
            "geo_score": _dimension_score(page_issues, GEO_CATEGORIES),
            "aeo_score": _dimension_score(page_issues, AEO_CATEGORIES),
            "entity_coverage_score": entity_cov,
            "authority_score": _dimension_score(page_issues, AUTHORITY_CATEGORIES),
            "citation_score": _research_citation_score(plain, html),
            "answerability_score": _research_answerability_score(plain, html),
            "overview_probability_score": _research_overview_probability(plain, html),
            "overview_score": _overview_score(plain, html),
            "faq_coverage_score": _faq_coverage_score(html),
            "question_coverage_score": _question_coverage_score(html, plain),
            "intent_coverage_score": _intent_coverage_score(page.get("keyword", keyword), plain),
            "entity_question_score": _entity_question_score(plain, _entity_names_from_payload(entities)),
            "paa_score": _paa_score([]),
            "autocomplete_score": _autocomplete_score(page.get("keyword", keyword), []),
            "llm_visibility_score": _research_llm_visibility(html, plain),
            "entities": entities,
            "word_count": _word_count(plain),
            "issues": page_issues,
        })

    site_issues = _site_level_checks(project_path, domain, pages, strict_mode)
    site_issues.extend(_analyze_topical_authority(pages, plan))
    all_issues.extend(site_issues)

    seo_score = _dimension_score(all_issues, SEO_CATEGORIES)
    geo_score = _dimension_score(all_issues, GEO_CATEGORIES)
    aeo_score = _dimension_score(all_issues, AEO_CATEGORIES)
    entity_score = int(round(sum(_entity_coverage_score(e) for e in all_entities) / max(len(all_entities), 1)))
    authority_score = _dimension_score(all_issues, AUTHORITY_CATEGORIES)
    graph_scores: dict[str, Any] = {}
    try:
        from app.moduller.entity_geo_graph import get_project_scores
        gs = get_project_scores(project_id)
        if gs.get("success"):
            graph_scores = gs
            entity_score = int((entity_score + gs.get("entity_strength_score", entity_score)) / 2)
            geo_score = int((geo_score + gs.get("geo_coverage_score", geo_score)) / 2)
            authority_score = int((authority_score + gs.get("topic_authority_score", authority_score)) / 2)
    except Exception as exc:
        logger.debug("Entity GEO Graph skor blend atlandı: %s", exc)
    risk_score = _calculate_risk_score(all_issues)
    competitive_strength = _research_competitive_gap_score(pages, keyword)
    authority_score = int((authority_score + competitive_strength) / 2)

    def _avg_page_field(field: str) -> int:
        vals = [p.get(field, 0) for p in page_reports if p.get(field) is not None]
        return int(sum(vals) / max(len(vals), 1)) if vals else 0

    citation_score = _avg_page_field("citation_score")
    answerability_score = _avg_page_field("answerability_score")
    overview_probability_score = _avg_page_field("overview_probability_score")
    overview_score = _avg_page_field("overview_score") or overview_probability_score
    faq_coverage_score = _avg_page_field("faq_coverage_score")
    question_coverage_score = _avg_page_field("question_coverage_score")
    intent_coverage_score = _avg_page_field("intent_coverage_score")
    entity_question_score = _avg_page_field("entity_question_score")
    paa_score = _avg_page_field("paa_score")
    autocomplete_score = _avg_page_field("autocomplete_score")
    llm_visibility_score = _avg_page_field("llm_visibility_score")
    aeo_score = int((aeo_score + answerability_score + overview_score) / 3)

    overall = _compute_overall_score(
        seo_score, geo_score, aeo_score, entity_score, authority_score, risk_score,
        citation_score=citation_score, llm_visibility_score=llm_visibility_score,
    )

    scores = {
        "seo_score": seo_score,
        "geo_score": geo_score,
        "aeo_score": aeo_score,
        "entity_score": entity_score,
        "authority_score": authority_score,
        "citation_score": citation_score,
        "answerability_score": answerability_score,
        "overview_probability_score": overview_probability_score,
        "overview_score": overview_score,
        "faq_coverage_score": faq_coverage_score,
        "question_coverage_score": question_coverage_score,
        "intent_coverage_score": intent_coverage_score,
        "entity_question_score": entity_question_score,
        "paa_score": paa_score,
        "autocomplete_score": autocomplete_score,
        "llm_visibility_score": llm_visibility_score,
        "competitive_strength": competitive_strength,
        "risk_score": risk_score,
        "overall_score": overall,
        "research_pack": "v2",
    }
    deploy_gate = _compute_deploy_gate(scores)
    readiness = _compute_readiness(scores)
    status = deploy_gate["status"]
    critical = [i for i in all_issues if i["severity"] == "critical"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]

    report_id = str(uuid.uuid4())[:12]
    report = {
        "report_id": report_id,
        "module": MODULE_NAME,
        "project_id": project_id,
        "project_slug": slug,
        "target_keyword": keyword,
        "main_site_url": main_site,
        "strict_mode": strict_mode,
        **scores,
        "status": status,
        "deploy_status": status,
        **deploy_gate,
        "readiness": readiness,
        "critical_issues": critical,
        "warnings": warnings,
        "info_issues": [i for i in all_issues if i["severity"] == "info"],
        "pages": page_reports,
        "entity_map": all_entities,
        "files_analyzed": {
            "pages_json": (project_path / "src" / "data" / "pages.json").is_file(),
            "faqs_json": (project_path / "src" / "data" / "faqs.json").is_file(),
            "blog_json": (project_path / "src" / "data" / "blog.json").is_file(),
            "robots_txt": (project_path / "public" / "robots.txt").is_file(),
            "sitemap_xml": (project_path / "public" / "sitemap.xml").is_file(),
            "dist_html_count": len(list((project_path / "dist").rglob("*.html"))) if (project_path / "dist").is_dir() else 0,
        },
        "talon_brief": talon_brief,
        "entity_geo_graph": graph_scores,
        "created_at": _now(),
    }

    state = _load_state()
    state.setdefault("reports", {})[report_id] = report
    _save_state(state)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"{report_id}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    return {"success": True, **report}


def analyze_url(url: str, target_keyword: str = "", strict_mode: bool = True) -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        return {"success": False, "error": "url gerekli"}
    if _is_blocked_url(url):
        return {"success": False, "error": "localhost / yerel URL analizi engellendi"}
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"

    try:
        resp = requests.get(url, timeout=URL_TIMEOUT, headers={"User-Agent": "HIVE-SEO-Quality-Gate/1.0"})
        resp.raise_for_status()
    except requests.RequestException as e:
        return {"success": False, "error": f"URL getirilemedi: {e}"}

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    title_text = title.get_text(strip=True) if title else ""
    body = soup.get_text(separator=" ", strip=True)

    page = {
        "slug": urlparse(url).path or "/",
        "type": "url",
        "title": title_text,
        "description": "",
        "content_html": str(soup.find("body") or html),
        "schema": None,
        "keyword": target_keyword,
    }
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag:
        page["description"] = desc_tag.get("content", "")

    issues = _analyze_page_content(
        page, target_keyword=target_keyword, location="", domain=urlparse(url).netloc,
        strict_mode=strict_mode,
    )
    canonical = soup.find("link", rel="canonical")
    if not canonical:
        issues.append(_issue("MISSING_CANONICAL", "Canonical link eksik", "warning", category="meta"))

    score = _calculate_score(issues)
    report_id = str(uuid.uuid4())[:12]
    report = {
        "report_id": report_id,
        "url": url,
        "target_keyword": target_keyword,
        "overall_score": score,
        "status": _status_from_score(score),
        "critical_issues": [i for i in issues if i["severity"] == "critical"],
        "warnings": [i for i in issues if i["severity"] == "warning"],
        "pages": [{
            "slug": page["slug"],
            "type": "url",
            "title": title_text,
            "score": score,
            "word_count": _word_count(body),
            "issues": issues,
        }],
        "created_at": _now(),
    }

    state = _load_state()
    state.setdefault("reports", {})[report_id] = report
    _save_state(state)

    return {"success": True, **report}


def list_reports(limit: int = 50) -> dict[str, Any]:
    state = _load_state()
    reports = list(state.get("reports", {}).values())
    reports.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    summary = [
        {
            "report_id": r.get("report_id"),
            "project_id": r.get("project_id"),
            "project_slug": r.get("project_slug"),
            "url": r.get("url"),
            "overall_score": r.get("overall_score"),
            "status": r.get("status"),
            "created_at": r.get("created_at"),
        }
        for r in reports[:limit]
    ]
    return {"success": True, "reports": summary, "count": len(summary)}


def get_report(report_id: str) -> dict[str, Any]:
    state = _load_state()
    report = state.get("reports", {}).get(report_id)
    if not report:
        json_path = REPORTS_DIR / f"{report_id}.json"
        if json_path.is_file():
            report = json.loads(json_path.read_text(encoding="utf-8"))
        else:
            return {"success": False, "error": f"Rapor bulunamadı: {report_id}"}
    return {"success": True, "report": report}


def fix_suggestions(report_id: str, use_llm: bool = True) -> dict[str, Any]:
    rep = get_report(report_id)
    if not rep.get("success"):
        return rep
    report = rep["report"]
    issues = (
        report.get("critical_issues", [])
        + report.get("warnings", [])
        + report.get("info_issues", [])
    )
    if not issues:
        flat_issues = []
        for p in report.get("pages", []):
            flat_issues.extend(p.get("issues", []))
        issues = flat_issues

    suggestions: list[dict[str, Any]] = []
    for iss in issues[:30]:
        code = iss.get("code", "")
        rule_map = {
            "MISSING_TITLE": "Her sayfaya benzersiz, 50-60 karakterlik title ekleyin.",
            "MISSING_META_DESCRIPTION": "155 karaktere kadar özgün meta description yazın.",
            "MISSING_H1": "Sayfada tek bir H1 kullanın; keyword içersin.",
            "THIN_CONTENT": "En az 150-300 kelime özgün içerik ekleyin.",
            "MISSING_ROBOTS_TXT": "public/robots.txt oluşturun ve Sitemap satırı ekleyin.",
            "MISSING_SITEMAP": "public/sitemap.xml güncelleyin; tüm sayfaları listeleyin.",
            "MISSING_CANONICAL": "BaseLayout canonical URL'yi proje domainine göre ayarlayın.",
            "SITEMAP_DOMAIN_MISMATCH": "sitemap.xml içindeki example.com'u gerçek domain ile değiştirin.",
            "DUPLICATE_PARAGRAPH": "Tekrarlayan paragrafları sayfaya özel içerikle değiştirin.",
            "DOORWAY_RISK": "GEO sayfalarını birleştirin veya içerikleri özgünleştirin.",
            "KEYWORD_STUFFING": "Keyword yoğunluğunu doğal seviyeye indirin.",
            "MISSING_ALT": "Tüm img etiketlerine açıklayıcı alt text ekleyin.",
            "AEO_NO_ANSWER_BOX": "Her H2 altına 40-60 kelimelik net, alıntılanabilir cevap paragrafı ekleyin.",
            "GEO_NO_CONTEXT": "Lokasyonu doğal cümleler içinde bağlamla anlatın; sadece keyword olarak geçirmeyin.",
            "GEO_MISSING_PLACE_SCHEMA": "Place veya LocalBusiness JSON-LD schema ekleyin.",
            "ENTITY_LOW_COVERAGE": "Ana, lokasyon, kategori ve hizmet entity'lerini içerikte açıkça geçirin.",
            "TOPICAL_WEAK_CLUSTER": "Aynı konu için blog, SSS veya cluster destek sayfaları ekleyin.",
            "GEO_COPY_VARIANT": "GEO sayfalarını özgünleştirin; sadece şehir adını değiştirmeyin.",
        }
        suggestions.append({
            "issue_code": code,
            "message": iss.get("message"),
            "page": iss.get("page", ""),
            "suggestion": rule_map.get(code, f"'{code}' için manuel düzeltme gerekli."),
            "source": "rule",
        })

    if use_llm and issues:
        try:
            from app.moduller import llm_router
            issue_text = "\n".join(f"- [{i['severity']}] {i['code']}: {i['message']}" for i in issues[:15])
            prompt = f"""SEO Quality Gate raporu için düzeltme önerileri ver.
Dosyaları değiştirme — sadece öneri listesi döndür.

Proje: {report.get('project_slug', report.get('url', ''))}
Skor: {report.get('overall_score')}
Sorunlar:
{issue_text}

Her sorun için 1-2 cümlelik uygulanabilir öneri yaz. Türkçe."""
            raw, engine = llm_router.generate(prompt, max_tokens=1500, min_length=50)
            if raw and len(raw.strip()) > 40:
                suggestions.append({
                    "issue_code": "LLM_SUMMARY",
                    "message": "LLM özet önerileri",
                    "suggestion": raw.strip(),
                    "source": engine or "llm",
                })
        except Exception as e:
            logger.warning("LLM öneri üretilemedi: %s", e)

    return {
        "success": True,
        "report_id": report_id,
        "suggestions": suggestions,
        "count": len(suggestions),
    }


def export_report(report_id: str, fmt: str = "json") -> dict[str, Any]:
    rep = get_report(report_id)
    if not rep.get("success"):
        return rep
    report = rep["report"]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if fmt == "md":
        lines = [
            f"# {MODULE_NAME} Raporu",
            "",
            f"- **Rapor ID:** {report_id}",
            f"- **Overall:** {report.get('overall_score')}/100",
            f"- **SEO:** {report.get('seo_score')} · **GEO:** {report.get('geo_score')} · **AEO:** {report.get('aeo_score')}",
            f"- **Entity:** {report.get('entity_score')} · **Authority:** {report.get('authority_score')} · **Risk:** {report.get('risk_score')}",
            f"- **Durum:** {report.get('status')}",
            f"- **Tarih:** {report.get('created_at')}",
            "",
        ]
        readiness = report.get("readiness") or {}
        lines.append("## Hazırlık")
        lines.append(f"- Google arama: {'✓' if readiness.get('google_search_ready') else '✗'}")
        lines.append(f"- GEO/local: {'✓' if readiness.get('geo_local_ready') else '✗'}")
        lines.append(f"- AI Overview: {'✓' if readiness.get('ai_overview_ready') else '✗'}")
        lines.append(f"- Destek ağı: {'✓' if readiness.get('support_network_ready') else '✗'}")
        lines.append("")
        if report.get("project_slug"):
            lines.append(f"- **Proje:** {report.get('project_slug')}")
        if report.get("url"):
            lines.append(f"- **URL:** {report.get('url')}")
        lines.append("")
        lines.append("## Kritik Sorunlar")
        for i in report.get("critical_issues", []):
            lines.append(f"- **[{i.get('code')}]** {i.get('message')}")
        lines.append("")
        lines.append("## Uyarılar")
        for i in report.get("warnings", []):
            lines.append(f"- [{i.get('code')}] {i.get('message')}")
        lines.append("")
        lines.append("## Sayfalar")
        lines.append("| Sayfa | Tip | Skor | Kelime |")
        lines.append("|-------|-----|------|--------|")
        for p in report.get("pages", []):
            lines.append(f"| {p.get('slug') or 'home'} | {p.get('type')} | {p.get('score')} | {p.get('word_count')} |")
        content = "\n".join(lines)
        out_path = REPORTS_DIR / f"{report_id}.md"
        out_path.write_text(content, encoding="utf-8")
        return {"success": True, "format": "md", "path": str(out_path.resolve()), "content": content}

    out_path = REPORTS_DIR / f"{report_id}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "format": "json", "path": str(out_path.resolve())}


def health() -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    state = _load_state()
    try:
        from app.moduller.astro_factory import list_projects
        projects = list_projects().get("projects", [])
    except Exception:
        projects = []
    return {
        "success": True,
        "status": "ok",
        "module": MODULE_NAME,
        "reports_dir": str(REPORTS_DIR.resolve()),
        "reports_dir_writable": os_access_writable(REPORTS_DIR),
        "report_count": len(state.get("reports", {})),
        "astro_projects": len(projects),
        "thresholds": {
            "pass": PASS_THRESHOLD,
            "warning": WARNING_THRESHOLD,
            "fail": FAIL_THRESHOLD,
            "geo_deploy_min": GEO_DEPLOY_MIN,
            "aeo_publisher_min": AEO_PUBLISHER_MIN,
            "risk_fail": RISK_FAIL_THRESHOLD,
            "penalties": SEVERITY_PENALTY,
        },
    }


def os_access_writable(path: Path) -> bool:
    import os
    return os.access(path, os.W_OK) if path.exists() else True


def analyze_page(
    content: str,
    keyword: str,
    location: str = "",
    title: str = "",
) -> dict[str, Any]:
    """Tek sayfa analizi (Talon entegrasyonu)."""
    page = {
        "slug": "inline",
        "type": "page",
        "title": title,
        "description": "",
        "content_html": content,
        "keyword": keyword,
    }
    talon_brief = _get_talon_brief(keyword, location) if keyword else None
    issues, entities = _analyze_page_full(
        page, target_keyword=keyword, location=location, domain="",
        main_site="", strict_mode=False, talon_brief=talon_brief,
    )
    risk_score = _calculate_risk_score(issues)
    plain = _strip_html(content)
    citation_score = _research_citation_score(plain, content)
    answerability_score = _research_answerability_score(plain, content)
    overview_probability_score = _research_overview_probability(plain, content)
    overview_score = _overview_score(plain, content)
    faq_coverage_score = _faq_coverage_score(content)
    question_coverage_score = _question_coverage_score(content, plain)
    intent_coverage_score = _intent_coverage_score(keyword, plain)
    entity_question_score = _entity_question_score(plain, _entity_names_from_payload(entities))
    llm_visibility_score = _research_llm_visibility(content, plain)
    scores = {
        "seo_score": _dimension_score(issues, SEO_CATEGORIES),
        "geo_score": _dimension_score(issues, GEO_CATEGORIES),
        "aeo_score": int((_dimension_score(issues, AEO_CATEGORIES) + answerability_score + overview_score) / 3),
        "entity_score": _entity_coverage_score(entities),
        "authority_score": _dimension_score(issues, AUTHORITY_CATEGORIES),
        "citation_score": citation_score,
        "answerability_score": answerability_score,
        "overview_probability_score": overview_probability_score,
        "overview_score": overview_score,
        "faq_coverage_score": faq_coverage_score,
        "question_coverage_score": question_coverage_score,
        "intent_coverage_score": intent_coverage_score,
        "entity_question_score": entity_question_score,
        "paa_score": _paa_score([]),
        "autocomplete_score": _autocomplete_score(keyword, []),
        "llm_visibility_score": llm_visibility_score,
        "risk_score": risk_score,
    }
    overall = _compute_overall_score(
        scores["seo_score"], scores["geo_score"], scores["aeo_score"],
        scores["entity_score"], scores["authority_score"], risk_score,
        citation_score=citation_score, llm_visibility_score=llm_visibility_score,
    )
    scores["overall_score"] = overall
    return {
        "success": True,
        "keyword": keyword,
        "intent": None,
        "content_brief": talon_brief,
        "entities": entities,
        "issues": issues,
        "word_count": _word_count(_strip_html(content)),
        **scores,
        "status": _status_from_score(overall, risk_score),
        "readiness": _compute_readiness({**scores, "overall_score": overall}),
        "pass": overall >= PASS_THRESHOLD and risk_score <= RISK_FAIL_THRESHOLD,
        "risk_level": "low" if risk_score <= 30 else "medium" if risk_score <= 60 else "high",
    }


seo_quality_gate = type("SEOQualityGate", (), {
    "health": staticmethod(health),
    "analyze_project": staticmethod(analyze_project),
    "analyze_url": staticmethod(analyze_url),
    "list_reports": staticmethod(list_reports),
    "get_report": staticmethod(get_report),
    "fix_suggestions": staticmethod(fix_suggestions),
    "export_report": staticmethod(export_report),
    "analyze_page": staticmethod(analyze_page),
    "_validate_project_path": staticmethod(_validate_project_path),
    "_calculate_score": staticmethod(_calculate_score),
    "_word_count": staticmethod(_word_count),
    "_is_blocked_url": staticmethod(_is_blocked_url),
})()
