"""HIVE Brain / Memory Engine V1 — merkezi hafıza katmanı."""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.brain")

STATE_FILE = Path(__file__).resolve().parent.parent / "hive_brain_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
HIVE_DATA_FILE = Path(__file__).resolve().parent.parent / "hive_data.json"

MAX_EVENTS = 10_000
MAX_DECISIONS = 2_000

EVENT_TYPES = {
    "project_created",
    "content_generated",
    "content_published",
    "content_refreshed",
    "quality_gate_pass",
    "quality_gate_fail",
    "keyword_tracked",
    "rank_drop",
    "rank_gain",
    "entity_created",
    "entity_missing",
    "faq_created",
    "deploy_started",
    "deploy_completed",
    "deploy_failed",
    "publisher_success",
    "publisher_failed",
    "network_created",
    "network_updated",
    "support_link_planned",
    "refresh_scheduled",
    "refresh_completed",
    "serp_defense_triggered",
    "citation_analysis_completed",
    "citation_gap_found",
    "citation_opportunity_created",
    "citation_score_increased",
    "citation_score_decreased",
    "executive_report_created",
    "executive_priority_changed",
    "executive_mission_generated",
    "executive_risk_detected",
    "executive_growth_detected",
    "provider_connected",
    "provider_disconnected",
    "provider_error_detected",
    "provider_health_restored",
    "audit_started",
    "audit_completed",
    "audit_issue_found",
    "audit_critical_found",
    "audit_issue_resolved",
    "campaign_created",
    "campaign_started",
    "campaign_completed",
    "campaign_paused",
    "campaign_goal_reached",
    "campaign_failed",
    "readiness_calculated",
    "launch_mode_changed",
    "production_ready",
    "enterprise_ready",
    "blocker_detected",
    "success_step_completed",
    "success_path_started",
    "success_path_completed",
    "first_campaign_created",
    "first_lead_received",
    "decision_recorded",
    "module_action",
    "performance_issue_detected",
    "performance_improved",
    "domain_discovered",
    "domain_expiring",
    "domain_scored",
    "authority_candidate_found",
    "data_mining_started",
    "data_mining_completed",
    "data_entity_discovered",
}

DEFAULT_STATE: dict[str, Any] = {
    "settings": {"max_events": MAX_EVENTS, "max_decisions": MAX_DECISIONS},
    "events": [],
    "decisions": [],
    "projects": {},
    "domains": {},
    "keywords": {},
    "last_backfill_at": None,
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key, val in DEFAULT_STATE.items():
                    data.setdefault(key, val if not isinstance(val, dict) else dict(val))
                return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("brain state load failed: %s", exc)
    return json.loads(json.dumps(DEFAULT_STATE))


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _new_event_id() -> str:
    return f"evt-{uuid.uuid4().hex[:12]}"


def _norm_domain(domain: str | None) -> str:
    if not domain:
        return ""
    d = domain.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d.split("/")[0]


def _norm_keyword(keyword: str | None) -> str:
    return (keyword or "").strip().lower()


def _event_summary(event: dict[str, Any]) -> str:
    et = event.get("event_type") or "module_action"
    module = event.get("module") or ""
    result = event.get("result") or {}
    keyword = event.get("keyword") or ""
    domain = event.get("domain") or ""
    templates = {
        "project_created": "Proje oluşturuldu",
        "content_generated": "İçerik üretildi",
        "content_published": "İçerik yayınlandı",
        "content_refreshed": "İçerik yenilendi",
        "quality_gate_pass": "Quality Gate geçildi",
        "quality_gate_fail": "Quality Gate başarısız",
        "keyword_tracked": f"Keyword izlendi: {keyword}" if keyword else "Keyword izlendi",
        "rank_drop": f"Sıra kaybı: {keyword}" if keyword else "Sıra kaybı tespit edildi",
        "rank_gain": f"Sıra kazancı: {keyword}" if keyword else "Sıra kazancı",
        "entity_created": "Entity oluşturuldu",
        "entity_missing": "Eksik entity tespit edildi",
        "faq_created": "FAQ oluşturuldu",
        "deploy_started": f"Deploy başladı: {domain}" if domain else "Deploy başladı",
        "deploy_completed": f"Deploy tamamlandı: {domain}" if domain else "Deploy tamamlandı",
        "deploy_failed": f"Deploy başarısız: {domain}" if domain else "Deploy başarısız",
        "publisher_success": "Publisher Hub yayını başarılı",
        "publisher_failed": "Publisher Hub yayını başarısız",
        "network_created": "Network oluşturuldu",
        "network_updated": "Network güncellendi",
        "support_link_planned": "Support link planı oluşturuldu",
        "refresh_scheduled": "Refresh planlandı",
        "refresh_completed": "Refresh tamamlandı",
        "serp_defense_triggered": f"SERP savunma tetiklendi: {keyword}" if keyword else "SERP savunma tetiklendi",
        "decision_recorded": "Karar kaydedildi",
        "module_action": f"{module} aksiyonu",
    }
    base = templates.get(et, et.replace("_", " "))
    if isinstance(result, dict):
        detail = result.get("summary") or result.get("mesaj") or result.get("message") or result.get("durum")
        if detail:
            return f"{base} — {detail}"
    return base


def _ensure_project(state: dict[str, Any], project_id: str) -> dict[str, Any]:
    projects = state.setdefault("projects", {})
    if project_id not in projects:
        projects[project_id] = {
            "project_id": project_id,
            "project_summary": "",
            "last_actions": [],
            "recent_events": [],
            "important_decisions": [],
            "next_recommended_actions": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
    return projects[project_id]


def _ensure_domain(state: dict[str, Any], domain: str) -> dict[str, Any]:
    domains = state.setdefault("domains", {})
    key = _norm_domain(domain)
    if not key:
        return {}
    if key not in domains:
        domains[key] = {
            "domain": key,
            "first_seen": _now(),
            "role_history": [],
            "authority_history": [],
            "publish_history": [],
            "deploy_history": [],
            "keyword_history": [],
        }
    return domains[key]


def _ensure_keyword(state: dict[str, Any], keyword: str) -> dict[str, Any]:
    keywords = state.setdefault("keywords", {})
    key = _norm_keyword(keyword)
    if not key:
        return {}
    if key not in keywords:
        keywords[key] = {
            "keyword": key,
            "first_discovery": _now(),
            "position_history": [],
            "fortress_history": [],
            "refresh_history": [],
            "defense_history": [],
            "publish_history": [],
        }
    return keywords[key]


def _append_limited(lst: list, item: Any, limit: int = 50) -> None:
    lst.insert(0, item)
    del lst[limit:]


def _update_indices(state: dict[str, Any], event: dict[str, Any]) -> None:
    project_id = event.get("project_id") or ""
    domain = event.get("domain") or ""
    keyword = event.get("keyword") or ""
    et = event.get("event_type") or ""
    ts = event.get("timestamp") or _now()
    status = event.get("status") or "ok"
    result = event.get("result") or {}

    if project_id:
        proj = _ensure_project(state, project_id)
        proj["updated_at"] = ts
        _append_limited(proj["last_actions"], {
            "event_id": event.get("event_id"),
            "event_type": et,
            "timestamp": ts,
            "summary": _event_summary(event),
            "status": status,
        }, 30)
        _append_limited(proj["recent_events"], event.get("event_id"), 40)
        proj["project_summary"] = _build_project_summary(state, project_id)

    dom_key = _norm_domain(domain)
    if dom_key:
        dom = _ensure_domain(state, dom_key)
        entry = {"timestamp": ts, "event_type": et, "status": status, "result": result}
        if et in ("deploy_started", "deploy_completed", "deploy_failed"):
            _append_limited(dom["deploy_history"], entry, 40)
        elif et in ("content_published", "publisher_success", "publisher_failed"):
            _append_limited(dom["publish_history"], entry, 40)
        elif et in ("network_created", "network_updated"):
            role = (event.get("metadata") or {}).get("role") or result.get("role")
            if role:
                _append_limited(dom["role_history"], {"timestamp": ts, "role": role}, 30)
        if keyword:
            _append_limited(dom["keyword_history"], {"timestamp": ts, "keyword": keyword, "event_type": et}, 40)

    kw_key = _norm_keyword(keyword)
    if kw_key:
        kw = _ensure_keyword(state, kw_key)
        entry = {"timestamp": ts, "event_type": et, "status": status, "result": result}
        if et in ("rank_drop", "rank_gain", "keyword_tracked"):
            pos = result.get("position") or result.get("rank") or result.get("avg_position")
            _append_limited(kw["position_history"], {**entry, "position": pos}, 60)
        if et == "serp_defense_triggered":
            _append_limited(kw["defense_history"], entry, 40)
        if et in ("refresh_scheduled", "refresh_completed", "content_refreshed"):
            _append_limited(kw["refresh_history"], entry, 40)
        if et in ("content_published", "publisher_success"):
            _append_limited(kw["publish_history"], entry, 40)
        if et == "quality_gate_pass" and result.get("fortress_score") is not None:
            _append_limited(kw["fortress_history"], {
                "timestamp": ts,
                "score": result.get("fortress_score"),
            }, 40)


def _infer_recommendations(state: dict[str, Any], project_id: str) -> list[str]:
    events = [e for e in state.get("events", []) if e.get("project_id") == project_id][:80]
    recs: list[str] = []
    types = {e.get("event_type") for e in events}
    if "quality_gate_fail" in types and "content_refreshed" not in types:
        recs.append("Quality Gate başarısız sayfalar için Content Refresh Engine ile tarama yapın.")
    if "rank_drop" in types and "serp_defense_triggered" not in types:
        recs.append("Sıra kaybı yaşanan keyword'ler için SERP Defense Engine analizi çalıştırın.")
    if "deploy_completed" in types and "publisher_success" not in types:
        recs.append("Deploy sonrası Publisher Hub ile dağıtım kanallarını senkronize edin.")
    if "entity_missing" in types:
        recs.append("Eksik entity'ler için Entity Detail Generator ile sayfa üretin.")
    if not recs:
        recs.append("Son olaylar stabil — haftalık Rank Watcher taraması önerilir.")
    return recs[:5]


def _build_project_summary(state: dict[str, Any], project_id: str) -> str:
    events = [e for e in state.get("events", []) if e.get("project_id") == project_id]
    if not events:
        return f"{project_id} için henüz kayıtlı olay yok."
    counts: dict[str, int] = defaultdict(int)
    for e in events:
        counts[e.get("event_type") or "unknown"] += 1
    parts = [f"{k.replace('_', ' ')}: {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])[:5]]
    return f"Toplam {len(events)} olay — " + ", ".join(parts)


def record_event(
    event_type: str,
    module: str,
    *,
    project_id: str = "",
    domain: str = "",
    keyword: str = "",
    entity: str = "",
    content_id: str = "",
    status: str = "ok",
    result: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    """Tek bir brain event kaydet ve indeksleri güncelle."""
    state = _load_state()
    event = {
        "event_id": _new_event_id(),
        "timestamp": _now(),
        "module": module,
        "event_type": event_type if event_type in EVENT_TYPES else "module_action",
        "project_id": project_id or "",
        "domain": _norm_domain(domain) or domain or "",
        "keyword": keyword or "",
        "entity": entity or "",
        "content_id": content_id or "",
        "status": status,
        "result": result or {},
        "metadata": metadata or {},
        "reason": reason or "",
        "summary": "",
    }
    event["summary"] = _event_summary(event)

    events = state.setdefault("events", [])
    events.insert(0, event)
    max_ev = int(state.get("settings", {}).get("max_events") or MAX_EVENTS)
    state["events"] = events[:max_ev]

    _update_indices(state, event)

    if project_id:
        proj = _ensure_project(state, project_id)
        proj["next_recommended_actions"] = _infer_recommendations(state, project_id)

    _save_state(state)
    return {"success": True, "event": event}


def record_decision(
    module: str,
    recommendation: str,
    reason: str = "",
    *,
    project_id: str = "",
    domain: str = "",
    keyword: str = "",
    applied: bool | None = None,
    outcome: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Modül önerisini decision memory'ye kaydet."""
    decision = {
        "decision_id": f"dec-{uuid.uuid4().hex[:10]}",
        "timestamp": _now(),
        "module": module,
        "recommendation": recommendation,
        "reason": reason,
        "project_id": project_id or "",
        "domain": _norm_domain(domain) or domain or "",
        "keyword": keyword or "",
        "applied": applied,
        "outcome": outcome or "",
        "metadata": metadata or {},
    }

    record_event(
        "decision_recorded",
        module,
        project_id=project_id,
        domain=domain,
        keyword=keyword,
        status="ok" if applied else ("pending" if applied is None else "skipped"),
        result={"recommendation": recommendation, "outcome": outcome},
        metadata={"decision_id": decision["decision_id"]},
        reason=reason,
    )

    state = _load_state()
    decisions = state.setdefault("decisions", [])
    decisions.insert(0, decision)
    max_dec = int(state.get("settings", {}).get("max_decisions") or MAX_DECISIONS)
    state["decisions"] = decisions[:max_dec]

    if project_id:
        proj = _ensure_project(state, project_id)
        _append_limited(proj["important_decisions"], {
            "decision_id": decision["decision_id"],
            "recommendation": recommendation,
            "reason": reason,
            "applied": applied,
            "outcome": outcome,
            "timestamp": decision["timestamp"],
        }, 20)

    _save_state(state)
    return {"success": True, "decision": decision}


def health() -> dict[str, Any]:
    state = _load_state()
    events = state.get("events") or []
    return {
        "success": True,
        "module": "hive_brain_engine",
        "events_count": len(events),
        "decisions_count": len(state.get("decisions") or []),
        "projects_tracked": len(state.get("projects") or {}),
        "domains_tracked": len(state.get("domains") or {}),
        "keywords_tracked": len(state.get("keywords") or {}),
        "last_event_at": events[0]["timestamp"] if events else None,
        "last_backfill_at": state.get("last_backfill_at"),
    }


def dashboard() -> dict[str, Any]:
    state = _load_state()
    events = state.get("events") or []
    today = _today()
    today_events = [e for e in events if (e.get("timestamp") or "").startswith(today)]
    by_type: dict[str, int] = defaultdict(int)
    by_module: dict[str, int] = defaultdict(int)
    for e in events[:500]:
        by_type[e.get("event_type") or "unknown"] += 1
        by_module[e.get("module") or "unknown"] += 1
    payload: dict[str, Any] = {
        "success": True,
        "today_count": len(today_events),
        "total_events": len(events),
        "top_event_types": sorted(by_type.items(), key=lambda x: -x[1])[:8],
        "top_modules": sorted(by_module.items(), key=lambda x: -x[1])[:8],
        "recent": events[:12],
        "pending_decisions": sum(1 for d in (state.get("decisions") or []) if d.get("applied") is None),
    }
    if not events:
        payload.update({
            "status": "empty",
            "message": "Henüz kayıt yok",
            "next_action": {
                "label": "Backfill çalıştır",
                "path": "/hive-brain",
            },
        })
    return payload


def list_projects() -> dict[str, Any]:
    state = _load_state()
    projects = state.get("projects") or {}
    items: list[dict[str, Any]] = []
    for pid, proj in projects.items():
        event_count = sum(1 for e in (state.get("events") or []) if e.get("project_id") == pid)
        items.append({
            "project_id": pid,
            "event_count": event_count,
            "last_action_at": proj.get("last_action_at") or "",
            "summary": (proj.get("project_summary") or "")[:200],
        })
    items.sort(key=lambda x: x.get("last_action_at") or "", reverse=True)
    if not items:
        return {
            "success": True,
            "status": "empty",
            "message": "Henüz proje hafızası yok",
            "count": 0,
            "projects": [],
            "next_action": {
                "label": "Backfill çalıştır",
                "path": "/hive-brain",
            },
        }
    return {"success": True, "count": len(items), "projects": items}


def list_events(
    limit: int = 50,
    project_id: str = "",
    domain: str = "",
    keyword: str = "",
    event_type: str = "",
    module: str = "",
) -> dict[str, Any]:
    state = _load_state()
    events = state.get("events") or []
    if project_id:
        events = [e for e in events if e.get("project_id") == project_id]
    if domain:
        dk = _norm_domain(domain)
        events = [e for e in events if _norm_domain(e.get("domain")) == dk]
    if keyword:
        kk = _norm_keyword(keyword)
        events = [e for e in events if _norm_keyword(e.get("keyword")) == kk]
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    if module:
        events = [e for e in events if e.get("module") == module]
    limit = max(1, min(200, int(limit or 50)))
    return {"success": True, "count": len(events[:limit]), "events": events[:limit]}


def get_timeline(days: int = 14, project_id: str = "") -> dict[str, Any]:
    state = _load_state()
    events = state.get("events") or []
    if project_id:
        events = [e for e in events if e.get("project_id") == project_id]
    days = max(1, min(90, int(days or 14)))
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for e in events:
        day = (e.get("timestamp") or "")[:10]
        if day:
            by_day[day].append(e)
    sorted_days = sorted(by_day.keys(), reverse=True)[:days]
    timeline = []
    for day in sorted_days:
        day_events = by_day[day]
        summaries: dict[str, int] = defaultdict(int)
        for ev in day_events:
            summaries[_event_summary(ev)] += 1
        bullets = []
        for text, count in sorted(summaries.items(), key=lambda x: -x[1])[:6]:
            bullets.append(f"{count}× {text}" if count > 1 else text)
        timeline.append({
            "date": day,
            "event_count": len(day_events),
            "highlights": bullets,
            "events": day_events[:20],
        })
    return {"success": True, "days": len(timeline), "timeline": timeline}


def get_project_memory(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {"success": False, "error": "project_id gerekli"}
    state = _load_state()
    proj = _ensure_project(state, project_id)
    proj["project_summary"] = _build_project_summary(state, project_id)
    proj["next_recommended_actions"] = _infer_recommendations(state, project_id)
    events = [e for e in state.get("events", []) if e.get("project_id") == project_id][:30]
    return {"success": True, "project_id": project_id, "memory": proj, "recent_event_details": events}


def get_domain_memory(domain: str) -> dict[str, Any]:
    key = _norm_domain(domain)
    if not key:
        return {"success": False, "error": "domain gerekli"}
    state = _load_state()
    mem = state.get("domains", {}).get(key) or _ensure_domain(state, key)
    events = [
        e for e in state.get("events", [])
        if _norm_domain(e.get("domain")) == key
    ][:30]
    return {"success": True, "domain": key, "memory": mem, "recent_events": events}


def get_keyword_memory(keyword: str) -> dict[str, Any]:
    key = _norm_keyword(keyword)
    if not key:
        return {"success": False, "error": "keyword gerekli"}
    state = _load_state()
    mem = state.get("keywords", {}).get(key) or _ensure_keyword(state, key)
    events = [
        e for e in state.get("events", [])
        if _norm_keyword(e.get("keyword")) == key
    ][:30]
    return {"success": True, "keyword": key, "memory": mem, "recent_events": events}


def list_decisions(limit: int = 30, project_id: str = "") -> dict[str, Any]:
    state = _load_state()
    decisions = state.get("decisions") or []
    if project_id:
        decisions = [d for d in decisions if d.get("project_id") == project_id]
    limit = max(1, min(100, int(limit or 30)))
    return {"success": True, "count": len(decisions[:limit]), "decisions": decisions[:limit]}


def get_project_story(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {"success": False, "error": "project_id gerekli"}
    state = _load_state()
    events = [e for e in state.get("events", []) if e.get("project_id") == project_id]
    if not events:
        return {
            "success": True,
            "project_id": project_id,
            "story": f"{project_id} projesi için henüz HIVE Brain kaydı yok. Modül aksiyonları otomatik olarak buraya düşecek.",
            "sections": [],
        }
    events_chrono = list(reversed(events))
    paragraphs: list[str] = []
    sections: list[dict[str, Any]] = []

    first = events_chrono[0]
    paragraphs.append(
        f"Proje {project_id}, ilk kayıt {first.get('timestamp', '?')} tarihinde "
        f"{first.get('module', 'bir modül')} üzerinden sisteme girdi."
    )

    by_type: dict[str, list] = defaultdict(list)
    for e in events_chrono:
        by_type[e.get("event_type") or "module_action"].append(e)

    if by_type.get("project_created"):
        paragraphs.append("Proje resmi olarak oluşturuldu ve Astro/SEO pipeline'a eklendi.")
    if by_type.get("content_generated"):
        n = len(by_type["content_generated"])
        paragraphs.append(f"Toplam {n} içerik üretim olayı kaydedildi.")
    if by_type.get("deploy_completed"):
        n = len(by_type["deploy_completed"])
        paragraphs.append(f"{n} başarılı deploy tamamlandı.")
    if by_type.get("rank_drop"):
        kws = list({e.get("keyword") for e in by_type["rank_drop"] if e.get("keyword")})[:5]
        paragraphs.append(
            f"Sıra kaybı tespit edildi ({len(by_type['rank_drop'])} olay)"
            + (f": {', '.join(kws)}" if kws else "") + "."
        )
    if by_type.get("refresh_completed") or by_type.get("content_refreshed"):
        n = len(by_type.get("refresh_completed", [])) + len(by_type.get("content_refreshed", []))
        paragraphs.append(f"İçerik yenileme süreci {n} kez tamamlandı.")
    if by_type.get("serp_defense_triggered"):
        paragraphs.append(f"SERP Defense Engine {len(by_type['serp_defense_triggered'])} kez devreye girdi.")
    if by_type.get("publisher_success"):
        paragraphs.append(f"Publisher Hub {len(by_type['publisher_success'])} başarılı dağıtım yaptı.")

    proj = state.get("projects", {}).get(project_id, {})
    recs = proj.get("next_recommended_actions") or _infer_recommendations(state, project_id)
    if recs:
        paragraphs.append("Sonraki öneriler: " + " ".join(recs[:3]))

    tl = get_timeline(days=30, project_id=project_id)
    for day_block in tl.get("timeline", [])[:10]:
        sections.append(day_block)

    story = "\n\n".join(paragraphs)
    return {
        "success": True,
        "project_id": project_id,
        "story": story,
        "sections": sections,
        "event_count": len(events),
        "next_recommended_actions": recs,
    }


def backfill_from_activity_logs(limit: int = 300) -> dict[str, Any]:
    """hive_data.json log_module_run kayıtlarını brain event'e dönüştür (read-only)."""
    if not HIVE_DATA_FILE.exists():
        return {"success": False, "error": "hive_data.json bulunamadı"}
    try:
        data = json.loads(HIVE_DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"success": False, "error": str(exc)}

    logs = (data.get("logs") or [])[-limit:]
    imported = 0
    state = _load_state()
    existing_ids = {e.get("metadata", {}).get("source_log_ts") for e in state.get("events", [])}

    mod_type_map = {
        "content_refresh_engine": "content_refreshed",
        "astro_auto_publisher": "content_published",
        "astro_factory": "content_generated",
        "question_intelligence_engine": "faq_created",
        "talon_orchestrator": "keyword_tracked",
        "ranktracker": "keyword_tracked",
    }

    for log in logs:
        ts = log.get("timestamp") or ""
        if ts in existing_ids:
            continue
        mod_id = log.get("mod_id") or "unknown"
        inputs = log.get("inputs") or {}
        output = log.get("output") or {}
        event_type = mod_type_map.get(mod_id, "module_action")
        status = "error" if output.get("status") == "hata" else "ok"
        record_event(
            event_type,
            mod_id,
            project_id=str(inputs.get("project_id") or output.get("project_id") or ""),
            domain=str(inputs.get("domain") or output.get("domain") or ""),
            keyword=str(inputs.get("keyword") or inputs.get("kelime") or inputs.get("seed_keyword") or ""),
            status=status,
            result=output,
            metadata={"source": "activity_log", "source_log_ts": ts, "mod_ad": log.get("mod_ad")},
        )
        imported += 1

    state = _load_state()
    state["last_backfill_at"] = _now()
    _save_state(state)
    return {"success": True, "imported": imported}


def backfill_from_engine_states() -> dict[str, Any]:
    """Engine state JSON dosyalarından read-only olay çıkarımı."""
    app_dir = Path(__file__).resolve().parent.parent
    imported = 0

    def _read_json(name: str) -> dict:
        p = app_dir / name
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    # Content refresh jobs
    cre = _read_json("content_refresh_engine_state.json")
    for job in (cre.get("jobs") or [])[:50]:
        record_event(
            "refresh_completed" if job.get("status") == "completed" else "refresh_scheduled",
            "content_refresh_engine",
            project_id=str(job.get("project_id") or ""),
            status="ok" if job.get("status") == "completed" else "pending",
            result={"job_id": job.get("job_id"), "pages": job.get("pages_refreshed")},
            metadata={"source": "state_backfill", "job_id": job.get("job_id")},
        )
        imported += 1

    # SERP defense plans
    sde = _read_json("serp_defense_engine_state.json")
    for plan in (sde.get("plans") or [])[:30]:
        record_event(
            "serp_defense_triggered",
            "serp_defense_engine",
            project_id=str(plan.get("project_id") or ""),
            keyword=str(plan.get("keyword") or ""),
            result={"plan_id": plan.get("plan_id"), "actions": len(plan.get("actions") or [])},
            metadata={"source": "state_backfill"},
        )
        imported += 1

    # Network replicator — networks
    nre = _read_json("network_replicator_state.json")
    for net in (nre.get("networks") or [])[:20]:
        record_event(
            "network_created",
            "network_replicator",
            domain=str(net.get("main_domain") or ""),
            result={"network_id": net.get("network_id"), "domains": len(net.get("domains") or [])},
            metadata={"source": "state_backfill"},
        )
        imported += 1

    state = _load_state()
    state["last_backfill_at"] = _now()
    _save_state(state)
    return {"success": True, "imported": imported}


def export_report(project_id: str = "") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "exported_at": _now(),
        "health": health(),
        "dashboard": dashboard(),
        "timeline": get_timeline(project_id=project_id),
    }
    if project_id:
        payload["project_memory"] = get_project_memory(project_id)
        payload["project_story"] = get_project_story(project_id)
    safe = project_id.replace("/", "_") if project_id else "global"
    path = REPORTS_DIR / f"hive-brain-{safe}-{_now().replace(' ', '_').replace(':', '-')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path)}


hive_brain = type("HiveBrainEngine", (), {
    "health": staticmethod(health),
    "dashboard": staticmethod(dashboard),
    "record_event": staticmethod(record_event),
    "record_decision": staticmethod(record_decision),
    "list_events": staticmethod(list_events),
    "list_projects": staticmethod(list_projects),
    "get_timeline": staticmethod(get_timeline),
    "get_project_memory": staticmethod(get_project_memory),
    "get_domain_memory": staticmethod(get_domain_memory),
    "get_keyword_memory": staticmethod(get_keyword_memory),
    "list_decisions": staticmethod(list_decisions),
    "get_project_story": staticmethod(get_project_story),
    "backfill_from_activity_logs": staticmethod(backfill_from_activity_logs),
    "backfill_from_engine_states": staticmethod(backfill_from_engine_states),
    "export_report": staticmethod(export_report),
})()
