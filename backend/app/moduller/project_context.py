"""
HIVE V3 project context — active project + domain resolution via project_engine.
"""

from __future__ import annotations

from typing import Any

from app import panel_identity
from app.moduller import project_engine as pe
from app.moduller.legacy_project_migration import strip_legacy_active_project_id


def get_active_project_id() -> str:
    raw = panel_identity.get_active_project_id()
    return strip_legacy_active_project_id(raw)


def set_active_project(project_id: str) -> dict[str, Any]:
    pid = (project_id or "").strip()
    if not pid:
        if not panel_identity.set_active_project(""):
            return {"success": False, "error": "set_failed"}
        return {"success": True, "active_project_id": "", "project": None}

    if not pe.get_project(pid):
        return {"success": False, "error": "not_found", "project_id": pid}

    if not panel_identity.set_active_project(pid):
        return {"success": False, "error": "set_failed", "project_id": pid}

    project = pe.get_project(pid)
    return {
        "success": True,
        "active_project_id": pid,
        "project": project.get("project") if project else None,
    }


def get_active_project_payload() -> dict[str, Any]:
    pid = get_active_project_id()
    if not pid:
        return {"success": True, "active_project_id": "", "project": None}

    result = pe.get_project(pid)
    if not result:
        return {
            "success": True,
            "active_project_id": pid,
            "project": None,
            "stale": True,
        }
    return {
        "success": True,
        "active_project_id": pid,
        "project": result.get("project"),
    }


def resolve_domain(project_id: str = "") -> str:
    pid = (project_id or get_active_project_id()).strip()
    if not pid:
        return ""
    result = pe.get_project(pid)
    if not result:
        return ""
    return (result["project"].get("domain") or "").strip()


def resolve_site_url(project_id: str = "") -> str:
    domain = resolve_domain(project_id)
    if not domain:
        return ""
    if domain.startswith("http://") or domain.startswith("https://"):
        return domain.rstrip("/")
    return f"https://{domain.rstrip('/')}"


def list_projects_for_panel(limit: int = 200) -> list[dict[str, Any]]:
    result = pe.list_projects(limit=limit)
    items: list[dict[str, Any]] = []
    for project in result.get("projects", []):
        items.append({
            "project_id": project.get("id"),
            "id": project.get("id"),
            "name": project.get("name"),
            "domain": project.get("domain") or "",
            "type": project.get("sector") or "",
            "status": project.get("status") or "",
            "sector": project.get("sector") or "",
        })
    return items
