"""
HIVE V3 Project Engine — kalıcı proje CRUD (project_engine_state.json).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.moduller import site_seed
from app.moduller import block_engine, project_scores, creative_director, project_astro_export, astro_export_engine, astro_build_validator, astro_build_runner, astro_publish_prep, hive_cloud_deploy, hive_production_deploy, hive_production_apply

STATE_FILE = Path(__file__).resolve().parent.parent / "project_engine_state.json"

VALID_STATUSES = frozenset({"draft", "building", "active", "paused", "error"})
VALID_DEPLOY_MODES = frozenset({"hive_cloud", "customer_agent", "enterprise_agent"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("projects", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"projects": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:48] or "project"


def _new_project_id() -> str:
    return f"prj-{uuid.uuid4().hex[:10]}"


def _normalize_project(raw: dict[str, Any]) -> dict[str, Any]:
    pages = raw.get("pages") if isinstance(raw.get("pages"), list) else []
    site = raw.get("site") if isinstance(raw.get("site"), dict) else {}
    pages_count = int(raw.get("pages_count") or site.get("pages_count") or len(pages) or 0)
    return {
        "id": raw.get("id") or raw.get("project_id") or "",
        "name": raw.get("name") or "",
        "sector": raw.get("sector") or "",
        "domain": raw.get("domain") or "",
        "business_brief": raw.get("business_brief") or "",
        "design": raw.get("design") if isinstance(raw.get("design"), dict) else {},
        "site": site,
        "pages": pages,
        "theme": raw.get("theme") if isinstance(raw.get("theme"), dict) else {},
        "navigation": raw.get("navigation") if isinstance(raw.get("navigation"), list) else [],
        "deploy_mode": raw.get("deploy_mode") or "hive_cloud",
        "status": raw.get("status") or "draft",
        "seo_score": int(raw.get("seo_score") or 0),
        "geo_score": int(raw.get("geo_score") or 0),
        "pages_count": pages_count,
        "content_count": int(raw.get("content_count") or block_engine.count_blocks(pages) or site_seed.content_count_from_pages(pages) or 0),
        "metadata": raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {},
        "publishers_count": int(raw.get("publishers_count") or 0),
        "integrations_count": int(raw.get("integrations_count") or 0),
        "created_at": raw.get("created_at") or _now(),
        "updated_at": raw.get("updated_at") or _now(),
    }


def list_projects(
    *,
    status: str = "",
    sector: str = "",
    search: str = "",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    state = _load_state()
    items = [_normalize_project(p) for p in state.get("projects", {}).values()]
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    if status:
        items = [p for p in items if p.get("status") == status.strip()]
    if sector:
        items = [p for p in items if p.get("sector") == sector.strip()]
    if search:
        q = search.strip().lower()
        items = [
            p for p in items
            if q in (p.get("name") or "").lower()
            or q in (p.get("domain") or "").lower()
            or q in (p.get("sector") or "").lower()
        ]

    total = len(items)
    limit = max(1, min(200, int(limit or 50)))
    offset = max(0, int(offset or 0))
    page = items[offset: offset + limit]
    return {"success": True, "count": total, "projects": page}


def get_project(project_id: str) -> dict[str, Any] | None:
    state = _load_state()
    raw = state.get("projects", {}).get(project_id)
    if not raw:
        return None
    return {"success": True, "project": _normalize_project(raw)}


def create_project(
    *,
    name: str,
    sector: str,
    domain: str = "",
    business_brief: str = "",
    design: dict[str, Any] | None = None,
    deploy_mode: str = "hive_cloud",
    status: str = "draft",
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        return {"success": False, "error": "validation_error", "message": "name gerekli"}
    if not (sector or "").strip():
        return {"success": False, "error": "validation_error", "message": "sector gerekli"}

    deploy = (deploy_mode or "hive_cloud").strip()
    if deploy not in VALID_DEPLOY_MODES:
        return {"success": False, "error": "validation_error", "message": "invalid deploy_mode"}

    st = (status or "draft").strip()
    if st not in VALID_STATUSES:
        st = "draft"

    state = _load_state()
    projects = state.setdefault("projects", {})
    pid = _new_project_id()
    design_data = design or {}
    skeleton = site_seed.build_site_skeleton(
        sector=sector.strip(),
        design=design_data,
        project_name=name,
    )
    project = _normalize_project({
        "id": pid,
        "name": name,
        "sector": sector.strip(),
        "domain": (domain or "").strip(),
        "business_brief": (business_brief or "").strip(),
        "design": design_data,
        "deploy_mode": deploy,
        "status": st,
        "site": skeleton["site"],
        "pages": skeleton["pages"],
        "theme": skeleton["theme"],
        "navigation": skeleton["navigation"],
        "pages_count": len(skeleton["pages"]),
        "content_count": site_seed.content_count_from_pages(skeleton["pages"]),
        "created_at": _now(),
        "updated_at": _now(),
    })
    projects[pid] = project
    _save_state(state)
    fill_blocks(pid, use_llm=False)
    raw = _get_raw(pid)
    return {"success": True, "project": _normalize_project(raw or project)}


def update_project(project_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    projects = state.get("projects", {})
    raw = projects.get(project_id)
    if not raw:
        return {"success": False, "error": "not_found"}

    allowed = {
        "name", "sector", "domain", "business_brief", "design",
        "site", "pages", "theme", "navigation",
        "deploy_mode", "status", "seo_score", "geo_score",
        "pages_count", "content_count", "publishers_count", "integrations_count", "metadata",
    }
    for key, val in fields.items():
        if key not in allowed or val is None:
            continue
        if key == "deploy_mode" and val not in VALID_DEPLOY_MODES:
            continue
        if key == "status" and val not in VALID_STATUSES:
            continue
        raw[key] = val

    raw["updated_at"] = _now()
    projects[project_id] = raw
    _save_state(state)
    return {"success": True, "project": _normalize_project(raw)}


def delete_project(project_id: str) -> dict[str, Any]:
    state = _load_state()
    projects = state.get("projects", {})
    if project_id not in projects:
        return {"success": False, "error": "not_found"}
    del projects[project_id]
    _save_state(state)
    return {"success": True, "deleted": project_id}


def _get_raw(project_id: str) -> dict[str, Any] | None:
    state = _load_state()
    return state.get("projects", {}).get(project_id)


def _refresh_scores(project_id: str, *, state: dict[str, Any] | None = None, raw: dict[str, Any] | None = None) -> None:
    if raw is None:
        if state is None:
            state = _load_state()
        raw = state.get("projects", {}).get(project_id)
    if not raw:
        return
    scores = project_scores.compute_scores(raw)
    raw.update(scores)
    raw["content_count"] = block_engine.count_blocks(raw.get("pages") or [])


def fill_blocks(project_id: str, *, use_llm: bool = True) -> dict[str, Any]:
    state = _load_state()
    raw = state.get("projects", {}).get(project_id)
    if not raw:
        return {"success": False, "error": "not_found"}
    stats = block_engine.fill_project_blocks(raw, use_llm=use_llm)
    raw["content_count"] = block_engine.count_blocks(raw.get("pages") or [])
    raw["updated_at"] = _now()
    _refresh_scores(project_id, state=state, raw=raw)
    _save_state(state)
    return {"success": True, "project": _normalize_project(raw), **stats}


def retro_seed(project_id: str) -> dict[str, Any]:
    state = _load_state()
    raw = state.get("projects", {}).get(project_id)
    if not raw:
        return {"success": False, "error": "not_found"}
    if raw.get("site") and raw.get("site", {}).get("site_id"):
        return {"success": True, "project": _normalize_project(raw), "already_seeded": True}
    skeleton = site_seed.build_site_skeleton(
        sector=raw.get("sector", "ozel"),
        design=raw.get("design") if isinstance(raw.get("design"), dict) else {},
        project_name=raw.get("name", ""),
    )
    raw["site"] = skeleton["site"]
    raw["pages"] = skeleton["pages"]
    raw["theme"] = skeleton["theme"]
    raw["navigation"] = skeleton["navigation"]
    raw["pages_count"] = len(skeleton["pages"])
    raw["updated_at"] = _now()
    state["projects"][project_id] = raw
    _save_state(state)
    fill_blocks(project_id, use_llm=False)
    raw = _get_raw(project_id)
    return {"success": True, "project": _normalize_project(raw or {}), "retro_seeded": True}


def export_astro(project_id: str, *, build: bool = False) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found"}
    if not block_engine.count_blocks(raw.get("pages") or []):
        fill_blocks(project_id, use_llm=False)
        raw = _get_raw(project_id)
    result = project_astro_export.export_v3_project(raw or {}, build=build)
    if result.get("success"):
        meta = raw.setdefault("metadata", {}) if raw else {}
        meta["astro_slug"] = result.get("slug")
        meta["astro_path"] = result.get("path")
        meta["astro_built"] = result.get("built", False)
        if raw:
            site = raw.setdefault("site", {})
            site["export_path"] = result.get("path")
            raw["updated_at"] = _now()
            state = _load_state()
            state["projects"][project_id] = raw
            _save_state(state)
    return result


def export_astro_site(project_id: str) -> dict[str, Any]:
    """Sprint 5 — native Astro file export to app/generated_sites/{project_id}/."""
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}

    err = astro_export_engine.validate_project_for_export(raw)
    if err:
        return {"success": False, "error": err, "project_id": project_id}

    if not block_engine.count_blocks(raw.get("pages") or []):
        fill_blocks(project_id, use_llm=False)
        raw = _get_raw(project_id)

    result = astro_export_engine.export_project(raw or {})
    if not result.get("success"):
        return result

    meta = raw.setdefault("metadata", {})
    meta["astro_export"] = {
        "export_path": result.get("export_path"),
        "files_count": result.get("files_count"),
        "entry": result.get("entry"),
        "generated_at": result.get("generated_at"),
    }
    site = raw.setdefault("site", {})
    site["astro_export_path"] = result.get("export_path")
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return result


def get_astro_export_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return astro_export_engine.export_status(raw)


def validate_astro_export(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}

    result = astro_build_validator.validate_project_export(project_id, raw)
    if not result.get("success"):
        return result

    meta = raw.setdefault("metadata", {})
    meta["astro_export_validation"] = {
        "valid": result.get("valid"),
        "errors_count": result.get("errors_count"),
        "warnings_count": result.get("warnings_count"),
        "validated_at": result.get("validated_at"),
        "checks_count": result.get("checks_count"),
        "export_path": result.get("export_path"),
    }
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return result


def get_astro_validate_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return astro_build_validator.validation_status(raw)


def can_publish_astro(project: dict[str, Any]) -> dict[str, Any]:
    """Static publish gate — export + validation + sitemap required."""
    reasons: list[str] = []
    meta = project.get("metadata") or {}
    astro_export = meta.get("astro_export") or {}
    validation = meta.get("astro_export_validation") or {}

    export_path = astro_export.get("export_path")
    if not export_path:
        reasons.append("astro_export_missing")

    if not validation.get("validated_at"):
        reasons.append("astro_validation_missing")
    elif not validation.get("valid"):
        reasons.append("astro_validation_failed")
    elif int(validation.get("errors_count") or 0) > 0:
        reasons.append("astro_validation_failed")

    if export_path:
        sitemap = Path(export_path) / "public" / "sitemap.xml"
        if not sitemap.is_file():
            reasons.append("sitemap_missing")
    elif "sitemap_missing" not in reasons and "astro_export_missing" not in reasons:
        reasons.append("sitemap_missing")

    gate = {
        "can_publish": len(reasons) == 0,
        "reasons": reasons,
        "checked_at": _now(),
    }
    return gate


def get_publish_gate(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    astro_gate = can_publish_astro(raw)
    meta = raw.setdefault("metadata", {})
    meta["astro_publish_gate"] = astro_gate
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return {
        "success": True,
        "project_id": project_id,
        "astro": astro_gate,
    }


def run_astro_build(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}

    gate = can_publish_astro(raw)
    result = astro_build_runner.run_build(project_id, raw, gate=gate)

    meta = raw.setdefault("metadata", {})
    build_record = {
        "status": result.get("status", "build_failed"),
        "dist_path": result.get("dist_path"),
        "built_at": result.get("built_at"),
        "commands": result.get("commands") or [],
        "errors_count": int(result.get("errors_count") or (0 if result.get("success") else 1)),
        "error": result.get("error"),
        "export_path": result.get("export_path"),
        "stdout_tail": result.get("stdout_tail"),
        "stderr_tail": result.get("stderr_tail"),
    }
    meta["astro_build"] = build_record
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return result


def get_astro_build_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return astro_build_runner.build_status(raw)


def prepare_publish_artifact(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}

    result = astro_publish_prep.prepare_artifact(project_id, raw)
    meta = raw.setdefault("metadata", {})
    meta["astro_publish_artifact"] = {
        "status": result.get("status", "prep_failed"),
        "artifact_path": result.get("artifact_path"),
        "files_count": result.get("files_count"),
        "total_size_bytes": result.get("total_size_bytes"),
        "entry": result.get("entry"),
        "prepared_at": result.get("prepared_at"),
        "error": result.get("error"),
        "dist_path": result.get("dist_path"),
    }
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return result


def get_prepare_publish_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return astro_publish_prep.prep_status(raw)


def deploy_hive_cloud(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}

    result = hive_cloud_deploy.deploy_to_hive_cloud(project_id, raw)
    meta = raw.setdefault("metadata", {})
    meta["hive_cloud_deploy"] = {
        "status": result.get("status", "deploy_failed"),
        "deploy_path": result.get("deploy_path"),
        "live_url": result.get("live_url"),
        "files_count": result.get("files_count"),
        "total_size_bytes": result.get("total_size_bytes"),
        "deployed_at": result.get("deployed_at"),
        "error": result.get("error"),
    }
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return result


def get_hive_cloud_deploy_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return hive_cloud_deploy.deploy_status(raw)


def bind_project_domain(project_id: str, domain: str, *, include_www: bool = True) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    try:
        result = hive_production_deploy.bind_domain(domain, include_www=include_www)
    except ValueError as exc:
        return {"success": False, "error": str(exc), "project_id": project_id}
    meta = raw.setdefault("metadata", {})
    meta["domain_binding"] = {
        "domain": result["domain"],
        "www_domain": result.get("www_domain", ""),
        "target_type": result["target_type"],
        "status": result["status"],
        "ssl_status": result["ssl_status"],
        "created_at": result["created_at"],
    }
    raw["domain"] = result["domain"]
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return {**result, "project_id": project_id}


def get_domain_binding_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return hive_production_deploy.domain_status(raw)


def plan_production_deploy(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}

    result = hive_production_deploy.plan_production_deploy(project_id, raw)
    meta = raw.setdefault("metadata", {})
    meta["hive_production_deploy"] = {
        "status": result.get("status", "plan_failed"),
        "domain": result.get("domain"),
        "production_path": result.get("production_path"),
        "source_path": result.get("source_path"),
        "nginx_config_path": result.get("nginx_config_path"),
        "live_url": result.get("live_url"),
        "planned_at": result.get("planned_at"),
        "error": result.get("error"),
    }
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return result


def get_production_deploy_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return hive_production_deploy.production_deploy_status(raw)


def get_production_nginx_preview(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return hive_production_deploy.nginx_preview(raw)


def generate_production_apply_script(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}

    result = hive_production_apply.generate_production_apply_script(project_id, raw)
    meta = raw.setdefault("metadata", {})
    meta["hive_production_apply_script"] = {
        "status": result.get("status", "script_failed"),
        "domain": result.get("domain"),
        "created_at": result.get("created_at"),
        "requires_root": result.get("requires_root", True),
        "error": result.get("error"),
    }
    raw["updated_at"] = _now()
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return result


def get_production_apply_script_status(project_id: str) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found", "project_id": project_id}
    return hive_production_apply.apply_script_status(raw)


def publish_project(project_id: str, *, build: bool = True) -> dict[str, Any]:
    state = _load_state()
    raw = state.get("projects", {}).get(project_id)
    if not raw:
        return {"success": False, "error": "not_found"}
    raw["status"] = "building"
    site = raw.setdefault("site", {})
    site["status"] = "building"
    raw["updated_at"] = _now()
    _save_state(state)

    fill_blocks(project_id, use_llm=True)
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found"}
    _refresh_scores(project_id)
    raw = _get_raw(project_id)

    export_res = project_astro_export.export_v3_project(raw or {}, build=build)
    if not export_res.get("success"):
        raw["status"] = "error"
        site["status"] = "error"
        raw.setdefault("metadata", {})["publish_error"] = export_res.get("error")
        _save_state(state)
        return {"success": False, "error": export_res.get("error"), "stage": "export"}

    raw["status"] = "active"
    site["status"] = "active"
    site["live_url"] = raw.get("domain") or f"file://{export_res.get('path')}/dist"
    meta = raw.setdefault("metadata", {})
    meta["astro_slug"] = export_res.get("slug")
    meta["astro_path"] = export_res.get("path")
    meta["published_at"] = _now()
    site["export_path"] = export_res.get("path")
    raw["updated_at"] = _now()
    _save_state(state)
    return {
        "success": True,
        "project": _normalize_project(raw),
        "export": export_res,
    }


def creative_suggest(
    *,
    sector: str,
    business_brief: str = "",
    creative_brief: str = "",
    use_llm: bool = True,
) -> dict[str, Any]:
    return creative_director.suggest(
        sector=sector,
        business_brief=business_brief,
        creative_brief=creative_brief,
        use_llm=use_llm,
    )


def update_page(project_id: str, page_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    raw = _get_raw(project_id)
    if not raw:
        return {"success": False, "error": "not_found"}
    pages = raw.get("pages") or []
    page = next((p for p in pages if p.get("id") == page_id), None)
    if not page:
        return {"success": False, "error": "page_not_found"}
    for key in ("title", "slug", "type", "status", "seo", "sections"):
        if key in fields and fields[key] is not None:
            page[key] = fields[key]
    raw["updated_at"] = _now()
    _refresh_scores(project_id)
    state = _load_state()
    state["projects"][project_id] = raw
    _save_state(state)
    return {"success": True, "page": page, "project": _normalize_project(raw)}


def health() -> dict[str, Any]:
    state = _load_state()
    count = len(state.get("projects") or {})
    return {
        "success": True,
        "module": "project_engine",
        "projects_count": count,
        "state_file": str(STATE_FILE),
    }
