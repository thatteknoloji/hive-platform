"""Brain hooks — main.py route handler'larından event emit (modül dosyalarına dokunmadan)."""

from __future__ import annotations

from typing import Any


def _pick(data: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = data.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _status_from_result(result: dict[str, Any]) -> str:
    if result.get("status") == "hata" or result.get("success") is False:
        return "error"
    if result.get("error") or result.get("hata"):
        return "error"
    return "ok"


def emit_brain_event(
    path: str,
    req: dict[str, Any] | None,
    result: dict[str, Any] | None,
    *,
    module: str = "",
    event_type: str = "",
) -> dict[str, Any] | None:
    """Route sonrası brain event kaydet. Hata olursa sessizce None döner."""
    try:
        from app.moduller.hive_brain_engine import hive_brain

        req = req or {}
        result = result if isinstance(result, dict) else {}
        route = (path or "").rstrip("/")

        project_id = _pick(req, "project_id", "id", default=_pick(result, "project_id", "id"))
        domain = _pick(req, "domain", "main_domain", "target_domain", "url", default=_pick(result, "domain", "url"))
        keyword = _pick(req, "keyword", "kelime", "seed_keyword", "ana_kelime", default=_pick(result, "keyword"))

        mod = module or _module_from_path(route)
        et = event_type or _event_type_from_route(route, result)

        # Öneri/decision kayıtları
        recommendations = result.get("recommendations") or result.get("next_actions") or result.get("next_recommended_actions")
        if isinstance(recommendations, list):
            for rec in recommendations[:3]:
                text = rec if isinstance(rec, str) else rec.get("text") or rec.get("action") or str(rec)
                if text:
                    hive_brain.record_decision(
                        mod,
                        text,
                        reason=result.get("reason") or result.get("summary") or "",
                        project_id=project_id,
                        domain=domain,
                        keyword=keyword,
                        applied=None,
                    )

        return hive_brain.record_event(
            et,
            mod,
            project_id=project_id,
            domain=domain,
            keyword=keyword,
            entity=_pick(req, "entity", "entity_id", default=_pick(result, "entity")),
            content_id=_pick(req, "content_id", "page_id", "page_url", default=_pick(result, "content_id", "page_id")),
            status=_status_from_result(result),
            result={k: v for k, v in result.items() if k not in ("pages", "leads", "sayfalar") and not isinstance(v, (list, dict)) or k in (
                "summary", "count", "url", "job_id", "plan_id", "score", "deployed", "cloned", "status", "message", "mesaj"
            )},
            metadata={"route": route, "source": "main_hook"},
            reason=_pick(result, "reason", "mesaj", "message"),
        )
    except Exception:
        return None


def _module_from_path(path: str) -> str:
    mapping = {
        "/api/content-refresh": "content_refresh_engine",
        "/api/serp-defense": "serp_defense_engine",
        "/api/support-network": "support_network_engine",
        "/api/publisher-hub": "publisher_hub",
        "/api/rank-watcher": "rank_index_watcher",
        "/api/astro-auto": "astro_auto_publisher",
        "/api/astro-factory": "astro_factory",
        "/api/network-replicator": "network_replicator",
        "/api/entity-geo-graph": "entity_geo_graph",
        "/api/seo-quality-gate": "seo_quality_gate",
        "/api/place-seo": "place_seo_pipeline",
        "/api/entity-detail": "entity_detail_generator",
        "/api/listing-hub": "listing_hub",
        "/api/question-intelligence": "question_intelligence_engine",
    }
    for prefix, mod in mapping.items():
        if path.startswith(prefix):
            return mod
    parts = path.strip("/").split("/")
    return parts[1] if len(parts) > 1 else "hive"


def _event_type_from_route(path: str, result: dict[str, Any]) -> str:
    p = path.lower()
    if "create-project" in p or "create_project" in p:
        return "project_created"
    if "generate-pages" in p or "generate-plan" in p or "generate-blog" in p:
        return "content_generated"
    if "publish" in p and "hub" in p:
        return "publisher_success" if _status_from_result(result) == "ok" else "publisher_failed"
    if "publish" in p:
        return "content_published"
    if "refresh" in p or "content-refresh/process" in p:
        return "refresh_completed" if result.get("status") == "completed" else "content_refreshed"
    if "scan" in p and "content-refresh" in p:
        return "refresh_scheduled"
    if "quality-gate" in p or "seo-quality-gate" in p:
        score = result.get("score") or result.get("total_score")
        passed = result.get("passed") or result.get("pass") or (isinstance(score, (int, float)) and score >= 85)
        return "quality_gate_pass" if passed else "quality_gate_fail"
    if "deploy" in p:
        if "fail" in str(result.get("status", "")).lower():
            return "deploy_failed"
        if result.get("url") or result.get("deployment_url"):
            return "deploy_completed"
        return "deploy_started"
    if "create-network" in p:
        return "network_created"
    if "clone" in p or "add-domain" in p:
        return "network_updated"
    if "generate-plan" in p and "serp-defense" in p:
        return "serp_defense_triggered"
    if "analyze-keyword" in p or "defense" in p:
        return "serp_defense_triggered"
    if "link-strategy" in p or "link_strategy" in p:
        return "support_link_planned"
    if "generate-faq" in p or "question-intelligence" in p:
        return "faq_created"
    if "entity-detail" in p and "generate" in p:
        return "entity_created"
    if "rank" in p and ("drop" in str(result).lower() or result.get("change", 0) < 0):
        return "rank_drop"
    if "rank" in p and result.get("change", 0) > 0:
        return "rank_gain"
    if "track" in p or "keyword" in p:
        return "keyword_tracked"
    if "success-path" in p:
        if "recalculate" in p:
            return "success_step_completed"
        if "export" in p:
            return "module_action"
        return "success_path_started"
    if "readiness" in p:
        if "calculate" in p:
            return "readiness_calculated"
        if "export" in p:
            return "module_action"
        return "readiness_calculated"
    return "module_action"
