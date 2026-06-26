from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app import panel_identity
from app.moduller import project_engine as pe
from app.moduller.project_context import get_active_project_id, set_active_project as set_active_ctx

router = APIRouter(prefix="/api")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _current_user(request: Request) -> dict[str, Any]:
    user = getattr(request.state, "hive_user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user


def _require(request: Request, module: str, action: str) -> dict[str, Any]:
    user = _current_user(request)
    if not panel_identity.has_permission(user.get("role", ""), module, action):
        raise HTTPException(status_code=403, detail="Permission denied")
    return user


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


class UserCreateBody(BaseModel):
    email: str
    name: str = ""
    role: str = "viewer"
    allowed_projects: list[str] = []
    status: str = "active"
    password: str = "hive123"


class UserUpdateBody(BaseModel):
    name: str | None = None
    role: str | None = None
    allowed_projects: list[str] | None = None
    status: str | None = None


class ResetPasswordBody(BaseModel):
    password: str = "hive123"


class AssignRoleBody(BaseModel):
    role: str


class ProjectCreateBody(BaseModel):
    name: str
    domain: str
    type: str = "custom"
    status: str = "active"
    settings: dict[str, Any] = {}


class ProjectUpdateBody(BaseModel):
    name: str | None = None
    domain: str | None = None
    type: str | None = None
    status: str | None = None
    settings: dict[str, Any] | None = None


@router.post("/auth/change-password")
def auth_change_password(body: ChangePasswordBody, request: Request):
    user = _current_user(request)
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 chars")
    ok = panel_identity.change_password(user["email"], body.current_password, body.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail="Current password is invalid")
    return {"success": True}


@router.get("/users")
def list_users(request: Request):
    _require(request, "users", "view")
    return {"items": panel_identity.list_users()}


@router.post("/users")
def create_user(body: UserCreateBody, request: Request):
    _require(request, "users", "create")
    state = panel_identity.bootstrap()
    email = body.email.strip().lower()
    if any(u.get("email") == email for u in state["users"]):
        raise HTTPException(status_code=409, detail="User already exists")
    if body.role not in panel_identity.ROLE_PERMISSIONS:
        raise HTTPException(status_code=400, detail="Invalid role")
    state["users"].append(
        {
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": email,
            "name": body.name or email.split("@")[0],
            "role": body.role,
            "allowed_projects": body.allowed_projects or [],
            "status": body.status,
            "password_hash": panel_identity._hash_password(body.password),  # noqa: SLF001
            "must_change_password": body.password == "hive123",
            "created_at": _now(),
            "last_login_at": "",
        }
    )
    panel_identity._write(state)  # noqa: SLF001
    return {"success": True}


@router.get("/users/{user_id}")
def get_user(user_id: str, request: Request):
    _require(request, "users", "view")
    user = panel_identity.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return panel_identity.sanitize_user(user)


@router.patch("/users/{user_id}")
def patch_user(user_id: str, body: UserUpdateBody, request: Request):
    _require(request, "users", "edit")
    state = panel_identity.bootstrap()
    user = next((u for u in state["users"] if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.name is not None:
        user["name"] = body.name
    if body.role is not None:
        if body.role not in panel_identity.ROLE_PERMISSIONS:
            raise HTTPException(status_code=400, detail="Invalid role")
        user["role"] = body.role
    if body.allowed_projects is not None:
        user["allowed_projects"] = body.allowed_projects
    if body.status is not None:
        user["status"] = body.status
    panel_identity._write(state)  # noqa: SLF001
    return {"success": True}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, request: Request):
    _require(request, "users", "delete")
    state = panel_identity.bootstrap()
    before = len(state["users"])
    state["users"] = [u for u in state["users"] if u.get("user_id") != user_id]
    panel_identity._write(state)  # noqa: SLF001
    return {"success": len(state["users"]) < before}


@router.post("/users/{user_id}/reset-password")
def reset_user_password(user_id: str, body: ResetPasswordBody, request: Request):
    _require(request, "users", "edit")
    state = panel_identity.bootstrap()
    user = next((u for u in state["users"] if u.get("user_id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["password_hash"] = panel_identity._hash_password(body.password)  # noqa: SLF001
    user["must_change_password"] = True
    panel_identity._write(state)  # noqa: SLF001
    return {"success": True}


@router.post("/users/{user_id}/assign-role")
def assign_role(user_id: str, body: AssignRoleBody, request: Request):
    return patch_user(user_id, UserUpdateBody(role=body.role), request)


@router.get("/projects")
def list_projects(request: Request):
    _require(request, "projects", "view")
    user = _current_user(request)
    allowed = set(user.get("allowed_projects") or [])
    items = panel_identity.list_projects()
    if "*" not in allowed and allowed:
        items = [p for p in items if p.get("project_id") in allowed or p.get("id") in allowed]
    return {"items": items, "active_project_id": get_active_project_id()}


@router.post("/projects")
def create_project(body: ProjectCreateBody, request: Request):
    _require(request, "projects", "create")
    sector = (body.type or "custom").strip()
    status = body.status if body.status in pe.VALID_STATUSES else "draft"
    result = pe.create_project(
        name=body.name,
        sector=sector,
        domain=body.domain,
        status=status,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message") or result.get("error"))
    project = result["project"]
    return {"success": True, "project_id": project["id"], "project": project}


@router.get("/projects/{project_id}")
def get_project(project_id: str, request: Request):
    _require(request, "projects", "view")
    result = pe.get_project(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result["project"]


@router.patch("/projects/{project_id}")
def patch_project(project_id: str, body: ProjectUpdateBody, request: Request):
    _require(request, "projects", "edit")
    fields: dict[str, Any] = {}
    if body.name is not None:
        fields["name"] = body.name
    if body.domain is not None:
        fields["domain"] = body.domain
    if body.type is not None:
        fields["sector"] = body.type
    if body.status is not None:
        fields["status"] = body.status
    if body.settings is not None:
        fields["metadata"] = body.settings
    result = pe.update_project(project_id, fields)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "project": result.get("project")}


@router.delete("/projects/{project_id}")
def delete_project(project_id: str, request: Request):
    _require(request, "projects", "delete")
    result = pe.delete_project(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail="Project not found")
    state = panel_identity.bootstrap()
    if state.get("active_project_id") == project_id:
        state["active_project_id"] = ""
        panel_identity._write(state)  # noqa: SLF001
    return {"success": True}


@router.post("/projects/{project_id}/set-active")
def set_active_project_route(project_id: str, request: Request):
    _require(request, "projects", "edit")
    result = set_active_ctx(project_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error") or "Project not found")
    return {"success": True, "active_project_id": result.get("active_project_id", project_id)}
