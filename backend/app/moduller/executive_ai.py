"""
Executive AI V1 — stratejik karar ve önceliklendirme katmanı.

İçerik üretmez, yayın yapmaz, deploy etmez.
Tüm HIVE motorlarını okuyup CEO özeti, öncelik ve görev planı üretir.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("hive.executive_ai")

STATE_FILE = Path(__file__).resolve().parent.parent / "executive_ai_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 300
PRIORITY_LIMIT = 100

HEALTH_CATEGORIES = ("Healthy", "Warning", "Critical", "Growth Mode", "Recovery Mode")

SOURCE_MODULES = (
    "hive_brain_engine",
    "opportunity_engine",
    "serp_defense_engine",
    "citation_engine",
    "revenue_lead_engine",
    "authority_factory",
    "action_orchestrator",
    "publisher_hub",
    "support_network_engine",
    "rank_index_watcher",
    "provider_control_center",
    "hive_audit_engine",
    "campaign_engine",
    "content_refresh_engine",
    "crawl_gap_engine",
    "autonomous_seo_agent",
)

SUMMARY_WEIGHTS: dict[str, float] = {
    "health_score": 0.12,
    "growth_score": 0.12,
    "revenue_score": 0.12,
    "citation_score": 0.08,
    "authority_score": 0.08,
    "execution_score": 0.08,
    "performance_score": 0.10,
    "risk_score": -0.12,
    "performance_risk": -0.08,
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "default_project_id": "",
    "priority_threshold": 70,
    "risk_alert_threshold": 55,
    "growth_mode_threshold": 75,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("summaries", {})
                data.setdefault("priorities", [])
                data.setdefault("missions", {"daily": [], "weekly": [], "monthly": []})
                data.setdefault("reports", [])
                data.setdefault("forecasts", {})
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "summaries": {},
        "priorities": [],
        "missions": {"daily": [], "weekly": [], "monthly": []},
        "reports": [],
        "forecasts": {},
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


def _record_brain(event_type: str, *, keyword: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "executive_ai",
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "executive_ai", "executive_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _safe_read(module: str, fn_name: str, *args, default: Any = None, **kwargs) -> Any:
    try:
        import importlib
        mod = importlib.import_module(f"app.moduller.{module}")
        fn: Callable = getattr(mod, fn_name)
        res = fn(*args, **kwargs)
        if isinstance(res, dict) and res.get("success") is False and default is not None:
            return default
        return res
    except Exception as exc:
        logger.debug("executive read %s.%s: %s", module, fn_name, exc)
        return default if default is not None else {"success": False, "error": str(exc)}


def _clamp(v: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, v))


def _collect_sources(project_id: str = "") -> dict[str, Any]:
    """Tüm motorlardan read-only veri."""
    pid = (project_id or "").strip()
    return {
        "brain": _safe_read("hive_brain_engine", "dashboard", default={}),
        "brain_timeline": _safe_read("hive_brain_engine", "get_timeline", 14, default={"timeline": []}),
        "opportunity": _safe_read("opportunity_engine", "dashboard", pid, default={}),
        "serp": _safe_read("serp_defense_engine", "dashboard", pid, default={}),
        "citation": _safe_read("citation_engine", "mission_control_payload", default={}),
        "revenue": _safe_read("revenue_lead_engine", "mission_control_payload", default={}),
        "authority_factory": _safe_read("authority_factory", "mission_control_payload", default={}),
        "orchestrator": _safe_read("action_orchestrator", "build_dashboard", default={}),
        "publisher": _safe_read("publisher_hub", "health_summary", default={}),
        "support_network": _safe_read("support_network_engine", "dashboard", default={}),
        "rank": _safe_read("rank_index_watcher", "health", default={}),
        "refresh": _safe_read("content_refresh_engine", "get_dashboard", default={}),
        "crawl_gap": _safe_read("crawl_gap_engine", "health", default={}),
        "agent": _safe_read("autonomous_seo_agent", "health", default={}),
        "agent_missions": _safe_read("autonomous_seo_agent", "list_missions", default={"daily": [], "weekly": []}),
        "mission_control": _safe_read("mission_control_center", "health_summary", default={}),
        "performance": _safe_read("mission_control_center", "build_performance_status", default={}),
        "providers": _safe_read("provider_control_center", "executive_risk_payload", default={}),
        "audit": _safe_read("hive_audit_engine", "executive_risk_payload", default={}),
        "campaigns": _safe_read("campaign_engine", "executive_alignment_payload", default={}),
        "success_path": _safe_read("hive_success_path", "executive_activation_payload", default={}),
        "readiness": _safe_read("production_readiness_engine", "executive_readiness_payload", default={}),
    }


def _score_from_sources(sources: dict[str, Any], project_id: str = "") -> dict[str, Any]:
    opp = sources.get("opportunity") or {}
    serp = sources.get("serp") or {}
    cite = sources.get("citation") or {}
    rev = sources.get("revenue") or {}
    af = sources.get("authority_factory") or {}
    orch = sources.get("orchestrator") or {}
    sn = sources.get("support_network") or {}
    mc = sources.get("mission_control") or {}
    refresh = sources.get("refresh") or {}
    crawl = sources.get("crawl_gap") or {}
    prov = sources.get("providers") or {}
    audit = sources.get("audit") or {}
    camp = sources.get("campaigns") or {}
    perf = sources.get("performance") or {}

    growth_score = _clamp(
        float(mc.get("system_health") or 50) * 0.3
        + min(100, (opp.get("quick_wins") or 0) * 8)
        + min(100, (opp.get("total_opportunities") or 0) * 2)
        + min(20, (camp.get("aligned_campaigns") or [{}])[0].get("alignment_score", 0) * 0.2 if camp.get("aligned_campaigns") else 0)
    )
    risk_score = _clamp(
        min(100, (serp.get("critical_pressure_count") or 0) * 15 + (cite.get("citation_risks") or 0) * 10
                + len(serp.get("top_risks") or []) * 5 + (refresh.get("critical_pages") or 0) * 5
                + int(prov.get("provider_risk_score") or 0)
                + int(audit.get("audit_risk_score") or 0))
    )
    revenue_score = _clamp(
        min(100, (rev.get("today_leads") or 0) * 12 + (rev.get("high_value_leads") or 0) * 15
                + float(rev.get("revenue_opportunity") or 0) * 0.05)
    )
    citation_score = _clamp(float(cite.get("citation_health_score") or 50))
    authority_score = _clamp(
        min(100, (af.get("published_today") or 0) * 10 + (sn.get("sites_count") or 0) * 3
                + (af.get("queued_batches") or 0) * 5 + 40)
    )
    execution_score = _clamp(float(orch.get("action_success_rate") or orch.get("pipeline_success_rate") or 50))
    health_score = _clamp(float(mc.get("system_health") or 50))
    performance_score = _clamp(float(perf.get("performance_score") or 50))
    performance_risk = _clamp(float(perf.get("performance_risk") or 0))

    risk_penalty = risk_score * 0.30 + performance_risk * 0.15
    overall = _clamp(
        health_score * 0.12 + growth_score * 0.15 + revenue_score * 0.12
        + citation_score * 0.10 + authority_score * 0.10 + execution_score * 0.08
        + performance_score * 0.10
        - risk_penalty * 0.13
    )

    return {
        "project_id": project_id or "global",
        "health_score": int(round(health_score)),
        "growth_score": int(round(growth_score)),
        "risk_score": int(round(risk_score)),
        "revenue_score": int(round(revenue_score)),
        "citation_score": int(round(citation_score)),
        "authority_score": int(round(authority_score)),
        "execution_score": int(round(execution_score)),
        "performance_score": int(round(performance_score)),
        "performance_risk": int(round(performance_risk)),
        "overall_score": int(round(overall)),
    }


def _health_category(summary: dict[str, Any]) -> str:
    settings = get_settings()
    overall = int(summary.get("overall_score") or 0)
    risk = int(summary.get("risk_score") or 0)
    growth = int(summary.get("growth_score") or 0)
    growth_th = int(settings.get("growth_mode_threshold") or 75)
    risk_th = int(settings.get("risk_alert_threshold") or 55)

    if risk >= risk_th and growth < 50:
        return "Recovery Mode"
    if growth >= growth_th and risk < 35:
        return "Growth Mode"
    if overall >= 70 and risk < 40:
        return "Healthy"
    if overall < 50 or risk >= 60:
        return "Critical"
    return "Warning"


def _priority_item(
    *,
    title: str,
    source: str,
    impact: float = 50,
    difficulty: float = 50,
    revenue: float = 50,
    authority: float = 50,
    citation: float = 50,
    risk: float = 50,
    time_to_result: float = 50,
    keyword: str = "",
    metadata: dict | None = None,
) -> dict[str, Any]:
    priority_score = _clamp(
        impact * 0.25
        + (100 - difficulty) * 0.15
        + revenue * 0.20
        + authority * 0.10
        + citation * 0.10
        + (100 - risk) * 0.10
        + time_to_result * 0.10
    )
    return {
        "id": f"exec-pri-{uuid.uuid4().hex[:10]}",
        "title": title,
        "source": source,
        "keyword": keyword,
        "impact": round(impact, 1),
        "difficulty": round(difficulty, 1),
        "revenue": round(revenue, 1),
        "authority": round(authority, 1),
        "citation": round(citation, 1),
        "risk": round(risk, 1),
        "time_to_result": round(time_to_result, 1),
        "priority_score": round(priority_score, 1),
        "metadata": metadata or {},
        "created_at": _now(),
    }


def _build_priorities(sources: dict[str, Any], summary: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    opp = sources.get("opportunity") or {}
    for o in (opp.get("top_opportunities") or [])[:15]:
        items.append(_priority_item(
            title=o.get("title") or o.get("keyword") or "Opportunity",
            source="opportunity",
            impact=float(o.get("estimated_gain") or o.get("opportunity_score") or 60),
            difficulty=float(o.get("difficulty_score") or 45),
            revenue=float(o.get("commercial_opportunity_score") or o.get("opportunity_score") or 50),
            keyword=o.get("keyword") or "",
            time_to_result=65,
            metadata=o,
        ))

    serp = sources.get("serp") or {}
    for r in (serp.get("top_risks") or serp.get("fortresses") or [])[:10]:
        fs = int(r.get("fortress_score") or r.get("overall_fortress_score") or 50)
        items.append(_priority_item(
            title=f"SERP savunma: {r.get('keyword') or r.get('title', 'keyword')}",
            source="serp_defense",
            impact=80,
            difficulty=55,
            risk=100 - fs,
            citation=float(summary.get("citation_score") or 50),
            time_to_result=40,
            keyword=r.get("keyword") or "",
            metadata=r,
        ))

    cite = sources.get("citation") or {}
    for o in (cite.get("top_opportunities") or [])[:8]:
        items.append(_priority_item(
            title=o.get("title") or "Citation fırsatı",
            source="citation",
            impact=float(o.get("citation_opportunity_score") or 65),
            citation=float(o.get("citation_opportunity_score") or 65),
            difficulty=40,
            time_to_result=55,
            metadata=o,
        ))

    rev = sources.get("revenue") or {}
    if rev.get("best_lead_source"):
        bl = rev["best_lead_source"]
        items.append(_priority_item(
            title=f"Lead kaynağı ölçekle: {bl.get('source') or bl.get('domain', 'kaynak')}",
            source="revenue",
            impact=75,
            revenue=85,
            difficulty=35,
            time_to_result=70,
            metadata=bl,
        ))

    af = sources.get("authority_factory") or {}
    if int(af.get("queued_batches") or 0) > 0:
        items.append(_priority_item(
            title=f"Authority Factory batch işle ({af['queued_batches']} queued)",
            source="authority_factory",
            impact=70,
            authority=80,
            difficulty=45,
            time_to_result=50,
            metadata=af,
        ))

    crawl = sources.get("crawl_gap") or {}
    if int(crawl.get("quick_wins") or 0) > 0:
        items.append(_priority_item(
            title=f"Crawl Gap quick win ({crawl.get('quick_wins')} gap)",
            source="crawl_gap",
            impact=float(crawl.get("quick_wins") or 0) * 10,
            difficulty=40,
            time_to_result=60,
            metadata={"quick_wins": crawl.get("quick_wins")},
        ))

    items.sort(key=lambda x: -x.get("priority_score", 0))
    return items[:PRIORITY_LIMIT]


def _top_actions(priorities: list[dict], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "rank": i + 1,
            "title": p.get("title"),
            "source": p.get("source"),
            "priority_score": p.get("priority_score"),
            "keyword": p.get("keyword"),
        }
        for i, p in enumerate(priorities[:limit])
    ]


def _ceo_narrative(period: str, sources: dict[str, Any], summary: dict[str, Any], priorities: list[dict]) -> dict[str, Any]:
    top_opp = priorities[0] if priorities else None
    top_risk = None
    serp = sources.get("serp") or {}
    cite = sources.get("citation") or {}
    rev = sources.get("revenue") or {}
    af = sources.get("authority_factory") or {}

    risks: list[str] = []
    if int(summary.get("risk_score") or 0) >= 55:
        risks.append("Yüksek savunma riski")
    if int(cite.get("citation_risks") or 0) > 0:
        risks.append("Citation düşüşü / eksik sinyaller")
    if int(cite.get("low_citation_pages") or 0) > 2:
        risks.append(f"{cite['low_citation_pages']} düşük citation sayfası")
    for r in (serp.get("top_risks") or [])[:2]:
        risks.append(f"SERP: {r.get('keyword') or r.get('title', 'risk')}")

    revenue_source = "—"
    if rev.get("best_lead_source"):
        bl = rev["best_lead_source"]
        revenue_source = bl.get("source") or bl.get("domain") or bl.get("module") or "lead kaynağı"

    authority_note = "Authority üretimi düşük"
    if int(af.get("published_today") or 0) > 0:
        authority_note = f"Bugün {af['published_today']} authority item yayınlandı"
    elif int(af.get("queued_batches") or 0) > 0:
        authority_note = f"{af['queued_batches']} authority batch bekliyor"

    headlines = {
        "today": f"Bugün odak: {top_opp['title'] if top_opp else 'Genel sistem izleme'}",
        "week": f"Bu hafta en büyük fırsat: {top_opp['title'] if top_opp else '—'}",
        "month": f"Bu ay stratejik öncelik: büyüme skoru {summary.get('growth_score')} — risk {summary.get('risk_score')}",
    }

    return {
        "period": period,
        "headline": headlines.get(period, headlines["today"]),
        "top_opportunity": top_opp.get("title") if top_opp else None,
        "top_risk": risks[0] if risks else "Kritik risk yok",
        "risks": risks[:5],
        "top_revenue_source": revenue_source,
        "authority_note": authority_note,
        "overall_score": summary.get("overall_score"),
        "health_category": _health_category(summary),
        "generated_at": _now(),
    }


def _build_missions(priorities: list[dict], summary: dict[str, Any]) -> dict[str, list[dict]]:
    daily: list[dict] = []
    weekly: list[dict] = []
    monthly: list[dict] = []

    for i, p in enumerate(priorities[:3]):
        daily.append({
            "id": f"exec-daily-{uuid.uuid4().hex[:8]}",
            "title": p.get("title"),
            "source": p.get("source"),
            "priority_score": p.get("priority_score"),
            "type": "daily",
        })

    for p in priorities[3:8]:
        weekly.append({
            "id": f"exec-weekly-{uuid.uuid4().hex[:8]}",
            "title": p.get("title"),
            "source": p.get("source"),
            "priority_score": p.get("priority_score"),
            "type": "weekly",
        })

    cat = _health_category(summary)
    monthly.append({
        "id": f"exec-monthly-{uuid.uuid4().hex[:8]}",
        "title": f"Aylık mod: {cat} — overall {summary.get('overall_score')}",
        "source": "executive_ai",
        "type": "monthly",
        "focus": cat,
    })
    if summary.get("citation_score", 100) < 60:
        monthly.append({
            "id": f"exec-monthly-{uuid.uuid4().hex[:8]}",
            "title": "Citation sinyallerini güçlendir",
            "source": "citation",
            "type": "monthly",
        })
    if summary.get("authority_score", 100) < 55:
        monthly.append({
            "id": f"exec-monthly-{uuid.uuid4().hex[:8]}",
            "title": "Authority Factory batch planla",
            "source": "authority_factory",
            "type": "monthly",
        })

    return {"daily": daily, "weekly": weekly, "monthly": monthly}


def _build_forecasts(sources: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    rev = sources.get("revenue") or {}
    cite = sources.get("citation") or {}
    orch = sources.get("orchestrator") or {}
    af = sources.get("authority_factory") or {}

    today_leads = int(rev.get("today_leads") or 0)
    rev_opp = float(rev.get("revenue_opportunity") or 0)
    cite_health = int(cite.get("citation_health_score") or summary.get("citation_score") or 50)
    cite_vis = int(cite.get("ai_visibility_avg") or 50)

    return {
        "revenue_forecast": {
            "weekly_leads_est": today_leads * 7,
            "monthly_revenue_est": round(rev_opp * 4.3, 2),
            "roi_score": _clamp(rev_opp * 0.1 + today_leads * 5),
            "trend": "up" if today_leads >= 2 else "stable",
        },
        "citation_forecast": {
            "citation_health": cite_health,
            "ai_visibility_avg": cite_vis,
            "risk_pages": int(cite.get("low_citation_pages") or 0),
            "trend": "down" if int(cite.get("citation_risks") or 0) > 2 else "stable",
        },
        "risk_forecast": {
            "risk_score": summary.get("risk_score"),
            "category": _health_category(summary),
            "alert": int(summary.get("risk_score") or 0) >= int(get_settings().get("risk_alert_threshold") or 55),
        },
        "authority_forecast": {
            "queued_batches": int(af.get("queued_batches") or 0),
            "published_today": int(af.get("published_today") or 0),
            "execution_rate": float(orch.get("action_success_rate") or 50),
            "pending_actions": int((orch.get("mission_control") or {}).get("pending_actions") or orch.get("queued") or 0),
            "authority_execution_score": int((af.get("executive") or {}).get("authority_execution_score") or 0),
            "authority_factory_risk": int((af.get("executive") or {}).get("authority_factory_risk") or 0),
            "authority_growth_potential": int((af.get("executive") or {}).get("authority_growth_potential") or 0),
            "v2_batches": int(af.get("authority_factory_v2_batches") or 0),
        },
        "generated_at": _now(),
    }


def _agent_alignment(sources: dict[str, Any], priorities: list[dict]) -> dict[str, Any]:
    agent = sources.get("agent") or {}
    agent_suggested = [d.get("recommended_action") or d.get("title") for d in (agent.get("suggested_actions") or agent.get("suggested") or [])[:10]]
    exec_actions = [p.get("title") for p in priorities[:10]]
    if not agent_suggested:
        return {"success": True, "alignment_pct": 0, "agent_actions": [], "executive_actions": exec_actions, "note": "Agent önerisi yok"}

    matches = 0
    for aa in agent_suggested:
        aa_l = (aa or "").lower()
        if any(aa_l in (ea or "").lower() or (ea or "").lower() in aa_l for ea in exec_actions):
            matches += 1
    alignment = int(round(matches / max(len(agent_suggested), 1) * 100))
    return {
        "success": True,
        "alignment_pct": alignment,
        "agent_actions": agent_suggested,
        "executive_actions": exec_actions,
        "matches": matches,
    }


def analyze_project(project_id: str = "") -> dict[str, Any]:
    if not get_settings().get("enabled", True):
        return {"success": False, "error": "executive_ai disabled"}

    pid = (project_id or get_settings().get("default_project_id") or "").strip() or "global"
    sources = _collect_sources(pid)
    summary = _score_from_sources(sources, pid)
    summary["health_category"] = _health_category(summary)
    priorities = _build_priorities(sources, summary)
    top_actions = _top_actions(priorities)
    missions = _build_missions(priorities, summary)
    forecasts = _build_forecasts(sources, summary)
    alignment = _agent_alignment(sources, priorities)

    reports = {
        "today": _ceo_narrative("today", sources, summary, priorities),
        "week": _ceo_narrative("week", sources, summary, priorities),
        "month": _ceo_narrative("month", sources, summary, priorities),
    }

    st = _load_state()
    old_top_title = (st.get("priorities") or [{}])[0].get("title") if st.get("priorities") else None
    st.setdefault("summaries", {})[pid] = {**summary, "analyzed_at": _now()}
    st["priorities"] = priorities
    st["missions"] = missions
    st.setdefault("forecasts", {})[pid] = forecasts
    report_entry = {
        "report_id": f"exec-rpt-{uuid.uuid4().hex[:10]}",
        "project_id": pid,
        "reports": reports,
        "top_actions": top_actions,
        "alignment": alignment,
        "at": _now(),
    }
    st.setdefault("reports", []).insert(0, report_entry)
    st["reports"] = st["reports"][:50]
    _append_history(st, {"action": "analyze_project", "project_id": pid, "overall": summary.get("overall_score"), "at": _now()})
    _save_state(st)

    _record_brain("executive_report_created", keyword=pid, result={"overall_score": summary.get("overall_score")})
    if int(summary.get("risk_score") or 0) >= int(get_settings().get("risk_alert_threshold") or 55):
        _record_brain("executive_risk_detected", keyword=pid, result={"risk_score": summary.get("risk_score")})
    if int(summary.get("growth_score") or 0) >= int(get_settings().get("growth_mode_threshold") or 75):
        _record_brain("executive_growth_detected", keyword=pid, result={"growth_score": summary.get("growth_score")})
    _record_brain("executive_mission_generated", keyword=pid, result={"daily": len(missions.get("daily", []))})

    if priorities and old_top_title and old_top_title != priorities[0].get("title"):
        _record_brain("executive_priority_changed", keyword=pid, reason=f"Yeni #1: {priorities[0].get('title')}")

    return {
        "success": True,
        "project_id": pid,
        "summary": summary,
        "priorities": priorities[:20],
        "top_actions": top_actions,
        "missions": missions,
        "forecasts": forecasts,
        "ceo_reports": reports,
        "agent_alignment": alignment,
        "sources_read": list(sources.keys()),
    }


def list_reports(limit: int = 20) -> dict[str, Any]:
    reps = _load_state().get("reports") or []
    return {"success": True, "count": len(reps), "reports": reps[:limit]}


def list_missions(mission_type: str = "") -> dict[str, Any]:
    m = _load_state().get("missions") or {"daily": [], "weekly": [], "monthly": []}
    if mission_type in ("daily", "weekly", "monthly"):
        return {"success": True, "type": mission_type, "missions": m.get(mission_type) or []}
    return {"success": True, **m}


def list_priorities(limit: int = 30) -> dict[str, Any]:
    pri = _load_state().get("priorities") or []
    th = int(get_settings().get("priority_threshold") or 70)
    return {
        "success": True,
        "count": len(pri),
        "high_priority": [p for p in pri if p.get("priority_score", 0) >= th],
        "priorities": pri[:limit],
    }


def get_forecasts(project_id: str = "") -> dict[str, Any]:
    pid = (project_id or get_settings().get("default_project_id") or "global").strip() or "global"
    fc = (_load_state().get("forecasts") or {}).get(pid)
    if fc:
        return {"success": True, "project_id": pid, "forecasts": fc}
    res = analyze_project(pid)
    return {"success": True, "project_id": pid, "forecasts": res.get("forecasts", {})}


def mission_control_payload() -> dict[str, Any]:
    st = _load_state()
    summaries = st.get("summaries") or {}
    global_sum = summaries.get("global") or next(iter(summaries.values()), {})
    pri = st.get("priorities") or []
    fc = st.get("forecasts") or {}
    gfc = fc.get("global") or next(iter(fc.values()), {})
    top = pri[0] if pri else None
    activation = _safe_read("hive_success_path", "executive_activation_payload", default={})
    readiness = _safe_read("production_readiness_engine", "executive_readiness_payload", default={})
    return {
        "success": True,
        "executive_score": global_sum.get("overall_score", 0),
        "activation_score": int(activation.get("activation_score") or 0),
        "activation_category": activation.get("activation_category", "Needs Onboarding"),
        "executive_readiness_score": int(readiness.get("executive_readiness_score") or 0),
        "executive_launch_recommendation": readiness.get("executive_launch_recommendation", ""),
        "readiness_launch_mode": readiness.get("launch_mode", "development"),
        "top_priority": top,
        "top_priority_score": top.get("priority_score") if top else 0,
        "revenue_forecast": (gfc.get("revenue_forecast") or {}),
        "risk_forecast": (gfc.get("risk_forecast") or {}),
        "citation_forecast": (gfc.get("citation_forecast") or {}),
        "health_category": global_sum.get("health_category", "Warning"),
        "performance_score": global_sum.get("performance_score", 0),
        "performance_risk": global_sum.get("performance_risk", 0),
        "priorities_count": len(pri),
    }


def agent_alignment_payload(project_id: str = "") -> dict[str, Any]:
    """Autonomous Agent — Executive karar uyumu."""
    st = _load_state()
    reps = st.get("reports") or []
    if reps:
        return reps[0].get("alignment") or {"alignment_pct": 0}
    res = analyze_project(project_id)
    return res.get("agent_alignment") or {"alignment_pct": 0}


def dashboard() -> dict[str, Any]:
    st = _load_state()
    summaries = st.get("summaries") or {}
    pri = st.get("priorities") or []
    missions = st.get("missions") or {}
    latest_report = (st.get("reports") or [{}])[0] if st.get("reports") else {}
    global_sum = summaries.get("global") or _score_from_sources(_collect_sources("global"), "global")
    activation = _safe_read("hive_success_path", "executive_activation_payload", default={})
    readiness = _safe_read("production_readiness_engine", "executive_readiness_payload", default={})
    af_exec = _safe_read("authority_factory", "executive_payload", default={})

    return {
        "success": True,
        "module": "executive_ai",
        "enabled": get_settings().get("enabled", True),
        "executive_score": global_sum.get("overall_score", 0),
        "authority_execution_score": int(af_exec.get("authority_execution_score") or 0),
        "authority_factory_risk": int(af_exec.get("authority_factory_risk") or 0),
        "authority_growth_potential": int(af_exec.get("authority_growth_potential") or 0),
        "activation_score": int(activation.get("activation_score") or 0),
        "activation_category": activation.get("activation_category", "Needs Onboarding"),
        "executive_readiness_score": int(readiness.get("executive_readiness_score") or 0),
        "executive_launch_recommendation": readiness.get("executive_launch_recommendation", ""),
        "health_category": global_sum.get("health_category") or _health_category(global_sum),
        "performance_score": global_sum.get("performance_score", 0),
        "performance_risk": global_sum.get("performance_risk", 0),
        "summary": global_sum,
        "priorities_count": len(pri),
        "top_priorities": pri[:5],
        "missions_daily": len(missions.get("daily") or []),
        "missions_weekly": len(missions.get("weekly") or []),
        "latest_ceo_headline": (latest_report.get("reports") or {}).get("today", {}).get("headline"),
        "agent_alignment_pct": (latest_report.get("alignment") or {}).get("alignment_pct", 0),
        "projects_analyzed": len(summaries),
        "settings": get_settings(),
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "overview": dashboard,
        "priorities": list_priorities,
        "missions": list_missions,
        "reports": list_reports,
        "forecasts": lambda: get_forecasts("global"),
    }
    fn = generators.get(report_type, dashboard)
    payload = fn()
    path = REPORTS_DIR / f"executive-ai-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def health() -> dict[str, Any]:
    settings = get_settings()
    dash = dashboard()
    return {
        "success": True,
        "module": "executive_ai",
        "enabled": settings.get("enabled", True),
        "executive_score": dash.get("executive_score", 0),
        "source_modules": list(SOURCE_MODULES),
        "produces_content": False,
        "publishes": False,
        "deploys": False,
    }
