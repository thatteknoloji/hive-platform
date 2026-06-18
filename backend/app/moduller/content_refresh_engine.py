"""Content Refresh Engine V1 — decay tespiti, QIE entegrasyonu, gerçek Astro refresh."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.content_refresh_engine")

STATE_FILE = Path(__file__).resolve().parent.parent / "content_refresh_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
MIN_QUALITY_SCORE = 85

_job_lock = threading.Lock()

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "auto_refresh": False,
    "auto_publish": False,
    "auto_deploy": False,
    "refresh_interval_hours": 168,
    "priority_threshold": 70,
    "max_pages_per_run": 25,
}

DEFAULT_SIGNALS: dict[str, Any] = {
    "refresh_priority": 0,
    "ranking_decay_score": 0,
    "ctr_decay_score": 0,
    "entity_loss_score": 0,
    "citation_loss_score": 0,
    "ai_visibility_loss_score": 0,
    "authority_drop_score": 0,
    "question_gap_score": 0,
    "overview_gap_score": 0,
    "content_age_days": 0,
    "last_refresh_at": "",
    "refresh_needed": False,
}

GEO_OPPORTUNITY_LOCATIONS = [
    "Kadınlar Denizi", "Marina", "Barlar Sokağı", "Kaleiçi", "Davutlar",
    "Güzelçamlı", "Didim", "Bodrum", "Çeşme",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("candidates", {})
                data.setdefault("plans", {})
                data.setdefault("queue", [])
                data.setdefault("jobs", {})
                data.setdefault("running_job", "")
                data.setdefault("last_scan_at", "")
                data.setdefault("last_refresh_at", "")
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "candidates": {},
        "plans": {},
        "queue": [],
        "jobs": {},
        "running_job": "",
        "last_scan_at": "",
        "last_refresh_at": "",
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _priority_label(score: int) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def _page_id(page: dict[str, Any]) -> str:
    ptype = page.get("type") or "page"
    slug = (page.get("slug") or "").strip()
    return f"{ptype}:{slug}"


def _parse_age_days(updated_at: str) -> int:
    if not updated_at:
        return 999
    text = updated_at.replace(" UTC", "").strip()[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
            return max(0, (datetime.now(timezone.utc) - dt).days)
        except ValueError:
            continue
    return 0


def get_settings() -> dict[str, Any]:
    return {**DEFAULT_SETTINGS, **(_load_state().get("settings") or {})}


def update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = get_settings()
    for key in DEFAULT_SETTINGS:
        if key in payload:
            cur[key] = payload[key]
    st["settings"] = cur
    _save_state(st)
    return {"success": True, "settings": cur}


def _project_path(project_id: str) -> tuple[dict[str, Any], Path]:
    from app.moduller.astro_factory import GENERATED_DIR, _get_project, _project_path
    project = _get_project(project_id)
    path = _project_path(project["slug"])
    if not str(path.resolve()).startswith(str(GENERATED_DIR.resolve())):
        raise ValueError("generated-sites dışına yazma yasak")
    return project, path


def _load_pages(project_id: str) -> list[dict[str, Any]]:
    from app.moduller.seo_quality_gate import _collect_pages_from_data
    _, path = _project_path(project_id)
    data_dir = path / "src" / "data"
    pages_data = json.loads((data_dir / "pages.json").read_text(encoding="utf-8")) if (data_dir / "pages.json").exists() else {}
    faqs = json.loads((data_dir / "faqs.json").read_text(encoding="utf-8")) if (data_dir / "faqs.json").exists() else []
    blog = json.loads((data_dir / "blog.json").read_text(encoding="utf-8")) if (data_dir / "blog.json").exists() else []
    entity = json.loads((data_dir / "entity_pages.json").read_text(encoding="utf-8")) if (data_dir / "entity_pages.json").exists() else []
    pages = _collect_pages_from_data(pages_data, faqs, blog)
    for item in entity:
        if isinstance(item, dict):
            pages.append({
                "slug": item.get("slug", ""),
                "type": "entity",
                "title": item.get("title", ""),
                "content_html": item.get("content_html", ""),
                "keyword": item.get("keyword", ""),
                "updated_at": item.get("updated_at", ""),
            })
    for p in pages:
        p["page_id"] = _page_id(p)
        p["project_id"] = project_id
        if not p.get("updated_at"):
            p["updated_at"] = pages_data.get("updated_at", "")
    return pages


def _rank_context(project_id: str) -> dict[str, Any]:
    from app.moduller.rank_index_watcher import get_project
    ctx: dict[str, Any] = {"keywords": {}, "performance": {}, "ctr_drop": 0}
    res = get_project(project_id)
    if not res.get("success"):
        return ctx
    proj = res["project"]
    for kw in proj.get("keywords") or []:
        key = (kw.get("keyword") or "").lower()
        ctx["keywords"][key] = kw
    hist = proj.get("performance_history") or []
    if len(hist) >= 2:
        latest, prev = hist[0], hist[1]
        ctx["performance"] = latest
        if prev.get("ctr") and latest.get("ctr") is not None:
            ctx["ctr_drop"] = max(0.0, float(prev["ctr"]) - float(latest["ctr"]))
    return ctx


def _gate_context(project_id: str) -> dict[str, Any]:
    gate_path = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
    if not gate_path.exists():
        return {}
    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    best: dict[str, Any] = {}
    for report in (data.get("reports") or {}).values():
        if report.get("project_id") != project_id:
            continue
        if not best or (report.get("created_at", "") > best.get("created_at", "")):
            best = report
    return best


def _entity_context(project_id: str) -> dict[str, Any]:
    try:
        from app.moduller.entity_geo_graph import get_project_scores
        return get_project_scores(project_id) or {}
    except Exception:
        return {}


def _network_context(project_id: str) -> dict[str, Any]:
    try:
        from app.moduller.network_replicator import list_networks
        variants: list[dict[str, Any]] = []
        authority = 70
        freshness = 70
        for net in list_networks().get("networks") or []:
            for d in net.get("domains") or []:
                if d.get("project_id") == project_id:
                    variants.append({"network_id": net.get("network_id"), **d})
                    authority = max(authority, int(d.get("authority_score") or d.get("quality_score") or 0))
                    freshness = min(freshness, int(d.get("content_freshness") or 70))
        return {"variants": variants, "authority_score": authority, "freshness_score": freshness}
    except Exception:
        return {"variants": [], "authority_score": 70, "freshness_score": 70}


def _entity_graph_summary(project_id: str) -> dict[str, Any]:
    try:
        from app.moduller.entity_geo_graph import _latest_graph_for_project, _safe_project_id
        graph = _latest_graph_for_project(_safe_project_id(project_id))
        if not graph:
            return {}
        return graph.get("summary") or {}
    except Exception:
        return {}


def _resolve_rank_keyword(
    page: dict[str, Any],
    project_id: str,
    rank: dict[str, Any] | None = None,
) -> str:
    """Sayfa için rank watcher anahtar kelimesini çöz — keyword, title veya proje seed."""
    rank = rank or _rank_context(project_id)
    keywords = rank.get("keywords") or {}

    direct = (page.get("keyword") or "").strip().lower()
    if direct and direct in keywords:
        return direct

    haystack = f"{page.get('keyword', '')} {page.get('title', '')}".lower()
    for key in keywords:
        if key and (key in haystack or haystack in key):
            return key

    seed = ""
    try:
        project, path = _project_path(project_id)
        seed = (project.get("seed_keyword") or "").strip().lower()
        if seed and seed in keywords:
            return seed
        pages_path = path / "src" / "data" / "pages.json"
        if pages_path.exists():
            pages_data = json.loads(pages_path.read_text(encoding="utf-8"))
            file_seed = (pages_data.get("seed_keyword") or "").strip().lower()
            if file_seed:
                seed = file_seed
                if seed in keywords:
                    return seed
    except (ValueError, json.JSONDecodeError, OSError):
        pass

    if seed:
        for key in keywords:
            if key in seed or seed in key:
                return key
        return seed

    if direct:
        return direct
    return haystack.strip()


def _qie_gaps_for_keyword(keyword: str) -> dict[str, int]:
    qie_path = Path(__file__).resolve().parent.parent / "question_intelligence_engine_state.json"
    if not qie_path.exists():
        return {}
    try:
        data = json.loads(qie_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    kw = keyword.lower()
    matches = [
        o for o in (data.get("outputs") or [])
        if kw in (o.get("keyword") or "").lower() or kw in (o.get("title") or "").lower()
    ]
    if not matches:
        return {}
    return {
        "question_gap_score": max(int(m.get("question_gap_score") or m.get("question_gap") or 0) for m in matches),
        "intent_gap_score": max(int(m.get("intent_gap_score") or m.get("intent_gap") or 0) for m in matches),
        "paa_gap_score": max(int(m.get("paa_gap_score") or 0) for m in matches),
        "autocomplete_gap_score": max(int(m.get("autocomplete_gap_score") or 0) for m in matches),
    }


def _internal_link_analysis(project_id: str, page: dict[str, Any]) -> dict[str, Any]:
    summary = _entity_graph_summary(project_id)
    slug = (page.get("slug") or "home").lower()
    title = (page.get("title") or "").lower()
    orphan = [e for e in (summary.get("orphan_entities") or []) if e]
    missing = summary.get("missing_pages") or []
    cluster = summary.get("cluster_pages") or []
    pillar = summary.get("pillar_pages") or []
    is_orphan = slug not in "".join(cluster + pillar).lower() and page.get("type") not in ("home",)
    weak = page.get("type") in ("blog", "entity") and slug not in "".join(pillar).lower()
    isolated = is_orphan and not any(slug in (p or "").lower() for p in cluster)
    suggestions: list[str] = []
    if is_orphan:
        suggestions.append(f"Pillar sayfaya link: {pillar[0]}" if pillar else "Ana sayfaya iç link ekle")
    for m in missing[:3]:
        suggestions.append(f"Eksik hedef: {m}")
    for o in orphan[:2]:
        suggestions.append(f"Entity bağlantısı: {o}")
    return {
        "orphan_page": is_orphan,
        "weak_page": weak,
        "isolated_cluster": isolated,
        "link_suggestions": suggestions,
        "missing_pages": missing[:10],
        "orphan_entities": orphan[:10],
    }


def _geo_opportunities(page: dict[str, Any], project: dict[str, Any]) -> list[str]:
    loc = project.get("location") or "Kuşadası"
    html = (page.get("content_html") or "").lower()
    opportunities: list[str] = []
    for area in GEO_OPPORTUNITY_LOCATIONS:
        if area.lower() not in html and area.lower() != loc.lower():
            opportunities.append(f"{area} GEO kapsamı eksik")
    if "mahalle" not in html:
        opportunities.append(f"{loc} mahalle bazlı GEO bölümü eklenebilir")
    if "komşu" not in html and "bodrum" not in html:
        opportunities.append("Komşu şehir karşılaştırma fırsatı (Didim, Bodrum)")
    return opportunities[:8]


def _entity_refresh_gaps(project_id: str, page: dict[str, Any]) -> dict[str, Any]:
    summary = _entity_graph_summary(project_id)
    entity_ctx = _entity_context(project_id)
    gaps: list[str] = []
    for ent in (summary.get("orphan_entities") or [])[:5]:
        gaps.append(f"orphan_entity:{ent}")
    for mp in (summary.get("missing_pages") or entity_ctx.get("missing_pages") or [])[:5]:
        gaps.append(f"missing_page:{mp}")
    entity_gap = int(entity_ctx.get("entity_gap") or 0)
    if entity_gap >= 20:
        gaps.append("entity_expansion_needed")
    return {
        "entity_gaps": gaps,
        "entity_gap_score": entity_gap,
        "entity_strength": int(entity_ctx.get("entity_strength_score") or 70),
        "expansion_recommended": bool(gaps),
    }


def compute_page_signals(page: dict[str, Any], project_id: str) -> dict[str, Any]:
    signals = dict(DEFAULT_SIGNALS)
    rank = _rank_context(project_id)
    gate = _gate_context(project_id)
    entity = _entity_context(project_id)
    kw = _resolve_rank_keyword(page, project_id, rank)
    kw_data = rank["keywords"].get(kw, {})

    network = _network_context(project_id)
    qie = _qie_gaps_for_keyword(kw)

    signals["ranking_decay_score"] = int(kw_data.get("ranking_decay_score") or 0)
    signals["content_age_days"] = _parse_age_days(page.get("updated_at", ""))
    signals["ctr_decay_score"] = min(100, int(rank.get("ctr_drop", 0) * 10000))

    gate_pages = {p.get("slug") or "home": p for p in gate.get("pages") or []}
    gp = gate_pages.get(page.get("slug") or "home") or gate_pages.get(page.get("slug", "")) or {}
    overall = int(gate.get("overall_score") or gp.get("score") or 100)
    citation = int(gp.get("citation_score") or gate.get("citation_score") or overall)
    llm_vis = int(gp.get("llm_visibility_score") or gate.get("llm_visibility_score") or overall)
    overview = int(gp.get("overview_score") or gate.get("overview_score") or gp.get("overview_probability_score") or overall)
    entity_strength = int(entity.get("entity_strength_score") or 70)
    authority = int(gate.get("authority_score") or gp.get("authority_score") or overall)
    freshness = int(network.get("freshness_score") or 70)

    signals["citation_loss_score"] = max(0, 85 - citation)
    signals["ai_visibility_loss_score"] = max(0, 70 - llm_vis)
    signals["entity_loss_score"] = max(0, 75 - entity_strength)
    signals["authority_drop_score"] = max(0, 80 - min(authority, freshness))
    signals["overview_gap_score"] = max(0, 75 - overview)
    signals["question_gap_score"] = max(
        qie.get("question_gap_score", 0),
        qie.get("paa_gap_score", 0),
        qie.get("autocomplete_gap_score", 0),
    )

    priority = 0
    if signals["ranking_decay_score"] >= 36:
        priority += 30
    if signals["ctr_decay_score"] >= 20:
        priority += 15
    if signals["entity_loss_score"] >= 25:
        priority += 12
    if signals["citation_loss_score"] >= 20:
        priority += 10
    if signals["ai_visibility_loss_score"] >= 20:
        priority += 12
    if signals["overview_gap_score"] >= 20:
        priority += 10
    if signals["question_gap_score"] >= 25:
        priority += 12
    if signals["authority_drop_score"] >= 20:
        priority += 8
    if signals["content_age_days"] >= 90:
        priority += 10
    if kw_data.get("trend_direction") in ("decaying", "down"):
        priority += 10
    if int(kw_data.get("ranking_momentum") or 0) < 0:
        priority += 8

    signals["refresh_priority"] = min(100, priority)
    settings = get_settings()
    signals["refresh_needed"] = signals["refresh_priority"] >= int(settings.get("priority_threshold", 70))
    signals["priority_label"] = _priority_label(signals["refresh_priority"])
    return signals


def _suggest_actions(
    page: dict[str, Any],
    signals: dict[str, Any],
    entity: dict[str, Any],
    *,
    project_id: str = "",
    link_analysis: dict[str, Any] | None = None,
    geo_ops: list[str] | None = None,
    entity_gaps: dict[str, Any] | None = None,
) -> list[str]:
    actions: list[str] = []
    if signals["ranking_decay_score"] >= 30 or signals["ctr_decay_score"] >= 15:
        actions.extend(["update_statistics", "add_recent_data"])
    if signals["entity_loss_score"] >= 20 or (entity_gaps or {}).get("expansion_recommended"):
        actions.append("expand_entity_section")
    if signals["citation_loss_score"] >= 15:
        actions.append("increase_citation_density")
    if signals["ai_visibility_loss_score"] >= 15 or signals.get("overview_gap_score", 0) >= 15:
        actions.extend(["improve_answer_block", "add_ai_overview_block"])
    if signals.get("question_gap_score", 0) >= 20:
        actions.extend(["add_new_faq", "add_paa_questions"])
    if signals.get("question_gap_score", 0) >= 15:
        actions.append("add_autocomplete_blocks")
    if page.get("type") == "faq" or "?" in (page.get("title") or ""):
        actions.append("add_new_faq")
    if page.get("type") == "geo" or signals.get("content_age_days", 0) > 60 or geo_ops:
        actions.append("expand_geo_section")
    if geo_ops:
        actions.append("expand_local_intent")
    la = link_analysis or {}
    if la.get("orphan_page") or la.get("weak_page") or la.get("isolated_cluster"):
        actions.append("increase_internal_links")
    missing = entity.get("missing_pages") or la.get("missing_pages") or []
    if missing:
        actions.append("increase_internal_links")
    if signals.get("authority_drop_score", 0) >= 20:
        actions.append("add_recent_data")
    if not actions:
        actions.append("improve_answer_block")
    return list(dict.fromkeys(actions))


def scan(project_id: str) -> dict[str, Any]:
    try:
        pages = _load_pages(project_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    entity = _entity_context(project_id)
    candidates: list[dict[str, Any]] = []
    for page in pages:
        signals = compute_page_signals(page, project_id)
        entry = {
            "page_id": page["page_id"],
            "project_id": project_id,
            "slug": page.get("slug", ""),
            "type": page.get("type", ""),
            "title": page.get("title", ""),
            "keyword": page.get("keyword", ""),
            **signals,
        }
        candidates.append(entry)

    st = _load_state()
    st["candidates"][project_id] = candidates
    st["last_scan_at"] = _now()
    _save_state(st)
    needed = [c for c in candidates if c.get("refresh_needed")]
    return {
        "success": True,
        "project_id": project_id,
        "pages_scanned": len(candidates),
        "refresh_needed": len(needed),
        "candidates": candidates,
        "critical": [c for c in candidates if c.get("priority_label") == "CRITICAL"],
        "high": [c for c in candidates if c.get("priority_label") == "HIGH"],
    }


def analyze_page(project_id: str, page_id: str) -> dict[str, Any]:
    try:
        pages = _load_pages(project_id)
        project, _ = _project_path(project_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    page = next((p for p in pages if p["page_id"] == page_id), None)
    if not page:
        return {"success": False, "error": "Sayfa bulunamadı"}
    from app.moduller.seo_quality_gate import seo_quality_gate
    gate = seo_quality_gate.analyze_page(
        page.get("content_html", ""),
        page.get("keyword", ""),
        title=page.get("title", ""),
    )
    signals = compute_page_signals(page, project_id)
    entity = _entity_context(project_id)
    rank = _rank_context(project_id)
    kw = _resolve_rank_keyword(page, project_id, rank)
    link_analysis = _internal_link_analysis(project_id, page)
    geo_ops = _geo_opportunities(page, project)
    entity_gaps = _entity_refresh_gaps(project_id, page)
    actions = _suggest_actions(
        page, signals, entity, project_id=project_id,
        link_analysis=link_analysis, geo_ops=geo_ops, entity_gaps=entity_gaps,
    )
    return {
        "success": True,
        "page_id": page_id,
        "page": {k: page.get(k) for k in ("title", "slug", "type", "keyword")},
        "signals": signals,
        "quality_gate": gate,
        "rank_keyword": rank["keywords"].get(kw),
        "entity_scores": entity,
        "entity_refresh": entity_gaps,
        "geo_opportunities": geo_ops,
        "internal_links": link_analysis,
        "recommended_actions": actions,
        "qie_gaps": _qie_gaps_for_keyword(kw),
        "questions": {
            "ranking_loss": signals["ranking_decay_score"] >= 30,
            "ctr_drop": signals["ctr_decay_score"] >= 15,
            "entity_weak": signals["entity_loss_score"] >= 20,
            "ai_visibility_drop": signals["ai_visibility_loss_score"] >= 15,
            "overview_gap": signals.get("overview_gap_score", 0) >= 15,
            "question_gap": signals.get("question_gap_score", 0) >= 20,
            "citation_weak": signals["citation_loss_score"] >= 15,
            "content_stale": signals["content_age_days"] >= 90,
            "authority_drop": signals["authority_drop_score"] >= 20,
            "internal_links_weak": bool(link_analysis.get("link_suggestions")),
            "geo_coverage_weak": bool(geo_ops),
            "competitor_pressure": signals["ranking_decay_score"] >= 40,
        },
    }


def analyze_project(project_id: str) -> dict[str, Any]:
    scan_res = scan(project_id)
    if not scan_res.get("success"):
        return scan_res
    try:
        project, _ = _project_path(project_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    pages = _load_pages(project_id)
    page_analyses: list[dict[str, Any]] = []
    for cand in scan_res.get("candidates") or []:
        pid = cand.get("page_id", "")
        pa = analyze_page(project_id, pid)
        if pa.get("success"):
            page_analyses.append({
                "page_id": pid,
                "title": cand.get("title"),
                "priority": cand.get("priority_label"),
                "refresh_priority": cand.get("refresh_priority"),
                "signals": cand,
                "recommended_actions": pa.get("recommended_actions"),
                "geo_opportunities": pa.get("geo_opportunities"),
                "entity_refresh": pa.get("entity_refresh"),
            })
    refresh_needed = [c for c in scan_res.get("candidates") or [] if c.get("refresh_needed")]
    return {
        "success": True,
        "project_id": project_id,
        "project": {"site_name": project.get("site_name"), "location": project.get("location")},
        "pages_scanned": scan_res.get("pages_scanned", 0),
        "refresh_needed_count": len(refresh_needed),
        "critical_count": len(scan_res.get("critical") or []),
        "high_count": len(scan_res.get("high") or []),
        "candidates": scan_res.get("candidates"),
        "page_analyses": page_analyses,
        "network": _network_context(project_id),
        "entity_summary": _entity_graph_summary(project_id),
    }


def create_refresh_plan(project_id: str, page_id: str = "") -> dict[str, Any]:
    scan_res = scan(project_id)
    if not scan_res.get("success"):
        return scan_res
    entity = _entity_context(project_id)
    plans: list[dict[str, Any]] = []
    targets = scan_res.get("candidates") or []
    if page_id:
        targets = [c for c in targets if c.get("page_id") == page_id]
    for cand in targets:
        if not cand.get("refresh_needed") and page_id:
            pass
        elif not cand.get("refresh_needed") and not page_id:
            continue
        page = next((p for p in _load_pages(project_id) if p["page_id"] == cand["page_id"]), {})
        try:
            project, _ = _project_path(project_id)
        except ValueError:
            project = {}
        link_analysis = _internal_link_analysis(project_id, page)
        geo_ops = _geo_opportunities(page, project)
        entity_gaps = _entity_refresh_gaps(project_id, page)
        actions = _suggest_actions(
            page, cand, entity, project_id=project_id,
            link_analysis=link_analysis, geo_ops=geo_ops, entity_gaps=entity_gaps,
        )
        plan = {
            "plan_id": f"rp-{uuid.uuid4().hex[:10]}",
            "project_id": project_id,
            "page_id": cand["page_id"],
            "page": cand.get("title") or cand.get("slug"),
            "priority": cand.get("priority_label", "LOW"),
            "refresh_priority": cand.get("refresh_priority", 0),
            "actions": actions,
            "created_at": _now(),
        }
        plans.append(plan)

    st = _load_state()
    st.setdefault("plans", {}).setdefault(project_id, []).extend(plans)
    _save_state(st)
    return {"success": True, "project_id": project_id, "plans": plans, "count": len(plans)}


def queue_pages(project_id: str, page_ids: list[str] | None = None) -> dict[str, Any]:
    st = _load_state()
    candidates = (st.get("candidates") or {}).get(project_id) or []
    if not candidates:
        scan_res = scan(project_id)
        if not scan_res.get("success"):
            return scan_res
        candidates = scan_res.get("candidates") or []

    settings = get_settings()
    max_pages = int(settings.get("max_pages_per_run", 25))
    if page_ids:
        candidates = [c for c in candidates if c.get("page_id") in page_ids]
    else:
        candidates = [c for c in candidates if c.get("refresh_needed")]
    candidates.sort(key=lambda c: c.get("refresh_priority", 0), reverse=True)
    candidates = candidates[:max_pages]

    queue = st.get("queue") or []
    existing = {(q.get("project_id"), q.get("page_id")) for q in queue if q.get("status") == "queued"}
    added = 0
    for cand in candidates:
        key = (project_id, cand["page_id"])
        if key in existing:
            continue
        plan = next(
            (p for p in (st.get("plans") or {}).get(project_id, []) if p.get("page_id") == cand["page_id"]),
            None,
        )
        actions = (plan or {}).get("actions") or _suggest_actions({}, cand, _entity_context(project_id))
        queue.append({
            "queue_id": f"crq-{uuid.uuid4().hex[:10]}",
            "project_id": project_id,
            "page_id": cand["page_id"],
            "priority": cand.get("priority_label", _priority_label(cand.get("refresh_priority", 0))),
            "actions": actions,
            "status": "queued",
            "created_at": _now(),
            "signals": {k: cand.get(k) for k in DEFAULT_SIGNALS if k in cand},
        })
        existing.add(key)
        added += 1
    st["queue"] = queue
    _save_state(st)
    return {"success": True, "queued": added, "queue_size": len(queue)}


def _inject_qie_blocks(page: dict[str, Any], actions: list[str], project: dict[str, Any]) -> str:
    """Question Intelligence Engine ile refresh blokları üret."""
    from app.moduller import question_intelligence_engine as qie
    keyword = page.get("keyword") or page.get("title", "")
    location = project.get("location") or "Kuşadası"
    payload = {
        "keyword": keyword,
        "location": location,
        "category": project.get("niche", "gece hayatı"),
        "push_entity_graph": False,
        "write_astro": False,
        "count": 2,
    }
    blocks: list[str] = []
    try:
        if "add_new_faq" in actions or "add_paa_questions" in actions:
            res = qie.generate_people_also_ask(payload) if "add_paa_questions" in actions else qie.generate_faq(payload)
            for item in (res.get("items") or [])[:1]:
                blocks.append(item.get("content_html", "")[:4000])
        if "add_autocomplete_blocks" in actions:
            res = qie.generate_autocomplete({**payload, "count": 3})
            for item in (res.get("items") or [])[:2]:
                blocks.append(f'<section class="autocomplete-intent"><h2>{item.get("title")}</h2>{item.get("answer_block", "")}</section>')
        if "expand_local_intent" in actions:
            res = qie.generate_local_intent(payload)
            for item in (res.get("items") or [])[:1]:
                blocks.append(item.get("content_html", "")[:2000])
        if any(a in actions for a in ("add_new_faq",)) and "add_paa_questions" not in actions:
            res = qie.generate_objections({**payload, "count": 2})
            for item in (res.get("items") or [])[:1]:
                blocks.append(item.get("content_html", "")[:1500])
    except Exception as exc:
        logger.warning("QIE block injection: %s", exc)
    return "\n".join(blocks)


def _inject_ai_overview(html: str, keyword: str, location: str) -> str:
    from app.moduller import question_intelligence_engine as qie
    try:
        res = qie.generate_ai_overview({"keyword": keyword, "location": location, "push_entity_graph": False})
        overview_html = (res.get("items") or [{}])[0].get("content_html", "")
        if overview_html:
            return f'{html}\n<section class="ai-overview-refresh">{overview_html}</section>'
    except Exception as exc:
        logger.warning("AI overview injection: %s", exc)
    short = f"<p><strong>{keyword}</strong> — {location} için güncel 2026 özet cevap.</p>"
    return f'{html}\n<div class="ai-overview-short">{short}</div>'


def _llm_refresh_content(page: dict[str, Any], actions: list[str]) -> tuple[str, str]:
    from app.moduller import llm_router
    html = page.get("content_html", "")
    title = page.get("title", "")
    keyword = page.get("keyword", "")
    action_text = ", ".join(actions)
    prompt = f"""Mevcut SEO sayfasını GÜNCELLE — içeriği silme, yapıyı koru.

Başlık: {title}
Anahtar kelime: {keyword}
Yapılacaklar: {action_text}

Kurallar:
- Eski istatistikleri 2026 verileriyle güncelle
- Eksik FAQ / answer block ekle
- Entity bölümlerini genişlet
- GEO kapsamını güçlendir
- AI Overview için ilk paragrafta doğrudan cevap ver
- HTML formatında döndür (h1 bir tane, h2/h3, p, ul)
- Mevcut anlamı koru, sadece zenginleştir

MEVCUT HTML:
{html[:12000]}
"""
    raw, engine = llm_router.generate(prompt, max_tokens=4000, min_length=200)
    if not raw or len(raw.strip()) < 100:
        updated = html
        if "add_faq" in actions:
            updated += f'\n<h2>{keyword} SSS</h2><p><strong>{keyword} nedir?</strong> {keyword} hakkında güncel 2026 rehber bilgisi.</p>'
        if "improve_answer_block" in actions:
            updated = f'<p><strong>{title}</strong> — {keyword} için güncel özet cevap (2026).</p>\n' + updated
        return updated, "rule_fallback"
    text = raw.strip()
    if not text.startswith("<"):
        text = f"<div>{text}</div>"
    return text, engine or "llm"


def _write_page(project_id: str, page: dict[str, Any], new_html: str) -> None:
    _, path = _project_path(project_id)
    data_dir = path / "src" / "data"
    ptype = page.get("type", "page")
    slug = (page.get("slug") or "").strip()
    updated_at = _now()

    if ptype == "home":
        fp = data_dir / "pages.json"
        data = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
        home = data.get("home") or {}
        home["content_html"] = new_html
        home["updated_at"] = updated_at
        data["home"] = home
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif ptype == "geo":
        fp = data_dir / "pages.json"
        data = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {"geo": []}
        geo = []
        for g in data.get("geo") or []:
            if (g.get("slug") or "") == slug:
                g = {**g, "content_html": new_html, "updated_at": updated_at}
            geo.append(g)
        data["geo"] = geo
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif ptype == "faq":
        fp = data_dir / "faqs.json"
        arr = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        out = []
        for item in arr:
            if (item.get("slug") or "") == slug:
                item = {**item, "content_html": new_html, "updated_at": updated_at}
            out.append(item)
        fp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    elif ptype == "blog":
        fp = data_dir / "blog.json"
        arr = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        out = []
        for item in arr:
            if (item.get("slug") or "") == slug:
                item = {**item, "content_html": new_html, "updated_at": updated_at}
            out.append(item)
        fp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    elif ptype == "entity":
        fp = data_dir / "entity_pages.json"
        arr = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        out = []
        for item in arr:
            if (item.get("slug") or "") == slug:
                item = {**item, "content_html": new_html, "updated_at": updated_at}
            out.append(item)
        fp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        fp = data_dir / "pages.json"
        data = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
        home = data.get("home") or {}
        if not slug:
            home["content_html"] = new_html
            home["updated_at"] = updated_at
            data["home"] = home
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _quality_check(page: dict[str, Any], new_html: str) -> dict[str, Any]:
    from app.moduller.seo_quality_gate import seo_quality_gate
    analysis = seo_quality_gate.analyze_page(
        new_html, page.get("keyword", ""), title=page.get("title", ""),
    )
    score = analysis.get("overall_score") or 0
    passed = bool(analysis.get("pass")) and score >= MIN_QUALITY_SCORE
    return {"passed": passed, "score": score, "analysis": analysis}


def _push_auto_publisher(project_id: str, page: dict[str, Any], new_html: str, quality_score: int) -> dict[str, Any]:
    from app.moduller.astro_auto_publisher import queue_missing
    item = {
        "source": "content_refresh_engine",
        "source_id": page.get("page_id", ""),
        "title": page.get("title", ""),
        "slug": page.get("slug", ""),
        "content": new_html,
        "type": page.get("type", "landing"),
        "target_keyword": page.get("keyword", ""),
        "updated_at": _now(),
        "quality_score": quality_score,
        "sync_status": "outdated",
    }
    return queue_missing(project_id, [item], include_outdated=False)


def _network_variant_queue(project_id: str, page_id: str) -> list[dict[str, Any]]:
    from app.moduller.network_replicator import list_networks
    queued: list[dict[str, Any]] = []
    for net in list_networks().get("networks") or []:
        domains = net.get("domains") or []
        if not any(d.get("project_id") == project_id for d in domains):
            continue
        nid = net.get("network_id", "")
        for d in domains:
            pid = d.get("project_id")
            if not pid or pid == project_id:
                continue
            scan_res = scan(pid)
            variant_page_ids = [c["page_id"] for c in (scan_res.get("candidates") or []) if c.get("type") == page_id.split(":")[0]]
            if not variant_page_ids and page_id:
                variant_page_ids = [page_id]
            res = queue_pages(pid, variant_page_ids or None)
            queued.append({"network_id": nid, "domain": d.get("domain"), "project_id": pid, **res})
    return queued


def _rank_snapshot(project_id: str, page: dict[str, Any]) -> dict[str, Any]:
    rank = _rank_context(project_id)
    kw_key = _resolve_rank_keyword(page, project_id, rank)
    kw = rank["keywords"].get(kw_key, {})
    return {
        "keyword": kw_key,
        "position": kw.get("last_position"),
        "decay_score": kw.get("ranking_decay_score", 0),
        "strength": kw.get("keyword_strength_score", 0),
        "trend": kw.get("trend_direction", "flat"),
    }


def _new_job_id() -> str:
    return f"cre-{uuid.uuid4().hex[:12]}"


def _start_job(job_type: str, project_id: str) -> dict[str, Any] | None:
    with _job_lock:
        st = _load_state()
        if st.get("running_job"):
            return None
        jid = _new_job_id()
        job = {
            "job_id": jid,
            "type": job_type,
            "project_id": project_id,
            "status": "running",
            "started_at": _now(),
            "finished_at": "",
            "summary": {
                "pages_scanned": 0,
                "pages_refreshed": 0,
                "quality_passed": 0,
                "quality_failed": 0,
                "deploy_count": 0,
                "avg_improvement_score": 0,
            },
            "items": [],
            "errors": [],
        }
        st["jobs"][jid] = job
        st["running_job"] = jid
        _save_state(st)
        return job


def _finish_job(job_id: str, status: str, **extra: Any) -> dict[str, Any]:
    with _job_lock:
        st = _load_state()
        job = st["jobs"].get(job_id, {})
        job["status"] = status
        job["finished_at"] = _now()
        job.update(extra)
        st["jobs"][job_id] = job
        st["running_job"] = ""
        _save_state(st)
        return job


def refresh_page(
    project_id: str,
    page_id: str,
    *,
    auto_publish: bool | None = None,
    auto_deploy: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if auto_publish is None:
        auto_publish = settings.get("auto_publish", False)
    if auto_deploy is None:
        auto_deploy = settings.get("auto_deploy", False)

    pages = _load_pages(project_id)
    page = next((p for p in pages if p["page_id"] == page_id), None)
    if not page:
        return {"success": False, "error": "Sayfa bulunamadı"}

    st = _load_state()
    qitem = next(
        (q for q in (st.get("queue") or []) if q.get("page_id") == page_id and q.get("project_id") == project_id),
        {},
    )
    project, _ = _project_path(project_id)
    entity = _entity_context(project_id)
    signals = compute_page_signals(page, project_id)
    link_analysis = _internal_link_analysis(project_id, page)
    geo_ops = _geo_opportunities(page, project)
    entity_gaps = _entity_refresh_gaps(project_id, page)
    actions = qitem.get("actions") or _suggest_actions(
        page, signals, entity, project_id=project_id,
        link_analysis=link_analysis, geo_ops=geo_ops, entity_gaps=entity_gaps,
    )
    before_rank = _rank_snapshot(project_id, page)
    before_gate = _quality_check(page, page.get("content_html", ""))

    new_html, engine = _llm_refresh_content(page, actions)
    qie_html = ""
    if any(a in actions for a in (
        "add_new_faq", "add_paa_questions", "add_autocomplete_blocks", "expand_local_intent",
    )):
        qie_html = _inject_qie_blocks(page, actions, project)
    if qie_html:
        new_html = f"{new_html}\n{qie_html}"
    if "add_ai_overview_block" in actions or "improve_answer_block" in actions:
        new_html = _inject_ai_overview(new_html, page.get("keyword", ""), project.get("location", ""))
    gate = _quality_check(page, new_html)
    if not gate["passed"]:
        return {
            "success": False,
            "error": f"Quality Gate fail — skor {gate['score']} < {MIN_QUALITY_SCORE}",
            "quality_gate": gate,
            "before": {"rank": before_rank, "quality": before_gate},
        }

    _write_page(project_id, page, new_html)
    publish_res: dict[str, Any] = {}
    build_res: dict[str, Any] = {}
    deploy_res: dict[str, Any] = {}

    if auto_publish:
        publish_res = _push_auto_publisher(project_id, page, new_html, gate["score"])
        from app.moduller.astro_auto_publisher import process_queue
        build_res = process_queue(
            project_id,
            auto_deploy=auto_deploy,
            auto_build=True,
            manage_job=False,
        )

    try:
        from app.moduller.entity_geo_graph import build_project_graph
        build_project_graph(project_id)
    except Exception as exc:
        logger.warning("Entity graph rebuild: %s", exc)

    network_queued = _network_variant_queue(project_id, page_id)
    after_rank = _rank_snapshot(project_id, page)
    after_gate = gate
    improvement = max(0, after_gate["score"] - before_gate["score"])

    st = _load_state()
    st["last_refresh_at"] = _now()
    for q in st.get("queue") or []:
        if q.get("page_id") == page_id and q.get("project_id") == project_id:
            q["status"] = "completed"
    _save_state(st)

    return {
        "success": True,
        "page_id": page_id,
        "engine": engine,
        "actions": actions,
        "quality_gate": gate,
        "comparison": {
            "before": {"rank": before_rank, "quality_score": before_gate["score"]},
            "after": {"rank": after_rank, "quality_score": after_gate["score"]},
            "improvement_score": improvement,
        },
        "auto_publisher": publish_res,
        "build": build_res,
        "deploy": deploy_res,
        "network_variants_queued": network_queued,
        "entity_refresh": entity_gaps,
        "geo_opportunities": geo_ops,
        "internal_links": link_analysis,
        "qie_integrated": bool(qie_html),
    }


def process_queue(
    project_id: str,
    *,
    auto_publish: bool | None = None,
    auto_deploy: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    job = _start_job("process", project_id)
    if not job:
        return {"success": False, "error": "Başka bir refresh job çalışıyor"}
    job_id = job["job_id"]

    st = _load_state()
    items = [
        q for q in (st.get("queue") or [])
        if q.get("project_id") == project_id and q.get("status") == "queued"
    ][: int(settings.get("max_pages_per_run", 25))]

    refreshed = quality_passed = quality_failed = 0
    improvements: list[int] = []
    processed: list[dict[str, Any]] = []

    for qitem in items:
        qitem["status"] = "processing"
        _save_state(st)
        res = refresh_page(
            project_id,
            qitem["page_id"],
            auto_publish=auto_publish if auto_publish is not None else settings.get("auto_publish"),
            auto_deploy=auto_deploy if auto_deploy is not None else settings.get("auto_deploy"),
        )
        if res.get("success"):
            refreshed += 1
            quality_passed += 1
            improvements.append(res.get("comparison", {}).get("improvement_score", 0))
            qitem["status"] = "completed"
        else:
            quality_failed += 1
            qitem["status"] = "failed"
            qitem["error"] = res.get("error", "")
        processed.append(res)

    avg_imp = int(sum(improvements) / max(len(improvements), 1)) if improvements else 0
    summary = {
        "pages_scanned": len(items),
        "pages_refreshed": refreshed,
        "quality_passed": quality_passed,
        "quality_failed": quality_failed,
        "deploy_count": 0,
        "avg_improvement_score": avg_imp,
    }
    job = _finish_job(job_id, "completed", summary=summary, items=processed)
    return {"success": True, "job_id": job_id, "summary": summary, "job": job}


def refresh_project(
    project_id: str,
    *,
    auto_publish: bool | None = None,
    auto_deploy: bool | None = None,
) -> dict[str, Any]:
    scan_res = scan(project_id)
    if not scan_res.get("success"):
        return scan_res
    create_refresh_plan(project_id)
    queue_pages(project_id)
    return process_queue(project_id, auto_publish=auto_publish, auto_deploy=auto_deploy)


def get_dashboard() -> dict[str, Any]:
    st = _load_state()
    all_cands: list[dict[str, Any]] = []
    for cands in (st.get("candidates") or {}).values():
        all_cands.extend(cands)
    critical = sum(1 for c in all_cands if c.get("priority_label") == "CRITICAL")
    high = sum(1 for c in all_cands if c.get("priority_label") == "HIGH")
    decay_vals = [c.get("ranking_decay_score", 0) for c in all_cands if c.get("ranking_decay_score")]
    ai_vals = [c.get("ai_visibility_loss_score", 0) for c in all_cands if c.get("ai_visibility_loss_score")]
    entity_vals = [c.get("entity_loss_score", 0) for c in all_cands if c.get("entity_loss_score")]
    auth_vals = [c.get("authority_drop_score", 0) for c in all_cands if c.get("authority_drop_score")]
    return {
        "critical_pages": critical,
        "high_priority_pages": high,
        "high_priority": high,
        "avg_decay": int(sum(decay_vals) / max(len(decay_vals), 1)) if decay_vals else 0,
        "avg_ai_visibility_loss": int(sum(ai_vals) / max(len(ai_vals), 1)) if ai_vals else 0,
        "avg_entity_loss": int(sum(entity_vals) / max(len(entity_vals), 1)) if entity_vals else 0,
        "avg_authority_drop": int(sum(auth_vals) / max(len(auth_vals), 1)) if auth_vals else 0,
        "last_refresh_at": st.get("last_refresh_at", ""),
        "queue_size": len([q for q in (st.get("queue") or []) if q.get("status") == "queued"]),
        "engine_version": "v1",
    }


def export_report(project_id: str = "", job_id: str = "") -> dict[str, Any]:
    st = _load_state()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if job_id:
        job = (st.get("jobs") or {}).get(job_id)
        if not job:
            return {"success": False, "error": "Job bulunamadı"}
        path = REPORTS_DIR / f"content-refresh-job-{job_id}.json"
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "path": str(path), "job_id": job_id}
    payload = {
        "exported_at": _now(),
        "settings": get_settings(),
        "dashboard": get_dashboard(),
        "candidates": st.get("candidates", {}).get(project_id, []) if project_id else st.get("candidates"),
        "queue": st.get("queue") or [],
        "jobs": list((st.get("jobs") or {}).values())[-20:],
    }
    suffix = project_id or "all"
    path = REPORTS_DIR / f"content-refresh-{suffix}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path)}


def list_jobs(limit: int = 20) -> dict[str, Any]:
    jobs = list((_load_state().get("jobs") or {}).values())
    jobs.sort(key=lambda j: j.get("started_at", ""), reverse=True)
    return {"success": True, "jobs": jobs[:limit]}


def get_job_detail(job_id: str) -> dict[str, Any]:
    job = (_load_state().get("jobs") or {}).get(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    return {"success": True, "job": job}


def get_queue() -> dict[str, Any]:
    q = _load_state().get("queue") or []
    return {"success": True, "queue": q, "count": len(q)}


def health() -> dict[str, Any]:
    st = _load_state()
    return {
        "success": True,
        "module": "content_refresh_engine",
        "engine_version": "v1",
        "running_job": st.get("running_job", ""),
        "settings": get_settings(),
        "dashboard": get_dashboard(),
        "last_scan_at": st.get("last_scan_at", ""),
        "last_refresh_at": st.get("last_refresh_at", ""),
    }


content_refresh_engine = type("ContentRefreshEngine", (), {
    "health": staticmethod(health),
    "get_settings": staticmethod(get_settings),
    "update_settings": staticmethod(update_settings),
    "scan": staticmethod(scan),
    "analyze_page": staticmethod(analyze_page),
    "analyze_project": staticmethod(analyze_project),
    "create_refresh_plan": staticmethod(create_refresh_plan),
    "queue_pages": staticmethod(queue_pages),
    "process_queue": staticmethod(process_queue),
    "refresh_page": staticmethod(refresh_page),
    "refresh_project": staticmethod(refresh_project),
    "export_report": staticmethod(export_report),
    "list_jobs": staticmethod(list_jobs),
    "get_job_detail": staticmethod(get_job_detail),
    "get_queue": staticmethod(get_queue),
    "get_dashboard": staticmethod(get_dashboard),
    "compute_page_signals": staticmethod(compute_page_signals),
})()
