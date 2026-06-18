"""
Action Orchestrator V1 — karar → uygulama köprüsü.

Planları alır, görevlere dönüştürür, modüllere dağıtır, sonuçları Brain'e yazar.
Mevcut SEO motorlarını yeniden yazmaz.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("hive.action_orchestrator")

STATE_FILE = Path(__file__).resolve().parent.parent / "action_orchestrator_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "mode": "plan_only",
    "max_concurrent_actions": 5,
    "allow_publish": False,
    "allow_deploy": False,
    "allow_google_sites": False,
    "allow_github_pages": False,
    "allow_authority_actions": False,
    "allow_network_actions": False,
}

VALID_MODES = {"plan_only", "semi_autonomous", "autonomous"}
VALID_STATUSES = {"queued", "processing", "waiting_approval", "completed", "failed", "cancelled"}

ACTION_REGISTRY: dict[str, dict[str, Any]] = {
    "add_faq": {
        "assigned_module": "question_intelligence_engine",
        "label": "FAQ / QIE",
        "safety_key": None,
        "gain_type": "traffic",
    },
    "add_entity": {
        "assigned_module": "entity_detail_generator",
        "label": "Entity Detail",
        "safety_key": None,
        "gain_type": "traffic",
    },
    "geo_page": {
        "assigned_module": "place_seo_pipeline",
        "label": "GEO Page",
        "safety_key": None,
        "gain_type": "traffic",
    },
    "content_refresh": {
        "assigned_module": "content_refresh_engine",
        "label": "Content Refresh",
        "safety_key": None,
        "gain_type": "traffic",
    },
    "authority_source": {
        "assigned_module": "authority_mesh_engine",
        "label": "Authority Mesh",
        "safety_key": "allow_authority_actions",
        "gain_type": "authority",
    },
    "github_page": {
        "assigned_module": "github_pages_worker",
        "label": "GitHub Pages",
        "safety_key": "allow_github_pages",
        "gain_type": "authority",
    },
    "google_site": {
        "assigned_module": "google_sites_worker",
        "label": "Google Sites",
        "safety_key": "allow_google_sites",
        "gain_type": "authority",
    },
    "publish": {
        "assigned_module": "publisher_hub",
        "label": "Publish",
        "safety_key": "allow_publish",
        "gain_type": "traffic",
    },
    "astro_build": {
        "assigned_module": "astro_factory",
        "label": "Astro Build",
        "safety_key": None,
        "gain_type": "traffic",
    },
    "deploy": {
        "assigned_module": "astro_auto_publisher",
        "label": "Deploy",
        "safety_key": "allow_deploy",
        "gain_type": "traffic",
    },
    "network_action": {
        "assigned_module": "support_network_engine",
        "label": "Network",
        "safety_key": "allow_network_actions",
        "gain_type": "authority",
    },
}

ACTION_TYPE_ALIASES: dict[str, str] = {
    "faq": "add_faq",
    "add_faqs": "add_faq",
    "faqs_to_add": "add_faq",
    "entity": "add_entity",
    "entities_to_add": "add_entity",
    "geo": "geo_page",
    "geo_sections_to_add": "geo_page",
    "refresh": "content_refresh",
    "refreshes_needed": "content_refresh",
    "authority": "authority_source",
    "support_pages_needed": "authority_source",
    "github": "github_page",
    "google_sites": "google_site",
    "build": "astro_build",
    "cluster_expansions": "add_faq",
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
                data.setdefault("actions", [])
                data.setdefault("pipelines", [])
                data.setdefault("history", [])
                data.setdefault("stats", {"success_count": 0, "failure_count": 0, "completed_today": 0, "last_reset_date": ""})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "actions": [],
        "pipelines": [],
        "history": [],
        "stats": {"success_count": 0, "failure_count": 0, "completed_today": 0, "last_reset_date": ""},
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(updates: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    settings = dict(DEFAULT_SETTINGS)
    settings.update(st.get("settings") or {})
    for k, v in (updates or {}).items():
        if k in DEFAULT_SETTINGS:
            if k == "mode" and v not in VALID_MODES:
                return {"success": False, "error": f"Geçersiz mode: {v}"}
            settings[k] = v
    st["settings"] = settings
    _save_state(st)
    return {"success": True, "settings": settings}


def _record_brain(event: str, *, action: dict | None = None, result: dict | None = None) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        meta = {"engine": "action_orchestrator", "ao_event": event}
        if action:
            meta.update({
                "action_id": action.get("action_id"),
                "action_type": action.get("action_type"),
                "pipeline_id": action.get("pipeline_id"),
            })
        record_event(
            "module_action",
            "action_orchestrator",
            project_id=action.get("project_id", "") if action else "",
            keyword=action.get("keyword", "") if action else "",
            reason=event,
            result=result or {},
            metadata=meta,
        )
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _safe_call(module: str, func: str, **kwargs) -> dict[str, Any]:
    try:
        mod = __import__(f"app.moduller.{module}", fromlist=[func])
        fn: Callable = getattr(mod, func)
        res = fn(**kwargs)
        return res if isinstance(res, dict) else {"success": True, "data": res}
    except Exception as exc:
        logger.debug("ao.%s.%s: %s", module, func, exc)
        return {"success": False, "error": str(exc)}


def normalize_action_type(raw: str) -> str:
    key = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key in ACTION_REGISTRY:
        return key
    return ACTION_TYPE_ALIASES.get(key, key if key in ACTION_REGISTRY else "content_refresh")


def _action_fingerprint(source_module: str, action_type: str, project_id: str, keyword: str, title: str) -> str:
    parts = [source_module, action_type, project_id or "", keyword or "", (title or "")[:80].lower()]
    return "|".join(parts)


def _duplicate_blocked(fp: str, state: dict[str, Any] | None = None) -> bool:
    st = state or _load_state()
    active = {"queued", "processing", "waiting_approval"}
    for a in st.get("actions") or []:
        if a.get("fingerprint") == fp and a.get("status") in active:
            return True
    return False


def _reset_daily_stats(state: dict[str, Any]) -> None:
    stats = state.setdefault("stats", {})
    if stats.get("last_reset_date") != _today():
        stats["completed_today"] = 0
        stats["last_reset_date"] = _today()


def _make_action(
    *,
    source_module: str,
    action_type: str,
    project_id: str = "",
    keyword: str = "",
    title: str = "",
    priority: str = "MEDIUM",
    estimated_gain: int = 0,
    payload: dict | None = None,
    pipeline_id: str = "",
    pipeline_step: int = 0,
    source_ref: str = "",
) -> dict[str, Any]:
    at = normalize_action_type(action_type)
    reg = ACTION_REGISTRY.get(at, ACTION_REGISTRY["content_refresh"])
    fp = _action_fingerprint(source_module, at, project_id, keyword, title or at)
    return {
        "action_id": f"ao-{uuid.uuid4().hex[:12]}",
        "project_id": project_id or "",
        "source_module": source_module,
        "source_ref": source_ref,
        "action_type": at,
        "title": title or reg.get("label", at),
        "keyword": keyword or "",
        "priority": priority if priority in ("CRITICAL", "HIGH", "MEDIUM", "LOW") else "MEDIUM",
        "status": "queued",
        "estimated_gain": int(estimated_gain or 0),
        "estimated_authority_gain": int(estimated_gain or 0) if reg.get("gain_type") == "authority" else 0,
        "estimated_traffic_gain": int(estimated_gain or 0) if reg.get("gain_type") == "traffic" else 0,
        "created_at": _now(),
        "updated_at": _now(),
        "assigned_module": reg["assigned_module"],
        "payload": payload or {},
        "pipeline_id": pipeline_id or "",
        "pipeline_step": pipeline_step,
        "fingerprint": fp,
        "history": [{"at": _now(), "event": "created", "status": "queued"}],
        "result": {},
        "error": "",
    }


def _append_action(state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any] | None:
    if _duplicate_blocked(action["fingerprint"], state):
        return None
    state.setdefault("actions", []).insert(0, action)
    state["actions"] = state["actions"][:500]
    state.setdefault("history", []).insert(0, {
        "type": "action_created",
        "action_id": action["action_id"],
        "at": _now(),
    })
    _record_brain("action_created", action=action)
    return action


def create_action(
    *,
    source_module: str,
    action_type: str,
    project_id: str = "",
    keyword: str = "",
    title: str = "",
    priority: str = "MEDIUM",
    estimated_gain: int = 0,
    payload: dict | None = None,
    pipeline_id: str = "",
    pipeline_step: int = 0,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled"):
        return {"success": False, "error": "Action Orchestrator devre dışı — settings.enabled=true yapın"}

    action = _make_action(
        source_module=source_module,
        action_type=action_type,
        project_id=project_id,
        keyword=keyword,
        title=title,
        priority=priority,
        estimated_gain=estimated_gain,
        payload=payload,
        pipeline_id=pipeline_id,
        pipeline_step=pipeline_step,
    )
    st = _load_state()
    if _duplicate_blocked(action["fingerprint"], st):
        return {"success": False, "error": "Duplicate action blocked", "fingerprint": action["fingerprint"]}

    _append_action(st, action)
    _save_state(st)
    return {"success": True, "action": action}


def _priority_from_score(score: int | float) -> str:
    s = int(score or 0)
    if s >= 85:
        return "CRITICAL"
    if s >= 70:
        return "HIGH"
    if s >= 50:
        return "MEDIUM"
    return "LOW"


def _decision_to_action(dec: dict[str, Any]) -> dict[str, Any]:
    raw_action = dec.get("recommended_action") or dec.get("action") or dec.get("title") or "content_refresh"
    at = normalize_action_type(str(raw_action))
    gain = int(dec.get("estimated_gain") or dec.get("priority_score") or 0)
    return _make_action(
        source_module="autonomous_seo_agent",
        action_type=at,
        project_id=dec.get("project_id", ""),
        keyword=dec.get("keyword", ""),
        title=dec.get("recommended_action") or dec.get("title") or at,
        priority=_priority_from_score(dec.get("priority_score", 0)),
        estimated_gain=gain,
        payload={"decision_id": dec.get("decision_id"), "agent_type": dec.get("agent_type")},
        source_ref=dec.get("decision_id", ""),
    )


def _gap_to_action(gap: dict[str, Any], project_id: str = "") -> dict[str, Any]:
    rec = gap.get("recommended_action") or gap.get("type") or "content_refresh"
    at = normalize_action_type(str(rec))
    return _make_action(
        source_module="crawl_gap_engine",
        action_type=at,
        project_id=project_id or gap.get("project_id", ""),
        keyword=gap.get("keyword", ""),
        title=gap.get("title") or gap.get("question") or gap.get("type", at),
        priority=_priority_from_score(gap.get("overall_gap_score") or gap.get("gap_score") or 50),
        estimated_gain=int(gap.get("overall_gap_score") or gap.get("traffic_potential") or 40),
        payload={"gap_id": gap.get("gap_id"), "gap_type": gap.get("type")},
        source_ref=gap.get("gap_id", ""),
    )


def _mcc_action_to_ao(act: dict[str, Any]) -> dict[str, Any]:
    target = act.get("target_module") or act.get("source_module") or "content_refresh_engine"
    at_map = {
        "publisher_hub": "publish",
        "content_refresh_engine": "content_refresh",
        "serp_defense_engine": "add_faq",
        "opportunity_engine": "geo_page",
        "authority_mesh_engine": "authority_source",
        "question_intelligence_engine": "add_faq",
        "astro_auto_publisher": "deploy",
        "astro_factory": "astro_build",
    }
    at = at_map.get(target, "content_refresh")
    return _make_action(
        source_module="mission_control_center",
        action_type=at,
        title=act.get("title", at),
        priority=act.get("priority", "MEDIUM"),
        estimated_gain=50,
        payload={"mcc_action_id": act.get("action_id")},
        source_ref=act.get("action_id", ""),
    )


def _create_pipeline(state: dict[str, Any], source_module: str, step_count: int, meta: dict | None = None) -> str:
    pipeline_id = f"aop-{uuid.uuid4().hex[:10]}"
    state.setdefault("pipelines", []).insert(0, {
        "pipeline_id": pipeline_id,
        "source_module": source_module,
        "status": "queued",
        "steps_total": step_count,
        "steps_completed": 0,
        "created_at": _now(),
        "updated_at": _now(),
        "meta": meta or {},
        "action_ids": [],
    })
    state["pipelines"] = state["pipelines"][:100]
    return pipeline_id


def import_plan(source_module: str, plan: dict[str, Any], *, project_id: str = "") -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled"):
        return {"success": False, "error": "Action Orchestrator devre dışı"}

    st = _load_state()
    created: list[dict] = []
    skipped = 0
    pipeline_steps: list[dict] = []
    pid = project_id or plan.get("project_id") or ""

    src = (source_module or "").strip().lower()

    if src in ("autonomous_seo_agent", "autonomous_agent", "agent"):
        items = plan.get("decisions") or plan.get("suggested_actions") or []
        if not items:
            res = _safe_call("autonomous_seo_agent", "dashboard", project_id=pid)
            items = res.get("suggested_actions") or []
        for dec in items[:25]:
            action = _decision_to_action(dec)
            if _duplicate_blocked(action["fingerprint"], st):
                skipped += 1
                continue
            _append_action(st, action)
            created.append(action)

    elif src in ("opportunity_engine", "opportunity"):
        pl = plan.get("plan") or plan
        groups = pl.get("action_groups") or {}
        order = pl.get("priority_order") or [{"action": k, "count": len(v)} for k, v in groups.items()]
        step = 1
        for grp in order[:15]:
            raw = grp.get("action") if isinstance(grp, dict) else grp
            at = normalize_action_type(str(raw))
            action = _make_action(
                source_module="opportunity_engine",
                action_type=at,
                project_id=pid or pl.get("project_id", ""),
                title=f"Opportunity: {raw}",
                priority="HIGH",
                estimated_gain=int(grp.get("top_score", 60) if isinstance(grp, dict) else 60),
                payload={"plan_id": pl.get("plan_id"), "action_group": raw},
                source_ref=pl.get("plan_id", ""),
            )
            pipeline_steps.append(action)
            step += 1
        if len(pipeline_steps) > 1:
            pipe_id = _create_pipeline(st, "opportunity_engine", len(pipeline_steps), {"plan_id": pl.get("plan_id")})
            for i, action in enumerate(pipeline_steps):
                action["pipeline_id"] = pipe_id
                action["pipeline_step"] = i + 1
                if not _duplicate_blocked(action["fingerprint"], st):
                    _append_action(st, action)
                    created.append(action)
                    for pipe in st.get("pipelines") or []:
                        if pipe.get("pipeline_id") == pipe_id:
                            pipe.setdefault("action_ids", []).append(action["action_id"])
                else:
                    skipped += 1
        else:
            for action in pipeline_steps:
                if not _duplicate_blocked(action["fingerprint"], st):
                    _append_action(st, action)
                    created.append(action)
                else:
                    skipped += 1

    elif src in ("serp_defense_engine", "serp_defense", "serp"):
        pl = plan.get("plan") or plan
        ocd = pl.get("one_click_defense") or {}
        keyword = pl.get("keyword", "")
        step_defs = [
            ("add_faq", ocd.get("faqs_to_add", 0)),
            ("add_entity", ocd.get("entities_to_add", 0)),
            ("geo_page", ocd.get("geo_sections_to_add", 0)),
            ("content_refresh", ocd.get("refreshes_needed", 0)),
            ("publish", ocd.get("publishes_planned", 0)),
            ("authority_source", ocd.get("support_pages_needed", 0)),
            ("astro_build", ocd.get("cluster_expansions", 0)),
            ("deploy", ocd.get("pages_to_update", 0)),
        ]
        serp_steps: list[dict] = []
        for at, count in step_defs:
            if int(count or 0) <= 0:
                continue
            action = _make_action(
                source_module="serp_defense_engine",
                action_type=at,
                project_id=pid or pl.get("project_id", ""),
                keyword=keyword,
                title=f"SERP {at}: {keyword}"[:120],
                priority="CRITICAL",
                estimated_gain=min(95, 40 + int(count) * 5),
                payload={"plan_id": pl.get("plan_id"), "count": count, "one_click_defense": ocd},
                source_ref=pl.get("plan_id", ""),
            )
            serp_steps.append(action)

        if serp_steps:
            pipe_id = _create_pipeline(st, "serp_defense_engine", len(serp_steps), {
                "plan_id": pl.get("plan_id"),
                "keyword": keyword,
            })
            for i, action in enumerate(serp_steps):
                action["pipeline_id"] = pipe_id
                action["pipeline_step"] = i + 1
                if not _duplicate_blocked(action["fingerprint"], st):
                    _append_action(st, action)
                    created.append(action)
                    for pipe in st.get("pipelines") or []:
                        if pipe.get("pipeline_id") == pipe_id:
                            pipe.setdefault("action_ids", []).append(action["action_id"])
                else:
                    skipped += 1

    elif src in ("crawl_gap_engine", "crawl_gap"):
        gaps = plan.get("gaps") or plan.get("critical_gaps") or plan.get("exportable_opportunities") or []
        if not gaps:
            dash = _safe_call("crawl_gap_engine", "dashboard")
            raw = dash.get("critical_gaps")
            gaps = raw if isinstance(raw, list) else []
        for gap in gaps[:20]:
            action = _gap_to_action(gap if isinstance(gap, dict) else {"type": str(gap)}, pid)
            if _duplicate_blocked(action["fingerprint"], st):
                skipped += 1
                continue
            _append_action(st, action)
            created.append(action)

    elif src in ("mission_control_center", "mission_control", "mcc"):
        items = plan.get("actions") or plan.get("next_best_actions") or []
        for act in items[:15]:
            action = _mcc_action_to_ao(act)
            if _duplicate_blocked(action["fingerprint"], st):
                skipped += 1
                continue
            _append_action(st, action)
            created.append(action)

    else:
        return {"success": False, "error": f"Bilinmeyen kaynak: {source_module}"}

    _save_state(st)
    return {
        "success": True,
        "source_module": source_module,
        "imported": len(created),
        "skipped_duplicates": skipped,
        "actions": [{"action_id": a["action_id"], "action_type": a["action_type"], "status": a["status"]} for a in created],
    }


def _find_action(state: dict[str, Any], action_id: str) -> dict[str, Any] | None:
    for a in state.get("actions") or []:
        if a.get("action_id") == action_id:
            return a
    return None


def _processing_count(state: dict[str, Any]) -> int:
    return sum(1 for a in state.get("actions") or [] if a.get("status") == "processing")


def _safety_allowed(action_type: str, settings: dict[str, Any]) -> tuple[bool, str]:
    reg = ACTION_REGISTRY.get(action_type, {})
    key = reg.get("safety_key")
    if key and not settings.get(key):
        return False, f"{key} disabled — güvenlik kuralı"
    return True, ""


def _execute_action(action: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    at = action.get("action_type", "")
    payload = action.get("payload") or {}
    allowed, reason = _safety_allowed(at, settings)
    if not allowed:
        return {"success": False, "error": reason, "status": "waiting_approval"}

    if at == "publish":
        item = {
            "title": payload.get("title") or action.get("title") or "Orchestrator publish",
            "content_html": payload.get("content_html") or f"<p>{action.get('title', 'HIVE action')}</p>",
            "source_module": action.get("source_module"),
            "keyword": action.get("keyword"),
            "project_id": action.get("project_id"),
        }
        return _safe_call("publisher_hub", "enqueue", item=item, channels=payload.get("channels"))

    if at == "content_refresh":
        pid = action.get("project_id") or payload.get("project_id")
        page_ids = payload.get("page_ids")
        if pid:
            return _safe_call("content_refresh_engine", "queue_pages", project_id=pid, page_ids=page_ids)
        return {"success": True, "delegated": True, "module": "content_refresh_engine", "note": "Refresh task delegated"}

    if at == "deploy":
        return {"success": True, "delegated": True, "module": "astro_auto_publisher", "note": "Deploy queued for Astro Auto Publisher"}

    if at == "astro_build":
        return {"success": True, "delegated": True, "module": "astro_factory", "note": "Build task delegated to Astro Factory"}

    if at == "add_faq":
        return {"success": True, "delegated": True, "module": "question_intelligence_engine", "note": "FAQ task created for QIE"}

    if at == "add_entity":
        return {"success": True, "delegated": True, "module": "entity_detail_generator", "note": "Entity task delegated"}

    if at == "geo_page":
        return {"success": True, "delegated": True, "module": "place_seo_pipeline", "note": "GEO page task delegated"}

    if at in ("authority_source", "github_page", "google_site", "network_action"):
        if at in ("authority_source", "github_page", "google_site"):
            try:
                from app.moduller.authority_factory import create_batch_from_orchestrator
                return create_batch_from_orchestrator(action)
            except Exception as exc:
                return {"success": False, "error": str(exc), "status": "failed"}
        mod = ACTION_REGISTRY[at]["assigned_module"]
        return {"success": True, "delegated": True, "module": mod, "note": f"{at} delegated to {mod}"}

    return {"success": True, "delegated": True, "module": action.get("assigned_module"), "note": "Generic delegation"}


def _update_pipeline_on_step(state: dict[str, Any], action: dict[str, Any], success: bool) -> None:
    pid = action.get("pipeline_id")
    if not pid:
        return
    for pipe in state.get("pipelines") or []:
        if pipe.get("pipeline_id") != pid:
            continue
        if success:
            pipe["steps_completed"] = int(pipe.get("steps_completed") or 0) + 1
        pipe["updated_at"] = _now()
        total = int(pipe.get("steps_total") or 0)
        done = int(pipe.get("steps_completed") or 0)
        if done >= total and total > 0:
            pipe["status"] = "completed" if success else "failed"
            _record_brain("pipeline_completed" if success else "pipeline_failed", action=action, result={"pipeline_id": pid})
        break


def run_action(action_id: str, *, approve: bool = False, force: bool = False) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("enabled"):
        return {"success": False, "error": "Action Orchestrator devre dışı"}

    st = _load_state()
    _reset_daily_stats(st)
    action = _find_action(st, action_id)
    if not action:
        return {"success": False, "error": "action bulunamadı"}

    if action.get("status") == "cancelled":
        return {"success": False, "error": "Action cancelled"}

    if action.get("status") == "completed":
        return {"success": True, "action": action, "message": "Already completed"}

    mode = settings.get("mode", "plan_only")
    if mode == "plan_only" and not force:
        return {
            "success": False,
            "error": "plan_only mode — semi_autonomous veya autonomous moduna geçin veya force=true",
            "action": action,
        }

    if mode == "semi_autonomous" and not approve and not force:
        if action.get("status") != "waiting_approval":
            action["status"] = "waiting_approval"
            action["updated_at"] = _now()
            action.setdefault("history", []).append({"at": _now(), "event": "waiting_approval"})
            _save_state(st)
        return {"success": True, "status": "waiting_approval", "action": action, "message": "Onay bekleniyor"}

    max_conc = int(settings.get("max_concurrent_actions") or 5)
    if _processing_count(st) >= max_conc and action.get("status") != "processing":
        return {"success": False, "error": f"max_concurrent_actions ({max_conc}) limiti"}

    action["status"] = "processing"
    action["updated_at"] = _now()
    action.setdefault("history", []).append({"at": _now(), "event": "started"})
    _save_state(st)
    _record_brain("action_started", action=action)

    result = _execute_action(action, settings)
    stats = st.setdefault("stats", {})

    if result.get("success"):
        action["status"] = "completed"
        action["result"] = result
        action["error"] = ""
        stats["success_count"] = int(stats.get("success_count") or 0) + 1
        stats["completed_today"] = int(stats.get("completed_today") or 0) + 1
        _record_brain("action_completed", action=action, result=result)
        _record_brain("success_score_update", action=action, result={"gain": action.get("estimated_gain")})
        _update_pipeline_on_step(st, action, True)
    else:
        if result.get("status") == "waiting_approval":
            action["status"] = "waiting_approval"
        else:
            action["status"] = "failed"
            action["error"] = result.get("error", "execution failed")
            stats["failure_count"] = int(stats.get("failure_count") or 0) + 1
            _record_brain("action_failed", action=action, result=result)
            _record_brain("failure_score_update", action=action, result={"error": action.get("error")})
            _update_pipeline_on_step(st, action, False)

    action["updated_at"] = _now()
    action.setdefault("history", []).append({
        "at": _now(),
        "event": action["status"],
        "result": result,
    })
    _save_state(st)
    return {"success": result.get("success", False), "action": action, "result": result}


def cancel_action(action_id: str) -> dict[str, Any]:
    st = _load_state()
    action = _find_action(st, action_id)
    if not action:
        return {"success": False, "error": "action bulunamadı"}
    if action.get("status") in ("completed", "cancelled"):
        return {"success": False, "error": f"Cannot cancel status={action.get('status')}"}
    action["status"] = "cancelled"
    action["updated_at"] = _now()
    action.setdefault("history", []).append({"at": _now(), "event": "cancelled"})
    _save_state(st)
    return {"success": True, "action": action}


def list_actions(
    *,
    status: str = "",
    source_module: str = "",
    pipeline_id: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    st = _load_state()
    items = list(st.get("actions") or [])
    if status:
        items = [a for a in items if a.get("status") == status]
    if source_module:
        items = [a for a in items if a.get("source_module") == source_module]
    if pipeline_id:
        items = [a for a in items if a.get("pipeline_id") == pipeline_id]
    return {"success": True, "actions": items[:limit], "count": len(items[:limit])}


def get_action(action_id: str) -> dict[str, Any]:
    st = _load_state()
    action = _find_action(st, action_id)
    if not action:
        return {"success": False, "error": "action bulunamadı"}
    pipe = None
    if action.get("pipeline_id"):
        for p in st.get("pipelines") or []:
            if p.get("pipeline_id") == action.get("pipeline_id"):
                pipe = p
                break
    return {"success": True, "action": action, "pipeline": pipe}


def list_pipelines(limit: int = 30) -> dict[str, Any]:
    st = _load_state()
    pipes = (st.get("pipelines") or [])[:limit]
    return {"success": True, "pipelines": pipes, "count": len(pipes)}


def _sum_gains(actions: list[dict], gain_key: str) -> int:
    return sum(int(a.get(gain_key) or 0) for a in actions if a.get("status") == "queued")


def build_dashboard() -> dict[str, Any]:
    st = _load_state()
    _reset_daily_stats(st)
    _save_state(st)
    settings = get_settings()
    actions = st.get("actions") or []
    by_status: dict[str, list] = {s: [] for s in VALID_STATUSES}
    for a in actions:
        st_key = a.get("status", "queued")
        if st_key in by_status:
            by_status[st_key].append(a)

    queued = by_status["queued"]
    processing = by_status["processing"]
    completed = [a for a in by_status["completed"]]
    failed = by_status["failed"]
    waiting = by_status["waiting_approval"]

    stats = st.get("stats") or {}
    total_outcomes = int(stats.get("success_count") or 0) + int(stats.get("failure_count") or 0)
    pipeline_done = sum(1 for p in st.get("pipelines") or [] if p.get("status") == "completed")
    pipeline_total = len(st.get("pipelines") or [])

    return {
        "success": True,
        "enabled": settings.get("enabled", False),
        "mode": settings.get("mode", "plan_only"),
        "queued": len(queued),
        "processing": len(processing),
        "waiting_approval": len(waiting),
        "completed": len(completed),
        "failed": len(failed),
        "completed_today": int(stats.get("completed_today") or 0),
        "estimated_traffic_gain": _sum_gains(queued + waiting, "estimated_traffic_gain") or _sum_gains(queued, "estimated_gain"),
        "estimated_authority_gain": _sum_gains(queued + waiting, "estimated_authority_gain"),
        "today_executions": int(stats.get("completed_today") or 0),
        "pipeline_success_rate": round(pipeline_done / max(pipeline_total, 1) * 100, 1),
        "action_success_rate": round(int(stats.get("success_count") or 0) / max(total_outcomes, 1) * 100, 1),
        "recent_actions": actions[:12],
        "recent_pipelines": (st.get("pipelines") or [])[:8],
        "mission_control": {
            "pending_actions": len(queued) + len(waiting),
            "running_actions": len(processing),
            "failed_actions": len(failed),
            "completed_today": int(stats.get("completed_today") or 0),
        },
        "safety": {k: settings.get(k) for k in DEFAULT_SETTINGS if k.startswith("allow_")},
    }


def health() -> dict[str, Any]:
    dash = build_dashboard()
    return {
        "success": True,
        "module": "action_orchestrator",
        "enabled": dash.get("enabled"),
        "mode": dash.get("mode"),
        "queued": dash.get("queued"),
        "processing": dash.get("processing"),
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "exported_at": _now(),
        "report_type": report_type,
        "dashboard": build_dashboard(),
        "settings": get_settings(),
        "actions": list_actions(limit=100),
        "pipelines": list_pipelines(limit=50),
    }
    fname = f"action_orchestrator_{report_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    path = REPORTS_DIR / fname
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path), "filename": fname}
