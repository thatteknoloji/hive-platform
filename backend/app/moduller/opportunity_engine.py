"""Opportunity Engine V1 — trafik fırsatı keşfi (orkestrasyon katmanı)."""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.opportunity")

STATE_FILE = Path(__file__).resolve().parent.parent / "opportunity_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

MAX_STORED = 500

OPPORTUNITY_TYPES = {
    "keyword", "entity", "faq", "geo", "publisher", "authority",
    "cluster", "ai_overview", "local", "trend",
}

ACTION_TYPES = [
    "new_faq",
    "new_entity",
    "new_geo_page",
    "new_astro_site",
    "new_publisher_dispatch",
    "new_cluster",
    "new_support_site",
]

DEFAULT_STATE: dict[str, Any] = {
    "settings": {
        "quick_win_threshold": 72,
        "high_impact_threshold": 80,
        "low_competition_max_difficulty": 45,
    },
    "analyses": {},
    "plans": [],
}


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", DEFAULT_STATE["settings"])
                data.setdefault("analyses", {})
                data.setdefault("plans", [])
                return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("opportunity state load failed: %s", exc)
    return json.loads(json.dumps(DEFAULT_STATE))


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _score_opportunity(
    *,
    traffic: float = 50,
    difficulty: float = 50,
    authority_req: float = 40,
    gain: float = 50,
    effort: float = 50,
) -> dict[str, float]:
    traffic_score = _clamp(traffic)
    difficulty_score = _clamp(difficulty)
    authority_requirement = _clamp(authority_req)
    estimated_gain = _clamp(gain)
    implementation_effort = _clamp(effort)
    opportunity_score = _clamp(
        (traffic_score * 0.30)
        + ((100 - difficulty_score) * 0.25)
        + (estimated_gain * 0.25)
        + ((100 - implementation_effort) * 0.12)
        + ((100 - authority_requirement) * 0.08)
    )
    return {
        "traffic_score": round(traffic_score, 1),
        "difficulty_score": round(difficulty_score, 1),
        "authority_requirement": round(authority_requirement, 1),
        "estimated_gain": round(estimated_gain, 1),
        "implementation_effort": round(implementation_effort, 1),
        "opportunity_score": round(opportunity_score, 1),
    }


def _action_plan(opp_type: str, item: dict[str, Any]) -> list[str]:
    plans: list[str] = []
    subtype = item.get("subtype") or item.get("type") or opp_type
    if opp_type in ("keyword", "trend") or subtype in ("quick_win", "near_win", "low_competition"):
        plans.append("new_faq")
        plans.append("new_cluster")
    if opp_type == "entity" or subtype.startswith("missing_"):
        plans.append("new_entity")
    if opp_type == "geo" or subtype in ("missing_geo", "geo_expand"):
        plans.append("new_geo_page")
    if opp_type == "faq":
        plans.append("new_faq")
    if opp_type == "authority" or subtype in ("missing_role", "no_content", "fill_gap"):
        plans.append("new_support_site")
        plans.append("new_astro_site")
    if opp_type == "publisher":
        plans.append("new_publisher_dispatch")
    if opp_type == "ai_overview" or subtype == "ai_gap":
        plans.append("new_faq")
        plans.append("new_entity")
    if opp_type == "cluster":
        plans.append("new_cluster")
    if not plans:
        plans.append("new_geo_page")
    return list(dict.fromkeys(plans))


def _make_opp(
    opp_type: str,
    title: str,
    *,
    source: str,
    project_id: str = "",
    domain: str = "",
    keyword: str = "",
    entity: str = "",
    subtype: str = "",
    reason: str = "",
    scores: dict[str, float] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_scores = scores or _score_opportunity()
    item = {
        "id": f"opp-{uuid.uuid4().hex[:10]}",
        "type": opp_type,
        "subtype": subtype,
        "title": title,
        "source": source,
        "project_id": project_id,
        "domain": domain,
        "keyword": keyword,
        "entity": entity,
        "reason": reason,
        **base_scores,
        "action_plan": _action_plan(opp_type, {"type": subtype or opp_type}),
        "metadata": metadata or {},
    }
    return item


def _integration_status() -> dict[str, Any]:
    status: dict[str, Any] = {"ready": True, "sources": {}, "errors": []}

    def _probe(name: str, fn) -> None:
        try:
            res = fn()
            ok = res.get("success") is not False
            status["sources"][name] = {"ok": ok, "detail": res}
            if not ok and res.get("error"):
                status["errors"].append(f"{name}: {res.get('error')}")
        except Exception as exc:
            status["sources"][name] = {"ok": False, "error": str(exc)}
            status["errors"].append(f"{name}: {exc}")
            status["ready"] = False

    from app.moduller.rank_index_watcher import rank_index_watcher
    from app.moduller.entity_geo_graph import entity_geo_graph
    from app.moduller.question_intelligence_engine import question_intelligence_engine
    from app.moduller.support_network_engine import health as sne_health
    from app.moduller.publisher_hub import health as pub_health
    from app.moduller.hive_brain_engine import hive_brain

    _probe("rank_index_watcher", rank_index_watcher.health)
    _probe("entity_geo_graph", entity_geo_graph.health)
    _probe("question_intelligence_engine", question_intelligence_engine.health)
    _probe("support_network_engine", sne_health)
    _probe("publisher_hub", pub_health)
    _probe("hive_brain", hive_brain.health)

    return status


def health() -> dict[str, Any]:
    integrations = _integration_status()
    state = _load_state()
    return {
        "success": True,
        "module": "opportunity_engine",
        "integrations": integrations["sources"],
        "integration_errors": integrations["errors"],
        "ready": integrations["ready"],
        "analyses_count": len(state.get("analyses") or {}),
        "plans_count": len(state.get("plans") or []),
    }


def dashboard(project_id: str = "") -> dict[str, Any]:
    state = _load_state()
    key = f"project:{project_id}" if project_id else "latest"
    analysis = (state.get("analyses") or {}).get(key) or {}
    opps = analysis.get("opportunities") or []
    by_type: dict[str, int] = defaultdict(int)
    for o in opps:
        by_type[o.get("type") or "unknown"] += 1
    quick = [o for o in opps if o.get("opportunity_score", 0) >= state["settings"].get("quick_win_threshold", 72)]
    top = sorted(opps, key=lambda x: -x.get("opportunity_score", 0))[:10]
    try:
        from app.moduller.revenue_lead_engine import apply_commercial_scores_to_opportunities
        top = apply_commercial_scores_to_opportunities(top)
    except Exception:
        pass
    try:
        from app.moduller.citation_engine import apply_citation_scores_to_opportunities
        top = apply_citation_scores_to_opportunities(top)
    except Exception:
        pass
    return {
        "success": True,
        "project_id": project_id,
        "total_opportunities": len(opps),
        "by_type": dict(by_type),
        "quick_wins": len(quick),
        "last_analysis_at": analysis.get("at"),
        "top_opportunities": top,
        "integrations": _integration_status()["sources"],
    }


def _collect_keyword_opportunities(project_id: str) -> tuple[list[dict], list[str]]:
    from app.moduller.rank_index_watcher import rank_index_watcher

    errors: list[str] = []
    out: list[dict] = []
    proj = rank_index_watcher.get_project(project_id)
    if not proj.get("success") and not proj.get("project"):
        return [], [f"Rank Watcher: proje bulunamadı ({project_id})"]

    project = proj.get("project") or proj
    finder = rank_index_watcher.opportunity_finder(project_id)
    if not finder.get("success"):
        errors.append(finder.get("error") or "Rank Watcher opportunity_finder başarısız")
    else:
        for row in finder.get("opportunities") or []:
            pos = row.get("position") or 20
            priority = row.get("priority") or "medium"
            traffic = 70 if priority == "high" else 55
            difficulty = _clamp(15 + (pos * 2.5))
            gain = _clamp(90 - pos * 3)
            scores = _score_opportunity(traffic=traffic, difficulty=difficulty, gain=gain, effort=35)
            subtype = "quick_win" if pos <= 10 else "near_win" if pos <= 20 else "low_competition"
            out.append(_make_opp(
                "keyword",
                f"Keyword: {row.get('keyword')}",
                source="rank_index_watcher",
                project_id=project_id,
                keyword=row.get("keyword") or "",
                subtype=subtype,
                reason=f"Pozisyon {pos}, CTR {row.get('ctr', 0)}",
                scores=scores,
                metadata=row,
            ))

    for kw in (project.get("keywords") or [])[:40]:
        pos = kw.get("last_position")
        if pos is None:
            continue
        strength = kw.get("keyword_strength_score") or 50
        if pos > 20 and strength >= 40:
            scores = _score_opportunity(traffic=45, difficulty=30, gain=55, effort=40)
            out.append(_make_opp(
                "keyword",
                f"Düşük rekabet adayı: {kw.get('keyword')}",
                source="rank_index_watcher",
                project_id=project_id,
                keyword=kw.get("keyword") or "",
                subtype="low_competition",
                reason=f"Sıra {pos}, strength {strength}",
                scores=scores,
                metadata=kw,
            ))
        elif 11 <= pos <= 20:
            scores = _score_opportunity(traffic=60, difficulty=40, gain=65, effort=35)
            out.append(_make_opp(
                "keyword",
                f"Yakın fırsat: {kw.get('keyword')}",
                source="rank_index_watcher",
                project_id=project_id,
                keyword=kw.get("keyword") or "",
                subtype="near_win",
                reason=f"Sıra {pos} — hızlı kazanılabilir",
                scores=scores,
                metadata=kw,
            ))

    return out, errors


def _collect_entity_opportunities(project_id: str, location: str = "", seed_keyword: str = "") -> tuple[list[dict], list[str]]:
    from app.moduller.entity_geo_graph import entity_geo_graph

    errors: list[str] = []
    out: list[dict] = []
    res = entity_geo_graph.missing_entities(project_id=project_id, location=location, seed_keyword=seed_keyword)
    if res.get("error"):
        errors.append(res.get("error"))
    for m in res.get("missing_entities") or []:
        name = m.get("entity") or m.get("name") or "?"
        etype = m.get("type") or "entity"
        scores = _score_opportunity(traffic=55, difficulty=35, authority_req=30, gain=60, effort=45)
        out.append(_make_opp(
            "entity",
            f"Eksik entity: {name}",
            source="entity_geo_graph",
            project_id=project_id,
            entity=name,
            subtype=f"missing_{etype}",
            reason=m.get("source") or "entity graph gap",
            scores=scores,
            metadata=m,
        ))
    return out, errors


def _collect_geo_opportunities(project_id: str, location: str = "", seed_keyword: str = "") -> tuple[list[dict], list[str]]:
    from app.moduller.entity_geo_graph import entity_geo_graph

    errors: list[str] = []
    out: list[dict] = []
    loc = location or "Kuşadası"
    res = entity_geo_graph.geo_expand(location=loc, seed_keyword=seed_keyword, radius_km=25)
    for w in res.get("warnings") or []:
        errors.append(str(w))
    for page in res.get("suggested_geo_pages") or []:
        title = page.get("title") or page.get("slug") or page.get("location") or "GEO sayfa"
        scores = _score_opportunity(traffic=50, difficulty=38, gain=58, effort=42)
        out.append(_make_opp(
            "geo",
            f"GEO fırsat: {title}",
            source="entity_geo_graph",
            project_id=project_id,
            keyword=seed_keyword,
            subtype="geo_expand",
            reason=page.get("reason") or f"Lokasyon: {loc}",
            scores=scores,
            metadata=page,
        ))
    for ent in res.get("geo_entities") or []:
        name = ent.get("name") or ""
        etype = ent.get("type") or "area"
        if not name:
            continue
        scores = _score_opportunity(traffic=48, difficulty=32, gain=52, effort=40)
        out.append(_make_opp(
            "geo",
            f"Eksik {etype}: {name}",
            source="entity_geo_graph",
            project_id=project_id,
            entity=name,
            subtype=f"missing_{etype}",
            reason="geo_expand",
            scores=scores,
            metadata=ent,
        ))
    return out, errors


def _collect_faq_opportunities(project_id: str = "") -> tuple[list[dict], list[str]]:
    from app.moduller.question_intelligence_engine import question_intelligence_engine

    errors: list[str] = []
    out: list[dict] = []
    jobs_res = question_intelligence_engine.list_jobs(limit=40)
    if not jobs_res.get("success") and jobs_res.get("error"):
        errors.append(jobs_res.get("error"))
    for job in jobs_res.get("jobs") or []:
        if project_id and job.get("project_id") and job.get("project_id") != project_id:
            continue
        detail = question_intelligence_engine.get_job_detail(job.get("job_id") or job.get("id") or "")
        items = (detail.get("job") or detail).get("items") or job.get("items") or []
        for it in items:
            paa_gap = float(it.get("paa_gap_score") or 0)
            faq_cov = float(it.get("faq_coverage_score") or 100)
            if not it.get("refresh_candidate") and paa_gap < 15 and faq_cov > 80:
                continue
            kw = it.get("keyword") or job.get("keyword") or ""
            subtype = "missing_paa" if paa_gap >= 20 else "missing_faq"
            if it.get("intent_gap"):
                subtype = "missing_intent"
            scores = _score_opportunity(
                traffic=58,
                difficulty=28,
                gain=min(85, 40 + paa_gap),
                effort=30,
            )
            out.append(_make_opp(
                "faq",
                f"FAQ/PAA açığı: {kw or it.get('question', '')[:50]}",
                source="question_intelligence_engine",
                project_id=project_id or job.get("project_id") or "",
                keyword=kw,
                subtype=subtype,
                reason=f"PAA gap {paa_gap}, FAQ coverage {faq_cov}",
                scores=scores,
                metadata=it,
            ))
    if not out and not jobs_res.get("jobs"):
        errors.append("Question Intelligence: job verisi yok — önce QIE ile analiz çalıştırın")
    return out, errors


def _collect_authority_opportunities(network_id: str = "") -> tuple[list[dict], list[str]]:
    from app.moduller.support_network_engine import growth_opportunities, network_gaps, authority_map

    errors: list[str] = []
    out: list[dict] = []
    gaps = network_gaps(network_id)
    if not gaps.get("success"):
        errors.append(gaps.get("error") or "Support Network gaps alınamadı")
    for g in gaps.get("gaps") or []:
        scores = _score_opportunity(traffic=45, difficulty=42, authority_req=55, gain=50, effort=55)
        out.append(_make_opp(
            "authority",
            g.get("label") or g.get("item") or g.get("type"),
            source="support_network_engine",
            domain=g.get("domain") or "",
            subtype=g.get("type") or "network_gap",
            reason="Support Network gap analizi",
            scores=scores,
            metadata=g,
        ))
    growth = growth_opportunities(network_id)
    for row in growth.get("opportunities") or []:
        scores = _score_opportunity(traffic=50, difficulty=38, authority_req=48, gain=62, effort=50)
        out.append(_make_opp(
            "authority",
            f"Authority: {row.get('domain') or row.get('item') or row.get('type')}",
            source="support_network_engine",
            domain=row.get("domain") or "",
            subtype=row.get("type") or "growth",
            reason=row.get("reason") or "",
            scores=scores,
            metadata=row,
        ))
    auth = authority_map(network_id)
    for d in (auth.get("no_content") or [])[:15]:
        scores = _score_opportunity(traffic=40, difficulty=35, authority_req=60, gain=55, effort=48)
        out.append(_make_opp(
            "authority",
            f"İçerik açığı: {d.get('domain')}",
            source="support_network_engine",
            domain=d.get("domain") or "",
            subtype="no_content",
            reason="Authority map — no_content",
            scores=scores,
            metadata=d,
        ))
    return out, errors


def _collect_publisher_opportunities() -> tuple[list[dict], list[str]]:
    from app.moduller.publisher_hub import scan_sources, get_queue, get_published

    errors: list[str] = []
    out: list[dict] = []
    scanned = scan_sources()
    if not scanned.get("success"):
        errors.append(scanned.get("error") or "Publisher Hub scan başarısız")
    in_pipeline = set()
    for bucket in (get_queue().get("queue") or [], get_published().get("published") or []):
        for x in bucket:
            in_pipeline.add(f"{x.get('source')}:{x.get('source_id')}")
    for it in scanned.get("items") or []:
        key = f"{it.get('source')}:{it.get('source_id')}"
        if key in in_pipeline:
            continue
        scores = _score_opportunity(traffic=52, difficulty=25, gain=48, effort=20)
        out.append(_make_opp(
            "publisher",
            f"Yayınlanmamış: {it.get('title') or key}",
            source="publisher_hub",
            subtype="unpublished_content",
            reason=f"Kaynak: {it.get('source')}",
            scores=scores,
            metadata=it,
        ))
    return out, errors


def _collect_ai_opportunities(project_id: str) -> tuple[list[dict], list[str]]:
    from app.moduller.serp_defense_engine import defense_opportunities, fortress_list
    from app.moduller.rank_index_watcher import rank_index_watcher

    errors: list[str] = []
    out: list[dict] = []
    defs = defense_opportunities(project_id)
    for row in defs.get("opportunities") or []:
        scores = _score_opportunity(
            traffic=62,
            difficulty=45,
            authority_req=50,
            gain=68,
            effort=38,
        )
        out.append(_make_opp(
            "ai_overview",
            f"AI/SERP savunma: {row.get('keyword')}",
            source="serp_defense_engine",
            project_id=project_id,
            keyword=row.get("keyword") or "",
            subtype="ai_gap",
            reason=row.get("top_action") or f"Fortress {row.get('fortress_score')}",
            scores=scores,
            metadata=row,
        ))
    fl = fortress_list(project_id)
    for r in (fl.get("fortresses") or [])[:20]:
        faq = r.get("faq_defense") or {}
        if faq.get("gap_score", 0) > 15:
            scores = _score_opportunity(traffic=55, difficulty=40, gain=60, effort=35)
            out.append(_make_opp(
                "ai_overview",
                f"Answer block eksik: {r.get('keyword')}",
                source="serp_defense_engine",
                project_id=project_id,
                keyword=r.get("keyword") or "",
                subtype="answer_block_gap",
                reason="FAQ defense gap",
                scores=scores,
                metadata=faq,
            ))

    proj = rank_index_watcher.get_project(project_id)
    project = proj.get("project") or {}
    for kw in (project.get("keywords") or [])[:5]:
        keyword = kw.get("keyword") or ""
        if not keyword:
            continue
        try:
            ai = rank_index_watcher.ai_overview(keyword)
            if ai.get("ai_overview_present") and not ai.get("cited"):
                scores = _score_opportunity(traffic=65, difficulty=42, gain=70, effort=40)
                out.append(_make_opp(
                    "ai_overview",
                    f"Citation fırsatı: {keyword}",
                    source="rank_index_watcher",
                    project_id=project_id,
                    keyword=keyword,
                    subtype="citation_gap",
                    reason="AI Overview var, citation yok",
                    scores=scores,
                    metadata=ai,
                ))
        except Exception as exc:
            errors.append(f"AI overview ({keyword}): {exc}")
    return out, errors


def _collect_cluster_opportunities(project_id: str) -> tuple[list[dict], list[str]]:
    from app.moduller.entity_geo_graph import entity_geo_graph

    errors: list[str] = []
    out: list[dict] = []
    try:
        clusters = entity_geo_graph.topic_clusters(project_id)
    except Exception as exc:
        return [], [f"Entity GEO Graph clusters: {exc}"]
    if clusters.get("error"):
        errors.append(clusters.get("error"))
    for cg in clusters.get("cluster_groups") or []:
        name = cg.get("name") or cg.get("pillar") or "cluster"
        scores = _score_opportunity(traffic=54, difficulty=36, gain=57, effort=44)
        out.append(_make_opp(
            "cluster",
            f"Cluster fırsat: {name}",
            source="entity_geo_graph",
            project_id=project_id,
            subtype="topic_cluster",
            reason=f"Authority {cg.get('authority_score', '—')}",
            scores=scores,
            metadata=cg,
        ))
    return out, errors


def _collect_brain_hints(project_id: str) -> tuple[list[dict], list[str]]:
    from app.moduller.hive_brain_engine import hive_brain

    errors: list[str] = []
    out: list[dict] = []
    mem = hive_brain.get_project_memory(project_id)
    if not mem.get("success"):
        return [], [mem.get("error") or "Brain memory yok"]
    for rec in (mem.get("memory") or {}).get("next_recommended_actions") or []:
        scores = _score_opportunity(traffic=50, difficulty=40, gain=55, effort=35)
        out.append(_make_opp(
            "trend",
            rec[:120],
            source="hive_brain_engine",
            project_id=project_id,
            subtype="brain_recommendation",
            reason="HIVE Brain önerisi",
            scores=scores,
            metadata={"recommendation": rec},
        ))
    return out, errors


def _collect_citation_opportunities(project_id: str) -> tuple[list[dict], list[str]]:
    try:
        from app.moduller.citation_engine import collect_citation_opportunities
        return collect_citation_opportunities(project_id)
    except Exception as exc:
        return [], [f"citation_engine: {exc}"]


def analyze_project(
    project_id: str,
    *,
    network_id: str = "",
    location: str = "",
    seed_keyword: str = "",
) -> dict[str, Any]:
    if not (project_id or "").strip():
        return {"success": False, "error": "project_id gerekli"}

    pid = project_id.strip()
    all_opps: list[dict] = []
    all_errors: list[str] = []

    collectors = [
        lambda: _collect_keyword_opportunities(pid),
        lambda: _collect_entity_opportunities(pid, location, seed_keyword),
        lambda: _collect_geo_opportunities(pid, location, seed_keyword),
        lambda: _collect_faq_opportunities(pid),
        lambda: _collect_authority_opportunities(network_id),
        lambda: _collect_publisher_opportunities(),
        lambda: _collect_ai_opportunities(pid),
        lambda: _collect_cluster_opportunities(pid),
        lambda: _collect_brain_hints(pid),
        lambda: _collect_citation_opportunities(pid),
    ]
    for fn in collectors:
        opps, errs = fn()
        all_opps.extend(opps)
        all_errors.extend(errs)

    if not all_opps and all_errors:
        return {
            "success": False,
            "error": "provider_missing",
            "mesaj": "; ".join(all_errors[:5]),
            "errors": all_errors,
            "project_id": pid,
        }

    all_opps.sort(key=lambda x: -x.get("opportunity_score", 0))
    state = _load_state()
    analysis = {
        "at": _now(),
        "project_id": pid,
        "network_id": network_id,
        "opportunity_count": len(all_opps),
        "opportunities": all_opps[:MAX_STORED],
        "errors": all_errors,
        "by_type": dict(defaultdict(int, {o["type"]: 0 for o in all_opps})),
    }
    for o in all_opps:
        analysis["by_type"][o["type"]] = analysis["by_type"].get(o["type"], 0) + 1

    state.setdefault("analyses", {})[f"project:{pid}"] = analysis
    state["analyses"]["latest"] = analysis
    _save_state(state)

    return {
        "success": True,
        "project_id": pid,
        "opportunity_count": len(all_opps),
        "by_type": analysis["by_type"],
        "errors": all_errors,
        "opportunities": all_opps[:100],
        "quick_wins": [o for o in all_opps if o.get("opportunity_score", 0) >= state["settings"].get("quick_win_threshold", 72)][:20],
    }


def analyze_domain(domain: str, *, network_id: str = "") -> dict[str, Any]:
    dom = (domain or "").strip().lower().replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
    if not dom:
        return {"success": False, "error": "domain gerekli"}

    all_opps, all_errors = _collect_authority_opportunities(network_id)
    pub_opps, pub_errs = _collect_publisher_opportunities()
    all_opps.extend(pub_opps)
    all_errors.extend(pub_errs)
    all_opps = [o for o in all_opps if dom in (o.get("domain") or "").lower()] or all_opps[:30]

    if not all_opps:
        return {
            "success": False,
            "error": "no_opportunities",
            "mesaj": f"{dom} için fırsat bulunamadı",
            "errors": all_errors,
            "domain": dom,
        }

    state = _load_state()
    state.setdefault("analyses", {})[f"domain:{dom}"] = {
        "at": _now(),
        "domain": dom,
        "opportunities": all_opps,
        "errors": all_errors,
    }
    _save_state(state)
    return {"success": True, "domain": dom, "opportunities": all_opps, "errors": all_errors}


def _get_cached_opportunities(project_id: str = "", opp_type: str = "") -> list[dict]:
    state = _load_state()
    key = f"project:{project_id}" if project_id else "latest"
    analysis = (state.get("analyses") or {}).get(key) or (state.get("analyses") or {}).get("latest") or {}
    opps = analysis.get("opportunities") or []
    if opp_type:
        opps = [o for o in opps if o.get("type") == opp_type]
    return opps


def list_keywords(project_id: str = "") -> dict[str, Any]:
    opps = _get_cached_opportunities(project_id, "keyword")
    if not opps and project_id:
        res = analyze_project(project_id)
        if not res.get("success"):
            return res
        opps = [o for o in (res.get("opportunities") or []) if o.get("type") == "keyword"]
    return {"success": True, "count": len(opps), "opportunities": opps}


def list_entities(project_id: str = "") -> dict[str, Any]:
    opps = _get_cached_opportunities(project_id, "entity")
    if not opps and project_id:
        opps, _ = _collect_entity_opportunities(project_id)
    return {"success": True, "count": len(opps), "opportunities": opps}


def list_geo(project_id: str = "", location: str = "") -> dict[str, Any]:
    opps = _get_cached_opportunities(project_id, "geo")
    if not opps and project_id:
        opps, errs = _collect_geo_opportunities(project_id, location)
        if not opps and errs:
            return {"success": False, "error": "provider_missing", "mesaj": "; ".join(errs[:3])}
    return {"success": True, "count": len(opps), "opportunities": opps}


def list_authority(network_id: str = "") -> dict[str, Any]:
    opps, errs = _collect_authority_opportunities(network_id)
    if not opps and errs:
        return {"success": False, "error": "provider_missing", "mesaj": "; ".join(errs[:3])}
    return {"success": True, "count": len(opps), "opportunities": opps, "errors": errs}


def list_ai(project_id: str = "") -> dict[str, Any]:
    opps = _get_cached_opportunities(project_id, "ai_overview")
    if not opps and project_id:
        opps, errs = _collect_ai_opportunities(project_id)
        if not opps and errs:
            return {"success": False, "error": "provider_missing", "mesaj": "; ".join(errs[:3])}
    return {"success": True, "count": len(opps), "opportunities": opps}


def quick_wins(project_id: str = "") -> dict[str, Any]:
    state = _load_state()
    threshold = state["settings"].get("quick_win_threshold", 72)
    low_diff = state["settings"].get("low_competition_max_difficulty", 45)
    opps = _get_cached_opportunities(project_id)
    if not opps and project_id:
        res = analyze_project(project_id)
        if not res.get("success"):
            return res
        opps = res.get("opportunities") or []
    quick = [o for o in opps if o.get("opportunity_score", 0) >= threshold]
    low_comp = [o for o in opps if o.get("difficulty_score", 100) <= low_diff]
    high_impact = [o for o in opps if o.get("estimated_gain", 0) >= state["settings"].get("high_impact_threshold", 80)]
    return {
        "success": True,
        "quick_wins": sorted(quick, key=lambda x: -x.get("opportunity_score", 0))[:30],
        "low_competition": sorted(low_comp, key=lambda x: -x.get("opportunity_score", 0))[:30],
        "high_impact": sorted(high_impact, key=lambda x: -x.get("estimated_gain", 0))[:30],
        "counts": {
            "quick_wins": len(quick),
            "low_competition": len(low_comp),
            "high_impact": len(high_impact),
        },
    }


def generate_one_click_plan(project_id: str = "", network_id: str = "") -> dict[str, Any]:
    """Sadece plan üret — otomatik uygulama yok."""
    if not project_id:
        return {"success": False, "error": "project_id gerekli"}
    analysis = analyze_project(project_id, network_id=network_id)
    if not analysis.get("success"):
        return analysis

    opps = analysis.get("opportunities") or []
    actions: dict[str, list] = defaultdict(list)
    for o in opps[:40]:
        for act in o.get("action_plan") or []:
            actions[act].append({
                "opportunity_id": o.get("id"),
                "title": o.get("title"),
                "score": o.get("opportunity_score"),
                "keyword": o.get("keyword"),
                "entity": o.get("entity"),
            })

    plan = {
        "plan_id": f"plan-{uuid.uuid4().hex[:10]}",
        "created_at": _now(),
        "project_id": project_id,
        "network_id": network_id,
        "total_opportunities": len(opps),
        "action_groups": dict(actions),
        "priority_order": sorted(
            [{"action": k, "count": len(v), "top_score": max(x["score"] for x in v)} for k, v in actions.items()],
            key=lambda x: -x["top_score"],
        ),
        "note": "Plan only — otomatik uygulama yapılmadı",
    }
    state = _load_state()
    state.setdefault("plans", []).insert(0, plan)
    state["plans"] = state["plans"][:50]
    _save_state(state)

    try:
        from app.moduller.hive_brain_engine import hive_brain
        hive_brain.record_decision(
            "opportunity_engine",
            f"One-click plan: {len(opps)} fırsat, {len(actions)} aksiyon grubu",
            reason="Opportunity Engine plan üretimi",
            project_id=project_id,
            applied=False,
            outcome="plan_generated",
            metadata={"plan_id": plan["plan_id"]},
        )
    except Exception:
        pass

    return {"success": True, "plan": plan}


def export_report(project_id: str = "", report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "exported_at": _now(),
        "report_type": report_type,
        "health": health(),
    }
    if project_id:
        payload["analysis"] = analyze_project(project_id) if report_type == "full" else {
            "opportunities": _get_cached_opportunities(project_id),
        }
        payload["quick_wins"] = quick_wins(project_id)
    else:
        payload["dashboard"] = dashboard()

    generators = {
        "keywords": lambda: list_keywords(project_id),
        "entities": lambda: list_entities(project_id),
        "geo": lambda: list_geo(project_id),
        "authority": lambda: list_authority(),
        "ai": lambda: list_ai(project_id),
        "quickwins": lambda: quick_wins(project_id),
    }
    if report_type in generators:
        payload["section"] = generators[report_type]()

    safe = (project_id or "global").replace("/", "_")
    path = REPORTS_DIR / f"opportunity-{report_type}-{safe}-{_now().replace(' ', '_').replace(':', '-')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path), "report_type": report_type}


def get_settings() -> dict[str, Any]:
    return _load_state().get("settings") or DEFAULT_STATE["settings"]


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    settings = state.setdefault("settings", {})
    for k, v in (patch or {}).items():
        if k in DEFAULT_STATE["settings"]:
            settings[k] = v
    _save_state(state)
    return settings


opportunity_engine = type("OpportunityEngine", (), {
    "health": staticmethod(health),
    "dashboard": staticmethod(dashboard),
    "analyze_project": staticmethod(analyze_project),
    "analyze_domain": staticmethod(analyze_domain),
    "list_keywords": staticmethod(list_keywords),
    "list_entities": staticmethod(list_entities),
    "list_geo": staticmethod(list_geo),
    "list_authority": staticmethod(list_authority),
    "list_ai": staticmethod(list_ai),
    "quick_wins": staticmethod(quick_wins),
    "generate_one_click_plan": staticmethod(generate_one_click_plan),
    "export_report": staticmethod(export_report),
    "get_settings": staticmethod(get_settings),
    "update_settings": staticmethod(update_settings),
})()
