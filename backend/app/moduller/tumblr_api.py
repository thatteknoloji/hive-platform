"""
Tumblr OAuth 1.0a + post API (legacy HTML + NPF)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

import requests
from fastapi import HTTPException

logger = logging.getLogger("hive.tumblr")

REQUEST_TOKEN_URL = "https://www.tumblr.com/oauth/request_token"
AUTHORIZE_URL = "https://www.tumblr.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://www.tumblr.com/oauth/access_token"
API_ROOT = "https://api.tumblr.com/v2"

DATA_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = DATA_DIR / "tumblr_tokens.json"
PENDING_FILE = DATA_DIR / "tumblr_pending.json"

_pending_tokens: dict[str, str] = {}


def _load_pending() -> None:
    global _pending_tokens
    if PENDING_FILE.exists():
        try:
            _pending_tokens = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _pending_tokens = {}


def _save_pending() -> None:
    try:
        PENDING_FILE.write_text(json.dumps(_pending_tokens), encoding="utf-8")
    except OSError:
        pass


def _consumer_key() -> str:
    return os.getenv("TUMBLR_CONSUMER_KEY", "").strip()


def _consumer_secret() -> str:
    return os.getenv("TUMBLR_CONSUMER_SECRET", "").strip()


def callback_url() -> str:
    """OAuth dönüş adresi — HIVE panel origin (Tumblr uygulama ayarıyla aynı olmalı)."""
    raw = (os.getenv("TUMBLR_CALLBACK_URL") or "http://localhost:4000").strip()
    return raw.rstrip("/")


def _encode(value: str) -> str:
    return quote(str(value), safe="")


def normalize_blog_identifier(blog_name: str = "") -> str:
    """
    Tumblr blog tanımlayıcısını API'nin kabul ettiği hostname formatına çevirir.
    Örn: balkutumcom -> balkutumcom.tumblr.com
    """
    blog = (blog_name or os.getenv("TUMBLR_DEFAULT_BLOG", "") or "").strip()
    if not blog:
        raise HTTPException(status_code=400, detail="Blog adı gerekli")

    if blog.startswith("t:"):
        return blog

    blog = blog.replace("https://", "").replace("http://", "").strip().strip("/")
    if "@" in blog:
        blog = blog.split("@", 1)[-1]

    host = urlparse(f"https://{blog}").netloc or blog.split("/")[0]
    host = host.lower()

    if host.endswith(".tumblr.com"):
        return host
    if "." in host:
        return host
    return f"{host}.tumblr.com"


def sign_request(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    token: str = "",
    token_secret: str = "",
) -> str:
    """OAuth 1.0a HMAC-SHA1 imzası — Authorization header döner."""
    consumer_key = _consumer_key()
    consumer_secret = _consumer_secret()
    if not consumer_key or not consumer_secret:
        raise HTTPException(status_code=400, detail="Tumblr Consumer Key/Secret eksik (.env)")

    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_version": "1.0",
    }
    if token:
        oauth_params["oauth_token"] = token

    all_params = {**oauth_params, **(params or {})}
    param_string = "&".join(
        f"{_encode(k)}={_encode(v)}" for k, v in sorted(all_params.items())
    )
    signature_base = f"{method.upper()}&{_encode(url)}&{_encode(param_string)}"
    signing_key = f"{_encode(consumer_secret)}&{_encode(token_secret)}"
    digest = hmac.new(
        signing_key.encode("utf-8"),
        signature_base.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    oauth_params["oauth_signature"] = base64.b64encode(digest).decode("utf-8")

    header_parts = ", ".join(
        f'{k}="{_encode(v)}"' for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


def _signed_get(url: str, token: str, token_secret: str) -> dict:
    auth_header = sign_request("GET", url, {}, token=token, token_secret=token_secret)
    response = requests.get(url, headers={"Authorization": auth_header}, timeout=30)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Tumblr API hatası: {response.text}",
        )
    return response.json()


def fetch_user_blogs(
    access_token: str | None = None,
    access_token_secret: str | None = None,
) -> list[dict[str, Any]]:
    """OAuth kullanıcısının yönetebildiği blogları döner."""
    stored = load_tokens()
    token = access_token or (stored or {}).get("oauth_token", "")
    token_secret = access_token_secret or (stored or {}).get("oauth_token_secret", "")
    if not token or not token_secret:
        return []

    data = _signed_get(f"{API_ROOT}/user/info", token, token_secret)
    blogs = (data.get("response") or {}).get("user", {}).get("blogs") or []
    result: list[dict[str, Any]] = []
    for blog in blogs:
        name = (blog.get("name") or "").strip()
        uuid = (blog.get("uuid") or "").strip()
        identifier = f"{name}.tumblr.com" if name and not name.endswith(".tumblr.com") else name
        if uuid:
            identifier = uuid
        result.append(
            {
                "name": name,
                "title": blog.get("title") or name,
                "url": blog.get("url") or "",
                "uuid": uuid,
                "identifier": identifier,
                "admin": bool(blog.get("admin")),
                "primary": bool(blog.get("primary")),
            }
        )
    return result


def _pick_primary_blog(blogs: list[dict[str, Any]]) -> str:
    if not blogs:
        return normalize_blog_identifier("")
    for blog in blogs:
        if blog.get("primary"):
            return blog["identifier"]
    for blog in blogs:
        if blog.get("admin"):
            return blog["identifier"]
    return blogs[0]["identifier"]


def sync_blog_from_account(tokens: dict[str, str]) -> dict[str, str]:
    """OAuth sonrası gerçek blog tanımlayıcısını kaydet."""
    try:
        blogs = fetch_user_blogs(tokens["oauth_token"], tokens["oauth_token_secret"])
        if blogs:
            tokens["blogs"] = blogs
            tokens["blog_name"] = _pick_primary_blog(blogs)
            save_tokens(tokens)
    except Exception as exc:
        logger.warning("Tumblr blog senkronu atlandı: %s", exc)
    return tokens


def get_request_token() -> dict[str, str]:
    params = {"oauth_callback": callback_url()}
    auth_header = sign_request("POST", REQUEST_TOKEN_URL, params)
    response = requests.post(
        REQUEST_TOKEN_URL,
        headers={"Authorization": auth_header},
        data=params,
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Request token alınamadı: {response.text}",
        )
    token_data = parse_qs(response.text)
    oauth_token = token_data.get("oauth_token", [""])[0]
    oauth_token_secret = token_data.get("oauth_token_secret", [""])[0]
    if not oauth_token or not oauth_token_secret:
        raise HTTPException(status_code=502, detail="Tumblr request token yanıtı geçersiz")

    _load_pending()
    _pending_tokens[oauth_token] = oauth_token_secret
    _save_pending()
    return {
        "oauth_token": oauth_token,
        "oauth_token_secret": oauth_token_secret,
        "callback_url": callback_url(),
    }


def get_authorize_url(oauth_token: str) -> str:
    return f"{AUTHORIZE_URL}?{urlencode({'oauth_token': oauth_token})}"


def get_access_token(
    oauth_token: str,
    oauth_verifier: str,
    oauth_token_secret: str | None = None,
) -> dict[str, str]:
    _load_pending()
    secret = oauth_token_secret or _pending_tokens.get(oauth_token)
    if not secret:
        raise HTTPException(status_code=400, detail="Geçersiz veya süresi dolmuş oauth_token")

    params = {
        "oauth_token": oauth_token,
        "oauth_verifier": oauth_verifier,
    }
    auth_header = sign_request(
        "POST",
        ACCESS_TOKEN_URL,
        params,
        token=oauth_token,
        token_secret=secret,
    )
    response = requests.post(
        ACCESS_TOKEN_URL,
        headers={"Authorization": auth_header},
        data=params,
        timeout=30,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Access token alınamadı: {response.text}",
        )

    token_data = parse_qs(response.text)
    access = {
        "oauth_token": token_data.get("oauth_token", [""])[0],
        "oauth_token_secret": token_data.get("oauth_token_secret", [""])[0],
    }
    if not access["oauth_token"] or not access["oauth_token_secret"]:
        raise HTTPException(status_code=502, detail="Tumblr access token yanıtı geçersiz")

    _pending_tokens.pop(oauth_token, None)
    _save_pending()
    save_tokens(access)
    return sync_blog_from_account(access)


def save_tokens(tokens: dict[str, str]) -> None:
    data = {
        "oauth_token": tokens.get("oauth_token", ""),
        "oauth_token_secret": tokens.get("oauth_token_secret", ""),
        "blog_name": tokens.get("blog_name", os.getenv("TUMBLR_DEFAULT_BLOG", "balkutumcom")),
        "blogs": tokens.get("blogs") or [],
        "connected_at": int(time.time()),
    }
    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_tokens() -> dict[str, str] | None:
    if not TOKEN_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        if data.get("oauth_token") and data.get("oauth_token_secret"):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def get_pending_secret(oauth_token: str) -> str | None:
    _load_pending()
    return _pending_tokens.get(oauth_token)


def _resolve_blog_name(blog_name: str) -> str:
    stored = load_tokens() or {}
    raw = (blog_name or stored.get("blog_name") or "").strip()
    if not raw and stored.get("blogs"):
        return _pick_primary_blog(stored["blogs"])
    return normalize_blog_identifier(raw)


def _content_to_html(content: Any, title: str = "") -> str:
    if isinstance(content, str):
        body = content.strip()
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if block.get("type") == "text":
                text = (block.get("text") or "").strip()
                if text:
                    parts.append(text)
        body = "\n".join(parts)
    else:
        body = str(content or "").strip()

    if title and title not in body:
        body = f"<h1>{title}</h1>\n{body}"
    return body


def _build_npf_content(content: Any, title: str = "") -> list[dict]:
    blocks: list[dict] = []
    if title:
        blocks.append({"type": "text", "text": title, "subtype": "heading1"})
    if isinstance(content, list):
        blocks.extend(content)
    elif isinstance(content, str):
        blocks.append({"type": "text", "text": content})
    return blocks


def _post_legacy_text(
    blog_id: str,
    content: Any,
    title: str,
    tags: list[str] | None,
    token: str,
    token_secret: str,
    state: str,
) -> dict:
    """Legacy text post — HTML içerik için en güvenilir yol."""
    url = f"{API_ROOT}/blog/{blog_id}/post"
    body = _content_to_html(content, title="")
    params: dict[str, Any] = {
        "type": "text",
        "body": body,
        "format": "html",
        "state": state,
    }
    if title:
        params["title"] = title
    if tags:
        clean = [t.strip() for t in tags if t and str(t).strip()]
        if clean:
            params["tags"] = ", ".join(clean)

    auth_header = sign_request("POST", url, params, token=token, token_secret=token_secret)
    response = requests.post(
        url,
        headers={"Authorization": auth_header},
        data=params,
        timeout=60,
    )
    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Post gönderilemedi: {response.text}",
        )
    return response.json()


def _post_npf(
    blog_id: str,
    content: Any,
    title: str,
    tags: list[str] | None,
    token: str,
    token_secret: str,
    state: str,
) -> dict:
    url = f"{API_ROOT}/blog/{blog_id}/posts"
    payload: dict[str, Any] = {
        "content": _build_npf_content(content, title),
        "state": state,
    }
    if tags:
        clean = [t.strip() for t in tags if t and str(t).strip()]
        if clean:
            payload["tags"] = ", ".join(clean)

    auth_header = sign_request("POST", url, {}, token=token, token_secret=token_secret)
    response = requests.post(
        url,
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Post gönderilemedi: {response.text}",
        )
    return response.json()


def post_to_tumblr(
    blog_name: str,
    content: Any,
    title: str = "",
    tags: list[str] | None = None,
    access_token: str | None = None,
    access_token_secret: str | None = None,
    state: str = "published",
) -> dict:
    """Tumblr'a yazı gönder — önce legacy HTML, gerekirse NPF dener."""
    stored = load_tokens()
    token = access_token or (stored or {}).get("oauth_token", "")
    token_secret = access_token_secret or (stored or {}).get("oauth_token_secret", "")
    if not token or not token_secret:
        raise HTTPException(status_code=401, detail="Tumblr access token yok — önce bağlanın")

    blog_id = _resolve_blog_name(blog_name)
    is_html = isinstance(content, str) and ("<" in content and ">" in content)

    try:
        if is_html or isinstance(content, str):
            return _post_legacy_text(blog_id, content, title, tags, token, token_secret, state)
        return _post_npf(blog_id, content, title, tags, token, token_secret, state)
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        alt_id = blog_id
        if blog_id.endswith(".tumblr.com"):
            alt_id = blog_id.replace(".tumblr.com", "")
        else:
            alt_id = f"{blog_id}.tumblr.com"
        logger.info("Tumblr 404 — alternatif blog tanımlayıcısı deneniyor: %s", alt_id)
        try:
            if is_html or isinstance(content, str):
                return _post_legacy_text(alt_id, content, title, tags, token, token_secret, state)
            return _post_npf(alt_id, content, title, tags, token, token_secret, state)
        except HTTPException:
            blogs = fetch_user_blogs(token, token_secret)
            names = ", ".join(b.get("identifier", b.get("name", "")) for b in blogs[:5])
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Post gönderilemedi: blog bulunamadı ({blog_id}). "
                    f"Erişilebilir bloglar: {names or 'yok — Tumblr hesabını yeniden bağlayın'}"
                ),
            ) from exc


def connection_status() -> dict:
    tokens = load_tokens()
    blogs = (tokens or {}).get("blogs") or []
    blog_name = (tokens or {}).get("blog_name", os.getenv("TUMBLR_DEFAULT_BLOG", "balkutumcom"))
    if tokens and not blogs:
        try:
            blogs = fetch_user_blogs()
            if blogs:
                blog_name = _pick_primary_blog(blogs)
                save_tokens({**tokens, "blogs": blogs, "blog_name": blog_name})
        except Exception:
            pass
    return {
        "connected": bool(tokens),
        "blog_name": blog_name,
        "blog_identifier": normalize_blog_identifier(blog_name) if blog_name else "",
        "blogs": blogs,
        "connected_at": (tokens or {}).get("connected_at"),
        "has_consumer_keys": bool(_consumer_key() and _consumer_secret()),
        "callback_url": callback_url(),
    }
