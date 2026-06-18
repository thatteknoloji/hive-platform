"""
Google Blogger API v3 — HIVE Panel modülü
"""

from __future__ import annotations

import logging
from typing import Any

from app import config

logger = logging.getLogger("hive.blogger")

SCOPES = ["https://www.googleapis.com/auth/blogger"]
_STATUS_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_STATUS_TTL_SEC = 300
_STATUS_LOCK = __import__("threading").Lock()


def _client_id() -> str:
    return (config.get("GOOGLE_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (config.get("GOOGLE_CLIENT_SECRET") or "").strip()


def _refresh_token() -> str:
    return (config.get("GOOGLE_REFRESH_TOKEN") or "").strip()


def default_blog_id() -> str:
    return (config.get("BLOGGER_DEFAULT_BLOG_ID") or "").strip()


def is_configured() -> bool:
    return bool(_client_id() and _client_secret() and _refresh_token())


def _service():
    if not is_configured():
        raise RuntimeError(
            "Blogger OAuth eksik. backend/.env → GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN"
        )
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError as e:
        raise RuntimeError("pip install google-api-python-client google-auth") from e

    creds = Credentials(
        token=None,
        refresh_token=_refresh_token(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_client_id(),
        client_secret=_client_secret(),
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("blogger", "v3", credentials=creds, cache_discovery=False)


def get_status(*, force: bool = False) -> dict[str, Any]:
    import time
    now = time.monotonic()
    if not force and _STATUS_CACHE["data"] is not None and (now - _STATUS_CACHE["at"]) < _STATUS_TTL_SEC:
        return dict(_STATUS_CACHE["data"])

    with _STATUS_LOCK:
        now = time.monotonic()
        if not force and _STATUS_CACHE["data"] is not None and (now - _STATUS_CACHE["at"]) < _STATUS_TTL_SEC:
            return dict(_STATUS_CACHE["data"])

        if not is_configured():
            result = {
                "success": True,
                "configured": False,
                "connected": False,
                "hint": "Google OAuth bilgilerini backend/.env dosyasına ekleyin",
            }
        else:
            try:
                svc = _service()
                blogs = svc.blogs().listByUser(userId="self").execute()
                items = blogs.get("items") or []
                default_id = default_blog_id()
                result = {
                    "success": True,
                    "configured": True,
                    "connected": True,
                    "blog_count": len(items),
                    "default_blog_id": default_id,
                    "blogs": [
                        {
                            "id": b.get("id"),
                            "name": b.get("name"),
                            "url": b.get("url"),
                            "posts": (b.get("posts") or {}).get("totalItems", 0),
                        }
                        for b in items
                    ],
                }
            except Exception as e:
                logger.warning("Blogger status hatası: %s", e)
                result = {"success": False, "configured": True, "connected": False, "error": str(e)}

        _STATUS_CACHE["at"] = now
        _STATUS_CACHE["data"] = result
        return dict(result)


def list_blogs() -> dict[str, Any]:
    svc = _service()
    res = svc.blogs().listByUser(userId="self").execute()
    items = res.get("items") or []
    return {
        "success": True,
        "blogs": [
            {
                "id": b.get("id"),
                "name": b.get("name"),
                "url": b.get("url"),
                "description": b.get("description", ""),
                "posts": (b.get("posts") or {}).get("totalItems", 0),
            }
            for b in items
        ],
    }


def _resolve_blog_id(blog_id: str | None) -> str:
    bid = (blog_id or default_blog_id() or "").strip()
    if not bid:
        raise ValueError("blog_id gerekli veya BLOGGER_DEFAULT_BLOG_ID tanımlayın")
    return bid


def list_posts(blog_id: str | None = None, max_results: int = 20, status: str = "live") -> dict[str, Any]:
    svc = _service()
    bid = _resolve_blog_id(blog_id)
    params: dict[str, Any] = {"blogId": bid, "maxResults": max(1, min(max_results, 50))}
    status_key = (status or "live").strip().lower()
    if status_key == "draft":
        params["status"] = "DRAFT"
    elif status_key in ("scheduled", "soft_trashed"):
        params["status"] = status_key.upper()
    res = svc.posts().list(**params).execute()
    posts = []
    for p in res.get("items") or []:
        posts.append({
            "id": p.get("id"),
            "title": p.get("title"),
            "url": p.get("url"),
            "published": p.get("published"),
            "updated": p.get("updated"),
            "status": p.get("status", "LIVE"),
            "labels": p.get("labels") or [],
        })
    return {"success": True, "blog_id": bid, "posts": posts, "total": len(posts)}


def create_post(
    title: str,
    content: str,
    blog_id: str | None = None,
    labels: list[str] | None = None,
    publish: bool = True,
) -> dict[str, Any]:
    if not title.strip():
        raise ValueError("Başlık gerekli")
    if not content.strip():
        raise ValueError("İçerik gerekli")

    svc = _service()
    bid = _resolve_blog_id(blog_id)
    body = {
        "kind": "blogger#post",
        "title": title.strip(),
        "content": content,
        "labels": labels or [],
    }
    res = svc.posts().insert(blogId=bid, body=body, isDraft=not publish).execute()
    post_id = res.get("id")
    status = res.get("status", "DRAFT" if not publish else "LIVE")

    if publish and status == "DRAFT" and post_id:
        res = svc.posts().publish(blogId=bid, postId=post_id).execute()
        status = res.get("status", "LIVE")

    return {
        "success": True,
        "post_id": post_id,
        "title": res.get("title"),
        "url": res.get("url"),
        "status": status,
        "published": res.get("published"),
        "message": "Yazı yayınlandı" if publish else "Taslak oluşturuldu",
    }


def publish_post(post_id: str, blog_id: str | None = None) -> dict[str, Any]:
    svc = _service()
    bid = _resolve_blog_id(blog_id)
    res = svc.posts().publish(blogId=bid, postId=post_id).execute()
    return {
        "success": True,
        "post_id": res.get("id"),
        "url": res.get("url"),
        "status": res.get("status"),
        "message": "Yazı yayınlandı",
    }


def delete_post(post_id: str, blog_id: str | None = None) -> dict[str, Any]:
    svc = _service()
    bid = _resolve_blog_id(blog_id)
    svc.posts().delete(blogId=bid, postId=post_id).execute()
    return {"success": True, "message": "Yazı silindi", "post_id": post_id}
