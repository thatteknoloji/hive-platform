"""HIVE panel authentication — JWT session for production panel."""

from __future__ import annotations

import time
from typing import Any

import jwt
from app import config
from app import panel_identity

JWT_ALGORITHM = "HS256"
JWT_TTL_SEC = int(config.get("HIVE_SESSION_TTL_HOURS", "24") or "24") * 60 * 60


def auth_enabled() -> bool:
    state = panel_identity.bootstrap()
    return len(state.get("users", [])) > 0


def _jwt_secret() -> str:
    secret = config.get("HIVE_JWT_SECRET", "").strip()
    if not secret:
        secret = config.get("HIVE_API_KEY", "").strip()
    return secret or "hive-dev-insecure-change-me"


def hash_password(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    if not plain or not password_hash:
        return False
    try:
        import bcrypt
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(*, email: str) -> str:
    now = int(time.time())
    payload = {
        "sub": email,
        "iat": now,
        "exp": now + JWT_TTL_SEC,
        "typ": "hive_panel",
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("typ") != "hive_panel":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def login(email: str, password: str) -> dict[str, Any]:
    if not auth_enabled():
        return {"success": False, "error": "auth_not_configured"}
    user = panel_identity.authenticate(email, password)
    if not user:
        return {"success": False, "error": "invalid_credentials"}
    token = create_access_token(email=user["email"])
    return {
        "success": True,
        "token": token,
        "expires_in": JWT_TTL_SEC,
        "user": user,
    }


def me_from_token(token: str) -> dict[str, Any]:
    payload = verify_access_token(token)
    if not payload:
        return {"success": False, "authenticated": False}
    user = panel_identity.get_user_by_email(payload.get("sub", ""))
    if not user:
        return {"success": False, "authenticated": False}
    return {
        "success": True,
        "authenticated": True,
        "user": panel_identity.sanitize_user(user),
        "active_project_id": panel_identity.get_active_project_id(),
        "permissions": panel_identity.ROLE_PERMISSIONS.get(user.get("role", ""), {}),
    }
