"""
Citation Engine V1 — AI citation görünürlük ve uygunluk analiz katmanı.

İçerik üretmez; citation uygunluğu, risk, entity güveni ve AI görünürlüğünü ölçer.
Opportunity, SERP Defense, Revenue ve Mission Control katmanlarına veri sağlar.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger("hive.citation_engine")

STATE_FILE = Path(__file__).resolve().parent.parent / "citation_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 500
PAGE_LIMIT = 500
ENTITY_LIMIT = 300

AI_TARGETS = (
    "Google AI Overview",
    "ChatGPT",
    "Gemini",
    "Claude",
    "Perplexity",
    "Copilot",
)

CITATION_OPPORTUNITY_TYPES = (
    "add_faq",
    "add_entity",
    "add_author",
    "add_source_list",
    "add_schema",
    "add_answer_block",
    "add_support_page",
    "add_citation_page",
    "expand_entity_graph",
)

SCORE_WEIGHTS: dict[str, float] = {
    "authority_score": 0.15,
    "entity_score": 0.12,
    "citation_structure_score": 0.12,
    "answer_quality_score": 0.15,
    "source_trust_score": 0.10,
    "freshness_score": 0.08,
    "ai_readability_score": 0.10,
    "overview_score": 0.08,
    "schema_score": 0.10,
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "citation_threshold": 75,
    "visibility_threshold": 70,
    "trust_threshold": 70,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("pages", [])
                data.setdefault("entities", [])
                data.setdefault("competitors", [])
                data.setdefault("opportunities", [])
                data.setdefault("visibility", [])
                data.setdefault("projects", {})
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "pages": [],
        "entities": [],
        "competitors": [],
        "opportunities": [],
        "visibility": [],
        "projects": {},
        "history": [],
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    for k, v in (patch or {}).items():
        if k in DEFAULT_SETTINGS:
            cur[k] = v
    _save_state(st)
    return dict(cur)


def _append_history(state: dict[str, Any], entry: dict[str, Any]) -> None:
    lst = state.setdefault("history", [])
    lst.insert(0, entry)
    state["history"] = lst[:HISTORY_LIMIT]


def _record_brain(
    event_type: str,
    *,
    domain: str = "",
    keyword: str = "",
    result: dict | None = None,
    reason: str = "",
) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "citation_engine",
            domain=domain,
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "citation_engine", "citation_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if u and "://" not in u:
        u = f"https://{u}"
    return u


def _domain_from_url(url: str) -> str:
    try:
        return (urlparse(_normalize_url(url)).netloc or "").lower()
    except Exception:
        return ""


def _page_id(url: str) -> str:
    return hashlib.sha256(_normalize_url(url).lower().encode()).hexdigest()[:16]


def _fetch_page(url: str, timeout: int = 12) -> dict[str, Any]:
    """Sayfa içeriği çek — başarısızsa boş döner (sahte veri yok)."""
    try:
        resp = requests.get(
            _normalize_url(url),
            timeout=timeout,
            headers={"User-Agent": "HIVE-CitationEngine/1.0"},
        )
        if resp.status_code >= 400:
            return {"success": False, "error": f"http_{resp.status_code}", "html": "", "status": resp.status_code}
        return {"success": True, "html": resp.text or "", "status": resp.status_code}
    except Exception as exc:
        return {"success": False, "error": str(exc), "html": ""}


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    return (m.group(1).strip() if m else "")[:200]


def _count_faq(html: str) -> int:
    faq_schema = len(re.findall(r'"@type"\s*:\s*"FAQPage"', html, re.I))
    h_faq = len(re.findall(r"<h[23][^>]*>[^<]*\?", html, re.I))
    return faq_schema + h_faq


def _schema_types(html: str) -> list[str]:
    types: list[str] = []
    for m in re.finditer(r'"@type"\s*:\s*"([^"]+)"', html):
        t = m.group(1)
        if t not in types:
            types.append(t)
    return types[:20]


def _has_author(html: str) -> bool:
    markers = (
        r'rel=["\']author["\']',
        r'itemprop=["\']author["\']',
        r'class=["\'][^"\']*author[^"\']*["\']',
        r'"author"\s*:',
        r"<meta[^>]+name=[\"']author[\"']",
    )
    return any(re.search(p, html, re.I) for p in markers)


def _has_citation_block(html: str) -> bool:
    markers = (
        r'class=["\'][^"\']*citation[^"\']*["\']',
        r"<blockquote",
        r"<cite",
        r'rel=["\']cite["\']',
        r'"citation"',
    )
    return any(re.search(p, html, re.I) for p in markers)


def _has_source_list(html: str) -> bool:
    markers = (
        r'class=["\'][^"\']*source[s]?[^"\']*["\']',
        r'class=["\'][^"\']*reference[s]?[^"\']*["\']',
        r"<ol[^>]*>[\s\S]{0,500}(kaynak|source|referans)",
        r'href=["\']https?://[^"\']+["\'][^>]*>[^<]*(kaynak|source)',
    )
    return any(re.search(p, html, re.I) for p in markers)


def _trust_indicators(html: str, plain: str) -> int:
    score = 0
    if re.search(r"(sertifika|lisans|güven|trust|verified|iso\s*\d+)", plain, re.I):
        score += 25
    if re.search(r"(iletişim|contact|hakkımızda|about)", plain, re.I):
        score += 20
    if re.search(r"(gizlilik|privacy|kvkk|gdpr)", plain, re.I):
        score += 15
    if re.search(r'itemtype=["\']https?://schema.org/Organization', html, re.I):
        score += 25
    return min(100, score)


def _answer_blocks_score(html: str, plain: str) -> int:
    if not plain.strip():
        return 10
    score = 35
    paras = re.split(r"\n\n+|<p[^>]*>", html or plain)
    short = sum(1 for p in paras if 20 <= len(_strip_html(p).split()) <= 80)
    score += min(35, short * 8)
    if re.search(r"\b(nasıl|nedir|cevap|sonuç|özet)\b", plain, re.I):
        score += 15
    if re.search(r"<h[23][^>]*>[^<]*\?", html or "", re.I):
        score += 15
    return max(0, min(100, score))


def _ai_readability_score(plain: str, html: str) -> int:
    if not plain.strip():
        return 10
    score = 40
    words = plain.split()
    if words:
        avg_len = sum(len(w) for w in words) / len(words)
        if avg_len <= 6:
            score += 20
        elif avg_len <= 8:
            score += 10
    sents = re.split(r"[.!?]+", plain)
    if sents and len(sents[0].split()) <= 25:
        score += 15
    bullets = len(re.findall(r"<li[^>]*>", html or "", re.I))
    score += min(25, bullets * 4)
    return max(0, min(100, score))


def _freshness_score(html: str, plain: str) -> int:
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", plain)]
    current = datetime.now(timezone.utc).year
    if not years:
        if re.search(r"(güncel|updated|son güncelleme)", plain, re.I):
            return 70
        return 45
    latest = max(years)
    age = current - latest
    if age <= 0:
        return 95
    if age == 1:
        return 80
    if age <= 3:
        return 60
    return max(15, 50 - age * 5)


def _schema_score(html: str) -> int:
    types = _schema_types(html)
    if not types:
        return 15
    score = 30 + len(types) * 12
    priority = {"Article", "FAQPage", "Organization", "Person", "WebPage", "BreadcrumbList"}
    score += sum(8 for t in types if t in priority)
    return max(0, min(100, score))


def _citation_structure_score(html: str) -> int:
    score = 20
    if _has_citation_block(html):
        score += 30
    if _has_source_list(html):
        score += 25
    if re.search(r"<blockquote", html, re.I):
        score += 15
    if re.search(r'itemprop=["\']citation["\']', html, re.I):
        score += 10
    return max(0, min(100, score))


def _entity_count(html: str, plain: str, project_id: str = "") -> int:
    count = len(re.findall(r'itemprop=["\']name["\']', html, re.I))
    count += len(re.findall(r'"@type"\s*:\s*"(?:Organization|Person|Place|LocalBusiness)"', html, re.I))
    if project_id:
        try:
            from app.moduller.entity_geo_graph import get_project_scores
            gs = get_project_scores(project_id)
            if gs.get("success"):
                count += max(0, int(gs.get("entity_strength_score", 0) // 15))
        except Exception:
            pass
    nouns = len(re.findall(r"\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]{3,}\b", plain))
    return count + min(10, nouns // 5)


def _compute_subscores(
    html: str,
    plain: str,
    *,
    project_id: str = "",
    gate_scores: dict | None = None,
) -> dict[str, int]:
    gate = gate_scores or {}
    authority = int(gate.get("authority_score") or gate.get("overall_score") or 50)
    entity_raw = _entity_count(html, plain, project_id)
    entity = min(100, 25 + entity_raw * 8)
    if project_id:
        try:
            from app.moduller.entity_geo_graph import get_project_scores
            gs = get_project_scores(project_id)
            if gs.get("success"):
                entity = max(entity, int(gs.get("entity_strength_score") or entity))
        except Exception:
            pass

    cite_struct = _citation_structure_score(html)
    answer_q = _answer_blocks_score(html, plain)
    source_trust = _trust_indicators(html, plain)
    freshness = _freshness_score(html, plain)
    ai_read = _ai_readability_score(plain, html)
    schema = _schema_score(html)
    overview = int(gate.get("llm_visibility_score") or gate.get("aeo_score") or (answer_q + ai_read) // 2)

    try:
        from app.moduller.seo_quality_gate import _research_citation_score
        gate_cite = _research_citation_score(plain, html)
        cite_struct = max(cite_struct, gate_cite)
    except Exception:
        pass

    return {
        "authority_score": max(0, min(100, authority)),
        "entity_score": max(0, min(100, entity)),
        "citation_structure_score": max(0, min(100, cite_struct)),
        "answer_quality_score": max(0, min(100, answer_q)),
        "source_trust_score": max(0, min(100, source_trust)),
        "freshness_score": max(0, min(100, freshness)),
        "ai_readability_score": max(0, min(100, ai_read)),
        "overview_score": max(0, min(100, overview)),
        "schema_score": max(0, min(100, schema)),
    }


def _overall_citation_score(subscores: dict[str, int]) -> int:
    total = 0.0
    for key, weight in SCORE_WEIGHTS.items():
        total += (subscores.get(key) or 0) * weight
    return int(round(total))


def _detect_missing_signals(html: str, plain: str, subscores: dict[str, int], entity_count: int) -> list[str]:
    missing: list[str] = []
    if not _has_author(html):
        missing.append("author eksik")
    if not _has_citation_block(html):
        missing.append("citation block eksik")
    if not _has_source_list(html):
        missing.append("source list eksik")
    if _count_faq(html) < 1:
        missing.append("faq eksik")
    if not _schema_types(html):
        missing.append("schema eksik")
    if entity_count < 2 or subscores.get("entity_score", 0) < 40:
        missing.append("entity coverage düşük")
    if subscores.get("freshness_score", 0) < 50:
        missing.append("outdated content")
    if subscores.get("source_trust_score", 0) < 40:
        missing.append("no trust indicators")
    if subscores.get("authority_score", 0) < 45:
        missing.append("no supporting pages")
    if subscores.get("answer_quality_score", 0) < 45:
        missing.append("weak answer blocks")
    return missing


def _improvements_from_missing(missing: list[str]) -> list[str]:
    mapping = {
        "author eksik": "add_author",
        "citation block eksik": "add_citation_page",
        "source list eksik": "add_source_list",
        "faq eksik": "add_faq",
        "schema eksik": "add_schema",
        "entity coverage düşük": "add_entity",
        "outdated content": "refresh_content",
        "no trust indicators": "add_trust_badges",
        "no supporting pages": "add_support_page",
        "weak answer blocks": "add_answer_block",
    }
    out: list[str] = []
    for m in missing:
        imp = mapping.get(m)
        if imp and imp not in out:
            out.append(imp)
    if "entity coverage düşük" in missing:
        out.append("expand_entity_graph")
    return out


def _compute_ai_visibility(subscores: dict[str, int], targets: list[str] | None = None) -> dict[str, Any]:
    base = (
        subscores.get("overview_score", 0) * 0.35
        + subscores.get("ai_readability_score", 0) * 0.25
        + subscores.get("answer_quality_score", 0) * 0.25
        + subscores.get("entity_score", 0) * 0.15
    )
    ai_visibility_score = int(round(base))
    overview_prob = int(round(subscores.get("overview_score", 0) * 0.9))
    citation_prob = int(round(subscores.get("citation_structure_score", 0) * 0.85 + subscores.get("answer_quality_score", 0) * 0.15))
    trust_prob = int(round(subscores.get("source_trust_score", 0) * 0.6 + subscores.get("authority_score", 0) * 0.4))

    per_target: dict[str, Any] = {}
    for t in (targets or AI_TARGETS):
        if t == "Google AI Overview":
            per_target[t] = {
                "status": "estimated",
                "visibility_score": overview_prob,
                "provider": "citation_engine_heuristic",
            }
        else:
            per_target[t] = {"status": "provider_missing", "visibility_score": None, "provider": None}

    return {
        "ai_visibility_score": ai_visibility_score,
        "overview_probability": overview_prob,
        "citation_probability": citation_prob,
        "trust_probability": trust_prob,
        "targets": per_target,
    }


def _gate_scores_for_project(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {}
    gate_path = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
    if not gate_path.exists():
        return {}
    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
        best: dict[str, Any] = {}
        for report in (data.get("reports") or {}).values():
            if report.get("project_id") != project_id:
                continue
            if not best or report.get("created_at", "") > best.get("created_at", ""):
                best = report
        if not best:
            return {}
        return {
            "authority_score": int(best.get("authority_score") or best.get("overall_score") or 50),
            "citation_score": int(best.get("citation_score") or 50),
            "llm_visibility_score": int(best.get("llm_visibility_score") or 50),
            "aeo_score": int(best.get("aeo_score") or 50),
            "overall_score": int(best.get("overall_score") or 0),
        }
    except Exception as exc:
        logger.debug("quality gate state: %s", exc)
    return {}


def _entity_trust_model(project_id: str = "", entity_name: str = "") -> dict[str, Any]:
    entity_strength = 0
    authority_sources = 0
    support_pages = 0
    citations = 0
    freshness = 50
    trust_score = 40

    if project_id:
        try:
            from app.moduller.entity_geo_graph import get_project_scores, missing_entities
            scores = get_project_scores(project_id)
            if scores.get("success"):
                entity_strength = int(scores.get("entity_strength_score") or 0)
                trust_score = int(
                    (scores.get("entity_strength_score") or 0) * 0.4
                    + (scores.get("topic_authority_score") or 0) * 0.35
                    + (scores.get("geo_coverage_score") or 0) * 0.25
                )
                authority_sources = max(0, entity_strength // 20)
                support_pages = max(0, int(scores.get("geo_coverage_score") or 0) // 25)
            missing = missing_entities(project_id=project_id)
            if missing.get("success"):
                gaps = len(missing.get("missing_entities") or [])
                trust_score = max(0, trust_score - min(25, gaps * 3))
                support_pages = max(support_pages, len(missing.get("recommended_pages") or []))
        except Exception as exc:
            logger.debug("entity trust: %s", exc)

    return {
        "entity": entity_name or project_id or "project",
        "entity_strength": entity_strength,
        "authority_sources": authority_sources,
        "support_pages": support_pages,
        "citations": citations,
        "freshness": freshness,
        "trust_score": max(0, min(100, trust_score)),
        "project_id": project_id,
    }


def _build_page_record(
    url: str,
    html: str,
    *,
    project_id: str = "",
    title: str = "",
    fetch_meta: dict | None = None,
) -> dict[str, Any]:
    plain = _strip_html(html)
    gate = _gate_scores_for_project(project_id)
    subscores = _compute_subscores(html, plain, project_id=project_id, gate_scores=gate)
    overall = _overall_citation_score(subscores)
    entity_count = _entity_count(html, plain, project_id)
    faq_count = _count_faq(html)
    schema_types = _schema_types(html)
    missing = _detect_missing_signals(html, plain, subscores, entity_count)
    improvements = _improvements_from_missing(missing)
    visibility = _compute_ai_visibility(subscores)
    settings = get_settings()
    threshold = int(settings.get("citation_threshold") or 75)

    return {
        "page_id": _page_id(url),
        "url": _normalize_url(url),
        "title": title or _extract_title(html) or url,
        "project_id": project_id,
        "entity_count": entity_count,
        "faq_count": faq_count,
        "schema_types": schema_types,
        "citation_score": overall,
        "overall_citation_score": overall,
        **subscores,
        "citation_ready": overall >= threshold and len(missing) <= 2,
        "missing_signals": missing,
        "improvements": improvements,
        "ai_visibility": visibility,
        "analyzed_at": _now(),
        "fetch": fetch_meta or {},
    }


def analyze_page(
    url: str = "",
    *,
    html: str = "",
    project_id: str = "",
    title: str = "",
    competitor_url: str = "",
) -> dict[str, Any]:
    if not get_settings().get("enabled", True):
        return {"success": False, "error": "citation_engine disabled"}

    u = (url or "").strip()
    if not u:
        return {"success": False, "error": "url gerekli"}

    fetch_meta: dict[str, Any] = {"fetched": False}
    page_html = html
    if not page_html:
        fetched = _fetch_page(u)
        fetch_meta = {"fetched": fetched.get("success", False), **{k: fetched.get(k) for k in ("error", "status")}}
        page_html = fetched.get("html") or ""

    if not page_html.strip():
        return {
            "success": False,
            "error": "page_content_unavailable",
            "url": u,
            "fetch": fetch_meta,
        }

    record = _build_page_record(u, page_html, project_id=project_id, title=title, fetch_meta=fetch_meta)
    st = _load_state()
    pages = st.get("pages") or []
    prev = next((p for p in pages if p.get("page_id") == record["page_id"]), None)
    pages = [p for p in pages if p.get("page_id") != record["page_id"]]
    pages.insert(0, record)
    st["pages"] = pages[:PAGE_LIMIT]

    opps = _derive_opportunities_from_page(record)
    st.setdefault("opportunities", [])
    for opp in opps:
        st["opportunities"] = [o for o in st["opportunities"] if o.get("id") != opp["id"]]
        st["opportunities"].insert(0, opp)
    st["opportunities"] = st["opportunities"][:200]

    vis_entry = {
        "page_id": record["page_id"],
        "url": record["url"],
        "project_id": project_id,
        **record["ai_visibility"],
        "at": _now(),
    }
    st.setdefault("visibility", [])
    st["visibility"] = [v for v in st["visibility"] if v.get("page_id") != record["page_id"]]
    st["visibility"].insert(0, vis_entry)
    st["visibility"] = st["visibility"][:PAGE_LIMIT]

    _append_history(st, {"action": "analyze_page", "url": u, "score": record["citation_score"], "at": _now()})
    _save_state(st)

    _record_brain(
        "citation_analysis_completed",
        domain=_domain_from_url(u),
        result={"page_id": record["page_id"], "score": record["citation_score"]},
    )
    if record["missing_signals"]:
        _record_brain(
            "citation_gap_found",
            domain=_domain_from_url(u),
            result={"missing": record["missing_signals"]},
            reason="Eksik citation sinyalleri",
        )
    if opps:
        _record_brain("citation_opportunity_created", domain=_domain_from_url(u), result={"count": len(opps)})
    if prev and prev.get("citation_score") is not None:
        diff = record["citation_score"] - int(prev.get("citation_score") or 0)
        if diff >= 5:
            _record_brain("citation_score_increased", domain=_domain_from_url(u), result={"delta": diff})
        elif diff <= -5:
            _record_brain("citation_score_decreased", domain=_domain_from_url(u), result={"delta": diff})

    gap_result = None
    if competitor_url:
        gap_result = _competitor_citation_gap(u, competitor_url, project_id=project_id, our_record=record)

    return {
        "success": True,
        "page": record,
        "opportunities": opps,
        "competitor_gap": gap_result,
    }


def _derive_opportunities_from_page(page: dict[str, Any]) -> list[dict[str, Any]]:
    settings = get_settings()
    threshold = int(settings.get("citation_threshold") or 75)
    opps: list[dict[str, Any]] = []
    score = int(page.get("citation_score") or 0)
    gap = max(0, threshold - score)

    for imp in page.get("improvements") or []:
        if imp not in CITATION_OPPORTUNITY_TYPES and imp != "refresh_content":
            continue
        opp_type = imp if imp in CITATION_OPPORTUNITY_TYPES else "add_answer_block"
        oid = f"cite-opp-{hashlib.sha256(f'{page.get('page_id')}:{opp_type}'.encode()).hexdigest()[:10]}"
        citation_opp_score = min(100, 40 + gap + (15 if opp_type in ("add_faq", "add_schema") else 10))
        opps.append({
            "id": oid,
            "type": opp_type,
            "page_id": page.get("page_id"),
            "url": page.get("url"),
            "title": f"Citation: {opp_type.replace('_', ' ')} — {page.get('title', '')[:60]}",
            "citation_opportunity_score": citation_opp_score,
            "citation_score": score,
            "gap": gap,
            "missing_signals": page.get("missing_signals") or [],
            "quick_win": citation_opp_score >= 72,
            "created_at": _now(),
        })
    return opps


def _competitor_citation_gap(
    our_url: str,
    competitor_url: str,
    *,
    project_id: str = "",
    our_record: dict | None = None,
) -> dict[str, Any]:
    our = our_record or analyze_page(our_url, project_id=project_id).get("page")
    if not our:
        return {"success": False, "error": "our_page_analysis_failed"}

    comp_res = analyze_page(competitor_url, project_id=project_id)
    comp = comp_res.get("page")
    if not comp:
        return {"success": False, "error": "competitor_page_analysis_failed"}

    def _side(rec: dict) -> dict[str, int]:
        return {
            "citation_score": int(rec.get("citation_score") or 0),
            "entity_score": int(rec.get("entity_score") or 0),
            "faq_score": min(100, int(rec.get("faq_count") or 0) * 25),
            "answer_score": int(rec.get("answer_quality_score") or 0),
        }

    us = _side(our)
    them = _side(comp)
    citation_gap_score = max(0, them["citation_score"] - us["citation_score"])

    entry = {
        "gap_id": f"gap-{uuid.uuid4().hex[:10]}",
        "our_url": our_url,
        "competitor_url": competitor_url,
        "project_id": project_id,
        "us": us,
        "competitor": them,
        "citation_gap_score": citation_gap_score,
        "why_competitor_wins": _why_competitor_wins(us, them, comp, our),
        "at": _now(),
    }

    st = _load_state()
    st.setdefault("competitors", [])
    st["competitors"].insert(0, entry)
    st["competitors"] = st["competitors"][:100]
    _append_history(st, {"action": "competitor_gap", "gap_score": citation_gap_score, "at": _now()})
    _save_state(st)

    return {"success": True, **entry}


def _why_competitor_wins(us: dict, them: dict, comp: dict, our: dict) -> list[str]:
    reasons: list[str] = []
    if them["citation_score"] > us["citation_score"] + 10:
        reasons.append("Rakip daha yüksek citation skoru")
    if them["entity_score"] > us["entity_score"] + 10:
        reasons.append("Rakip entity coverage daha güçlü")
    if them["faq_score"] > us["faq_score"] + 15:
        reasons.append("Rakip FAQ yapısı daha zengin")
    if them["answer_score"] > us["answer_score"] + 10:
        reasons.append("Rakip answer block kalitesi daha iyi")
    for sig in comp.get("missing_signals") or []:
        if sig not in (our.get("missing_signals") or []):
            pass
    for sig in our.get("missing_signals") or []:
        if sig not in (comp.get("missing_signals") or []):
            reasons.append(f"Bizde eksik: {sig}")
    return reasons[:8]


def analyze_project(
    project_id: str = "",
    *,
    urls: list[str] | None = None,
    competitor_domains: list[str] | None = None,
) -> dict[str, Any]:
    if not get_settings().get("enabled", True):
        return {"success": False, "error": "citation_engine disabled"}
    pid = (project_id or "").strip()
    if not pid:
        return {"success": False, "error": "project_id gerekli"}

    target_urls = list(urls or [])
    if not target_urls:
        try:
            from app.moduller.rank_index_watcher import rank_index_watcher
            proj = rank_index_watcher.get_project(pid)
            project = proj.get("project") or proj
            dom = project.get("domain") or ""
            if dom:
                target_urls.append(_normalize_url(dom))
            for kw in (project.get("keywords") or [])[:5]:
                lu = kw.get("landing_url") or kw.get("url")
                if lu:
                    target_urls.append(_normalize_url(lu))
        except Exception as exc:
            logger.debug("rank watcher urls: %s", exc)

    analyzed: list[dict] = []
    errors: list[str] = []
    for u in target_urls[:20]:
        res = analyze_page(u, project_id=pid)
        if res.get("success"):
            analyzed.append(res["page"])
        else:
            errors.append(f"{u}: {res.get('error')}")

    entity_trust = _entity_trust_model(project_id=pid)
    st = _load_state()
    st.setdefault("entities", [])
    ent_rec = {**entity_trust, "entity_id": f"ent-{pid}", "updated_at": _now()}
    st["entities"] = [e for e in st["entities"] if e.get("project_id") != pid]
    st["entities"].insert(0, ent_rec)
    st["entities"] = st["entities"][:ENTITY_LIMIT]

    avg_score = int(sum(p.get("citation_score", 0) for p in analyzed) / len(analyzed)) if analyzed else 0
    proj_summary = {
        "project_id": pid,
        "pages_analyzed": len(analyzed),
        "avg_citation_score": avg_score,
        "entity_trust": entity_trust,
        "errors": errors,
        "analyzed_at": _now(),
    }
    st.setdefault("projects", {})
    st["projects"][pid] = proj_summary
    _append_history(st, {"action": "analyze_project", "project_id": pid, "pages": len(analyzed), "at": _now()})
    _save_state(st)

    gaps: list[dict] = []
    for comp_dom in (competitor_domains or [])[:3]:
        if analyzed and comp_dom:
            cu = comp_dom if "://" in comp_dom else f"https://{comp_dom}"
            g = _competitor_citation_gap(analyzed[0]["url"], cu, project_id=pid, our_record=analyzed[0])
            if g.get("success"):
                gaps.append(g)

    _record_brain("citation_analysis_completed", keyword=pid, result=proj_summary)

    return {
        "success": True,
        "project_id": pid,
        "summary": proj_summary,
        "pages": analyzed,
        "competitor_gaps": gaps,
        "entity_trust": entity_trust,
    }


def list_pages(limit: int = 50, project_id: str = "") -> dict[str, Any]:
    pages = _load_state().get("pages") or []
    if project_id:
        pages = [p for p in pages if p.get("project_id") == project_id]
    return {"success": True, "count": len(pages), "pages": pages[:limit]}


def list_entities(limit: int = 50, project_id: str = "") -> dict[str, Any]:
    entities = _load_state().get("entities") or []
    if project_id:
        entities = [e for e in entities if e.get("project_id") == project_id]
    return {"success": True, "count": len(entities), "entities": entities[:limit]}


def list_opportunities(limit: int = 50) -> dict[str, Any]:
    opps = _load_state().get("opportunities") or []
    quick = [o for o in opps if o.get("quick_win")]
    return {"success": True, "count": len(opps), "quick_wins": len(quick), "opportunities": opps[:limit]}


def list_competitors(limit: int = 30) -> dict[str, Any]:
    gaps = _load_state().get("competitors") or []
    return {"success": True, "count": len(gaps), "competitors": gaps[:limit]}


def get_visibility(project_id: str = "", limit: int = 30) -> dict[str, Any]:
    vis = _load_state().get("visibility") or []
    if project_id:
        vis = [v for v in vis if v.get("project_id") == project_id]
    return {"success": True, "count": len(vis), "visibility": vis[:limit], "ai_targets": list(AI_TARGETS)}


def citation_revenue_score(page_url: str = "", citation_score: int = 0) -> dict[str, Any]:
    """Revenue Lead Engine — citation alan içeriklerin lead etkisi."""
    dom = _domain_from_url(page_url)
    lead_count = 0
    estimated_revenue = 0.0
    try:
        from app.moduller.revenue_lead_engine import _load_state as rev_load
        for lead in rev_load().get("leads") or []:
            src = (lead.get("source_url") or lead.get("source_domain") or "").lower()
            if dom and dom in src:
                lead_count += 1
                estimated_revenue += float(lead.get("estimated_value") or 0)
    except Exception:
        pass

    cite = citation_score or 0
    correlation = min(100, int(cite * 0.5 + min(50, lead_count * 12)))
    citation_revenue = int(round(correlation * 0.6 + estimated_revenue * 0.01))

    return {
        "success": True,
        "page_url": page_url,
        "citation_score": cite,
        "lead_count": lead_count,
        "estimated_revenue": round(estimated_revenue, 2),
        "citation_revenue_score": max(0, min(100, citation_revenue)),
        "correlation_note": "Citation ↑ Revenue ↑ — ölçüm katmanı, üretim yok",
    }


def serp_fortress_adjustment(
    project_id: str = "",
    keyword: str = "",
    current_citation_score: int = 50,
) -> dict[str, Any]:
    """SERP Defense — citation düşüş/yükseliş fortress delta."""
    prev = 50
    st = _load_state()
    for h in st.get("history") or []:
        if h.get("action") == "analyze_page" and h.get("score") is not None:
            prev = int(h.get("score") or 50)
            break
    for p in st.get("pages") or []:
        if project_id and p.get("project_id") == project_id:
            prev = int(p.get("citation_score") or prev)
            break

    delta = 0
    diff = current_citation_score - prev
    if diff <= -10:
        delta -= 8
    elif diff >= 10:
        delta += 6
    if current_citation_score < 50:
        delta -= 5
    elif current_citation_score >= 75:
        delta += 4

    return {
        "success": True,
        "fortress_delta": delta,
        "fortress_penalty": delta < 0,
        "fortress_boost": delta > 0,
        "previous_citation_score": prev,
        "current_citation_score": current_citation_score,
        "keyword": keyword,
        "project_id": project_id,
    }


def opportunity_scoring_payload() -> dict[str, Any]:
    """Opportunity Engine — citation_opportunity_score sinyalleri."""
    opps = _load_state().get("opportunities") or []
    signals = []
    for o in opps[:40]:
        signals.append({
            "keyword": o.get("url", ""),
            "citation_opportunity_score": float(o.get("citation_opportunity_score") or 50),
            "citation_score": float(o.get("citation_score") or 0),
            "gap": float(o.get("gap") or 0),
            "type": o.get("type"),
            "quick_win": bool(o.get("quick_win")),
            "boost": bool(o.get("quick_win")),
        })
    return {"success": True, "signals": signals}


def apply_citation_scores_to_opportunities(opportunities: list[dict]) -> list[dict]:
    """Opportunity Engine entegrasyonu."""
    payload = opportunity_scoring_payload()
    by_url = {s["keyword"].lower(): s for s in payload.get("signals") or [] if s.get("keyword")}
    out = []
    for opp in opportunities:
        o = dict(opp)
        url = (o.get("domain") or o.get("url") or o.get("keyword") or "").lower()
        sig = by_url.get(url)
        base = float(o.get("opportunity_score") or 50)
        if sig:
            cite_opp = float(sig.get("citation_opportunity_score") or base)
            o["citation_opportunity_score"] = cite_opp
            if sig.get("quick_win") or cite_opp >= 72:
                o["opportunity_score"] = round(min(100, base * 0.75 + cite_opp * 0.25 + 6), 1)
                o["citation_quick_win"] = True
            elif cite_opp >= 60:
                o["opportunity_score"] = round(min(100, base * 0.85 + cite_opp * 0.15), 1)
        else:
            o["citation_opportunity_score"] = round(base * 0.4, 1)
        out.append(o)
    return out


def collect_citation_opportunities(project_id: str = "") -> tuple[list[dict], list[str]]:
    """Opportunity Engine read-only collector."""
    errors: list[str] = []
    out: list[dict] = []
    opps = _load_state().get("opportunities") or []
    if not opps and project_id:
        res = analyze_project(project_id)
        if not res.get("success"):
            return [], [res.get("error") or "citation analyze_project failed"]
        opps = _load_state().get("opportunities") or []

    for o in opps:
        if project_id and o.get("project_id") and o.get("project_id") != project_id:
            continue
        score = float(o.get("citation_opportunity_score") or 55)
        out.append({
            "id": o.get("id") or f"cite-{uuid.uuid4().hex[:8]}",
            "type": "citation",
            "subtype": o.get("type") or "citation_gap",
            "title": o.get("title") or "Citation fırsatı",
            "source": "citation_engine",
            "project_id": project_id or o.get("project_id", ""),
            "domain": o.get("url", ""),
            "keyword": "",
            "reason": f"Citation gap: {o.get('type')} (skor {o.get('citation_score', 0)})",
            "traffic_score": 45.0,
            "difficulty_score": 35.0,
            "authority_requirement": 30.0,
            "estimated_gain": min(90.0, score),
            "implementation_effort": 40.0,
            "opportunity_score": round(score, 1),
            "citation_opportunity_score": score,
            "action_plan": [o.get("type")] if o.get("type") in CITATION_OPPORTUNITY_TYPES else ["add_faq"],
            "metadata": o,
        })
    return out, errors


def agent_signals(project_id: str = "") -> dict[str, Any]:
    """Autonomous Agent insight tipleri."""
    settings = get_settings()
    threshold = int(settings.get("citation_threshold") or 75)
    pages = _load_state().get("pages") or []
    if project_id:
        pages = [p for p in pages if p.get("project_id") == project_id]
    insights: list[dict] = []

    for p in pages[:15]:
        score = int(p.get("citation_score") or 0)
        url = p.get("url") or ""
        if score < 50:
            insights.append({
                "type": "low_citation_score",
                "keyword": url,
                "message": f"Düşük citation skoru ({score}): {p.get('title', url)[:50]}",
                "recommended_action": "improve_citation_signals",
                "priority": "HIGH",
                "metadata": {"page_id": p.get("page_id"), "score": score},
            })
        elif score >= threshold and score < 90:
            insights.append({
                "type": "high_citation_potential",
                "keyword": url,
                "message": f"Yüksek citation potansiyeli ({score})",
                "recommended_action": "optimize_ai_visibility",
                "priority": "MEDIUM",
            })

    for g in (_load_state().get("competitors") or [])[:10]:
        if int(g.get("citation_gap_score") or 0) >= 15:
            insights.append({
                "type": "citation_gap_detected",
                "keyword": g.get("competitor_url") or "",
                "message": f"Rakip citation gap: {g.get('citation_gap_score')} puan",
                "recommended_action": "close_citation_gap",
                "priority": "HIGH",
                "metadata": g,
            })

    hist = _load_state().get("history") or []
    for h in hist[:5]:
        if h.get("action") == "analyze_page" and h.get("score") is not None:
            if int(h.get("score") or 0) < 45:
                insights.append({
                    "type": "citation_decline",
                    "keyword": h.get("url") or "",
                    "message": "Citation skoru kritik seviyede",
                    "recommended_action": "refresh_citation_content",
                    "priority": "HIGH",
                })
            break

    return {"success": True, "insights": insights[:25], "project_id": project_id}


def mission_control_payload() -> dict[str, Any]:
    st = _load_state()
    pages = st.get("pages") or []
    opps = st.get("opportunities") or []
    settings = get_settings()
    threshold = int(settings.get("citation_threshold") or 75)

    low = [p for p in pages if int(p.get("citation_score") or 0) < 50]
    ready = [p for p in pages if p.get("citation_ready")]
    risks = [p for p in pages if len(p.get("missing_signals") or []) >= 4]
    avg_vis = 0
    if pages:
        avg_vis = int(sum((p.get("ai_visibility") or {}).get("ai_visibility_score", 0) for p in pages) / len(pages))

    return {
        "success": True,
        "citation_health_score": int(sum(p.get("citation_score", 0) for p in pages) / len(pages)) if pages else 0,
        "pages_tracked": len(pages),
        "citation_ready_count": len(ready),
        "low_citation_pages": len(low),
        "citation_risks": len(risks),
        "ai_visibility_avg": avg_vis,
        "opportunities_count": len(opps),
        "quick_wins": len([o for o in opps if o.get("quick_win")]),
        "top_risks": [{"url": p.get("url"), "score": p.get("citation_score"), "missing": p.get("missing_signals")} for p in risks[:5]],
        "top_opportunities": opps[:5],
    }


def dashboard() -> dict[str, Any]:
    st = _load_state()
    pages = st.get("pages") or []
    opps = st.get("opportunities") or []
    mc = mission_control_payload()
    return {
        "success": True,
        "module": "citation_engine",
        "enabled": get_settings().get("enabled", True),
        "pages_count": len(pages),
        "entities_count": len(st.get("entities") or []),
        "opportunities_count": len(opps),
        "competitor_gaps": len(st.get("competitors") or []),
        "citation_health": mc.get("citation_health_score", 0),
        "ai_visibility_avg": mc.get("ai_visibility_avg", 0),
        "citation_ready_count": mc.get("citation_ready_count", 0),
        "low_citation_pages": mc.get("low_citation_pages", 0),
        "quick_wins": mc.get("quick_wins", 0),
        "recent_pages": pages[:10],
        "top_opportunities": opps[:8],
        "ai_targets": list(AI_TARGETS),
        "settings": get_settings(),
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "overview": dashboard,
        "pages": lambda: list_pages(limit=200),
        "entities": lambda: list_entities(limit=100),
        "opportunities": lambda: list_opportunities(limit=100),
        "competitors": lambda: list_competitors(limit=50),
        "visibility": lambda: get_visibility(limit=100),
    }
    fn = generators.get(report_type, dashboard)
    payload = fn()
    path = REPORTS_DIR / f"citation-engine-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def health() -> dict[str, Any]:
    settings = get_settings()
    dash = dashboard()
    entity_ok = False
    try:
        from app.moduller.entity_geo_graph import health as eg_health
        entity_ok = eg_health().get("success", False)
    except Exception:
        pass
    return {
        "success": True,
        "module": "citation_engine",
        "enabled": settings.get("enabled", True),
        "pages_tracked": dash.get("pages_count", 0),
        "citation_threshold": settings.get("citation_threshold", 75),
        "visibility_threshold": settings.get("visibility_threshold", 70),
        "trust_threshold": settings.get("trust_threshold", 70),
        "ai_targets": list(AI_TARGETS),
        "entity_geo_graph_ready": entity_ok,
        "produces_content": False,
    }
