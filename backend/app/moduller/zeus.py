"""
Zeus — Parasite SEO (gerçek platform API'leri).

Google Sites kaldırıldı. Simülasyon yok — her platform kendi API/MCP'si ile yayınlar.
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

logger = logging.getLogger("hive.zeus")

PLATFORMLAR = ["Medium", "LinkedIn", "Reddit", "YouTube", "GitHub", "Blogger"]
ZEUS_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "zeus_pages.json"
)

PLATFORM_ENV: dict[str, str | list[str]] = {
    "Medium": "MEDIUM_TOKEN",
    "LinkedIn": "LINKEDIN_ACCESS_TOKEN",
    "Reddit": ["REDDIT_USERNAME", "REDDIT_PASSWORD"],
    "YouTube": ["YOUTUBE_API_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"],
    "GitHub": "GITHUB_TOKEN",
    "Blogger": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"],
}


def _yukle() -> list[dict]:
    if not os.path.exists(ZEUS_DB_PATH):
        return []
    try:
        with open(ZEUS_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _kaydet(data: list[dict]) -> None:
    os.makedirs(os.path.dirname(ZEUS_DB_PATH), exist_ok=True)
    with open(ZEUS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(data[-500:], f, indent=2, ensure_ascii=False)


def _missing_keys(platform: str) -> list[str]:
    spec = PLATFORM_ENV.get(platform)
    if not spec:
        return []
    keys = spec if isinstance(spec, list) else [spec]
    return [k for k in keys if not (config.get(k) or "").strip()]


def _api_key_error(platform: str) -> dict[str, Any]:
    missing = _missing_keys(platform)
    return {
        "status": "hata",
        "hata": "Hata: API anahtarı eksik",
        "platform": platform,
        "eksik_anahtarlar": missing,
    }


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", (text or "zeus-parasite").lower())
    s = re.sub(r"\s+", "-", s.strip())
    return (s[:60] or "zeus-parasite").strip("-")


def _build_markdown(konu: str, hedef_url: str) -> str:
    konu = konu.strip() or "SEO Rehberi"
    link_block = f"\n\n**Kaynak:** [{hedef_url}]({hedef_url})\n" if hedef_url else ""
    return (
        f"# {konu}\n\n"
        f"{konu} hakkında güncel bilgiler, ipuçları ve öneriler.\n"
        f"{link_block}\n\n"
        f"---\n*HIVE Zeus — parasite SEO*"
    )


def _http_exc_to_dict(exc: HTTPException) -> dict[str, Any]:
    return {"status": "hata", "hata": str(exc.detail), "http_status": exc.status_code}


def _publish_medium(konu: str, hedef_url: str, tags: list[str] | None = None) -> dict[str, Any]:
    from .medium_bot import publish_to_medium

    content = _build_markdown(konu, hedef_url)
    try:
        res = publish_to_medium(konu, content, tags=tags or ["seo", "zeus"])
    except HTTPException as exc:
        return _http_exc_to_dict(exc)
    return {"durum": "yayında", "kaynak": "medium_api", **res}


def _publish_reddit(konu: str, hedef_url: str, subreddit: str = "") -> dict[str, Any]:
    from .reddit_mcp import reddit_mcp

    sub = (subreddit or config.get("REDDIT_DEFAULT_SUBREDDIT") or "").strip()
    if not sub:
        return {"status": "hata", "hata": "subreddit gerekli (REDDIT_DEFAULT_SUBREDDIT veya parametre)"}
    body = _build_markdown(konu, hedef_url)
    try:
        res = reddit_mcp.submit_post(sub, konu, body)
    except HTTPException as exc:
        return _http_exc_to_dict(exc)
    return {"durum": "yayında", "kaynak": "reddirect_mcp", "subreddit": sub, **res}


def _publish_github(konu: str, hedef_url: str) -> dict[str, Any]:
    token = (config.get("GITHUB_TOKEN") or "").strip()
    if not token:
        return _api_key_error("GitHub")

    slug = _slugify(konu)
    readme = _build_markdown(konu, hedef_url)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "name": f"zeus-{slug}"[:100],
        "description": f"Zeus parasite SEO — {konu}"[:350],
        "private": False,
        "auto_init": True,
    }
    try:
        r = requests.post("https://api.github.com/user/repos", json=payload, headers=headers, timeout=30)
        if r.status_code not in (200, 201):
            return {"status": "hata", "hata": f"GitHub repo oluşturulamadı: {r.status_code}", "detay": r.text[:300]}
        repo = r.json()
        owner = repo.get("owner", {}).get("login") or config.get("GITHUB_OWNER") or ""
        repo_name = repo.get("name") or payload["name"]
        if owner and repo_name:
            upd_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/README.md"
            requests.put(
                upd_url,
                headers=headers,
                json={
                    "message": f"Zeus: {konu}",
                    "content": __import__("base64").b64encode(readme.encode()).decode(),
                },
                timeout=30,
            )
        return {
            "durum": "yayında",
            "kaynak": "github_api",
            "repo_url": repo.get("html_url"),
            "repo_name": repo_name,
            "success": True,
        }
    except requests.RequestException as exc:
        return {"status": "hata", "hata": f"GitHub API: {exc}"}


def _publish_blogger(konu: str, hedef_url: str) -> dict[str, Any]:
    from . import blogger_api

    if not blogger_api.is_configured():
        return _api_key_error("Blogger")
    content = _build_markdown(konu, hedef_url).replace("\n", "<br/>")
    try:
        res = blogger_api.create_post(konu, content, labels=["zeus", "seo"])
    except Exception as exc:
        return {"status": "hata", "hata": str(exc)}
    return {"durum": "yayında", "kaynak": "blogger_api", **res}


def _publish_linkedin(konu: str, hedef_url: str) -> dict[str, Any]:
    token = (config.get("LINKEDIN_ACCESS_TOKEN") or "").strip()
    if not token:
        return _api_key_error("LinkedIn")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    try:
        me = requests.get("https://api.linkedin.com/v2/me", headers=headers, timeout=20)
        if me.status_code != 200:
            return {"status": "hata", "hata": f"LinkedIn kimlik doğrulama hatası: {me.status_code}"}
        author_urn = f"urn:li:person:{me.json().get('id')}"
        text = f"{konu}\n\n{hedef_url}" if hedef_url else konu
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "ARTICLE" if hedef_url else "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        if hedef_url:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "originalUrl": hedef_url,
                    "title": {"text": konu[:200]},
                }
            ]
        post = requests.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=payload, timeout=30)
        if post.status_code not in (200, 201):
            return {"status": "hata", "hata": f"LinkedIn yayın hatası: {post.status_code}", "detay": post.text[:300]}
        post_id = post.headers.get("x-restli-id") or post.json().get("id") if post.content else ""
        return {"durum": "yayında", "kaynak": "linkedin_api", "post_id": post_id, "success": True}
    except requests.RequestException as exc:
        return {"status": "hata", "hata": f"LinkedIn API: {exc}"}


def _publish_youtube(konu: str, hedef_url: str, video_id: str = "") -> dict[str, Any]:
    api_key = (config.get("YOUTUBE_API_KEY") or "").strip()
    if not api_key:
        return _api_key_error("YouTube")

    vid = (video_id or config.get("YOUTUBE_DEFAULT_VIDEO_ID") or "").strip()
    if not vid:
        return {
            "status": "hata",
            "hata": "YouTube video_id gerekli (parametre veya YOUTUBE_DEFAULT_VIDEO_ID)",
        }

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        return {"status": "hata", "hata": "pip install google-api-python-client google-auth"}

    cid = (config.get("GOOGLE_CLIENT_ID") or "").strip()
    csec = (config.get("GOOGLE_CLIENT_SECRET") or "").strip()
    refresh = (config.get("GOOGLE_REFRESH_TOKEN") or "").strip()
    if not (cid and csec and refresh):
        return _api_key_error("YouTube")

    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=cid,
        client_secret=csec,
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
    )
    creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds, developerKey=api_key)

    current = yt.videos().list(part="snippet", id=vid).execute()
    items = current.get("items") or []
    if not items:
        return {"status": "hata", "hata": f"Video bulunamadı: {vid}"}

    snippet = items[0].get("snippet") or {}
    desc = snippet.get("description") or ""
    link_line = f"\n\n🔗 {konu}: {hedef_url}" if hedef_url else f"\n\n🔗 {konu}"
    if hedef_url and hedef_url in desc:
        new_desc = desc
    else:
        new_desc = (desc + link_line).strip()

    snippet["description"] = new_desc[:5000]
    yt.videos().update(part="snippet", body={"id": vid, "snippet": snippet}).execute()
    return {
        "durum": "yayında",
        "kaynak": "youtube_api",
        "video_id": vid,
        "success": True,
        "description_updated": new_desc != desc,
    }


_PUBLISHERS = {
    "Medium": _publish_medium,
    "LinkedIn": _publish_linkedin,
    "Reddit": _publish_reddit,
    "YouTube": _publish_youtube,
    "GitHub": _publish_github,
    "Blogger": _publish_blogger,
}


def parazit_yerlestir(
    platform: str,
    konu: str = "",
    hedef_url: str = "",
    subreddit: str = "",
    video_id: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Seçilen platformda gerçek API ile parasite içerik yayınla."""
    platform = (platform or "Medium").strip()
    if platform not in PLATFORMLAR:
        return {
            "status": "hata",
            "hata": f"Geçersiz platform: {platform}. Seçenekler: {', '.join(PLATFORMLAR)}",
        }

    missing = _missing_keys(platform)
    if missing:
        return _api_key_error(platform)

    konu = (konu or "SEO Rehberi").strip()
    publisher = _PUBLISHERS[platform]

    kwargs: dict[str, Any] = {}
    if platform == "Reddit":
        kwargs["subreddit"] = subreddit
    if platform == "YouTube":
        kwargs["video_id"] = video_id
    if platform == "Medium":
        kwargs["tags"] = tags

    try:
        result = publisher(konu, hedef_url, **kwargs)
    except TypeError:
        result = publisher(konu, hedef_url)
    except Exception as exc:
        return {"status": "hata", "hata": str(exc)}

    if result.get("status") == "hata" or result.get("hata"):
        return result

    page_id = f"ZEUS-{simdi().replace(' ', '').replace(':', '')[:12]}"
    sayfa = {
        "id": page_id,
        "platform": platform,
        "konu": konu,
        "icerik": _build_markdown(konu, hedef_url),
        "hedef_url": hedef_url,
        "olusturma": simdi(),
        "durum": result.get("durum", "yayında"),
        "backlink_eklendi": bool(hedef_url),
        "yayin_url": (
            result.get("url")
            or result.get("repo_url")
            or result.get("response_url")
            or (result.get("result") or {}).get("url")
        ),
        "kaynak": result.get("kaynak") or result.get("provider") or "api",
        "api_response": {k: v for k, v in result.items() if k not in ("icerik",)},
    }
    pages = _yukle()
    pages.append(sayfa)
    _kaydet(pages)

    return {
        "durum": "aktif",
        "platform": platform,
        "konu": konu,
        "page_id": page_id,
        "sayfa": sayfa,
        "kaynak": sayfa["kaynak"],
        "yayin_url": sayfa.get("yayin_url"),
    }


def parazit_listele(platform: str = "") -> dict[str, Any]:
    pages = _yukle()
    if platform:
        pages = [p for p in pages if p.get("platform") == platform]
    pages.sort(key=lambda p: p.get("olusturma", ""), reverse=True)
    return {"toplam": len(pages), "sayfalar": pages[-50:]}


def parazit_sil(page_id: str) -> dict[str, Any]:
    pages = _yukle()
    filtered = [p for p in pages if p.get("id") != page_id]
    if len(filtered) == len(pages):
        return {"status": "hata", "hata": "Sayfa bulunamadı"}
    _kaydet(filtered)
    return {"durum": "silindi", "page_id": page_id}


def platform_analiz() -> dict[str, Any]:
    pages = _yukle()
    platform_sayilari: dict[str, int] = {}
    for p in pages:
        plat = p.get("platform", "Bilinmeyen")
        platform_sayilari[plat] = platform_sayilari.get(plat, 0) + 1
    return {
        "toplam_sayfa": len(pages),
        "platform_dagilimi": platform_sayilari,
        "desteklenen_platformlar": PLATFORMLAR,
        "google_sites_kaldirildi": True,
    }


def health() -> dict[str, Any]:
    configured = {p: not _missing_keys(p) for p in PLATFORMLAR}
    return {
        "status": "aktif",
        "module": "zeus",
        "simulation": False,
        "platformlar": PLATFORMLAR,
        "configured": configured,
        "sayfa_sayisi": len(_yukle()),
    }
