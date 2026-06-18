"""
Medium Bot — Medium Integration API (OAuth token).

MEDIUM_TOKEN backend/.env'den okunur.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests
from fastapi import HTTPException

from app import config
from .modul_base import simdi

logger = logging.getLogger("hive.medium_bot")

MEDIUM_API = "https://api.medium.com/v1"
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "medium_bot_posts.json"
)


def _token() -> str:
    tok = (config.get("MEDIUM_TOKEN") or "").strip()
    if not tok:
        raise HTTPException(
            status_code=400,
            detail="Medium bağlantısı kurulmamış — backend/.env dosyasına MEDIUM_TOKEN ekleyin",
        )
    return tok


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _load_db() -> list[dict]:
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_db(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(rows[-500:], f, indent=2, ensure_ascii=False)


def _request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    url = f"{MEDIUM_API}{path}"
    try:
        r = requests.request(method, url, headers=_headers(), timeout=30, **kwargs)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Medium API bağlantı hatası: {exc}") from exc
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Medium token geçersiz — MEDIUM_TOKEN yenileyin")
    if r.status_code >= 400:
        try:
            err = r.json()
            msg = err.get("errors", [{}])[0].get("message") if isinstance(err.get("errors"), list) else r.text
        except Exception:
            msg = r.text[:300]
        raise HTTPException(status_code=r.status_code, detail=f"Medium API: {msg or r.status_code}")
    try:
        return r.json()
    except Exception:
        return {"raw": r.text}


def get_me() -> dict[str, Any]:
    """Medium kullanıcı bilgisi — token doğrulama."""
    _token()
    data = _request("GET", "/me")
    user = data.get("data") or {}
    return {
        "success": True,
        "connected": True,
        "user_id": user.get("id"),
        "username": user.get("username"),
        "name": user.get("name"),
        "url": user.get("url"),
        "image_url": user.get("imageUrl"),
    }


def health() -> dict[str, Any]:
    try:
        me = get_me()
        return {
            "success": True,
            "module": "medium_bot",
            "connected": True,
            "username": me.get("username"),
            "posts_logged": len(_load_db()),
        }
    except HTTPException as exc:
        return {
            "success": False,
            "module": "medium_bot",
            "connected": False,
            "error": exc.detail,
        }


def publish_to_medium(title: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
    """Medium'da yazı yayınla — gerçek API."""
    if not title.strip():
        raise HTTPException(status_code=400, detail="title gerekli")
    if not content.strip():
        raise HTTPException(status_code=400, detail="content gerekli")

    me = get_me()
    user_id = me.get("user_id")
    if not user_id:
        raise HTTPException(status_code=502, detail="Medium user_id alınamadı")

    tag_list = [t.strip() for t in (tags or []) if t and str(t).strip()][:5]
    payload = {
        "title": title.strip(),
        "contentFormat": "markdown",
        "content": content.strip(),
        "tags": tag_list,
        "publishStatus": "public",
    }
    data = _request("POST", f"/users/{user_id}/posts", json=payload)
    post = data.get("data") or {}

    record = {
        "type": "publish",
        "post_id": post.get("id"),
        "title": post.get("title") or title,
        "url": post.get("url"),
        "published_at": post.get("publishedAt") or simdi(),
        "tags": tag_list,
        "created_at": simdi(),
    }
    db = _load_db()
    db.append(record)
    _save_db(db)

    return {
        "success": True,
        "post_id": post.get("id"),
        "url": post.get("url"),
        "title": post.get("title"),
        "published_at": post.get("publishedAt"),
        "provider": "medium_api",
        "record": record,
    }


def _extract_post_id(article_url: str) -> str:
    """Medium URL'den post id veya slug çıkar."""
    url = (article_url or "").strip()
    if not url:
        return ""
    m = re.search(r"medium\.com/(?:@[\w-]+/)?([a-f0-9]{12,})(?:\?|$|/)", url, re.I)
    if m:
        return m.group(1)
    m = re.search(r"/p/([a-f0-9]{12,})", url, re.I)
    if m:
        return m.group(1)
    return ""


def comment_on_article(article_url: str, comment_text: str) -> dict[str, Any]:
    """
    Medium yorumu — resmi API yorum endpoint'i olmadığından
    makaleye linkli kısa public response post oluşturur.
    """
    if not article_url.strip():
        raise HTTPException(status_code=400, detail="article_url gerekli")
    if not comment_text.strip():
        raise HTTPException(status_code=400, detail="comment_text gerekli")

    post_id = _extract_post_id(article_url)
    title = f"Response — {article_url[:80]}"
    body = (
        f"> Yorum hedefi: [{article_url}]({article_url.strip()})\n\n"
        f"{comment_text.strip()}\n\n"
        f"---\n*Medium Integration API — linked response*"
    )
    if post_id:
        body = f"<!-- inResponseTo:{post_id} -->\n\n" + body

    result = publish_to_medium(title, body, tags=["response"])
    record = {
        "type": "comment",
        "article_url": article_url.strip(),
        "comment": comment_text.strip()[:500],
        "response_url": result.get("url"),
        "response_post_id": result.get("post_id"),
        "created_at": simdi(),
    }
    db = _load_db()
    db.append(record)
    _save_db(db)

    return {
        "success": True,
        "article_url": article_url.strip(),
        "comment": comment_text.strip(),
        "response_url": result.get("url"),
        "response_post_id": result.get("post_id"),
        "provider": "medium_api",
        "note": "Medium resmi API doğrudan yorum desteklemez; linkli response post oluşturuldu",
        "record": record,
    }


def list_activity(limit: int = 50) -> dict[str, Any]:
    rows = _load_db()
    rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"success": True, "total": len(rows), "items": rows[:limit]}
