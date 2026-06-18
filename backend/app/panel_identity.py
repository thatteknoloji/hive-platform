from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bcrypt

STATE_FILE = Path(__file__).resolve().parent / "panel_identity_state.json"

ROLE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "super_admin": {"*": ["view", "create", "edit", "delete", "run", "publish", "admin"]},
    "admin": {
        "dashboard": ["view"],
        "mission_control": ["view", "run"],
        "campaign_engine": ["view", "create", "edit", "run"],
        "seo_core": ["view", "create", "edit", "run"],
        "rank_watcher": ["view", "run"],
        "citation_engine": ["view", "create", "edit", "run"],
        "authority_factory": ["view", "create", "edit", "run", "publish"],
        "data_miner": ["view", "run"],
        "publisher_hub": ["view", "create", "edit", "publish"],
        "content": ["view", "create", "edit", "publish"],
        "projects": ["view", "create", "edit", "delete"],
    },
    "seo_manager": {
        "dashboard": ["view"],
        "campaign_engine": ["view", "create", "edit", "run"],
        "seo_core": ["view", "create", "edit", "run"],
        "rank_watcher": ["view", "run"],
        "citation_engine": ["view", "create", "edit", "run"],
        "authority_factory": ["view", "create", "edit", "run"],
        "mission_control": ["view"],
    },
    "editor": {
        "dashboard": ["view"],
        "content": ["view", "create", "edit", "publish"],
        "publisher_hub": ["view", "create", "edit", "publish"],
        "data_miner": ["view", "run"],
    },
    "viewer": {"dashboard": ["view"], "reports": ["view"]},
}

ROUTE_PERMISSIONS: list[tuple[str, str]] = [
    ("/api/users", "users"),
    ("/api/v3/projects", "projects"),
    ("/api/projects", "projects"),
    ("/api/campaign", "campaign_engine"),
    ("/api/crawl-gap", "seo_core"),
    ("/api/rank-watcher", "rank_watcher"),
    ("/api/ranktracker", "rank_watcher"),
    ("/api/citation", "citation_engine"),
    ("/api/authority-factory", "authority_factory"),
    ("/api/authority-mesh", "authority_factory"),
    ("/api/data-miner", "data_miner"),
    ("/api/publisher-hub", "publisher_hub"),
    ("/api/content-refresh", "content"),
    ("/api/question-intelligence", "content"),
    ("/api/mission-control", "mission_control"),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"users": [], "projects": [], "active_project_id": "", "audit": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"users": [], "projects": [], "active_project_id": "", "audit": []}


def _write(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def bootstrap() -> dict[str, Any]:
    state = _read()
    changed = False
    now = _now()

    if not any(p.get("project_id") == "balkutusu" for p in state["projects"]):
        state["projects"].append(
            {
                "project_id": "balkutusu",
                "name": "Bal Kutusu",
                "domain": "https://www.balkutusu.com",
                "type": "listing",
                "status": "active",
                "settings": {
                    "target_city": "",
                    "target_keywords": [],
                    "brand_name": "Bal Kutusu",
                    "language": "tr",
                },
                "created_at": now,
                "updated_at": now,
            }
        )
        changed = True

    if not state.get("active_project_id"):
        state["active_project_id"] = "balkutusu"
        changed = True

    default_email = (os.environ.get("HIVE_DEFAULT_ADMIN_EMAIL") or os.environ.get("HIVE_ADMIN_EMAIL") or "").strip().lower()
    default_password = (os.environ.get("HIVE_DEFAULT_ADMIN_PASSWORD") or "").strip()
    old_hash = (os.environ.get("HIVE_ADMIN_PASSWORD_HASH") or "").strip()

    if default_email and not any(u.get("email") == default_email for u in state["users"]):
        password_hash = old_hash or _hash_password(default_password or "hive123")
        state["users"].append(
            {
                "user_id": f"user_{uuid.uuid4().hex[:12]}",
                "email": default_email,
                "name": "HIVE Admin",
                "role": "super_admin",
                "allowed_projects": ["*"],
                "status": "active",
                "password_hash": password_hash,
                "must_change_password": (default_password or "hive123") == "hive123",
                "created_at": now,
                "last_login_at": "",
            }
        )
        changed = True

    if changed:
        _write(state)
    return state


def reset_user_password(email: str, new_password: str) -> dict[str, Any]:
    state = bootstrap()
    em = email.strip().lower()
    if not em or not new_password:
        return {"success": False, "error": "validation_error"}
    user = next((u for u in state["users"] if u.get("email") == em), None)
    if not user:
        return {"success": False, "error": "user_not_found"}
    user["password_hash"] = _hash_password(new_password)
    user["must_change_password"] = False
    user["updated_at"] = _now()
    _write(state)
    _audit("password_reset", em)
    return {"success": True, "email": em}


def create_user(
    *,
    email: str,
    password: str,
    name: str = "",
    role: str = "admin",
    allowed_projects: list[str] | None = None,
) -> dict[str, Any]:
    state = bootstrap()
    em = email.strip().lower()
    if not em or not password:
        return {"success": False, "error": "validation_error"}
    if get_user_by_email(em):
        return {"success": False, "error": "email_exists"}
    if role not in ROLE_PERMISSIONS:
        return {"success": False, "error": "invalid_role"}
    user = {
        "user_id": f"user_{uuid.uuid4().hex[:12]}",
        "email": em,
        "name": (name or em.split("@")[0]).strip(),
        "role": role,
        "allowed_projects": allowed_projects if allowed_projects is not None else ["*"],
        "status": "active",
        "password_hash": _hash_password(password),
        "must_change_password": False,
        "created_at": _now(),
        "last_login_at": "",
    }
    state["users"].append(user)
    _write(state)
    _audit("user_created", em)
    return {"success": True, "user": sanitize_user(user)}


def list_users() -> list[dict[str, Any]]:
    state = bootstrap()
    out = []
    for user in state["users"]:
        safe = {k: v for k, v in user.items() if k != "password_hash"}
        out.append(safe)
    return out


def get_user_by_email(email: str) -> dict[str, Any] | None:
    state = bootstrap()
    em = email.strip().lower()
    return next((u for u in state["users"] if u.get("email") == em), None)


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    state = bootstrap()
    return next((u for u in state["users"] if u.get("user_id") == user_id), None)


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    state = bootstrap()
    em = email.strip().lower()
    user = next((u for u in state["users"] if u.get("email") == em), None)
    if not user or user.get("status") != "active":
        _audit("login_failed", em)
        return None
    if not _verify_password(password, user.get("password_hash", "")):
        _audit("login_failed", em)
        return None
    user["last_login_at"] = _now()
    _write(state)
    _audit("login_success", em)
    return {k: v for k, v in user.items() if k != "password_hash"}


def change_password(email: str, current_password: str, new_password: str) -> bool:
    state = bootstrap()
    em = email.strip().lower()
    user = next((u for u in state["users"] if u.get("email") == em), None)
    if not user:
        return False
    if not _verify_password(current_password, user.get("password_hash", "")):
        return False
    user["password_hash"] = _hash_password(new_password)
    user["must_change_password"] = False
    _write(state)
    return True


def _audit(event: str, email: str) -> None:
    state = _read()
    state.setdefault("audit", []).append({"event": event, "email": email, "at": _now()})
    state["audit"] = state["audit"][-500:]
    _write(state)


def list_projects() -> list[dict[str, Any]]:
    return bootstrap()["projects"]


def get_active_project_id() -> str:
    return bootstrap().get("active_project_id", "balkutusu")


def set_active_project(project_id: str) -> bool:
    state = bootstrap()
    if not any(p.get("project_id") == project_id for p in state["projects"]):
        return False
    state["active_project_id"] = project_id
    _write(state)
    return True


def has_permission(role: str, module: str, action: str) -> bool:
    module_map = ROLE_PERMISSIONS.get(role, {})
    if "*" in module_map:
        return True
    actions = module_map.get(module, [])
    return action in actions or "admin" in actions


def module_for_path(path: str) -> str | None:
    for prefix, module in ROUTE_PERMISSIONS:
        if path.startswith(prefix):
            return module
    return None


def sanitize_user(user: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in user.items() if k != "password_hash"}
