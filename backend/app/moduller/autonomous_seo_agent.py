"""
Autonomous SEO Agent V1 — merkezi karar katmanı.

Mevcut modüllerin çıktılarını okur; içerik üretmez. Defense, Growth, Content,
Authority, Publisher ve Memory ajanları ile aksiyon kararı verir.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.autonomous_seo_agent")

STATE_FILE = Path(__file__).resolve().parent.parent / "autonomous_seo_agent_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 500
DECISION_LIMIT = 500
MISSION_LIMIT = 100

AGENT_TYPES = ("defense", "growth", "content", "authority", "publisher", "memory")
ACTION_MODES = ("plan_only", "semi_autonomous", "autonomous")

DEFENSE_ACTIONS = (
    "refresh", "faq_expansion", "entity_expansion", "publisher_boost", "authority_boost",
)
GROWTH_ACTIONS = ("create_content", "fill_gap", "target_keyword", "geo_page", "entity_page")
CONTENT_ACTIONS = ("refresh", "expand_content", "create_faq", "create_geo", "renew_stale")
AUTHORITY_ACTIONS = ("authority_boost", "support_site", "mesh_plan", "network_fill")
PUBLISHER_ACTIONS = ("publish", "queue_distribute", "deploy")

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "mode": "plan_only",
    "max_actions_per_day": 25,
    "min_confidence_score": 70,
    "allow_refresh": True,
    "allow_publish": False,
    "allow_authority_actions": False,
    "allow_network_actions": False,
    "allow_deploy": False,
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
                data.setdefault("decisions", [])
                data.setdefault("missions", {"daily": [], "weekly": []})
                data.setdefault("action_plans", [])
                data.setdefault("audit_history", [])
                data.setdefault("stats", {"success_count": 0, "failure_count": 0})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "decisions": [],
        "missions": {"daily": [], "weekly": []},
        "action_plans": [],
        "audit_history": [],
        "stats": {"success_count": 0, "failure_count": 0},
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    if "mode" in patch and patch["mode"] not in ACTION_MODES:
        raise ValueError(f"Geçersiz mode: {patch['mode']}")
    cur.update(patch)
    _save_state(st)
    _audit_log("settings_updated", settings={k: cur[k] for k in patch})
    return dict(cur)


def _append_limited(lst: list, item: dict, limit: int) -> None:
    lst.insert(0, item)
    del lst[limit:]


def _audit_log(event: str, **meta: Any) -> None:
    blocked = ("key", "token", "secret", "password", "credential")
    safe = {}
    for k, v in meta.items():
        if any(b in k.lower() for b in blocked):
            safe[k] = "[redacted]"
        else:
            safe[k] = v
    logger.info("autonomous_agent.%s %s", event, json.dumps(safe, ensure_ascii=False, default=str))
    st = _load_state()
    _append_limited(st.setdefault("audit_history", []), {"action": event, "meta": safe, "at": _now()}, HISTORY_LIMIT)
    _save_state(st)


def _decision_fingerprint(agent_type: str, action: str, keyword: str, project_id: str) -> str:
    raw = f"{agent_type}:{action}:{keyword}:{project_id}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _duplicate_decision_blocked(fp: str) -> bool:
    st = _load_state()
    for d in st.get("decisions") or []:
        if d.get("fingerprint") == fp and d.get("status") in ("planned", "pending", "approved"):
            return True
    return False


def _record_brain_decision(decision: dict[str, Any]) -> None:
    try:
        from app.moduller.hive_brain_engine import record_decision
        record_decision(
            "autonomous_seo_agent",
            decision.get("recommended_action", ""),
            reason=decision.get("reason", ""),
            project_id=decision.get("project_id", ""),
            domain=decision.get("domain", ""),
            keyword=decision.get("keyword", ""),
            applied=None,
            outcome="",
            metadata={
                "decision_id": decision.get("decision_id"),
                "agent_type": decision.get("agent_type"),
                "confidence_score": decision.get("confidence_score"),
                "priority_score": decision.get("priority_score"),
                "status": decision.get("status"),
            },
        )
    except Exception as exc:
        logger.debug("brain decision: %s", exc)


def compute_decision_scores(
    *,
    impact: float = 50,
    confidence: float = 60,
    risk: float = 30,
    estimated_gain: float = 40,
    memory_boost: float = 0,
    memory_penalty: float = 0,
) -> dict[str, Any]:
    impact_score = max(0, min(100, int(impact)))
    confidence_score = max(0, min(100, int(confidence + memory_boost - memory_penalty)))
    risk_score = max(0, min(100, int(risk)))
    priority_score = max(
        0,
        min(100, int((impact_score * 0.4) + (confidence_score * 0.35) + (estimated_gain * 0.15) - (risk_score * 0.1))),
    )
    return {
        "priority_score": priority_score,
        "impact_score": impact_score,
        "confidence_score": confidence_score,
        "risk_score": risk_score,
        "estimated_gain": max(0, min(100, int(estimated_gain))),
    }


def _make_decision(
    agent_type: str,
    recommended_action: str,
    reason: str,
    *,
    project_id: str = "",
    keyword: str = "",
    domain: str = "",
    source_module: str = "",
    scores: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any] | None:
    fp = _decision_fingerprint(agent_type, recommended_action, keyword, project_id)
    if _duplicate_decision_blocked(fp):
        return None

    sc = scores or compute_decision_scores()
    decision = {
        "decision_id": f"asa-dec-{uuid.uuid4().hex[:10]}",
        "timestamp": _now(),
        "project_id": project_id,
        "agent_type": agent_type,
        "reason": reason,
        "recommended_action": recommended_action,
        "keyword": keyword,
        "domain": domain,
        "source_module": source_module,
        "status": "planned",
        "fingerprint": fp,
        **sc,
        "metadata": metadata or {},
    }

    if persist:
        settings = get_settings()
        if decision["confidence_score"] < settings.get("min_confidence_score", 70):
            decision["status"] = "below_threshold"
        st = _load_state()
        _append_limited(st.setdefault("decisions", []), decision, DECISION_LIMIT)
        _save_state(st)
        _record_brain_decision(decision)
        _audit_log("decision_created", decision_id=decision["decision_id"], agent_type=agent_type, action=recommended_action)

    return decision


# ── Memory Agent ─────────────────────────────────────────────────────────────

def _memory_context(project_id: str = "") -> dict[str, Any]:
    """Brain'den başarı/başarısızlık sinyalleri — tekrarlayan kötü aksiyonları cezalandır."""
    success_actions: dict[str, int] = {}
    failure_actions: dict[str, int] = {}
    recent_decisions: list[dict] = []
    try:
        from app.moduller.hive_brain_engine import _load_state as brain_load
        brain = brain_load()
        for dec in (brain.get("decisions") or [])[:200]:
            if project_id and dec.get("project_id") and dec.get("project_id") != project_id:
                continue
            act = dec.get("recommendation") or dec.get("metadata", {}).get("recommended_action") or ""
            if not act:
                continue
            outcome = (dec.get("outcome") or "").lower()
            applied = dec.get("applied")
            if outcome in ("success", "ok", "published") or applied is True:
                success_actions[act] = success_actions.get(act, 0) + 1
            elif outcome in ("fail", "failed", "error") or applied is False:
                failure_actions[act] = failure_actions.get(act, 0) + 1
            recent_decisions.append(dec)
    except Exception as exc:
        return {"success": False, "error": str(exc), "success_actions": {}, "failure_actions": {}}

    st = _load_state()
    for d in (st.get("decisions") or [])[:100]:
        act = d.get("recommended_action", "")
        if d.get("status") == "success":
            success_actions[act] = success_actions.get(act, 0) + 1
        elif d.get("status") == "failed":
            failure_actions[act] = failure_actions.get(act, 0) + 1

    return {
        "success": True,
        "success_actions": success_actions,
        "failure_actions": failure_actions,
        "recent_decision_count": len(recent_decisions),
    }


def _memory_adjustments(action: str, memory: dict[str, Any]) -> tuple[float, float]:
    boost = min(15, memory.get("success_actions", {}).get(action, 0) * 3)
    penalty = min(25, memory.get("failure_actions", {}).get(action, 0) * 5)
    return boost, penalty


# ── Signal collectors ────────────────────────────────────────────────────────

def _collect_defense_signals(project_id: str) -> list[dict[str, Any]]:
    signals: list[dict] = []
    try:
        from app.moduller.serp_defense_engine import dashboard as sd_dash
        dash = sd_dash(project_id)
        for risk in (dash.get("top_risks") or [])[:10]:
            kw = risk.get("keyword") or risk.get("query") or ""
            pressure = risk.get("pressure_level") or "MEDIUM"
            fortress = risk.get("fortress_score") or 50
            actions = risk.get("recommended_actions") or []
            action = "refresh"
            if actions:
                first = actions[0] if isinstance(actions[0], str) else actions[0].get("action", "refresh")
                action_map = {
                    "content_refresh": "refresh",
                    "faq_expansion": "faq_expansion",
                    "entity_expansion": "entity_expansion",
                    "publisher_boost": "publisher_boost",
                    "support_network_boost": "authority_boost",
                    "authority_boost": "authority_boost",
                }
                action = action_map.get(first, first)
            impact = 90 if pressure == "CRITICAL" else 75 if pressure == "HIGH" else 55
            signals.append({
                "keyword": kw,
                "recommended_action": action,
                "reason": f"SERP Defense: {pressure} pressure, fortress {fortress}",
                "impact": impact,
                "confidence": 80 if kw else 55,
                "risk": 25 if action == "refresh" else 40,
                "estimated_gain": max(30, 100 - fortress),
                "source_module": "serp_defense_engine",
                "metadata": risk,
            })
    except Exception as exc:
        signals.append({"error": f"serp_defense: {exc}", "source_module": "serp_defense_engine"})

    if project_id:
        try:
            from app.moduller.rank_index_watcher import opportunity_finder
            opp = opportunity_finder(project_id)
            for row in (opp.get("opportunities") or [])[:8]:
                pos = row.get("position") or 20
                ctr = row.get("ctr") or 0
                kw = row.get("keyword") or ""
                action = "refresh" if ctr < 0.01 else "faq_expansion"
                signals.append({
                    "keyword": kw,
                    "recommended_action": action,
                    "reason": f"Rank Watcher: pos {pos}, CTR {ctr}",
                    "impact": 70 if row.get("priority") == "high" else 55,
                    "confidence": 75,
                    "risk": 20,
                    "estimated_gain": max(20, 90 - pos * 2),
                    "source_module": "rank_index_watcher",
                    "metadata": row,
                })
        except Exception as exc:
            signals.append({"error": f"rank_watcher: {exc}", "source_module": "rank_index_watcher"})

    return [s for s in signals if s.get("recommended_action")]


def _collect_growth_signals(project_id: str) -> list[dict[str, Any]]:
    signals: list[dict] = []
    try:
        from app.moduller.opportunity_engine import _get_cached_opportunities, dashboard as opp_dash
        opps = _get_cached_opportunities(project_id, "")
        if not opps:
            dash = opp_dash(project_id)
            opps = dash.get("top_opportunities") or []
        for o in sorted(opps, key=lambda x: -(x.get("opportunity_score") or 0))[:15]:
            score = o.get("opportunity_score") or 50
            traffic = o.get("traffic_gain_score") or o.get("scores", {}).get("traffic") or 50
            difficulty = o.get("difficulty_score") or o.get("scores", {}).get("difficulty") or 50
            authority_need = o.get("authority_need_score") or 40
            impl_cost = o.get("implementation_cost_score") or o.get("scores", {}).get("effort") or 50
            otype = o.get("type") or "keyword"
            action = "target_keyword" if otype == "keyword" else "fill_gap" if "gap" in otype else "create_content"
            signals.append({
                "keyword": o.get("keyword") or o.get("title") or "",
                "recommended_action": action,
                "reason": o.get("reason") or f"Opportunity score {score}",
                "impact": score,
                "confidence": min(90, 50 + score // 3),
                "risk": min(60, difficulty // 2),
                "estimated_gain": traffic,
                "source_module": "opportunity_engine",
                "metadata": {
                    **o,
                    "traffic_gain": traffic,
                    "difficulty": difficulty,
                    "authority_need": authority_need,
                    "implementation_cost": impl_cost,
                },
            })
    except Exception as exc:
        signals.append({"error": f"opportunity: {exc}"})

    try:
        from app.moduller.crawl_gap_engine import dashboard as cg_dash, _latest_analysis
        dash = cg_dash(project_id)
        a = _latest_analysis(project_id)
        for item in ((a or {}).get("action_plan") or [])[:10]:
            signals.append({
                "keyword": item.get("keyword") or item.get("label") or "",
                "recommended_action": "fill_gap",
                "reason": item.get("reason") or item.get("action") or "Crawl gap action",
                "impact": item.get("priority_score") or 65,
                "confidence": 70,
                "risk": 25,
                "estimated_gain": item.get("estimated_gain") or 55,
                "source_module": "crawl_gap_engine",
                "metadata": item,
            })
        if dash.get("quick_wins"):
            for _ in range(min(3, int(dash.get("quick_wins") or 0))):
                signals.append({
                    "keyword": "",
                    "recommended_action": "create_content",
                    "reason": f"Crawl Gap: {dash.get('quick_wins')} quick win gap",
                    "impact": 72,
                    "confidence": 68,
                    "risk": 20,
                    "estimated_gain": 60,
                    "source_module": "crawl_gap_engine",
                    "metadata": {"quick_wins": dash.get("quick_wins")},
                })
    except Exception as exc:
        signals.append({"error": f"crawl_gap: {exc}"})

    return [s for s in signals if s.get("recommended_action")]


def _collect_revenue_signals(project_id: str = "") -> list[dict[str, Any]]:
    signals: list[dict] = []
    try:
        from app.moduller.revenue_lead_engine import agent_signals
        res = agent_signals(project_id)
        for ins in res.get("insights") or []:
            action_map = {
                "optimize_conversion": "refresh",
                "scale_content": "create_content",
                "replicate_authority_pattern": "authority_source",
            }
            signals.append({
                "keyword": ins.get("keyword") or "",
                "recommended_action": action_map.get(ins.get("recommended_action"), "target_keyword"),
                "reason": ins.get("message") or ins.get("type", "revenue insight"),
                "impact": 75 if ins.get("priority") == "HIGH" else 60,
                "confidence": 72,
                "risk": 20,
                "estimated_gain": 65,
                "source_module": "revenue_lead_engine",
                "metadata": ins,
            })
    except Exception as exc:
        signals.append({"error": f"revenue_lead: {exc}"})
    return [s for s in signals if s.get("recommended_action") or s.get("error")]


def _collect_citation_signals(project_id: str = "") -> list[dict[str, Any]]:
    signals: list[dict] = []
    try:
        from app.moduller.citation_engine import agent_signals
        res = agent_signals(project_id)
        action_map = {
            "improve_citation_signals": "add_citation",
            "optimize_ai_visibility": "create_content",
            "close_citation_gap": "add_faq",
            "refresh_citation_content": "refresh",
        }
        for ins in res.get("insights") or []:
            signals.append({
                "keyword": ins.get("keyword") or "",
                "recommended_action": action_map.get(ins.get("recommended_action"), "add_citation"),
                "reason": ins.get("message") or ins.get("type", "citation insight"),
                "impact": 80 if ins.get("priority") == "HIGH" else 62,
                "confidence": 74,
                "risk": 18,
                "estimated_gain": 68,
                "source_module": "citation_engine",
                "metadata": ins,
            })
    except Exception as exc:
        signals.append({"error": f"citation_engine: {exc}"})
    return [s for s in signals if s.get("recommended_action") or s.get("error")]


def _collect_content_signals(project_id: str) -> list[dict[str, Any]]:
    signals: list[dict] = []
    if project_id:
        try:
            from app.moduller.content_refresh_engine import scan, _load_state as cr_load
            cr_st = cr_load()
            candidates = (cr_st.get("candidates") or {}).get(project_id) or []
            if not candidates:
                scan_res = scan(project_id)
                candidates = scan_res.get("candidates") or []
            for c in sorted(candidates, key=lambda x: -(x.get("refresh_score") or 0))[:12]:
                if not c.get("refresh_needed") and (c.get("refresh_score") or 0) < 40:
                    continue
                label = c.get("priority_label") or "MEDIUM"
                signals.append({
                    "keyword": c.get("keyword") or c.get("title") or "",
                    "recommended_action": "refresh",
                    "reason": f"Content Refresh: {label} — score {c.get('refresh_score', 0)}",
                    "impact": 85 if label == "CRITICAL" else 70 if label == "HIGH" else 55,
                    "confidence": 78,
                    "risk": 15,
                    "estimated_gain": c.get("refresh_score") or 50,
                    "source_module": "content_refresh_engine",
                    "metadata": {"page_id": c.get("page_id"), "slug": c.get("slug")},
                })
        except Exception as exc:
            signals.append({"error": f"content_refresh: {exc}"})

    try:
        from app.moduller.question_intelligence_engine import list_jobs
        jobs = list_jobs(10)
        for j in (jobs.get("jobs") or [])[:5]:
            if j.get("status") in ("completed", "failed"):
                continue
            signals.append({
                "keyword": j.get("keyword") or j.get("seed") or "",
                "recommended_action": "create_faq",
                "reason": f"QIE job pending: {j.get('job_type', 'faq')}",
                "impact": 60,
                "confidence": 65,
                "risk": 20,
                "estimated_gain": 55,
                "source_module": "question_intelligence_engine",
                "metadata": j,
            })
    except Exception as exc:
        signals.append({"error": f"qie: {exc}"})

    if project_id:
        try:
            from app.moduller.entity_geo_graph import get_project_scores, missing_entities
            scores = get_project_scores(project_id)
            if scores.get("success"):
                geo = scores.get("geo_coverage_score") or 0
                if geo < 60:
                    signals.append({
                        "keyword": "",
                        "recommended_action": "create_geo",
                        "reason": f"Entity GEO: geo coverage {geo}",
                        "impact": 70,
                        "confidence": 72,
                        "risk": 25,
                        "estimated_gain": 100 - geo,
                        "source_module": "entity_geo_graph",
                        "metadata": scores,
                    })
            missing = missing_entities(project_id=project_id)
            for ent in (missing.get("missing_entities") or [])[:5]:
                signals.append({
                    "keyword": ent.get("name") or ent.get("entity") or "",
                    "recommended_action": "expand_content",
                    "reason": "Entity GEO: missing entity coverage",
                    "impact": 65,
                    "confidence": 70,
                    "risk": 20,
                    "estimated_gain": 50,
                    "source_module": "entity_geo_graph",
                    "metadata": ent,
                })
        except Exception as exc:
            signals.append({"error": f"entity_geo: {exc}"})

    return [s for s in signals if s.get("recommended_action")]


def _collect_authority_signals(project_id: str, network_id: str = "") -> list[dict[str, Any]]:
    signals: list[dict] = []
    try:
        from app.moduller.authority_mesh_engine import dashboard as am_dash, _load_state as am_load
        dash = am_dash()
        queued = dash.get("queued_tasks") or 0
        if queued:
            signals.append({
                "keyword": "",
                "recommended_action": "mesh_plan",
                "reason": f"Authority Mesh: {queued} queued Google Sites / browser tasks",
                "impact": 65,
                "confidence": 70,
                "risk": 35,
                "estimated_gain": 55,
                "source_module": "authority_mesh_engine",
                "metadata": {"queued_tasks": queued},
            })
        am_st = am_load()
        idle = [s for s in (am_st.get("authority_sites") or []) if s.get("status") in ("planned", "draft")]
        for site in idle[:5]:
            signals.append({
                "keyword": site.get("target_keyword_cluster") or "",
                "recommended_action": "authority_boost",
                "reason": f"Authority site idle: {site.get('provider')} — {site.get('status')}",
                "impact": 60,
                "confidence": 68,
                "risk": 30,
                "estimated_gain": 45,
                "source_module": "authority_mesh_engine",
                "metadata": {"authority_id": site.get("authority_id"), "provider": site.get("provider")},
            })
    except Exception as exc:
        signals.append({"error": f"authority_mesh: {exc}"})

    if network_id:
        try:
            from app.moduller.support_network_engine import dashboard as sn_dash, growth_opportunities
            dash = sn_dash(network_id)
            if (dash.get("gap_count") or 0) > 0:
                signals.append({
                    "keyword": "",
                    "recommended_action": "network_fill",
                    "reason": f"Support Network: {dash.get('gap_count')} gaps",
                    "impact": 70,
                    "confidence": 75,
                    "risk": 35,
                    "estimated_gain": 60,
                    "source_module": "support_network_engine",
                    "metadata": {"gap_count": dash.get("gap_count")},
                })
            for opp in (growth_opportunities(network_id).get("opportunities") or [])[:5]:
                signals.append({
                    "keyword": opp.get("item") or opp.get("domain") or "",
                    "recommended_action": "support_site",
                    "reason": opp.get("reason") or opp.get("type") or "Support network opportunity",
                    "impact": 75 if opp.get("priority") == "high" else 58,
                    "confidence": 72,
                    "risk": 30,
                    "estimated_gain": 55,
                    "source_module": "support_network_engine",
                    "metadata": opp,
                })
        except Exception as exc:
            signals.append({"error": f"support_network: {exc}"})

    return [s for s in signals if s.get("recommended_action")]


def _collect_publisher_signals(project_id: str) -> list[dict[str, Any]]:
    signals: list[dict] = []
    try:
        from app.moduller.publisher_hub import get_queue, get_drafts, scan_sources
        queue = get_queue()
        for item in (queue.get("queue") or [])[:8]:
            signals.append({
                "keyword": item.get("keyword") or "",
                "recommended_action": "publish",
                "reason": f"Publisher Hub queue: {item.get('title', '')[:60]}",
                "impact": 55,
                "confidence": 70,
                "risk": 45,
                "estimated_gain": 40,
                "source_module": "publisher_hub",
                "metadata": {"publish_id": item.get("publish_id"), "channels": item.get("channels")},
            })
        drafts = get_drafts()
        for d in (drafts.get("drafts") or [])[:5]:
            signals.append({
                "keyword": d.get("keyword") or "",
                "recommended_action": "queue_distribute",
                "reason": f"Publisher draft ready: {d.get('title', '')[:60]}",
                "impact": 50,
                "confidence": 65,
                "risk": 40,
                "estimated_gain": 35,
                "source_module": "publisher_hub",
                "metadata": d,
            })
        scan = scan_sources()
        for item in (scan.get("items") or [])[:5]:
            if item.get("quality_gate_passed") or item.get("gate_score", 0) >= 70:
                signals.append({
                    "keyword": item.get("keyword") or "",
                    "recommended_action": "publish",
                    "reason": f"Quality gate passed: {item.get('source')}",
                    "impact": 62,
                    "confidence": 75,
                    "risk": 35,
                    "estimated_gain": 48,
                    "source_module": "publisher_hub",
                    "metadata": item,
                })
    except Exception as exc:
        signals.append({"error": f"publisher_hub: {exc}"})

    try:
        from app.moduller.astro_auto_publisher import list_jobs
        jobs = list_jobs(10)
        for j in (jobs.get("jobs") or [])[:5]:
            if j.get("status") in ("deployed", "failed"):
                continue
            action = "deploy" if j.get("status") == "built" else "queue_distribute"
            signals.append({
                "keyword": j.get("keyword") or j.get("project_id") or "",
                "recommended_action": action,
                "reason": f"Astro Auto Publisher: {j.get('status', 'pending')}",
                "impact": 58,
                "confidence": 68,
                "risk": 50 if action == "deploy" else 35,
                "estimated_gain": 42,
                "source_module": "astro_auto_publisher",
                "metadata": j,
            })
    except Exception as exc:
        signals.append({"error": f"astro_auto: {exc}"})

    return [s for s in signals if s.get("recommended_action")]


def _run_agent(agent_type: str, project_id: str, network_id: str, memory: dict) -> list[dict]:
    collectors = {
        "defense": lambda: _collect_defense_signals(project_id),
        "growth": lambda: _collect_growth_signals(project_id) + _collect_revenue_signals(project_id) + _collect_citation_signals(project_id),
        "content": lambda: _collect_content_signals(project_id),
        "authority": lambda: _collect_authority_signals(project_id, network_id),
        "publisher": lambda: _collect_publisher_signals(project_id),
    }
    if agent_type == "memory":
        return []

    signals = collectors.get(agent_type, lambda: [])()
    decisions: list[dict] = []
    for sig in signals:
        if sig.get("error"):
            continue
        action = sig["recommended_action"]
        boost, penalty = _memory_adjustments(action, memory)
        scores = compute_decision_scores(
            impact=sig.get("impact", 50),
            confidence=sig.get("confidence", 60),
            risk=sig.get("risk", 30),
            estimated_gain=sig.get("estimated_gain", 40),
            memory_boost=boost,
            memory_penalty=penalty,
        )
        dec = _make_decision(
            agent_type,
            action,
            sig.get("reason", ""),
            project_id=project_id,
            keyword=sig.get("keyword", ""),
            domain=sig.get("domain", ""),
            source_module=sig.get("source_module", ""),
            scores=scores,
            metadata=sig.get("metadata"),
        )
        if dec:
            decisions.append(dec)
    return decisions


def analyze_project(
    project_id: str = "",
    network_id: str = "",
    *,
    agents: list[str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled"):
        return {"success": False, "error": "agent_disabled", "message": "Autonomous SEO Agent kapalı — Settings'ten enabled=true yapın"}

    memory = _memory_context(project_id)
    agent_list = agents or [a for a in AGENT_TYPES if a != "memory"]
    all_decisions: list[dict] = []
    by_agent: dict[str, list] = {}

    for agent_type in agent_list:
        decs = _run_agent(agent_type, project_id, network_id, memory)
        by_agent[agent_type] = decs
        all_decisions.extend(decs)

    all_decisions.sort(key=lambda d: -(d.get("priority_score") or 0))
    max_actions = settings.get("max_actions_per_day", 25)
    trimmed = all_decisions[:max_actions]

    st = _load_state()
    plan = {
        "plan_id": f"asa-plan-{uuid.uuid4().hex[:10]}",
        "project_id": project_id,
        "network_id": network_id,
        "created_at": _now(),
        "decision_count": len(trimmed),
        "decisions": [d["decision_id"] for d in trimmed],
        "by_agent": {k: len(v) for k, v in by_agent.items()},
    }
    _append_limited(st.setdefault("action_plans", []), plan, 50)
    _save_state(st)
    _audit_log("analyze_project", project_id=project_id, decision_count=len(trimmed))

    return {
        "success": True,
        "project_id": project_id,
        "network_id": network_id,
        "mode": settings.get("mode", "plan_only"),
        "decisions": trimmed,
        "by_agent": by_agent,
        "plan_id": plan["plan_id"],
        "memory": memory,
    }


def generate_action_plan(project_id: str = "", network_id: str = "") -> dict[str, Any]:
    return analyze_project(project_id, network_id)


def _mission_items_from_decisions(decisions: list[dict], limit: int = 10) -> list[dict]:
    items: list[dict] = []
    action_counts: dict[str, int] = {}
    for d in decisions:
        act = d.get("recommended_action", "")
        action_counts[act] = action_counts.get(act, 0) + 1
    for act, count in sorted(action_counts.items(), key=lambda x: -x[1])[:limit]:
        items.append({"action": act, "count": count, "label": f"{count}× {act.replace('_', ' ')}"})
    return items


def generate_daily_mission(project_id: str = "", network_id: str = "") -> dict[str, Any]:
    res = analyze_project(project_id, network_id)
    if not res.get("success"):
        return res

    decisions = res.get("decisions") or []
    items = _mission_items_from_decisions(decisions, 8)
    mission = {
        "mission_id": f"asa-daily-{_today()}-{uuid.uuid4().hex[:6]}",
        "type": "daily",
        "date": _today(),
        "project_id": project_id,
        "network_id": network_id,
        "created_at": _now(),
        "items": items,
        "decision_ids": [d["decision_id"] for d in decisions[:15]],
        "summary": [it["label"] for it in items],
    }

    st = _load_state()
    daily = st.setdefault("missions", {}).setdefault("daily", [])
    daily = [m for m in daily if m.get("date") != _today() or m.get("project_id") != project_id]
    daily.insert(0, mission)
    st["missions"]["daily"] = daily[:MISSION_LIMIT]
    _save_state(st)
    _audit_log("daily_mission_generated", mission_id=mission["mission_id"], item_count=len(items))

    return {"success": True, "mission": mission, "decisions": decisions}


def generate_weekly_mission(project_id: str = "", network_id: str = "") -> dict[str, Any]:
    res = analyze_project(project_id, network_id)
    if not res.get("success"):
        return res

    decisions = res.get("decisions") or []
    by_agent = res.get("by_agent") or {}
    sections = {
        "growth": [d for d in decisions if d.get("agent_type") == "growth"][:5],
        "defense": [d for d in decisions if d.get("agent_type") == "defense"][:5],
        "authority": [d for d in decisions if d.get("agent_type") == "authority"][:5],
        "refresh": [d for d in decisions if d.get("agent_type") == "content" and d.get("recommended_action") == "refresh"][:5],
        "deploy": [d for d in decisions if d.get("recommended_action") in ("deploy", "publish")] [:5],
    }
    mission = {
        "mission_id": f"asa-weekly-{uuid.uuid4().hex[:8]}",
        "type": "weekly",
        "week_start": _today(),
        "project_id": project_id,
        "network_id": network_id,
        "created_at": _now(),
        "sections": {
            k: [{"decision_id": d["decision_id"], "action": d["recommended_action"], "reason": d["reason"][:80]} for d in v]
            for k, v in sections.items()
        },
        "agent_counts": {k: len(v) for k, v in by_agent.items()},
    }

    st = _load_state()
    _append_limited(st.setdefault("missions", {}).setdefault("weekly", []), mission, MISSION_LIMIT)
    _save_state(st)
    _audit_log("weekly_mission_generated", mission_id=mission["mission_id"])

    return {"success": True, "mission": mission, "sections": sections}


def list_decisions(limit: int = 50, agent_type: str = "", project_id: str = "") -> dict[str, Any]:
    st = _load_state()
    decs = list(st.get("decisions") or [])
    if agent_type:
        decs = [d for d in decs if d.get("agent_type") == agent_type]
    if project_id:
        decs = [d for d in decs if d.get("project_id") == project_id]
    decs = decs[:max(1, min(200, limit))]
    return {"success": True, "count": len(decs), "decisions": decs}


def list_missions(mission_type: str = "") -> dict[str, Any]:
    st = _load_state()
    missions = st.get("missions") or {"daily": [], "weekly": []}
    if mission_type == "daily":
        return {"success": True, "missions": missions.get("daily") or []}
    if mission_type == "weekly":
        return {"success": True, "missions": missions.get("weekly") or []}
    return {"success": True, "daily": missions.get("daily") or [], "weekly": missions.get("weekly") or []}


def list_reports() -> dict[str, Any]:
    st = _load_state()
    return {
        "success": True,
        "decisions_count": len(st.get("decisions") or []),
        "daily_missions": len((st.get("missions") or {}).get("daily") or []),
        "weekly_missions": len((st.get("missions") or {}).get("weekly") or []),
        "action_plans": len(st.get("action_plans") or []),
        "audit_entries": len(st.get("audit_history") or []),
        "stats": st.get("stats") or {},
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "overview": dashboard,
        "decisions": lambda: list_decisions(100),
        "missions": list_missions,
        "audit": lambda: {"success": True, "audit": _load_state().get("audit_history", [])[:100]},
    }
    fn = generators.get(report_type, dashboard)
    payload = fn()
    path = REPORTS_DIR / f"autonomous-agent-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def dashboard(project_id: str = "", network_id: str = "") -> dict[str, Any]:
    st = _load_state()
    settings = get_settings()
    decisions = st.get("decisions") or []
    if project_id:
        decisions = [d for d in decisions if not d.get("project_id") or d.get("project_id") == project_id]

    threats = [d for d in decisions if d.get("agent_type") == "defense"][:10]
    growth = sorted(
        [d for d in decisions if d.get("agent_type") == "growth"],
        key=lambda x: -(x.get("priority_score") or 0),
    )[:10]
    authority = [d for d in decisions if d.get("agent_type") == "authority"][:10]
    refresh = [d for d in decisions if d.get("agent_type") == "content" and d.get("recommended_action") == "refresh"][:10]
    pending_publish = [d for d in decisions if d.get("agent_type") == "publisher"][:10]
    suggested = sorted(decisions, key=lambda x: -(x.get("priority_score") or 0))[:15]

    stats = st.get("stats") or {}
    total_outcomes = (stats.get("success_count") or 0) + (stats.get("failure_count") or 0)
    success_rate = round((stats.get("success_count") or 0) / max(total_outcomes, 1) * 100, 1)

    weekly_impact = sum(d.get("estimated_gain") or 0 for d in decisions[:50])

    integrations = _integration_status()

    executive_alignment: dict[str, Any] = {"alignment_pct": 0}
    try:
        from app.moduller.executive_ai import agent_alignment_payload
        executive_alignment = agent_alignment_payload(project_id)
    except Exception:
        pass

    return {
        "success": True,
        "enabled": settings.get("enabled", False),
        "mode": settings.get("mode", "plan_only"),
        "active_threats": len(threats),
        "threats": threats,
        "growth_opportunities": len(growth),
        "growth_queue": growth,
        "authority_opportunities": len(authority),
        "authority_queue": authority,
        "refresh_candidates": len(refresh),
        "refresh_queue": refresh,
        "pending_publish": len(pending_publish),
        "publish_queue": pending_publish,
        "suggested_actions": suggested,
        "success_rate": success_rate,
        "weekly_impact_estimate": weekly_impact,
        "decisions_count": len(decisions),
        "integrations": integrations,
        "integration_errors": [k for k, v in integrations.items() if not v.get("ok")],
        "latest_daily_mission": ((st.get("missions") or {}).get("daily") or [{}])[0],
        "latest_weekly_mission": ((st.get("missions") or {}).get("weekly") or [{}])[0],
        "executive_alignment": executive_alignment,
    }


_INTEGRATION_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_INTEGRATION_TTL_SEC = 90


def _integration_status() -> dict[str, Any]:
    import time
    now = time.monotonic()
    cached = _INTEGRATION_CACHE.get("data")
    if cached is not None and (now - _INTEGRATION_CACHE["at"]) < _INTEGRATION_TTL_SEC:
        return dict(cached)

    checks: dict[str, Any] = {}
    modules = (
        "opportunity_engine", "serp_defense_engine", "crawl_gap_engine",
        "content_refresh_engine", "publisher_hub", "authority_mesh_engine",
        "support_network_engine", "rank_index_watcher", "hive_brain_engine",
        "entity_geo_graph", "question_intelligence_engine", "astro_auto_publisher",
    )
    for name in modules:
        try:
            mod = __import__(f"app.moduller.{name}", fromlist=["health"])
            if name == "publisher_hub":
                res = mod.health_summary()
            else:
                res = mod.health()
            checks[name] = {"ok": bool(res.get("success", True)), "detail": res}
        except Exception as exc:
            checks[name] = {"ok": False, "error": str(exc)}
    _INTEGRATION_CACHE["at"] = now
    _INTEGRATION_CACHE["data"] = checks
    return checks


def health() -> dict[str, Any]:
    st = _load_state()
    settings = get_settings()
    integrations = _integration_status()
    errors = [{"module": k, "error": v.get("error") or "not ready"} for k, v in integrations.items() if not v.get("ok")]
    return {
        "success": True,
        "module": "autonomous_seo_agent",
        "enabled": settings.get("enabled", False),
        "mode": settings.get("mode", "plan_only"),
        "agent_types": list(AGENT_TYPES),
        "integrations": integrations,
        "integration_errors": errors,
        "decisions_count": len(st.get("decisions") or []),
        "missions_count": len((st.get("missions") or {}).get("daily") or []) + len((st.get("missions") or {}).get("weekly") or []),
        "security": {
            "plan_only_default": settings.get("mode") == "plan_only",
            "allow_publish": settings.get("allow_publish", False),
            "allow_deploy": settings.get("allow_deploy", False),
            "allow_authority_actions": settings.get("allow_authority_actions", False),
            "allow_network_actions": settings.get("allow_network_actions", False),
        },
    }
