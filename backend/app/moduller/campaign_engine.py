"""
Campaign Engine V1 — uçtan uca SEO kampanya planlayıcısı.

İçerik üretmez, publish yapmaz.
Hedef belirler, plan üretir, görevleri modüllere dağıtır ve ilerlemeyi takip eder.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("hive.campaign_engine")

STATE_FILE = Path(__file__).resolve().parent.parent / "campaign_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 300
CAMPAIGN_LIMIT = 200
TASK_LIMIT = 5000

DATASET_TASK_TYPES = (
    "authority_source", "publisher_content", "support_site", "citation_expansion",
    "faq_page", "entity_page", "geo_page", "internal_link", "content_refresh",
)

INDEX_RECOVERY_TASKS = (
    {"item_type": "content_refresh", "module": "indexing_fix", "action_type": "canonical_cleanup", "title": "Canonical cleanup"},
    {"item_type": "content_refresh", "module": "indexing_fix", "action_type": "redirect_map_deploy", "title": "Redirect map deploy"},
    {"item_type": "internal_link", "module": "indexing_fix", "action_type": "internal_link_update", "title": "Internal link graph update"},
    {"item_type": "content_refresh", "module": "indexing_fix", "action_type": "sitemap_resubmit", "title": "Sitemap resubmit"},
    {"item_type": "content_refresh", "module": "indexing_fix", "action_type": "request_indexing", "title": "Request indexing (IndexNow/GSC)"},
    {"item_type": "internal_link", "module": "rank_index_watcher", "action_type": "priority_keyword_tracking", "title": "Priority keyword tracking"},
)

GOALS = ("ranking", "authority", "citation", "lead_generation")
CAMPAIGN_TYPES = (
    "ranking", "authority", "citation", "lead", "local_geo", "full_domination",
)
PRIORITIES = ("low", "medium", "high", "critical")
STATUSES = ("planned", "active", "paused", "completed", "failed")

DEFAULT_BLUEPRINT: dict[str, int] = {
    "pillar": 1,
    "cluster": 12,
    "faq": 50,
    "entity": 20,
    "authority_source": 10,
    "publisher_content": 25,
    "support_site": 5,
    "citation_expansion": 15,
    "refresh": 8,
}

WEEKLY_PHASES = (
    ("week_1", "Foundation"),
    ("week_2", "Expansion"),
    ("week_3", "Authority"),
    ("week_4", "Defense"),
    ("week_5_plus", "Maintenance"),
)

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "default_goal": "ranking",
    "default_priority": "medium",
    "auto_score_on_plan": True,
    "commercial_intent_boost": True,
    "citation_gap_threshold": 15,
    "serp_risk_threshold": 60,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("campaigns", [])
                data.setdefault("tasks", [])
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "campaigns": [],
        "tasks": [],
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
    keyword: str = "",
    result: dict | None = None,
    reason: str = "",
) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "campaign_engine",
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "campaign_engine", "campaign_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _safe_read(module: str, func: str, *args: Any, default: Any = None, **kwargs: Any) -> Any:
    try:
        import importlib
        mod = importlib.import_module(f"app.moduller.{module}")
        fn = getattr(mod, func)
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.debug("read %s.%s: %s", module, func, exc)
        return default if default is not None else {}


def _clamp(n: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, round(n))))


def _priority_num(p: str) -> int:
    return {"critical": 95, "high": 75, "medium": 50, "low": 25}.get(p, 50)


def _find_campaign(state: dict[str, Any], campaign_id: str) -> dict[str, Any] | None:
    for c in state.get("campaigns") or []:
        if c.get("campaign_id") == campaign_id:
            return c
    return None


def collect_sources_lite(*, keyword: str = "", domain: str = "", project_id: str = "") -> dict[str, Any]:
    """Plan üretimi için hafif kaynak özeti — provider health fan-out yok."""
    return {
        "opportunity": {},
        "serp": {},
        "citation": {},
        "revenue": {},
        "authority_factory": {},
        "support_network": {},
        "crawl_gap": {},
        "rank": {},
        "executive": {},
        "keyword": keyword or "",
        "domain": domain or "",
        "project_id": project_id or "",
    }


def _collect_provider_warnings() -> list[str]:
    """Provider hatalarını warnings olarak topla; plan üretimini bloklamaz."""
    warnings: list[str] = []
    try:
        from app.moduller.publisher_hub import _channel_status

        for channel in ("blogger", "tumblr", "wordpress", "devto"):
            try:
                st = _channel_status(channel)
                if st.get("configured") and not st.get("connected"):
                    err = str(st.get("error") or "not_connected")
                    if "invalid_grant" in err.lower() or "token" in err.lower():
                        warnings.append(f"{channel}:provider_auth_failed:{err}")
                    else:
                        warnings.append(f"{channel}:provider_warning:{err}")
            except Exception as exc:
                warnings.append(f"{channel}:provider_check_failed:{exc}")
    except Exception as exc:
        warnings.append(f"provider_check_failed:{exc}")
    return warnings


def collect_sources(*, keyword: str = "", domain: str = "", project_id: str = "") -> dict[str, Any]:
    pid = project_id or ""
    kw = keyword or ""
    return {
        "opportunity": _safe_read("opportunity_engine", "dashboard", pid, default={}),
        "serp": _safe_read("serp_defense_engine", "dashboard", pid, default={}),
        "citation": _safe_read("citation_engine", "mission_control_payload", default={}),
        "revenue": _safe_read("revenue_lead_engine", "mission_control_payload", default={}),
        "authority_factory": _safe_read("authority_factory", "mission_control_payload", default={}),
        "support_network": _safe_read("support_network_engine", "dashboard", default={}),
        "crawl_gap": _safe_read("crawl_gap_engine", "dashboard", pid, default={}),
        "rank": _safe_read("rank_index_watcher", "health", default={}),
        "executive": _safe_read("executive_ai", "mission_control_payload", default={}),
    }


def _scale_blueprint(base: dict[str, int], factor: float) -> dict[str, int]:
    return {k: max(1, int(round(v * factor))) if k != "pillar" else max(1, int(v)) for k, v in base.items()}


def _goal_to_type(goal: str, campaign_type: str = "") -> str:
    if campaign_type and campaign_type in CAMPAIGN_TYPES:
        return campaign_type
    mapping = {
        "ranking": "ranking",
        "authority": "authority",
        "citation": "citation",
        "lead_generation": "lead",
    }
    return mapping.get(goal, "ranking")


def compute_blueprint(
    *,
    keyword: str,
    goal: str = "ranking",
    campaign_type: str = "",
    sources: dict[str, Any] | None = None,
) -> dict[str, Any]:
    src = sources or collect_sources(keyword=keyword)
    settings = get_settings()
    bp = dict(DEFAULT_BLUEPRINT)
    ctype = _goal_to_type(goal, campaign_type)

    opp = src.get("opportunity") or {}
    crawl = src.get("crawl_gap") or {}
    cite = src.get("citation") or {}
    rev = src.get("revenue") or {}
    serp = src.get("serp") or {}

    factor = 1.0
    if ctype == "full_domination":
        factor = 1.5
    elif ctype == "local_geo":
        bp["entity"] = max(bp["entity"], 30)
        bp["faq"] = max(bp["faq"], 40)
        factor = 1.1
    elif ctype == "authority":
        factor = 1.2
        bp["authority_source"] = max(bp["authority_source"], 15)
        bp["support_site"] = max(bp["support_site"], 8)
    elif ctype == "citation":
        bp["citation_expansion"] = max(bp["citation_expansion"], 20)
        factor = 1.0
    elif ctype == "lead":
        bp["publisher_content"] = max(bp["publisher_content"], 30)
        factor = 1.1

    if int(crawl.get("faq_gaps") or 0) > 10:
        bp["faq"] = max(bp["faq"], int(crawl.get("faq_gaps") or 0) + 20)
    if int(crawl.get("entity_gaps") or 0) > 5:
        bp["entity"] = max(bp["entity"], int(crawl.get("entity_gaps") or 0) + 10)
    if int(cite.get("citation_risks") or 0) >= int(settings.get("citation_gap_threshold") or 15):
        bp["citation_expansion"] += int(cite.get("citation_risks") or 0)
    if int(serp.get("critical_pressure_count") or 0) > 0:
        bp["refresh"] = max(bp["refresh"], 12)
        bp["cluster"] = max(bp["cluster"], 15)

    if settings.get("commercial_intent_boost") and int(rev.get("high_value_leads") or 0) > 0:
        bp["publisher_content"] = max(bp["publisher_content"], 30)

    quick_wins = int(opp.get("quick_wins") or 0)
    if quick_wins > 3:
        bp["cluster"] = max(bp["cluster"], 12 + quick_wins)

    scaled = _scale_blueprint(bp, factor)
    return {
        "keyword": keyword,
        "goal": goal,
        "campaign_type": ctype,
        "counts": scaled,
        "sources_used": list(src.keys()),
        "adjustments": {
            "faq_gaps": crawl.get("faq_gaps", 0),
            "entity_gaps": crawl.get("entity_gaps", 0),
            "citation_risks": cite.get("citation_risks", 0),
            "serp_critical": serp.get("critical_pressure_count", 0),
            "quick_wins": quick_wins,
            "high_value_leads": rev.get("high_value_leads", 0),
        },
    }


def build_weekly_blueprint(blueprint: dict[str, Any]) -> dict[str, Any]:
    counts = blueprint.get("counts") or DEFAULT_BLUEPRINT
    ctype = blueprint.get("campaign_type", "ranking")

    schedule: dict[str, Any] = {}
    w1 = {"phase": "Foundation", "focus": ["pillar", "cluster"], "items": {}}
    w1["items"] = {k: counts.get(k, 0) for k in ("pillar", "cluster") if counts.get(k, 0)}
    schedule["week_1"] = w1

    w2 = {"phase": "Expansion", "focus": ["faq", "entity"], "items": {}}
    w2["items"] = {k: counts.get(k, 0) for k in ("faq", "entity") if counts.get(k, 0)}
    schedule["week_2"] = w2

    w3 = {"phase": "Authority", "focus": ["authority_source", "support_site", "publisher_content"], "items": {}}
    w3["items"] = {k: counts.get(k, 0) for k in ("authority_source", "support_site", "publisher_content") if counts.get(k, 0)}
    schedule["week_3"] = w3

    w4 = {"phase": "Defense", "focus": ["citation_expansion", "refresh"], "items": {}}
    w4["items"] = {k: counts.get(k, 0) for k in ("citation_expansion", "refresh") if counts.get(k, 0)}
    if ctype in ("lead", "full_domination"):
        w4["items"]["publisher_content"] = max(5, counts.get("publisher_content", 0) // 3)
    schedule["week_4"] = w4

    w5 = {"phase": "Maintenance", "focus": ["refresh", "citation_expansion"], "items": {}}
    w5["items"] = {
        "refresh": max(2, counts.get("refresh", 0) // 2),
        "citation_expansion": max(3, counts.get("citation_expansion", 0) // 3),
    }
    schedule["week_5_plus"] = w5
    return schedule


def _task_specs(blueprint: dict[str, Any], weekly: dict[str, Any], campaign: dict[str, Any]) -> list[dict[str, Any]]:
    counts = blueprint.get("counts") or {}
    kw = campaign.get("target_keyword", "")
    cid = campaign.get("campaign_id", "")
    domain = campaign.get("target_domain", "")
    priority = _priority_num(campaign.get("priority", "medium"))
    specs: list[dict[str, Any]] = []

    module_map = {
        "pillar": ("place_seo_pipeline", "create_pillar", 85),
        "cluster": ("crawl_gap_engine", "expand_cluster", 70),
        "faq": ("question_intelligence_engine", "generate_faq", 65),
        "entity": ("entity_detail_generator", "create_entity_page", 72),
        "authority_source": ("authority_factory", "create_authority_batch", 80),
        "publisher_content": ("publisher_hub", "queue_publish", 60),
        "support_site": ("support_network_engine", "plan_support_site", 75),
        "citation_expansion": ("citation_engine", "citation_opportunity", 68),
        "refresh": ("content_refresh_engine", "schedule_refresh", 55),
    }

    week_idx = 0
    for week_key, week_data in weekly.items():
        week_idx += 1
        for item_type, count in (week_data.get("items") or {}).items():
            mod, action, impact_base = module_map.get(item_type, ("action_orchestrator", "content_refresh", 50))
            for i in range(int(count or 0)):
                specs.append({
                    "campaign_id": cid,
                    "module": mod,
                    "action_type": action,
                    "priority": min(100, priority + (10 if week_idx <= 2 else 0)),
                    "estimated_impact": min(95, impact_base + (i % 5)),
                    "status": "planned",
                    "week": week_key,
                    "item_type": item_type,
                    "title": f"{item_type.replace('_', ' ').title()} #{i + 1}: {kw}"[:120],
                    "keyword": kw,
                    "domain": domain,
                    "payload": {"item_type": item_type, "week": week_key, "index": i + 1},
                })

    if campaign.get("goal") in ("ranking", "lead_generation") or campaign.get("campaign_type") == "full_domination":
        specs.append({
            "campaign_id": cid,
            "module": "serp_defense_engine",
            "action_type": "serp_defense_pack",
            "priority": min(100, priority + 15),
            "estimated_impact": 78,
            "status": "planned",
            "week": "week_4",
            "item_type": "serp_defense",
            "title": f"SERP Defense Pack: {kw}",
            "keyword": kw,
            "domain": domain,
            "payload": {"defense": True},
        })

    if int(blueprint.get("adjustments", {}).get("citation_risks", 0) or 0) >= get_settings().get("citation_gap_threshold", 15):
        specs.append({
            "campaign_id": cid,
            "module": "citation_engine",
            "action_type": "close_citation_gap",
            "priority": min(100, priority + 10),
            "estimated_impact": 72,
            "status": "planned",
            "week": "week_4",
            "item_type": "citation_gap",
            "title": f"Citation gap close: {kw}",
            "keyword": kw,
            "payload": {"citation_gap": True},
        })

    if get_settings().get("commercial_intent_boost") and campaign.get("goal") == "lead_generation":
        specs.append({
            "campaign_id": cid,
            "module": "revenue_lead_engine",
            "action_type": "optimize_lead_funnel",
            "priority": min(100, priority + 12),
            "estimated_impact": 70,
            "status": "planned",
            "week": "week_3",
            "item_type": "revenue",
            "title": f"Lead funnel optimize: {kw}",
            "keyword": kw,
            "payload": {"commercial": True},
        })

    return specs


def _tasks_to_records(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for spec in specs:
        out.append({
            "task_id": f"ctask-{uuid.uuid4().hex[:10]}",
            "campaign_id": spec["campaign_id"],
            "module": spec["module"],
            "action_type": spec["action_type"],
            "priority": spec["priority"],
            "status": spec.get("status", "planned"),
            "estimated_impact": spec.get("estimated_impact", 0),
            "title": spec.get("title", ""),
            "keyword": spec.get("keyword", ""),
            "week": spec.get("week", ""),
            "item_type": spec.get("item_type", ""),
            "payload": spec.get("payload") or {},
            "created_at": _now(),
            "orchestrator_action_id": "",
        })
    return out


def compute_campaign_scores(campaign: dict[str, Any], sources: dict[str, Any] | None = None) -> dict[str, int]:
    src = sources or campaign.get("sources") or collect_sources(
        keyword=campaign.get("target_keyword", ""),
        domain=campaign.get("target_domain", ""),
        project_id=campaign.get("project_id", ""),
    )
    opp = src.get("opportunity") or {}
    serp = src.get("serp") or {}
    cite = src.get("citation") or {}
    rev = src.get("revenue") or {}
    af = src.get("authority_factory") or {}

    tasks = campaign.get("tasks") or []
    completed = sum(1 for t in tasks if t.get("status") == "completed")
    total = max(len(tasks), 1)
    execution = _clamp(completed / total * 100)

    ranking = _clamp(
        min(100, (opp.get("quick_wins") or 0) * 8 + min(100, (opp.get("total_opportunities") or 0) * 2) + 40)
    )
    authority = _clamp(min(100, (af.get("published_today") or 0) * 10 + (af.get("queued_batches") or 0) * 8 + 45))
    citation = _clamp(float(cite.get("citation_health_score") or 50))
    revenue = _clamp(min(100, (rev.get("today_leads") or 0) * 12 + (rev.get("high_value_leads") or 0) * 15 + 35))
    risk = _clamp(min(100, (serp.get("critical_pressure_count") or 0) * 15 + len(serp.get("top_risks") or []) * 5))

    overall = _clamp(
        ranking * 0.20 + authority * 0.18 + citation * 0.15 + revenue * 0.15
        + execution * 0.22 - risk * 0.10
    )

    return {
        "ranking": ranking,
        "authority": authority,
        "citation": citation,
        "revenue": revenue,
        "execution": execution,
        "risk": risk,
        "overall": overall,
    }


def _update_campaign_progress(state: dict[str, Any], campaign: dict[str, Any]) -> None:
    cid = campaign.get("campaign_id", "")
    all_tasks = [t for t in (state.get("tasks") or []) if t.get("campaign_id") == cid]
    campaign["tasks"] = all_tasks
    if not all_tasks:
        campaign["progress"] = 0
        return
    completed = sum(1 for t in all_tasks if t.get("status") == "completed")
    failed = sum(1 for t in all_tasks if t.get("status") == "failed")
    campaign["progress"] = _clamp(completed / len(all_tasks) * 100)
    if failed > 0 and failed >= len(all_tasks) // 2:
        campaign["status"] = "failed"
        _record_brain("campaign_failed", keyword=campaign.get("target_keyword", ""), result={"campaign_id": cid})
    elif campaign["progress"] >= 100:
        campaign["status"] = "completed"
        _record_brain("campaign_completed", keyword=campaign.get("target_keyword", ""), result={"campaign_id": cid})
        _record_brain("campaign_goal_reached", keyword=campaign.get("target_keyword", ""), result={"progress": 100})
    campaign["updated_at"] = _now()


def create_campaign(
    *,
    name: str = "",
    target_keyword: str = "",
    target_domain: str = "",
    target_market: str = "",
    goal: str = "ranking",
    campaign_type: str = "",
    priority: str = "medium",
    project_id: str = "",
) -> dict[str, Any]:
    kw = (target_keyword or "").strip()
    if not kw:
        return {"success": False, "error": "target_keyword gerekli"}

    if goal not in GOALS:
        goal = get_settings().get("default_goal", "ranking")
    if priority not in PRIORITIES:
        priority = get_settings().get("default_priority", "medium")

    st = _load_state()
    cid = f"camp-{uuid.uuid4().hex[:10]}"
    campaign = {
        "campaign_id": cid,
        "name": (name or f"{kw.title()} Campaign").strip(),
        "target_keyword": kw,
        "target_domain": (target_domain or "").strip(),
        "target_market": (target_market or "").strip(),
        "goal": goal,
        "campaign_type": _goal_to_type(goal, campaign_type),
        "status": "planned",
        "priority": priority,
        "project_id": project_id or "",
        "created_at": _now(),
        "updated_at": _now(),
        "progress": 0,
        "score": 0,
        "scores": {},
        "blueprint": {},
        "weekly_blueprint": {},
        "sources": {},
        "dataset_id": "",
        "dataset_source": "",
        "dataset_summary": {},
        "dataset_entities": [],
        "dataset_faqs": [],
        "dataset_categories": [],
        "dataset_backed_campaign": False,
        "index_recovery": False,
    }
    st.setdefault("campaigns", []).insert(0, campaign)
    st["campaigns"] = st["campaigns"][:CAMPAIGN_LIMIT]
    _append_history(st, {"action": "create", "campaign_id": cid, "keyword": kw, "at": _now()})
    _save_state(st)
    _record_brain("campaign_created", keyword=kw, result={"campaign_id": cid, "goal": goal})
    return {"success": True, "campaign": campaign}


def generate_plan(campaign_id: str) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}

    if campaign.get("dataset_id"):
        return _generate_dataset_plan(st, campaign)

    sources = collect_sources(
        keyword=campaign.get("target_keyword", ""),
        domain=campaign.get("target_domain", ""),
        project_id=campaign.get("project_id", ""),
    )
    blueprint = compute_blueprint(
        keyword=campaign.get("target_keyword", ""),
        goal=campaign.get("goal", "ranking"),
        campaign_type=campaign.get("campaign_type", ""),
        sources=sources,
    )
    weekly = build_weekly_blueprint(blueprint)
    specs = _task_specs(blueprint, weekly, campaign)
    tasks = _tasks_to_records(specs)

    st["tasks"] = [t for t in (st.get("tasks") or []) if t.get("campaign_id") != campaign_id] + tasks
    st["tasks"] = st["tasks"][-TASK_LIMIT:]

    campaign["blueprint"] = blueprint
    campaign["weekly_blueprint"] = weekly
    campaign["sources"] = sources
    campaign["tasks"] = tasks
    campaign["status"] = "active"
    campaign["updated_at"] = _now()

    if get_settings().get("auto_score_on_plan"):
        scores = compute_campaign_scores(campaign, sources)
        campaign["scores"] = scores
        campaign["score"] = scores.get("overall", 0)

    _append_history(st, {"action": "generate_plan", "campaign_id": campaign_id, "tasks": len(tasks), "at": _now()})
    _save_state(st)
    _record_brain("campaign_started", keyword=campaign.get("target_keyword", ""), result={"campaign_id": campaign_id, "tasks": len(tasks)})

    return {
        "success": True,
        "campaign": campaign,
        "blueprint": blueprint,
        "weekly_blueprint": weekly,
        "tasks": tasks,
        "task_count": len(tasks),
    }


def create_authority_batch(campaign_id: str) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}

    counts = (campaign.get("blueprint") or {}).get("counts") or DEFAULT_BLUEPRINT
    factory_counts = {
        "google_sites": max(1, counts.get("support_site", 0) // 2),
        "github_pages": max(1, counts.get("authority_source", 0) // 3),
        "blogger": max(1, counts.get("publisher_content", 0) // 5),
        "tumblr": max(0, counts.get("publisher_content", 0) // 8),
    }
    result = _safe_read(
        "authority_factory", "create_batch",
        campaign.get("target_keyword", ""),
        money_site=campaign.get("target_domain", ""),
        name=f"Campaign {campaign.get('name', '')} Authority",
        source="campaign_engine",
        factory_counts=factory_counts,
        project_id=campaign.get("project_id", ""),
        default={"success": False, "error": "authority_factory unavailable"},
    )
    if result.get("success"):
        campaign.setdefault("authority_batches", []).insert(0, {
            "batch_id": (result.get("batch") or {}).get("batch_id") or result.get("batch_id"),
            "created_at": _now(),
        })
        _save_state(st)
    return result


def send_to_orchestrator(campaign_id: str) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}

    tasks = [t for t in (st.get("tasks") or []) if t.get("campaign_id") == campaign_id and t.get("status") == "planned"]
    if not tasks:
        return {"success": False, "error": "Gönderilecek planned task yok — önce generate-plan çalıştırın"}

    imported = 0
    skipped = 0
    action_ids: list[str] = []

    for task in tasks:
        ao_priority = "CRITICAL" if task.get("priority", 0) >= 85 else "HIGH" if task.get("priority", 0) >= 70 else "MEDIUM"
        res = _safe_read(
            "action_orchestrator", "create_action",
            source_module="campaign_engine",
            action_type=task.get("action_type", "content_refresh"),
            project_id=campaign.get("project_id", ""),
            keyword=task.get("keyword") or campaign.get("target_keyword", ""),
            title=task.get("title", ""),
            priority=ao_priority,
            estimated_gain=int(task.get("estimated_impact") or 0),
            payload={
                **(task.get("payload") or {}),
                "campaign_id": campaign_id,
                "task_id": task.get("task_id"),
                "module": task.get("module"),
            },
            default={"success": False},
        )
        if res.get("success"):
            action = res.get("action") or {}
            task["status"] = "queued"
            task["orchestrator_action_id"] = action.get("action_id", "")
            action_ids.append(action.get("action_id", ""))
            imported += 1
        else:
            skipped += 1

    campaign["status"] = "active"
    campaign["updated_at"] = _now()
    _append_history(st, {"action": "send_to_orchestrator", "campaign_id": campaign_id, "imported": imported, "at": _now()})
    _save_state(st)

    return {
        "success": True,
        "campaign_id": campaign_id,
        "imported": imported,
        "skipped": skipped,
        "action_ids": action_ids,
    }


def list_campaigns(*, status: str = "", limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    items = st.get("campaigns") or []
    if status:
        items = [c for c in items if c.get("status") == status]
    for c in items:
        cid = c.get("campaign_id", "")
        c["tasks"] = [t for t in (st.get("tasks") or []) if t.get("campaign_id") == cid]
        _update_campaign_progress(st, c)
    return {"success": True, "campaigns": items[:limit], "count": len(items[:limit])}


def get_campaign(campaign_id: str) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}
    campaign["tasks"] = [t for t in (st.get("tasks") or []) if t.get("campaign_id") == campaign_id]
    _update_campaign_progress(st, campaign)
    _save_state(st)
    return {"success": True, "campaign": campaign}


def list_tasks(*, campaign_id: str = "", status: str = "", limit: int = 200) -> dict[str, Any]:
    st = _load_state()
    items = st.get("tasks") or []
    if campaign_id:
        items = [t for t in items if t.get("campaign_id") == campaign_id]
    if status:
        items = [t for t in items if t.get("status") == status]
    return {"success": True, "tasks": items[:limit], "count": len(items[:limit])}


def pause_campaign(campaign_id: str) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}
    campaign["status"] = "paused"
    campaign["updated_at"] = _now()
    _save_state(st)
    _record_brain("campaign_paused", keyword=campaign.get("target_keyword", ""), result={"campaign_id": campaign_id})
    return {"success": True, "campaign": campaign}


def mission_control_payload() -> dict[str, Any]:
    st = _load_state()
    campaigns = st.get("campaigns") or []
    active = [c for c in campaigns if c.get("status") == "active"]
    completed = [c for c in campaigns if c.get("status") == "completed"]

    for c in campaigns:
        cid = c.get("campaign_id", "")
        c["tasks"] = [t for t in (st.get("tasks") or []) if t.get("campaign_id") == cid]
        if not c.get("scores"):
            c["scores"] = compute_campaign_scores(c)

    top = sorted(active or campaigns, key=lambda x: -(x.get("score") or 0))[:1]
    top_c = top[0] if top else None
    avg_progress = 0
    if active:
        for c in active:
            tasks = c.get("tasks") or []
            if tasks:
                avg_progress += sum(1 for t in tasks if t.get("status") == "completed") / len(tasks) * 100
        avg_progress = int(avg_progress / len(active))

    roi = 0
    if top_c:
        sc = top_c.get("scores") or {}
        roi = _clamp((sc.get("revenue", 0) + sc.get("ranking", 0)) / 2)

    return {
        "success": True,
        "active_campaigns": len(active),
        "total_campaigns": len(campaigns),
        "completed_campaigns": len(completed),
        "campaign_progress_avg": avg_progress,
        "campaign_roi_estimate": roi,
        "top_campaign": top_c,
        "recent_campaigns": campaigns[:5],
        "dataset_campaigns": sum(1 for c in campaigns if c.get("dataset_id")),
        "dataset_attached_campaigns": sum(1 for c in campaigns if c.get("dataset_backed_campaign")),
        "campaigns_ready_for_factory": sum(
            1 for c in campaigns
            if c.get("status") == "active"
            and any(
                t.get("item_type") in ("authority_source", "publisher_content", "support_site", "citation_expansion")
                for t in (c.get("tasks") or [])
            )
        ),
    }


def executive_alignment_payload() -> dict[str, Any]:
    """Executive AI priority → campaign eşleşmesi."""
    st = _load_state()
    campaigns = st.get("campaigns") or []
    exec_data = _safe_read("executive_ai", "mission_control_payload", default={})
    top_pri = exec_data.get("top_priority") or {}
    pri_kw = (top_pri.get("keyword") or top_pri.get("title") or "").lower()

    matches: list[dict[str, Any]] = []
    for c in campaigns:
        kw = (c.get("target_keyword") or "").lower()
        score = 0
        if pri_kw and pri_kw in kw:
            score += 50
        if c.get("status") == "active":
            score += 20
        if c.get("dataset_backed_campaign") or c.get("dataset_id"):
            score += 25
        score += int(c.get("score") or 0) * 0.3
        if score > 0:
            matches.append({
                "campaign_id": c.get("campaign_id"),
                "name": c.get("name"),
                "alignment_score": _clamp(score),
                "keyword": c.get("target_keyword"),
                "dataset_backed_campaign": bool(c.get("dataset_backed_campaign") or c.get("dataset_id")),
            })

    matches.sort(key=lambda x: -x.get("alignment_score", 0))
    return {
        "success": True,
        "executive_top_priority": top_pri,
        "aligned_campaigns": matches[:5],
        "best_match": matches[0] if matches else None,
    }


def dashboard() -> dict[str, Any]:
    st = _load_state()
    mc = mission_control_payload()
    align = executive_alignment_payload()
    campaigns = st.get("campaigns") or []
    all_tasks = st.get("tasks") or []
    return {
        "success": True,
        "module": "campaign_engine",
        "enabled": get_settings().get("enabled", True),
        "campaigns_total": len(campaigns),
        "tasks_total": len(all_tasks),
        "active_campaigns": mc.get("active_campaigns", 0),
        "campaign_progress_avg": mc.get("campaign_progress_avg", 0),
        "top_campaign": mc.get("top_campaign"),
        "executive_alignment": align,
        "recent_campaigns": campaigns[:8],
        "campaign_types": list(CAMPAIGN_TYPES),
        "goals": list(GOALS),
        "default_blueprint": DEFAULT_BLUEPRINT,
        "settings": get_settings(),
    }


def health() -> dict[str, Any]:
    dash = dashboard()
    return {
        "success": True,
        "module": "campaign_engine",
        "enabled": get_settings().get("enabled", True),
        "campaigns_total": dash.get("campaigns_total", 0),
        "active_campaigns": dash.get("active_campaigns", 0),
        "produces_content": False,
        "publishes": False,
    }


def update_task_factory_status(task_id: str, status: str) -> dict[str, Any]:
    """Authority Factory V2 — campaign task durum güncellemesi."""
    allowed = {
        "planned", "sent_to_factory", "factory_processing", "factory_completed",
        "completed", "failed", "paused",
    }
    if status not in allowed:
        return {"success": False, "error": f"invalid_status:{status}"}
    st = _load_state()
    task = next((t for t in (st.get("tasks") or []) if t.get("task_id") == task_id), None)
    if not task:
        return {"success": False, "error": f"Task not found: {task_id}"}
    task["status"] = status
    task["updated_at"] = _now()
    _save_state(st)
    return {"success": True, "task": task}


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if report_type == "campaigns":
        payload = list_campaigns(limit=100)
    elif report_type == "tasks":
        payload = list_tasks(limit=500)
    else:
        payload = dashboard()
    path = REPORTS_DIR / f"campaign-engine-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


# ─── Dataset Bridge (Data Miner → Campaign) ───────────────────────────────────


def _load_dataset(dataset_id: str) -> dict[str, Any]:
    """Data Miner state'inden gerçek dataset yükle — mock yok."""
    did = (dataset_id or "").strip()
    if not did:
        return {"success": False, "error": "dataset_id gerekli"}
    try:
        from app.moduller.data_miner_engine import get_results
        res = get_results(did)
    except Exception as exc:
        return {"success": False, "error": f"data_miner_unavailable:{exc}"}
    if not res.get("success"):
        return {"success": False, "error": res.get("error") or "dataset_not_found", "dataset_id": did}
    if res.get("status") not in ("completed", "success"):
        return {
            "success": False,
            "error": "dataset_not_ready",
            "dataset_id": did,
            "status": res.get("status"),
        }
    return res


def _dataset_snapshot_from_job(job: dict[str, Any]) -> dict[str, Any]:
    result = job.get("result") or {}
    entities = list(result.get("entities") or [])
    faqs = list(result.get("faqs") or [])
    categories = list(result.get("categories") or [])
    addresses = list(result.get("addresses") or [])
    phones = list(result.get("phones") or [])
    emails = list(result.get("emails") or [])
    schema_types = list(result.get("schema_types") or [])
    return {
        "dataset_id": job.get("job_id") or job.get("dataset_id", ""),
        "dataset_source": job.get("source") or result.get("source") or "",
        "dataset_summary": {
            "entity_count": len(entities),
            "faq_count": len(faqs),
            "category_count": len(categories),
            "phone_count": len(phones),
            "email_count": len(emails),
            "address_count": len(addresses),
            "schema_type_count": len(schema_types),
        },
        "dataset_entities": entities,
        "dataset_faqs": faqs,
        "dataset_categories": categories,
        "dataset_addresses": addresses,
        "dataset_phones": phones,
        "dataset_emails": emails,
        "dataset_schema_types": schema_types,
    }


def _apply_dataset_to_campaign(campaign: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    snap = _dataset_snapshot_from_job(job)
    campaign.update(snap)
    campaign["dataset_backed_campaign"] = True
    campaign["updated_at"] = _now()
    return campaign


def list_datasets_for_campaign() -> dict[str, Any]:
    """Data Miner dataset listesi — campaign panel için zenginleştirilmiş."""
    try:
        from app.moduller.data_miner_engine import list_datasets, get_results
        base = list_datasets()
    except Exception as exc:
        return {"success": False, "error": str(exc), "datasets": []}
    enriched: list[dict[str, Any]] = []
    for ds in base.get("datasets") or []:
        did = ds.get("id", "")
        job_res = get_results(did) if did else {}
        result = (job_res.get("result") or {}) if job_res.get("success") else {}
        enriched.append({
            "dataset_id": did,
            "source": ds.get("source") or job_res.get("source", ""),
            "type": ds.get("type") or job_res.get("job_type", ""),
            "created_at": ds.get("created_at") or job_res.get("created_at", ""),
            "status": job_res.get("status", "unknown"),
            "entity_count": len(result.get("entities") or []),
            "faq_count": len(result.get("faqs") or []),
            "category_count": len(result.get("categories") or []),
            "phone_count": len(result.get("phones") or []),
            "address_count": len(result.get("addresses") or []),
        })
    return {"success": True, "datasets": enriched, "count": len(enriched)}


def create_from_dataset(
    *,
    dataset_id: str,
    target_domain: str = "",
    campaign_type: str = "full_domination",
    goal: str = "ranking",
    market: str = "",
    primary_keyword: str = "",
    name: str = "",
    priority: str = "high",
    project_id: str = "",
) -> dict[str, Any]:
    job = _load_dataset(dataset_id)
    if not job.get("success"):
        return job

    kw = (primary_keyword or job.get("source") or "").strip()
    if not kw:
        return {"success": False, "error": "primary_keyword gerekli"}

    res = create_campaign(
        name=name or f"{kw.title()} Dataset Campaign",
        target_keyword=kw,
        target_domain=target_domain,
        target_market=market,
        goal=goal,
        campaign_type=campaign_type or "full_domination",
        priority=priority,
        project_id=project_id,
    )
    if not res.get("success"):
        return res

    st = _load_state()
    campaign = _find_campaign(st, res["campaign"]["campaign_id"])
    if not campaign:
        return {"success": False, "error": "campaign_create_failed"}

    _apply_dataset_to_campaign(campaign, job)
    if "index recovery" in (campaign.get("name") or "").lower():
        campaign["index_recovery"] = True

    _append_history(st, {
        "action": "create_from_dataset",
        "campaign_id": campaign["campaign_id"],
        "dataset_id": dataset_id,
        "at": _now(),
    })
    _save_state(st)
    _record_brain(
        "campaign_created_from_dataset",
        keyword=kw,
        result={"campaign_id": campaign["campaign_id"], "dataset_id": dataset_id},
    )
    return {"success": True, "campaign": campaign, "dataset_id": dataset_id}


def attach_dataset(campaign_id: str, dataset_id: str) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}

    job = _load_dataset(dataset_id)
    if not job.get("success"):
        return job

    _apply_dataset_to_campaign(campaign, job)
    if "index recovery" in (campaign.get("name") or "").lower():
        campaign["index_recovery"] = True

    _append_history(st, {
        "action": "attach_dataset",
        "campaign_id": campaign_id,
        "dataset_id": dataset_id,
        "at": _now(),
    })
    _save_state(st)
    _record_brain(
        "campaign_dataset_attached",
        keyword=campaign.get("target_keyword", ""),
        result={"campaign_id": campaign_id, "dataset_id": dataset_id},
    )
    return {"success": True, "campaign": campaign, "dataset_id": dataset_id}


def _compute_dataset_blueprint(campaign: dict[str, Any]) -> dict[str, Any]:
    summary = campaign.get("dataset_summary") or {}
    base = compute_blueprint(
        keyword=campaign.get("target_keyword", ""),
        goal=campaign.get("goal", "ranking"),
        campaign_type=campaign.get("campaign_type", "full_domination"),
        sources=campaign.get("sources") or collect_sources_lite(
            keyword=campaign.get("target_keyword", ""),
            domain=campaign.get("target_domain", ""),
            project_id=campaign.get("project_id", ""),
        ),
    )
    counts = dict(base.get("counts") or DEFAULT_BLUEPRINT)
    counts["entity"] = max(counts.get("entity", 0), int(summary.get("entity_count") or 0))
    counts["faq"] = max(counts.get("faq", 0), int(summary.get("faq_count") or 0))
    counts["cluster"] = max(counts.get("cluster", 0), int(summary.get("category_count") or 0))
    counts["citation_expansion"] = max(
        counts.get("citation_expansion", 0),
        int(summary.get("schema_type_count") or 0) + 5,
    )
    counts["publisher_content"] = max(
        counts.get("publisher_content", 0),
        int(summary.get("phone_count") or 0) + int(summary.get("email_count") or 0),
    )
    counts["authority_source"] = max(counts.get("authority_source", 0), 3)
    counts["support_site"] = max(counts.get("support_site", 0), 2)
    base["counts"] = counts
    base["dataset_driven"] = True
    base["dataset_summary"] = summary
    return base


def _dataset_task_specs(campaign: dict[str, Any], blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    cid = campaign.get("campaign_id", "")
    kw = campaign.get("target_keyword", "")
    domain = campaign.get("target_domain", "")
    priority = _priority_num(campaign.get("priority", "medium"))
    specs: list[dict[str, Any]] = []

    def _add(item_type: str, module: str, action: str, title: str, *, week: str = "week_2", payload: dict | None = None, impact: int = 70):
        specs.append({
            "campaign_id": cid,
            "module": module,
            "action_type": action,
            "priority": min(100, priority + 5),
            "estimated_impact": impact,
            "status": "planned",
            "week": week,
            "item_type": item_type,
            "title": title[:120],
            "keyword": kw,
            "domain": domain,
            "payload": payload or {},
            "factory_eligible": item_type in ("authority_source", "publisher_content", "support_site", "citation_expansion"),
        })

    entities = campaign.get("dataset_entities") or []
    for i, ent in enumerate(entities[:20]):
        label = ent.get("label") or ent.get("name") or f"Entity {i + 1}"
        _add(
            "entity_page", "entity_detail_generator", "create_entity_page",
            f"Entity page: {label}",
            week="week_2",
            payload={"entity": ent, "dataset_id": campaign.get("dataset_id")},
            impact=72,
        )

    faqs = campaign.get("dataset_faqs") or []
    for i, faq in enumerate(faqs[:50]):
        q = faq.get("question") or f"FAQ {i + 1}"
        _add(
            "faq_page", "question_intelligence_engine", "generate_faq",
            f"FAQ page: {q[:80]}",
            week="week_2",
            payload={"faq": faq, "dataset_id": campaign.get("dataset_id")},
            impact=68,
        )

    categories = campaign.get("dataset_categories") or []
    for i, cat in enumerate(categories[:12]):
        _add(
            "cluster", "crawl_gap_engine", "expand_cluster",
            f"Category cluster: {str(cat)[:60]}",
            week="week_1",
            payload={"category": cat, "dataset_id": campaign.get("dataset_id")},
            impact=70,
        )

    addresses = campaign.get("dataset_addresses") or []
    for i, addr in enumerate(addresses[:10]):
        _add(
            "geo_page", "place_seo_pipeline", "create_geo_pages",
            f"GEO page: {str(addr)[:60]}",
            week="week_2",
            payload={"address": addr, "dataset_id": campaign.get("dataset_id")},
            impact=74,
        )

    schema_types = campaign.get("dataset_schema_types") or []
    for i, stype in enumerate(schema_types[:8]):
        _add(
            "citation_expansion", "citation_engine", "citation_opportunity",
            f"Schema expansion: {str(stype)[:50]}",
            week="week_4",
            payload={"schema_type": stype},
            impact=66,
        )

    phones = campaign.get("dataset_phones") or []
    emails = campaign.get("dataset_emails") or []
    for i, phone in enumerate(phones[:5]):
        _add(
            "publisher_content", "publisher_hub", "queue_publish",
            f"Listing opportunity (phone): {phone}",
            week="week_3",
            payload={"phone": phone, "listing": True},
            impact=62,
        )
    for i, email in enumerate(emails[:5]):
        _add(
            "publisher_content", "publisher_hub", "queue_publish",
            f"Business dataset (email): {email}",
            week="week_3",
            payload={"email": email, "listing": True},
            impact=60,
        )

    # Authority Factory uyumlu çekirdek görevler — dataset verisiyle
    _add(
        "authority_source", "authority_factory", "create_authority_batch",
        f"Authority source: {kw}",
        week="week_3",
        payload={"entities": entities[:5], "faqs": faqs[:3], "dataset_id": campaign.get("dataset_id")},
        impact=82,
    )
    _add(
        "support_site", "support_network_engine", "plan_support_site",
        f"Support site: {kw}",
        week="week_3",
        payload={
            "categories": categories[:5],
            "entities": entities[:5],
            "faqs": faqs[:5],
            "dataset_id": campaign.get("dataset_id"),
        },
        impact=78,
    )
    _add(
        "citation_expansion", "citation_engine", "citation_opportunity",
        f"Citation expansion: {kw}",
        week="week_4",
        payload={
            "schema_types": schema_types,
            "entities": entities[:5],
            "faqs": faqs[:3],
            "dataset_id": campaign.get("dataset_id"),
        },
        impact=70,
    )
    _add(
        "publisher_content", "publisher_hub", "queue_publish",
        f"Publisher content: {kw}",
        week="week_3",
        payload={"faqs": faqs[:5], "entities": entities[:3]},
        impact=65,
    )

    if campaign.get("index_recovery"):
        for ir in INDEX_RECOVERY_TASKS:
            _add(
                ir["item_type"], ir["module"], ir["action_type"], ir["title"],
                week="week_1",
                payload={"index_recovery": True, "dataset_id": campaign.get("dataset_id")},
                impact=80,
            )

    return specs


def _generate_dataset_plan(st: dict[str, Any], campaign: dict[str, Any]) -> dict[str, Any]:
    if not campaign.get("dataset_id"):
        return {"success": False, "error": "dataset_id_missing"}

    job = _load_dataset(campaign["dataset_id"])
    if not job.get("success"):
        return job

    _apply_dataset_to_campaign(campaign, job)
    warnings = _collect_provider_warnings()
    sources = collect_sources_lite(
        keyword=campaign.get("target_keyword", ""),
        domain=campaign.get("target_domain", ""),
        project_id=campaign.get("project_id", ""),
    )
    sources["data_miner"] = {
        "dataset_id": campaign["dataset_id"],
        "summary": campaign.get("dataset_summary") or {},
    }
    campaign["sources"] = sources
    blueprint = _compute_dataset_blueprint(campaign)
    weekly = build_weekly_blueprint(blueprint)
    specs = _dataset_task_specs(campaign, blueprint)
    tasks = _tasks_to_records(specs)

    cid = campaign["campaign_id"]
    st["tasks"] = [t for t in (st.get("tasks") or []) if t.get("campaign_id") != cid] + tasks
    st["tasks"] = st["tasks"][-TASK_LIMIT:]

    campaign["blueprint"] = blueprint
    campaign["weekly_blueprint"] = weekly
    campaign["sources"] = sources
    campaign["tasks"] = tasks
    campaign["status"] = "active"
    plan_status = "generated_with_warnings" if warnings else "generated"
    campaign["plan_status"] = plan_status
    campaign["plan_warnings"] = warnings
    campaign["updated_at"] = _now()

    if get_settings().get("auto_score_on_plan"):
        scores = compute_campaign_scores(campaign, sources)
        campaign["scores"] = scores
        campaign["score"] = scores.get("overall", 0)

    _append_history(st, {
        "action": "generate_plan_from_dataset",
        "campaign_id": cid,
        "dataset_id": campaign["dataset_id"],
        "tasks": len(tasks),
        "plan_status": plan_status,
        "warnings": warnings,
        "at": _now(),
    })
    _save_state(st)
    _record_brain(
        "campaign_dataset_plan_generated",
        keyword=campaign.get("target_keyword", ""),
        result={
            "campaign_id": cid,
            "dataset_id": campaign["dataset_id"],
            "tasks": len(tasks),
            "plan_status": plan_status,
            "warnings": warnings,
        },
    )
    _record_brain("campaign_started", keyword=campaign.get("target_keyword", ""), result={"campaign_id": cid, "tasks": len(tasks)})

    return {
        "success": True,
        "campaign": campaign,
        "blueprint": blueprint,
        "weekly_blueprint": weekly,
        "tasks": tasks,
        "task_count": len(tasks),
        "dataset_driven": True,
        "plan_status": plan_status,
        "warnings": warnings,
    }


def generate_plan_from_dataset(campaign_id: str) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}
    if not campaign.get("dataset_id"):
        return {"success": False, "error": "campaign_has_no_dataset — önce attach-dataset veya create-from-dataset"}
    return _generate_dataset_plan(st, campaign)


def send_to_authority_factory(campaign_id: str, *, auto_process: bool = False) -> dict[str, Any]:
    st = _load_state()
    campaign = _find_campaign(st, campaign_id)
    if not campaign:
        return {"success": False, "error": f"Campaign not found: {campaign_id}"}

    factory_tasks = [
        t for t in (campaign.get("tasks") or st.get("tasks") or [])
        if t.get("campaign_id") == campaign_id
        and (
            t.get("item_type") in ("authority_source", "publisher_content", "support_site", "citation_expansion")
            or t.get("factory_eligible")
        )
    ]
    if not factory_tasks and not campaign.get("dataset_id"):
        return {"success": False, "error": "no_factory_tasks — önce generate-plan çalıştırın"}

    if not factory_tasks and campaign.get("dataset_id"):
        plan = generate_plan_from_dataset(campaign_id)
        if not plan.get("success"):
            return plan
        campaign = plan.get("campaign") or campaign

    result = _safe_read(
        "authority_factory", "create_from_campaign",
        campaign_id,
        auto_process=auto_process,
        default={"success": False, "error": "authority_factory unavailable"},
    )
    if result.get("success"):
        _record_brain(
            "campaign_sent_to_authority_factory",
            keyword=campaign.get("target_keyword", ""),
            result={"campaign_id": campaign_id, "batch_id": (result.get("batch") or {}).get("batch_id")},
        )
    return result
