"""
SERP Defense Engine V1 — savunma orkestrasyon katmanı.

Risk analizi, canlı GSC/DataForSEO verisi ve savunma planını mevcut modüllere
(Publisher, Content Refresh, QIE, Entity GEO, Support Network) delegasyon ile uygular.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.serp_defense_engine")

STATE_FILE = Path(__file__).resolve().parent.parent / "serp_defense_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

DECAY_WINDOWS = (7, 14, 30, 60, 90)
FRESHNESS_BUCKETS = (30, 60, 90, 180, 365)
PRESSURE_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
HISTORY_LIMIT = 500
RANK_DECAY_STATUSES = ("stable", "growing", "warning", "declining", "critical")

DEFENSE_ACTIONS = (
    "add_faq", "expand_entity", "expand_geo", "add_ai_block", "add_answer_block",
    "add_comparison", "refresh_content", "publisher_boost", "support_network_boost",
    "cluster_expansion", "citation_expansion",
)

FORTRESS_WEIGHTS = {
    "ranking_score": 0.14,
    "entity_score": 0.10,
    "faq_score": 0.10,
    "authority_score": 0.10,
    "freshness_score": 0.10,
    "ai_visibility_score": 0.12,
    "citation_score": 0.08,
    "geo_score": 0.08,
    "internal_link_score": 0.08,
    "support_network_score": 0.10,
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "decay_warning_threshold": 30,
    "decay_critical_threshold": 60,
    "fortress_warning_threshold": 55,
    "fortress_critical_threshold": 40,
    "auto_apply_enabled": True,
    "auto_publish_on_execute": True,
    "auto_deploy_on_execute": False,
    "live_refresh_on_analyze": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("fortress_cache", {})
                data.setdefault("attack_surface_cache", {})
                data.setdefault("fortress_history", [])
                data.setdefault("attack_surface_history", [])
                data.setdefault("defense_plan_history", [])
                data.setdefault("pressure_history", [])
                data.setdefault("keyword_defense_history", [])
                data.setdefault("plans", [])
                data.setdefault("execution_history", [])
                data.setdefault("jobs", {})
                data.setdefault("last_analyze_at", "")
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "fortress_cache": {},
        "attack_surface_cache": {},
        "fortress_history": [],
        "attack_surface_history": [],
        "defense_plan_history": [],
        "pressure_history": [],
        "keyword_defense_history": [],
        "plans": [],
        "execution_history": [],
        "jobs": {},
        "last_analyze_at": "",
    }


def _append_history(state: dict[str, Any], key: str, entry: dict[str, Any]) -> None:
    lst = state.setdefault(key, [])
    lst.insert(0, entry)
    state[key] = lst[:HISTORY_LIMIT]


def _record_brain(
    event_type: str,
    *,
    project_id: str = "",
    domain: str = "",
    keyword: str = "",
    result: dict[str, Any] | None = None,
    reason: str = "",
) -> None:
    try:
        from app.moduller.hive_brain_engine import record_event, record_decision
        record_event(
            event_type,
            "serp_defense_engine",
            project_id=project_id,
            domain=domain,
            keyword=keyword,
            result=result or {},
            reason=reason,
        )
        if result and result.get("strategy_recommendation"):
            rec = result["strategy_recommendation"]
            record_decision(
                "serp_defense_engine",
                rec.get("decision", "defend"),
                reason=rec.get("reason", ""),
                project_id=project_id,
                domain=domain,
                keyword=keyword,
                metadata=rec,
            )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    cur.update(patch)
    _save_state(st)
    return dict(cur)


_INTEGRATION_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_INTEGRATION_TTL_SEC = 90


def _integration_status() -> dict[str, Any]:
    import time
    now = time.monotonic()
    cached = _INTEGRATION_CACHE.get("data")
    if cached is not None and (now - _INTEGRATION_CACHE["at"]) < _INTEGRATION_TTL_SEC:
        return dict(cached)

    checks: dict[str, Any] = {}

    def _chk(name: str, fn):
        try:
            res = fn()
            ok = bool(res.get("success", True)) if isinstance(res, dict) else bool(res)
            checks[name] = {"ok": ok, "detail": res}
        except Exception as exc:
            checks[name] = {"ok": False, "error": str(exc)}

    _chk("rank_index_watcher", lambda: __import__(
        "app.moduller.rank_index_watcher", fromlist=["health"]
    ).health())
    _chk("entity_geo_graph", lambda: __import__(
        "app.moduller.entity_geo_graph", fromlist=["health"]
    ).health())
    _chk("content_refresh_engine", lambda: __import__(
        "app.moduller.content_refresh_engine", fromlist=["health"]
    ).health())
    _chk("seo_quality_gate", lambda: __import__(
        "app.moduller.seo_quality_gate", fromlist=["health"]
    ).health())
    _chk("support_network_engine", lambda: __import__(
        "app.moduller.support_network_engine", fromlist=["health"]
    ).health())
    _chk("opportunity_engine", lambda: __import__(
        "app.moduller.opportunity_engine", fromlist=["health"]
    ).health())
    _chk("hive_brain_engine", lambda: __import__(
        "app.moduller.hive_brain_engine", fromlist=["health"]
    ).health())

    try:
        from app.moduller.rank_index_watcher import _gsc_oauth_configured, _dataforseo_configured
        checks["search_console"] = {
            "ok": _gsc_oauth_configured(),
            "error": None if _gsc_oauth_configured() else "search_console_not_configured",
        }
        checks["dataforseo_ai_overview"] = {
            "ok": _dataforseo_configured(),
            "error": None if _dataforseo_configured() else "provider_missing — AI Overview için DataForSEO gerekli",
        }
    except Exception as exc:
        checks["search_console"] = {"ok": False, "error": str(exc)}
        checks["dataforseo_ai_overview"] = {"ok": False, "error": str(exc)}

    _INTEGRATION_CACHE["at"] = now
    _INTEGRATION_CACHE["data"] = checks
    return checks


def _parse_ts(at: str) -> float | None:
    if not at:
        return None
    text = at.replace(" UTC", "").strip()[:19].replace("T", " ")
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _rank_project(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {}
    try:
        from app.moduller.rank_index_watcher import get_project
        res = get_project(project_id)
        return res.get("project") or {} if res.get("success") else {}
    except Exception as exc:
        logger.debug("rank project: %s", exc)
        return {}


def _find_keyword_entry(project: dict[str, Any], keyword: str) -> dict[str, Any]:
    kw_l = keyword.lower().strip()
    for entry in project.get("keywords") or []:
        if (entry.get("keyword") or "").lower() == kw_l:
            from app.moduller.rank_index_watcher import _apply_keyword_metrics
            _apply_keyword_metrics(entry)
            return entry
    return {}


def _position_delta_for_window(history: list[dict], days: int) -> int | None:
    if not history:
        return None
    now = datetime.now(timezone.utc).timestamp()
    cur_pos = history[0].get("position")
    if cur_pos is None:
        return None
    for h in history[1:]:
        ts = _parse_ts(h.get("at", ""))
        if ts and (now - ts) / 86400 >= days:
            old = h.get("position")
            if old is not None:
                return int(cur_pos) - int(old)
            break
    if len(history) >= 2 and days <= 14:
        old = history[-1].get("position")
        if old is not None:
            return int(cur_pos) - int(old)
    return None


def _decay_trend_status(kw: dict[str, Any], settings: dict[str, Any]) -> str:
    decay = int(kw.get("ranking_decay_score") or 0)
    trend = kw.get("trend_direction", "flat")
    warn = int(settings.get("decay_warning_threshold") or 30)
    crit = int(settings.get("decay_critical_threshold") or 60)
    if decay >= crit or (trend == "decaying" and decay >= warn):
        return "critical"
    if decay >= warn or trend == "decaying":
        return "declining"
    if trend == "recovering":
        return "growing"
    if trend == "up":
        return "growing"
    if decay >= warn // 2:
        return "warning"
    return "stable"


def _rank_decay_analysis(kw: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    history = kw.get("history") or []
    windows: dict[str, Any] = {}
    for d in DECAY_WINDOWS:
        delta = _position_delta_for_window(history, d)
        windows[f"{d}d"] = {
            "position_delta": delta,
            "direction": "down" if delta and delta > 3 else "up" if delta and delta < -3 else "flat",
        }
    return {
        "status": _decay_trend_status(kw, settings),
        "decay_score": kw.get("ranking_decay_score", 0),
        "trend_direction": kw.get("trend_direction", "flat"),
        "velocity": kw.get("ranking_velocity", 0),
        "momentum": kw.get("ranking_momentum", 0),
        "windows": windows,
        "last_position": kw.get("last_position"),
    }


def _gsc_configured() -> bool:
    try:
        from app.moduller.rank_index_watcher import _gsc_oauth_configured
        return _gsc_oauth_configured()
    except Exception:
        return False


def _dataforseo_configured() -> bool:
    try:
        from app.moduller.rank_index_watcher import _dataforseo_configured
        return _dataforseo_configured()
    except Exception:
        return False


def _sync_live_gsc(project_id: str, domain: str, days: int = 28) -> dict[str, Any]:
    dom = (domain or "").strip()
    if not dom:
        return {"success": False, "error": "domain gerekli", "source": "search_console"}
    if not _gsc_configured():
        return {
            "success": False,
            "error": "search_console_not_configured",
            "message": "CTR analizi için Search Console OAuth gerekli",
            "source": "search_console",
        }
    try:
        from app.moduller.rank_index_watcher import performance
        return performance(dom, project_id=project_id, days=days)
    except Exception as exc:
        return {"success": False, "error": str(exc), "source": "search_console"}


def refresh_live_data(
    project_id: str = "",
    keyword: str = "",
    domain: str = "",
    *,
    refresh_gsc: bool = True,
    refresh_rank: bool = True,
    refresh_ai: bool = False,
) -> dict[str, Any]:
    """GSC performance, DataForSEO rank snapshot ve isteğe bağlı AI Overview canlı yenileme."""
    rank_proj = _rank_project(project_id) if project_id else {}
    dom = (domain or rank_proj.get("domain") or "").strip()
    kw = (keyword or "").strip()
    results: dict[str, Any] = {}

    if refresh_gsc and dom:
        results["gsc"] = _sync_live_gsc(project_id, dom)
    elif refresh_gsc:
        results["gsc"] = {"success": False, "error": "domain gerekli", "skipped": True}

    if refresh_rank and kw and dom:
        if _dataforseo_configured():
            try:
                from app.moduller.rank_index_watcher import track_keyword
                results["rank"] = track_keyword(kw, dom, project_id=project_id)
            except Exception as exc:
                results["rank"] = {"success": False, "error": str(exc)}
        else:
            results["rank"] = {
                "success": False,
                "error": "provider_missing",
                "message": "DataForSEO yapılandırılmadı — rank snapshot atlandı",
                "skipped": True,
            }
    elif refresh_rank and not kw:
        results["rank"] = {"success": False, "error": "keyword gerekli", "skipped": True}

    if refresh_ai and kw:
        results["ai_overview"] = _ai_defense(kw)

    return {
        "success": True,
        "project_id": project_id,
        "keyword": kw,
        "domain": dom,
        "live_refresh": results,
        "providers": {
            "search_console": _gsc_configured(),
            "dataforseo": _dataforseo_configured(),
        },
        "refreshed_at": _now(),
    }


def _project_context(project_id: str, keyword: str = "") -> dict[str, Any]:
    rank_proj = _rank_project(project_id) if project_id else {}
    location = (rank_proj.get("location") or "Kuşadası").strip()
    return {
        "project_id": project_id,
        "domain": (rank_proj.get("domain") or "").strip(),
        "location": location,
        "city": (rank_proj.get("city") or "Aydın").strip(),
        "district": location,
        "category": (rank_proj.get("category") or "gece hayatı").strip(),
        "keyword": keyword,
    }


def _qie_payload(ctx: dict[str, Any], keyword: str = "") -> dict[str, Any]:
    kw = (keyword or ctx.get("keyword") or "").strip()
    return {
        "keyword": kw,
        "location": ctx.get("location", "Kuşadası"),
        "city": ctx.get("city", "Aydın"),
        "district": ctx.get("district", ctx.get("location", "Kuşadası")),
        "category": ctx.get("category", "gece hayatı"),
        "project_id": ctx.get("project_id", ""),
    }


def _find_refresh_page_id(project_id: str, keyword: str) -> str | None:
    try:
        from app.moduller.content_refresh_engine import scan
        scan_res = scan(project_id)
        if not scan_res.get("success"):
            return None
        kw_l = keyword.lower()
        candidates = scan_res.get("candidates") or []
        for cand in candidates:
            if kw_l in (cand.get("keyword") or "").lower() or kw_l in (cand.get("title") or "").lower():
                return cand.get("page_id")
        for cand in candidates:
            if cand.get("refresh_needed"):
                return cand.get("page_id")
        return candidates[0].get("page_id") if candidates else None
    except Exception as exc:
        logger.debug("find refresh page: %s", exc)
        return None


def _publish_qie_items(items: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, Any]:
    if not items:
        return {"success": False, "error": "Yayınlanacak içerik yok"}
    try:
        from app.moduller.publisher_hub import enqueue, publish_item
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    published: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for item in items:
        title = (item.get("title") or item.get("keyword") or "").strip()
        html = item.get("content_html") or ""
        if not title or not html:
            failed.append({"title": title or "—", "error": "title veya content_html eksik"})
            continue
        enq = enqueue({
            "title": title,
            "content_html": html,
            "project_id": ctx.get("project_id", ""),
            "keyword": item.get("keyword", ""),
            "source": "serp_defense_engine",
            "content_type": item.get("content_type", ""),
        })
        if not enq.get("success"):
            failed.append({"title": title, "error": enq.get("error", "enqueue failed"), "status": enq.get("status")})
            continue
        pub_result: dict[str, Any] = {"publish_id": enq["publish_id"], "status": "queued", "success": True}
        if ctx.get("auto_publish"):
            pub = publish_item(enq["publish_id"])
            pub_result = {
                "publish_id": enq["publish_id"],
                "status": pub.get("status"),
                "success": bool(pub.get("success")),
                "error": pub.get("error"),
            }
            if not pub.get("success"):
                failed.append({"title": title, **pub_result})
                continue
        published.append(pub_result)
    return {
        "success": bool(published),
        "published": published,
        "failed": failed,
        "count": len(published),
    }


def _execute_defense_action(action: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    act = (action.get("action") or "").strip()
    kw = (action.get("keyword") or ctx.get("keyword") or "").strip()
    pid = ctx.get("project_id", "")
    base = {"action": act, "keyword": kw, "priority": action.get("priority"), "module": ""}

    if act not in DEFENSE_ACTIONS:
        return {**base, "success": False, "error": f"Bilinmeyen aksiyon: {act}"}

    try:
        if act == "refresh_content":
            base["module"] = "content_refresh_engine"
            if not pid:
                return {**base, "success": False, "error": "project_id gerekli"}
            from app.moduller.content_refresh_engine import queue_pages, refresh_page, process_queue
            page_id = _find_refresh_page_id(pid, kw)
            if page_id:
                queue_pages(pid, [page_id])
                res = refresh_page(
                    pid, page_id,
                    auto_publish=ctx.get("auto_publish"),
                    auto_deploy=ctx.get("auto_deploy"),
                )
                return {**base, **res, "page_id": page_id}
            proc = process_queue(
                project_id=pid,
                auto_publish=ctx.get("auto_publish"),
                auto_deploy=ctx.get("auto_deploy"),
            )
            summary = proc.get("summary") or {}
            if proc.get("success") and summary.get("pages_refreshed", 0) > 0:
                return {**base, **proc}
            return {**base, "success": False, "error": "Refresh edilecek sayfa bulunamadı", "scan": proc}

        if act == "add_faq":
            base["module"] = "question_intelligence_engine"
            from app.moduller.question_intelligence_engine import generate_faq
            gen = generate_faq(_qie_payload(ctx, kw))
            if not gen.get("success"):
                return {**base, **gen}
            pub = _publish_qie_items(gen.get("items") or [], ctx)
            return {**base, "success": pub.get("success"), "generate": gen, "publish": pub}

        if act == "add_comparison":
            base["module"] = "question_intelligence_engine"
            from app.moduller.question_intelligence_engine import generate_comparisons
            gen = generate_comparisons({**_qie_payload(ctx, kw), "count": 1})
            if not gen.get("success"):
                return {**base, **gen}
            pub = _publish_qie_items(gen.get("items") or [], ctx)
            return {**base, "success": pub.get("success"), "generate": gen, "publish": pub}

        if act in ("add_ai_block", "add_answer_block"):
            base["module"] = "question_intelligence_engine"
            from app.moduller.question_intelligence_engine import generate_ai_overview
            gen = generate_ai_overview(_qie_payload(ctx, kw))
            if not gen.get("success"):
                return {**base, **gen}
            pub = _publish_qie_items(gen.get("items") or [], ctx)
            return {**base, "success": pub.get("success"), "generate": gen, "publish": pub}

        if act == "expand_entity":
            base["module"] = "entity_geo_graph"
            if not pid:
                return {**base, "success": False, "error": "project_id gerekli"}
            from app.moduller.entity_geo_graph import build_project_graph, missing_entities, internal_link_plan
            graph = build_project_graph(pid, domain=ctx.get("domain", ""), seed_keyword=kw, location=ctx.get("location", ""))
            missing = missing_entities(project_id=pid, seed_keyword=kw)
            links = internal_link_plan(pid, max_links_per_page=5)
            ok = graph.get("success") or missing.get("success") or links.get("success")
            return {
                **base,
                "success": bool(ok),
                "graph": graph,
                "missing_entities": missing,
                "internal_links": links,
            }

        if act == "expand_geo":
            base["module"] = "entity_geo_graph"
            from app.moduller.entity_geo_graph import geo_expand, build_project_graph
            from app.moduller.question_intelligence_engine import generate_local_intent
            geo = geo_expand(ctx.get("location", "Kuşadası"), seed_keyword=kw)
            graph = build_project_graph(pid, seed_keyword=kw, location=ctx.get("location", "")) if pid else {"skipped": True}
            gen = generate_local_intent(_qie_payload(ctx, kw))
            pub = _publish_qie_items(gen.get("items") or [], ctx) if gen.get("success") else {"success": False, "error": gen.get("error")}
            return {
                **base,
                "success": bool(geo.get("success") or pub.get("success")),
                "geo_expand": geo,
                "graph": graph,
                "local_intent": gen,
                "publish": pub,
            }

        if act == "cluster_expansion":
            base["module"] = "entity_geo_graph"
            if not pid:
                return {**base, "success": False, "error": "project_id gerekli"}
            from app.moduller.entity_geo_graph import build_project_graph
            from app.moduller.question_intelligence_engine import generate_far
            graph = build_project_graph(pid, seed_keyword=kw, location=ctx.get("location", ""))
            gen = generate_far({**_qie_payload(ctx, kw), "count": 2})
            pub = _publish_qie_items(gen.get("items") or [], ctx) if gen.get("success") else {"success": False}
            return {**base, "success": bool(graph.get("success") or pub.get("success")), "graph": graph, "far": gen, "publish": pub}

        if act == "support_network_boost":
            base["module"] = "support_network_engine"
            from app.moduller.support_network_engine import sync_network
            res = sync_network()
            return {**base, **res, "success": bool(res.get("success"))}

        if act == "citation_expansion":
            base["module"] = "seo_quality_gate"
            if not pid:
                return {**base, "success": False, "error": "project_id gerekli"}
            from app.moduller.seo_quality_gate import analyze_project
            res = analyze_project(pid, target_keyword=kw)
            return {**base, **res, "success": bool(res.get("success"))}

        if act == "publisher_boost":
            base["module"] = "publisher_hub"
            from app.moduller.publisher_hub import process_queue
            res = process_queue(max_items=5)
            return {**base, **res, "success": bool(res.get("success"))}

    except Exception as exc:
        logger.exception("execute action %s: %s", act, exc)
        return {**base, "success": False, "error": str(exc)}

    return {**base, "success": False, "error": "Aksiyon işlenemedi"}


def execute_defense_plan(
    plan_id: str = "",
    keyword: str = "",
    project_id: str = "",
    *,
    auto_publish: bool | None = None,
    auto_deploy: bool | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("auto_apply_enabled", True):
        return {
            "success": False,
            "error": "auto_apply_disabled",
            "message": "Otomatik plan uygulama ayarlardan kapalı — auto_apply_enabled açın",
        }

    st = _load_state()
    plan: dict[str, Any] | None = None
    if plan_id:
        plan = next((p for p in (st.get("plans") or []) if p.get("plan_id") == plan_id), None)
        if not plan:
            return {"success": False, "error": f"Plan bulunamadı: {plan_id}"}

    if not plan:
        if not keyword.strip() and not project_id:
            return {"success": False, "error": "plan_id veya keyword+project_id gerekli"}
        gen = generate_plan(keyword=keyword, project_id=project_id)
        if not gen.get("success"):
            return gen
        plan = gen["plan"]

    pid = (plan.get("project_id") or project_id or "").strip()
    if not pid:
        return {"success": False, "error": "project_id gerekli — plan uygulama için Rank Watcher projesi şart"}

    if auto_publish is None:
        auto_publish = settings.get("auto_publish_on_execute", True)
    if auto_deploy is None:
        auto_deploy = settings.get("auto_deploy_on_execute", False)

    ctx = _project_context(pid, keyword or plan.get("keyword", ""))
    ctx["auto_publish"] = auto_publish
    ctx["auto_deploy"] = auto_deploy
    ctx["settings"] = settings

    execution_id = f"sde-exec-{uuid.uuid4().hex[:10]}"
    steps: list[dict[str, Any]] = []
    seen_actions: set[str] = set()

    for action in plan.get("actions") or []:
        dedupe_key = f"{action.get('action')}:{action.get('keyword', '')}"
        if dedupe_key in seen_actions:
            steps.append({**action, "success": True, "skipped": True, "note": "duplicate action"})
            continue
        seen_actions.add(dedupe_key)
        step = _execute_defense_action(action, ctx)
        steps.append(step)

    success_count = sum(1 for s in steps if s.get("success"))
    fail_count = sum(1 for s in steps if not s.get("success") and not s.get("skipped"))
    if not steps:
        status = "empty"
    elif fail_count == 0:
        status = "completed"
    elif success_count > 0:
        status = "partial"
    else:
        status = "failed"

    execution = {
        "execution_id": execution_id,
        "plan_id": plan.get("plan_id"),
        "project_id": pid,
        "keyword": plan.get("keyword") or keyword,
        "status": status,
        "steps": steps,
        "success_count": success_count,
        "fail_count": fail_count,
        "auto_publish": auto_publish,
        "auto_deploy": auto_deploy,
        "executed_at": _now(),
    }

    st = _load_state()
    for i, p in enumerate(st.get("plans") or []):
        if p.get("plan_id") == plan.get("plan_id"):
            st["plans"][i]["execution"] = execution
            st["plans"][i]["status"] = status
            st["plans"][i]["executed_at"] = execution["executed_at"]
            plan = st["plans"][i]
            break
    _append_history(st, "execution_history", execution)
    _save_state(st)

    _record_brain(
        "serp_defense_executed",
        project_id=pid,
        domain=ctx.get("domain", ""),
        keyword=plan.get("keyword") or keyword,
        result={"execution_id": execution_id, "status": status, "success_count": success_count},
        reason=f"Plan uygulandı: {status} ({success_count}/{len(steps)} adım)",
    )

    return {
        "success": status in ("completed", "partial", "empty"),
        "execution": execution,
        "plan": plan,
    }


def _ctr_analysis(project: dict[str, Any], keyword: str) -> dict[str, Any]:
    kw_l = keyword.lower()
    perf_history = project.get("performance_history") or []
    current = perf_history[0] if perf_history else {}
    prior = perf_history[1] if len(perf_history) > 1 else {}

    for row in current.get("top_queries") or []:
        if (row.get("query") or "").lower() == kw_l:
            ctr = float(row.get("ctr") or 0)
            impressions = int(row.get("impressions") or 0)
            clicks = int(row.get("clicks") or 0)
            pos = row.get("position")
            issues: list[str] = []
            if ctr < 0.02 and pos and pos <= 10:
                issues.append("snippet_problem")
            if ctr < 0.01:
                issues.append("title_problem")
            if ctr < 0.015:
                issues.append("possible_ai_overview_impact")
            impression_loss = False
            ctr_drop = False
            for prow in prior.get("top_queries") or []:
                if (prow.get("query") or "").lower() != kw_l:
                    continue
                old_imp = int(prow.get("impressions") or 0)
                old_ctr = float(prow.get("ctr") or 0)
                if old_imp > impressions and old_imp > 0:
                    impression_loss = True
                    issues.append("impression_loss")
                if old_ctr > ctr + 0.005:
                    ctr_drop = True
                    issues.append("ctr_decline")
                break
            return {
                "success": True,
                "ctr": ctr,
                "position": pos,
                "clicks": clicks,
                "impressions": impressions,
                "issues": issues,
                "ctr_decay_detected": ctr < 0.02 or ctr_drop,
                "impression_loss": impression_loss,
                "title_problem": "title_problem" in issues,
                "snippet_problem": "snippet_problem" in issues,
                "ai_overview_impact": "possible_ai_overview_impact" in issues,
                "source": "search_console",
                "period_comparison": {
                    "prior_impressions": int((prior.get("top_queries") or [{}])[0].get("impressions") or 0) if prior else None,
                    "prior_ctr": float((prior.get("top_queries") or [{}])[0].get("ctr") or 0) if prior else None,
                },
            }
    try:
        if not _gsc_configured():
            return {
                "success": False,
                "error": "search_console_not_configured",
                "message": "CTR analizi için Search Console OAuth gerekli",
            }
    except Exception:
        pass
    return {
        "success": True,
        "ctr": None,
        "note": "Bu keyword için GSC sorgu verisi yok",
        "live_sync_required": True,
    }


def _ai_defense(keyword: str) -> dict[str, Any]:
    try:
        from app.moduller.rank_index_watcher import ai_overview
        res = ai_overview(keyword)
        if not res.get("success"):
            return {
                "success": False,
                "error": res.get("error", "provider_missing"),
                "message": res.get("message", "AI Overview verisi alınamadı"),
                "ai_overview_present": False,
                "ai_visibility_score": 0,
                "ai_competitor_count": 0,
                "answer_block_score": 0,
            }
        sources = res.get("sources") or []
        present = bool(res.get("has_ai_overview"))
        competitors = len({s.get("source") or s.get("url") for s in sources if s})
        visibility = 30 if present else 70
        answer_score = max(0, 100 - competitors * 8) if present else 85
        citation_strength = max(0, min(100, 100 - competitors * 10)) if sources else 0
        return {
            "success": True,
            "ai_overview_present": present,
            "ai_visibility_score": visibility,
            "ai_competitor_count": competitors,
            "answer_block_score": answer_score,
            "citation_strength": citation_strength,
            "sources": sources[:10],
            "missing_answer_block": present and answer_score < 60,
            "suggested_answer_blocks": (
                [f"{keyword} nedir?", f"{keyword} nasıl?", f"En iyi {keyword}?"]
                if present and answer_score < 60 else []
            ),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "ai_overview_present": False}


def _entity_defense(project_id: str, keyword: str) -> dict[str, Any]:
    try:
        from app.moduller.entity_geo_graph import get_project_scores, missing_entities
        scores = get_project_scores(project_id) if project_id else {"success": False}
        missing = missing_entities(project_id=project_id, seed_keyword=keyword) if project_id else {"success": False}
        weak: list[dict] = []
        missing_list = (missing.get("missing_entities") or []) if missing.get("success") else []
        competitor_entities: list[dict] = []
        for ent in missing_list[:15]:
            weak.append({"entity": ent.get("entity") or ent.get("label", ""), "type": "missing"})
        entity_score = int(scores.get("entity_strength_score") or 50) if scores.get("success") else 50
        return {
            "success": scores.get("success", False) or bool(missing_list),
            "entity_strength": entity_score,
            "weak_entities": weak,
            "missing_entities": missing_list[:10],
            "competitor_entities": competitor_entities,
            "entities_we_lack": [e.get("entity") for e in missing_list[:10]],
            "geo_score": int(scores.get("geo_coverage_score") or 50) if scores.get("success") else 50,
            "error": scores.get("error") if not scores.get("success") and not missing_list else None,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "entity_strength": 0}


def _faq_defense(project_id: str, keyword: str) -> dict[str, Any]:
    gaps: list[dict] = []
    qie_path = Path(__file__).resolve().parent.parent / "question_intelligence_engine_state.json"
    kw_l = keyword.lower()
    faq_count = 0
    if project_id:
        try:
            from app.moduller.rank_index_watcher import _read_astro_data
            data, err = _read_astro_data(project_id)
            if data:
                faqs = data.get("faqs") or []
                faq_count = len(faqs) if isinstance(faqs, list) else len((faqs or {}).get("faqs") or [])
                kw_faqs = sum(
                    1 for f in (faqs if isinstance(faqs, list) else (faqs or {}).get("faqs") or [])
                    if kw_l in json.dumps(f, ensure_ascii=False).lower()
                )
                if kw_faqs < 2:
                    gaps.append({"type": "missing_faq", "count": kw_faqs})
        except Exception as exc:
            logger.debug("astro faq read: %s", exc)

    if qie_path.exists():
        try:
            qie = json.loads(qie_path.read_text(encoding="utf-8"))
            for o in (qie.get("outputs") or []):
                if kw_l not in (o.get("keyword") or "").lower():
                    continue
                if int(o.get("paa_gap_score") or 0) > 20:
                    gaps.append({"type": "missing_paa", "score": o.get("paa_gap_score")})
                if int(o.get("autocomplete_gap_score") or 0) > 20:
                    gaps.append({"type": "missing_autocomplete", "score": o.get("autocomplete_gap_score")})
                if o.get("type") in ("comparison", "best_of") and not o.get("written"):
                    gaps.append({"type": "missing_comparison"})
                if o.get("type") == "local_intent":
                    gaps.append({"type": "missing_local_intent"})
        except Exception:
            pass

    if faq_count == 0:
        gaps.append({"type": "missing_faq"})
    if not gaps:
        gaps.append({"type": "missing_objection", "note": "QIE çıktısı yok — objection analizi eksik"})

    missing_paa = [g for g in gaps if "paa" in g.get("type", "")]
    missing_faq_list = [g for g in gaps if "faq" in g.get("type", "")]
    missing_objection = [g for g in gaps if "objection" in g.get("type", "")]
    missing_comparison = [g for g in gaps if "comparison" in g.get("type", "")]
    missing_local = [g for g in gaps if "local" in g.get("type", "")]
    missing_autocomplete = [g for g in gaps if "autocomplete" in g.get("type", "")]

    faq_score = max(0, min(100, 40 + faq_count * 5 - len(gaps) * 12))
    return {
        "faq_strength": faq_score,
        "gaps": gaps,
        "faq_count": faq_count,
        "missing_paa": missing_paa,
        "missing_faq": missing_faq_list,
        "missing_objection": missing_objection,
        "missing_comparison": missing_comparison,
        "missing_local_intent": missing_local,
        "missing_autocomplete": missing_autocomplete,
    }


def _freshness_defense(project_id: str, keyword: str) -> dict[str, Any]:
    cre_path = Path(__file__).resolve().parent.parent / "content_refresh_engine_state.json"
    stale_buckets: dict[str, int] = {f"{d}+": 0 for d in FRESHNESS_BUCKETS}
    risk = 0
    pages: list[dict] = []
    if not cre_path.exists():
        return {"freshness_score": 70, "stale_buckets": stale_buckets, "risk_score": 0, "pages": []}
    try:
        data = json.loads(cre_path.read_text(encoding="utf-8"))
        cands = (data.get("candidates") or {}).get(project_id) or []
        kw_l = keyword.lower()
        for c in cands:
            if kw_l not in (c.get("keyword") or "").lower() and kw_l not in (c.get("title") or "").lower():
                if c.get("slug") != "home":
                    continue
            age = int(c.get("content_age_days") or 0)
            pages.append({"page_id": c.get("page_id"), "age_days": age, "refresh_needed": c.get("refresh_needed")})
            for d in FRESHNESS_BUCKETS:
                if age >= d:
                    stale_buckets[f"{d}+"] += 1
            if age >= 90:
                risk += 25
            elif age >= 60:
                risk += 15
            elif age >= 30:
                risk += 8
        freshness_score = max(0, 100 - risk)
        return {
            "freshness_score": freshness_score,
            "stale_buckets": stale_buckets,
            "risk_score": min(100, risk),
            "pages": pages[:20],
        }
    except Exception:
        return {"freshness_score": 50, "stale_buckets": stale_buckets, "risk_score": 0, "pages": []}


def _support_network_defense(keyword: str) -> dict[str, Any]:
    try:
        from app.moduller.support_network_engine import list_domains, keyword_distribution
        domains_res = list_domains()
        kw_res = keyword_distribution()
        kw_l = keyword.lower()
        supporting = []
        not_contributing = []
        strengthen = []
        for d in domains_res.get("domains") or []:
            sk = (d.get("seed_keyword") or "").lower()
            kws = [k.get("keyword", "").lower() for k in d.get("ranking_keywords") or []]
            if kw_l == sk or kw_l in kws:
                if d.get("authority_score", 0) >= 50:
                    supporting.append(d["domain"])
                else:
                    strengthen.append(d["domain"])
            elif d.get("role") in ("support_hub", "blog_hub", "faq_hub"):
                not_contributing.append(d["domain"])
        dup = [
            d for d in (kw_res.get("duplicate_keywords") or [])
            if d.get("keyword", "").lower() == kw_l
        ]
        score = min(100, len(supporting) * 20 + 40) if supporting else max(20, 40 - len(not_contributing))
        return {
            "support_network_score": score,
            "supporting_domains": supporting,
            "not_contributing": not_contributing[:10],
            "strengthen_domains": strengthen,
            "cannibalization": dup,
        }
    except Exception as exc:
        return {"support_network_score": 0, "error": str(exc)}


def _gate_scores(project_id: str) -> dict[str, Any]:
    gate_path = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
    if not gate_path.exists():
        return {"authority_score": 50, "citation_score": 50, "overall_score": 0}
    try:
        data = json.loads(gate_path.read_text(encoding="utf-8"))
        best: dict[str, Any] = {}
        for report in (data.get("reports") or {}).values():
            if report.get("project_id") != project_id:
                continue
            if not best or report.get("created_at", "") > best.get("created_at", ""):
                best = report
        if not best:
            return {"authority_score": 50, "citation_score": 50, "overall_score": 0}
        return {
            "authority_score": int(best.get("authority_score") or best.get("overall_score") or 50),
            "citation_score": int(best.get("citation_score") or best.get("overall_score") or 50),
            "overall_score": int(best.get("overall_score") or 0),
            "deploy_blocked": best.get("deploy_allowed") is False,
        }
    except Exception:
        return {"authority_score": 50, "citation_score": 50, "overall_score": 0}


def _internal_link_score(project_id: str) -> int:
    if not project_id:
        return 50
    try:
        from app.moduller.entity_geo_graph import internal_link_plan
        plan = internal_link_plan(project_id, max_links_per_page=3)
        if plan.get("success") and plan.get("links"):
            return max(30, 100 - len(plan.get("links") or []) * 5)
        return 70
    except Exception:
        return 50


def _attack_surface(keyword: str, components: dict[str, Any]) -> dict[str, Any]:
    missing = {
        "missing_faq": False,
        "missing_entity": False,
        "missing_geo": False,
        "missing_cluster": False,
        "missing_answer_block": False,
        "missing_ai_overview_section": False,
        "missing_local_intent": False,
        "missing_comparison_content": False,
        "missing_objection_content": False,
    }
    faq = components.get("faq_defense") or {}
    entity = components.get("entity_defense") or {}
    ai = components.get("ai_defense") or {}
    for g in faq.get("gaps") or []:
        t = g.get("type", "")
        if "faq" in t or "paa" in t or "autocomplete" in t:
            missing["missing_faq"] = True
        if "comparison" in t:
            missing["missing_comparison_content"] = True
        if "local" in t:
            missing["missing_local_intent"] = True
        if "objection" in t:
            missing["missing_objection_content"] = True
    if entity.get("missing_entities"):
        missing["missing_entity"] = True
    if (entity.get("geo_score") or 100) < 50:
        missing["missing_geo"] = True
    if ai.get("missing_answer_block"):
        missing["missing_answer_block"] = True
    if ai.get("ai_overview_present") and (ai.get("answer_block_score") or 0) < 50:
        missing["missing_ai_overview_section"] = True
    if (components.get("ranking_score") or 0) < 40:
        missing["missing_cluster"] = True

    gaps = [k.replace("missing_", "").replace("_", " ") for k, v in missing.items() if v]
    count = sum(1 for v in missing.values() if v)
    attack_surface_score = min(100, count * 12 + 10)
    return {
        "keyword": keyword,
        "missing": missing,
        "gaps": gaps,
        "attack_surface_score": attack_surface_score,
        "gap_count": count,
    }


def _pressure_score(
    rank_decay: dict[str, Any],
    ai: dict[str, Any],
    attack_surface_score: int,
    kw_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    score = 0
    status = rank_decay.get("status", "stable")
    if status == "critical":
        score += 40
    elif status == "declining":
        score += 28
    elif status == "warning":
        score += 15
    score += min(30, int(rank_decay.get("decay_score") or 0) // 3)
    score += min(20, (ai.get("ai_competitor_count") or 0) * 4)
    score += min(25, attack_surface_score // 4)

    serp_competitors = 0
    if kw_entry:
        snap = kw_entry.get("serp_snapshot") or []
        serp_competitors = len(snap)
        score += min(15, serp_competitors)

    score = min(100, score)
    if score >= 75:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 25:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {
        "pressure_score": score,
        "pressure_level": level,
        "serp_competitor_count": serp_competitors,
    }


def _recommended_actions(
    attack: dict[str, Any],
    components: dict[str, Any],
    rank_decay: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    missing = attack.get("missing") or {}

    def add(action: str, reason: str, priority: str = "medium"):
        if action in DEFENSE_ACTIONS:
            actions.append({"action": action, "reason": reason, "priority": priority, "apply": "plan_only"})

    if missing.get("missing_faq"):
        add("add_faq", "FAQ/PAA eksik", "high")
    if missing.get("missing_entity"):
        add("expand_entity", "Entity kapsamı zayıf", "high")
    if missing.get("missing_geo"):
        add("expand_geo", "GEO bölümü eksik", "medium")
    if missing.get("missing_answer_block") or missing.get("missing_ai_overview_section"):
        add("add_ai_block", "AI Overview answer block eksik", "high")
        add("add_answer_block", "Yapılandırılmış cevap bloğu önerilir", "high")
    if missing.get("missing_comparison_content"):
        add("add_comparison", "Comparison içeriği eksik", "medium")
    if missing.get("missing_local_intent"):
        add("expand_geo", "Yerel niyet içeriği eksik", "medium")
    if missing.get("missing_objection_content"):
        add("add_faq", "Objection içeriği eksik", "medium")
    if missing.get("missing_cluster"):
        add("cluster_expansion", "Topic cluster genişletme gerekli", "medium")
    if rank_decay.get("status") in ("declining", "critical"):
        add("refresh_content", f"Sıra düşüşü: {rank_decay.get('status')}", "high")
    if (components.get("freshness_score") or 100) < 60:
        add("refresh_content", "İçerik bayat", "high")
    if attack.get("attack_surface_score", 0) >= 40:
        add("support_network_boost", "Attack surface yüksek — support network güçlendir", "medium")
    if (components.get("citation_score") or 100) < 50:
        add("citation_expansion", "Citation gücü düşük", "medium")
    if rank_decay.get("status") in ("warning", "declining"):
        add("publisher_boost", "Görünürlük için çok kanallı yayın", "low")

    seen: set[str] = set()
    unique = []
    for a in actions:
        if a["action"] not in seen:
            seen.add(a["action"])
            unique.append(a)
    return unique


def _fortress_score(components: dict[str, int]) -> int:
    total = 0.0
    for key, weight in FORTRESS_WEIGHTS.items():
        total += (components.get(key) or 0) * weight
    return int(round(total))


def _opportunity_strategy(
    keyword: str,
    project_id: str,
    fortress_score: int,
    pressure_level: str,
) -> dict[str, Any]:
    """Opportunity Engine ile çakışma — savunma mı büyüme mi."""
    kw_l = keyword.lower().strip()
    overlap: dict[str, Any] = {"found": False, "opportunity_score": None, "opportunity_type": None}
    try:
        from app.moduller.opportunity_engine import list_keywords, _get_cached_opportunities
        opps = _get_cached_opportunities(project_id, "keyword")
        if not opps and project_id:
            res = list_keywords(project_id)
            if res.get("success"):
                opps = res.get("opportunities") or []
        for o in opps:
            okw = (o.get("keyword") or o.get("title") or "").lower()
            if kw_l in okw or okw in kw_l:
                overlap = {
                    "found": True,
                    "opportunity_score": o.get("opportunity_score"),
                    "opportunity_type": o.get("type"),
                    "estimated_gain": o.get("estimated_gain"),
                    "item": o,
                }
                break
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "decision": "defend",
            "reason": "Opportunity Engine okunamadı — varsayılan savunma",
        }

    if not overlap["found"]:
        if pressure_level in ("HIGH", "CRITICAL") or fortress_score < 45:
            return {
                "success": True,
                "decision": "defend",
                "reason": "Opportunity yok ama yüksek savunma riski",
                "overlap": overlap,
            }
        return {
            "success": True,
            "decision": "grow",
            "reason": "Savunma riski düşük — büyüme fırsatı araştırılabilir",
            "overlap": overlap,
        }

    opp_score = int(overlap.get("opportunity_score") or 0)
    if pressure_level in ("CRITICAL", "HIGH") or fortress_score < 50:
        return {
            "success": True,
            "decision": "defend",
            "reason": f"Keyword hem fırsat ({opp_score}) hem savunma riski taşıyor — önce savun",
            "overlap": overlap,
        }
    if opp_score >= 70 and fortress_score >= 55:
        return {
            "success": True,
            "decision": "grow",
            "reason": f"Fortress yeterli ({fortress_score}) — büyüme öncelikli (opp {opp_score})",
            "overlap": overlap,
        }
    return {
        "success": True,
        "decision": "balanced",
        "reason": "Hem savunma hem büyüme — önce kritik gap'leri kapat, sonra genişlet",
        "overlap": overlap,
    }


def _competitor_entities_from_serp(kw_entry: dict[str, Any], our_domain: str = "") -> list[dict]:
    out: list[dict] = []
    host = our_domain.replace("https://", "").replace("http://", "").split("/")[0].lower()
    for row in kw_entry.get("serp_snapshot") or []:
        url = (row.get("url") or row.get("link") or "").lower()
        title = row.get("title") or row.get("domain") or ""
        if host and host in url:
            continue
        out.append({"entity": title, "url": url, "position": row.get("position"), "source": "serp_snapshot"})
    return out[:10]


def analyze_keyword(
    keyword: str,
    project_id: str = "",
    domain: str = "",
) -> dict[str, Any]:
    kw = (keyword or "").strip()
    if not kw:
        return {"success": False, "error": "keyword gerekli"}

    settings = get_settings()
    rank_proj = _rank_project(project_id) if project_id else {}
    live_meta: dict[str, Any] = {}
    if settings.get("live_refresh_on_analyze", True) and project_id:
        dom = domain or rank_proj.get("domain", "")
        live_meta = refresh_live_data(
            project_id,
            kw,
            dom,
            refresh_gsc=bool(dom),
            refresh_rank=bool(dom and kw),
            refresh_ai=False,
        )
        rank_proj = _rank_project(project_id)
    kw_entry = _find_keyword_entry(rank_proj, kw) if rank_proj else {}
    rank_decay = _rank_decay_analysis(kw_entry, settings) if kw_entry else {
        "status": "stable", "decay_score": 0, "windows": {}, "note": "Keyword Rank Watcher'da kayıtlı değil",
    }

    ranking_score = int(kw_entry.get("keyword_strength_score") or 50) if kw_entry else 50
    gate = _gate_scores(project_id)
    entity_def = _entity_defense(project_id, kw)
    if kw_entry:
        comp_ents = _competitor_entities_from_serp(kw_entry, rank_proj.get("domain", domain))
        if comp_ents:
            entity_def["competitor_entities"] = comp_ents
    faq_def = _faq_defense(project_id, kw)
    fresh = _freshness_defense(project_id, kw)
    ai_def = _ai_defense(kw)
    ctr = _ctr_analysis(rank_proj, kw) if rank_proj else {"success": False, "error": "project_id gerekli CTR için"}
    support = _support_network_defense(kw)
    internal_link = _internal_link_score(project_id)

    components = {
        "ranking_score": ranking_score,
        "entity_score": int(entity_def.get("entity_strength") or 50),
        "faq_score": int(faq_def.get("faq_strength") or 50),
        "authority_score": int(gate.get("authority_score") or 50),
        "freshness_score": int(fresh.get("freshness_score") or 70),
        "ai_visibility_score": int(ai_def.get("ai_visibility_score") or 50),
        "citation_score": int(gate.get("citation_score") or 50),
        "geo_score": int(entity_def.get("geo_score") or 50),
        "internal_link_score": internal_link,
        "support_network_score": int(support.get("support_network_score") or 50),
    }

    bundle = {
        "rank_decay": rank_decay,
        "ctr": ctr,
        "ai_defense": ai_def,
        "entity_defense": entity_def,
        "faq_defense": faq_def,
        "freshness_defense": fresh,
        "support_network": support,
        "quality_gate": gate,
        **components,
    }
    attack = _attack_surface(kw, bundle)
    pressure = _pressure_score(rank_decay, ai_def, attack["attack_surface_score"], kw_entry)
    fortress = _fortress_score(components)
    try:
        from app.moduller.citation_engine import serp_fortress_adjustment
        adj = serp_fortress_adjustment(project_id, kw, int(components.get("citation_score") or 50))
        fortress = max(0, min(100, fortress + int(adj.get("fortress_delta") or 0)))
        if adj.get("fortress_boost"):
            components["citation_fortress_boost"] = adj.get("fortress_delta")
        if adj.get("fortress_penalty"):
            components["citation_fortress_penalty"] = adj.get("fortress_delta")
    except Exception:
        pass
    actions = _recommended_actions(attack, components, rank_decay)
    strategy = _opportunity_strategy(kw, project_id, fortress, pressure["pressure_level"])

    estimated_quality = min(100, int(
        (fortress * 0.5) + (components["authority_score"] * 0.3) + (components["faq_score"] * 0.2)
    ))

    report = {
        "keyword": kw,
        "project_id": project_id,
        "domain": domain,
        "position": kw_entry.get("last_position"),
        "fortress_score": fortress,
        "overall_fortress_score": fortress,
        "attack_surface_score": attack["attack_surface_score"],
        "pressure_score": pressure["pressure_score"],
        "pressure_level": pressure["pressure_level"],
        "ai_visibility": components["ai_visibility_score"],
        "entity_strength": components["entity_score"],
        "faq_strength": components["faq_score"],
        "freshness": components["freshness_score"],
        "components": components,
        "rank_decay": rank_decay,
        "ctr_analysis": ctr,
        "ai_overview": ai_def,
        "entity_defense": entity_def,
        "faq_defense": faq_def,
        "freshness_defense": fresh,
        "attack_surface": attack,
        "support_network": support,
        "quality_gate": gate,
        "recommended_actions": actions,
        "estimated_quality_score": estimated_quality,
        "strategy_recommendation": strategy,
        "opportunity_overlap": strategy.get("overlap"),
        "live_refresh": live_meta if live_meta else None,
        "analyzed_at": _now(),
    }

    st = _load_state()
    cache = st.setdefault("fortress_cache", {})
    cache.setdefault(project_id or "_global", {})[kw.lower()] = report
    st["attack_surface_cache"][kw.lower()] = attack
    st["last_analyze_at"] = _now()

    _append_history(st, "fortress_history", {
        "keyword": kw, "project_id": project_id, "fortress_score": fortress,
        "overall_fortress_score": fortress, "components": components, "at": _now(),
    })
    _append_history(st, "attack_surface_history", {**attack, "at": _now(), "project_id": project_id})
    _append_history(st, "pressure_history", {
        **pressure, "keyword": kw, "project_id": project_id, "at": _now(),
    })
    _append_history(st, "keyword_defense_history", {
        "keyword": kw, "project_id": project_id,
        "report_summary": {
            "fortress_score": fortress,
            "pressure_level": pressure["pressure_level"],
            "decision": strategy.get("decision"),
        },
        "at": _now(),
    })
    _save_state(st)

    _record_brain(
        "serp_defense_triggered",
        project_id=project_id,
        domain=domain or rank_proj.get("domain", ""),
        keyword=kw,
        result={
            "fortress_score": fortress,
            "pressure_level": pressure["pressure_level"],
            "strategy_recommendation": strategy,
        },
        reason=f"Keyword analizi: fortress={fortress}, pressure={pressure['pressure_level']}",
    )

    return {"success": True, "report": report}


def analyze_project(project_id: str) -> dict[str, Any]:
    if not project_id:
        return {"success": False, "error": "project_id gerekli"}
    rank_proj = _rank_project(project_id)
    if not rank_proj:
        return {"success": False, "error": "Rank Watcher projesi bulunamadı"}
    keywords = [k.get("keyword") for k in rank_proj.get("keywords") or [] if k.get("keyword")]
    if not keywords:
        try:
            from app.moduller.rank_index_watcher import _read_astro_data, _extract_keywords_from_astro
            data, _ = _read_astro_data(project_id)
            if data:
                keywords = _extract_keywords_from_astro(data)[:15]
        except Exception:
            pass
    if not keywords:
        return {"success": False, "error": "Projede analiz edilecek keyword yok"}
    reports = []
    for kw in keywords[:25]:
        res = analyze_keyword(kw, project_id=project_id, domain=rank_proj.get("domain", ""))
        if res.get("success"):
            reports.append(res["report"])
    return {"success": True, "project_id": project_id, "count": len(reports), "reports": reports}


def fortress_list(project_id: str = "") -> dict[str, Any]:
    st = _load_state()
    cache = st.get("fortress_cache") or {}
    if project_id:
        items = list((cache.get(project_id) or {}).values())
    else:
        items = []
        for proj_reports in cache.values():
            items.extend(proj_reports.values())
    items.sort(key=lambda x: x.get("fortress_score", 0))
    return {"success": True, "count": len(items), "fortresses": items}


def attack_surface_list(project_id: str = "") -> dict[str, Any]:
    if project_id:
        fl = fortress_list(project_id)
        surfaces = [r.get("attack_surface") for r in fl.get("fortresses") or [] if r.get("attack_surface")]
    else:
        st = _load_state()
        surfaces = list((st.get("attack_surface_cache") or {}).values())
    return {"success": True, "count": len(surfaces), "attack_surfaces": surfaces}


def pressure_overview(project_id: str = "") -> dict[str, Any]:
    fl = fortress_list(project_id)
    items = fl.get("fortresses") or []
    by_level: dict[str, list] = {l: [] for l in PRESSURE_LEVELS}
    for r in items:
        lvl = r.get("pressure_level", "LOW")
        by_level.setdefault(lvl, []).append({
            "keyword": r.get("keyword"),
            "pressure_score": r.get("pressure_score"),
            "fortress_score": r.get("fortress_score"),
        })
    return {"success": True, "by_level": by_level, "total": len(items)}


def _ctr_report(project_id: str, keyword: str) -> dict[str, Any]:
    if keyword and project_id:
        res = analyze_keyword(keyword, project_id=project_id)
        if res.get("success"):
            return {"success": True, "ctr_reports": [res["report"].get("ctr_analysis")]}
    fl = fortress_list(project_id)
    return {
        "success": True,
        "ctr_reports": [r.get("ctr_analysis") for r in fl.get("fortresses") or [] if r.get("ctr_analysis")],
    }


def defense_opportunities(project_id: str = "") -> dict[str, Any]:
    fl = fortress_list(project_id)
    opps: list[dict] = []
    for r in fl.get("fortresses") or []:
        if r.get("fortress_score", 100) < 60 or r.get("pressure_level") in ("HIGH", "CRITICAL"):
            strat = r.get("strategy_recommendation") or _opportunity_strategy(
                r.get("keyword", ""),
                project_id,
                r.get("fortress_score", 50),
                r.get("pressure_level", "LOW"),
            )
            opps.append({
                "keyword": r.get("keyword"),
                "fortress_score": r.get("fortress_score"),
                "pressure_level": r.get("pressure_level"),
                "top_action": (r.get("recommended_actions") or [{}])[0].get("action"),
                "strategy_decision": strat.get("decision"),
                "strategy_reason": strat.get("reason"),
                "opportunity_overlap": strat.get("overlap"),
            })
    return {"success": True, "opportunities": opps, "count": len(opps)}


def generate_plan(
    keyword: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    if keyword:
        analysis = analyze_keyword(keyword, project_id=project_id)
        if not analysis.get("success"):
            return analysis
        report = analysis["report"]
        reports = [report]
    elif project_id:
        proj = analyze_project(project_id)
        if not proj.get("success"):
            return proj
        reports = proj.get("reports") or []
    else:
        return {"success": False, "error": "keyword veya project_id gerekli"}

    actions: list[dict] = []
    modules: set[str] = set()
    counts = {
        "faqs_to_add": 0,
        "entities_to_add": 0,
        "geo_sections_to_add": 0,
        "refreshes_needed": 0,
        "publishes_planned": 0,
        "support_pages_needed": 0,
        "comparisons_to_add": 0,
        "cluster_expansions": 0,
        "citation_expansions": 0,
        "pages_to_update": 0,
    }
    for r in reports:
        for a in r.get("recommended_actions") or []:
            actions.append({**a, "keyword": r.get("keyword")})
            act = a.get("action", "")
            if act in ("refresh_content",):
                counts["refreshes_needed"] += 1
                counts["pages_to_update"] += 1
                modules.add("content_refresh_engine")
            if act == "publisher_boost":
                counts["publishes_planned"] += 1
                modules.add("publisher_hub")
            if act in ("add_faq",):
                counts["faqs_to_add"] += 1
                modules.add("question_intelligence_engine")
            if act in ("expand_entity",):
                counts["entities_to_add"] += 1
                modules.add("entity_geo_graph")
            if act in ("expand_geo",):
                counts["geo_sections_to_add"] += 1
                counts["entities_to_add"] += 1
                modules.add("entity_geo_graph")
            if act in ("support_network_boost",):
                counts["support_pages_needed"] += 1
                modules.add("support_network_engine")
            if act in ("add_comparison",):
                counts["comparisons_to_add"] += 1
                modules.add("question_intelligence_engine")
            if act in ("cluster_expansion",):
                counts["cluster_expansions"] += 1
                modules.add("entity_geo_graph")
            if act in ("add_ai_block", "add_answer_block"):
                modules.add("question_intelligence_engine")
                modules.add("seo_quality_gate")
            if act == "citation_expansion":
                counts["citation_expansions"] += 1
                modules.add("seo_quality_gate")

    settings = get_settings()
    plan_id = f"sde-plan-{uuid.uuid4().hex[:10]}"
    auto_apply = bool(settings.get("auto_apply_enabled", True))
    plan = {
        "plan_id": plan_id,
        "keyword": keyword,
        "project_id": project_id,
        "actions": actions,
        "one_click_defense": {
            "modules_to_run": sorted(modules),
            "faqs_to_add": counts["faqs_to_add"],
            "entities_to_add": counts["entities_to_add"],
            "geo_sections_to_add": counts["geo_sections_to_add"],
            "refreshes_needed": counts["refreshes_needed"],
            "publishes_planned": counts["publishes_planned"],
            "support_pages_needed": counts["support_pages_needed"],
            "comparisons_to_add": counts["comparisons_to_add"],
            "cluster_expansions": counts["cluster_expansions"],
            "citation_expansions": counts["citation_expansions"],
            "pages_to_update": counts["pages_to_update"],
            "auto_apply": auto_apply,
            "note": (
                "Plan uygulanabilir — «Planı Uygula» ile Publisher/Refresh tetiklenir"
                if auto_apply
                else "Otomatik uygulama kapalı — ayarlardan auto_apply_enabled açın"
            ),
        },
        "estimated_quality_score": round(
            sum(r.get("estimated_quality_score", 0) for r in reports) / max(len(reports), 1), 1
        ),
        "created_at": _now(),
    }
    st = _load_state()
    st.setdefault("plans", []).append(plan)
    st["plans"] = st["plans"][-200:]
    _append_history(st, "defense_plan_history", {
        "plan_id": plan_id,
        "keyword": keyword,
        "project_id": project_id,
        "one_click_defense": plan["one_click_defense"],
        "at": _now(),
    })
    _save_state(st)

    _record_brain(
        "serp_defense_triggered",
        project_id=project_id,
        keyword=keyword,
        result={"plan_id": plan_id, "one_click_defense": plan["one_click_defense"]},
        reason="Savunma planı üretildi",
    )
    return {"success": True, "plan": plan, "reports": reports}


def export_report(report_type: str = "fortress", project_id: str = "", keyword: str = "") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "fortress": lambda: fortress_list(project_id),
        "attack_surface": lambda: attack_surface_list(project_id),
        "keyword_risk": lambda: fortress_list(project_id),
        "ctr": lambda: _ctr_report(project_id, keyword),
        "ai_overview": lambda: analyze_keyword(keyword, project_id) if keyword else fortress_list(project_id),
        "entity": lambda: analyze_keyword(keyword, project_id) if keyword else fortress_list(project_id),
        "faq": lambda: analyze_keyword(keyword, project_id) if keyword else fortress_list(project_id),
        "pressure": lambda: pressure_overview(project_id),
        "opportunities": lambda: defense_opportunities(project_id),
        "defense_plan": lambda: {"plans": _load_state().get("plans", [])[-20:]},
        "overview": lambda: dashboard(project_id),
    }
    fn = generators.get(report_type, generators["fortress"])
    payload = fn()
    path = REPORTS_DIR / f"serp-defense-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def dashboard(project_id: str = "") -> dict[str, Any]:
    fl = fortress_list(project_id)
    items = fl.get("fortresses") or []
    integrations = _integration_status()
    errors = [k for k, v in integrations.items() if not v.get("ok")]
    avg_fortress = round(sum(r.get("fortress_score", 0) for r in items) / max(len(items), 1), 1) if items else None
    critical = sum(1 for r in items if r.get("pressure_level") == "CRITICAL")
    return {
        "success": True,
        "keyword_count": len(items),
        "avg_fortress_score": avg_fortress,
        "critical_pressure_count": critical,
        "integrations": integrations,
        "integration_errors": errors,
        "last_analyze_at": _load_state().get("last_analyze_at", ""),
        "top_risks": sorted(items, key=lambda x: x.get("pressure_score", 0), reverse=True)[:5],
        "weakest_fortresses": sorted(items, key=lambda x: x.get("fortress_score", 0))[:5],
    }


def health() -> dict[str, Any]:
    integrations = _integration_status()
    errors = [
        {"module": k, "error": v.get("error") or "not ready"}
        for k, v in integrations.items() if not v.get("ok")
    ]
    st = _load_state()
    return {
        "success": True,
        "module": "serp_defense_engine",
        "enabled": get_settings().get("enabled", True),
        "integrations": integrations,
        "integration_errors": errors,
        "fortress_cache_size": sum(len(v) for v in (st.get("fortress_cache") or {}).values()),
        "plans_count": len(st.get("plans") or []),
        "execution_count": len(st.get("execution_history") or []),
        "providers": {
            "search_console": _gsc_configured(),
            "dataforseo": _dataforseo_configured(),
        },
        "history_counts": {
            "fortress_history": len(st.get("fortress_history") or []),
            "attack_surface_history": len(st.get("attack_surface_history") or []),
            "defense_plan_history": len(st.get("defense_plan_history") or []),
            "pressure_history": len(st.get("pressure_history") or []),
            "keyword_defense_history": len(st.get("keyword_defense_history") or []),
        },
        "last_analyze_at": st.get("last_analyze_at", ""),
    }
