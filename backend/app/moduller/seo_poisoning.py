"""
SEO Poisoning — Ollama ile içerik üretimi + çoklu platform yayını.

Sorumluluk kullanıcıya aittir. Etik sınırlarda kullanın.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import HTTPException

from app import config
from .modul_base import simdi
from .ollama_helper import generate

logger = logging.getLogger("hive.seo_poisoning")

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data", "seo_poisoning_log.json"
)

DISCLAIMER = (
    "Bu modül yalnızca yetkili güvenlik/SEO test ortamları içindir. "
    "Yanıltıcı veya yasadışı içerik yayınlamak kullanıcının sorumluluğundadır."
)


def _load_log() -> list[dict]:
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_log(rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(rows[-200:], f, indent=2, ensure_ascii=False)


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    for p in ("https://", "http://", "www."):
        d = d.replace(p, "")
    return d.split("/")[0]


def generate_negative_content(target_domain: str, keywords: list[str] | None = None) -> dict[str, Any]:
    """Ollama ile negatif SEO içeriği üret."""
    dom = _normalize_domain(target_domain)
    if not dom:
        raise HTTPException(status_code=400, detail="target_domain gerekli")

    kws = [k.strip() for k in (keywords or []) if k and str(k).strip()]
    if not kws:
        kws = ["dolandırıcı", "şikayet", "güvenilir mi", "yorumlar"]

    kw_str = ", ".join(kws[:8])
    prompt = (
        f"Aşağıdaki hedef domain için SEO amaçlı eleştirel bir blog yazısı yaz (Türkçe).\n"
        f"Hedef: {dom}\n"
        f"Anahtar kelimeler: {kw_str}\n"
        f"Başlık örneği: '{dom} dolandırıcı mı? — kullanıcı deneyimleri'\n"
        f"Markdown formatında 400-700 kelime. Gerçekçi ama eleştirel ton.\n"
        f"Yanıt formatı:\n"
        f"TITLE: ...\n"
        f"BODY:\n...\n"
    )
    text, ai_used = generate(prompt, max_tokens=1200)
    if not text.strip():
        raise HTTPException(status_code=502, detail="Ollama içerik üretemedi — OLLAMA_URL kontrol edin")

    title = f"{dom} — {kws[0]} hakkında kullanıcı uyarısı"
    body = text.strip()
    if "TITLE:" in text and "BODY:" in text:
        parts = text.split("BODY:", 1)
        title_part = parts[0].replace("TITLE:", "").strip()
        if title_part:
            title = title_part.split("\n")[0].strip()
        body = parts[1].strip() if len(parts) > 1 else body

    content = {
        "title": title[:200],
        "body": body,
        "target_domain": dom,
        "keywords": kws,
        "generated_at": simdi(),
        "engine": "ollama" if ai_used else "fallback",
    }
    return {"success": True, "content": content, "disclaimer": DISCLAIMER}


def _publish_medium(content: dict[str, Any]) -> dict[str, Any]:
    from .medium_bot import publish_to_medium
    tags = (content.get("keywords") or [])[:3]
    return publish_to_medium(content["title"], content["body"], tags=tags)


def _publish_wordpress(content: dict[str, Any]) -> dict[str, Any]:
    from .wordpress_api import ensure_wp_connected, wp_api
    conn = ensure_wp_connected(verify=False)
    if not conn.get("connected") and not conn.get("success"):
        url = (config.get("WP_URL") or "").strip()
        if not url:
            return {"success": False, "platform": "wordpress", "error": "WP_URL tanımlı değil"}
        return {"success": False, "platform": "wordpress", "error": "WordPress bağlantısı yok — WP_URL/WP_USERNAME/WP_APP_PASSWORD"}
    api = wp_api()
    res = api.create_post(content["title"], content["body"], status="publish")
    return {
        "success": bool(res.get("success") or res.get("id")),
        "platform": "wordpress",
        "post_id": res.get("id") or res.get("post_id"),
        "url": res.get("link") or res.get("url"),
        "detail": res,
    }


def _publish_blogger(content: dict[str, Any]) -> dict[str, Any]:
    from . import blogger_api
    try:
        status = blogger_api.get_status()
        if not status.get("connected"):
            return {"success": False, "platform": "blogger", "error": "Blogger bağlantısı yok — Google OAuth .env"}
        res = blogger_api.create_post(
            content["title"],
            content["body"],
            labels=content.get("keywords") or [],
            publish=True,
        )
        return {"success": True, "platform": "blogger", "post_id": res.get("post_id"), "url": res.get("url"), "detail": res}
    except Exception as exc:
        return {"success": False, "platform": "blogger", "error": str(exc)}


def publish_to_platforms(content: dict[str, Any], platforms: list[str] | None = None) -> dict[str, Any]:
    """Medium, WordPress, Blogger — gerçek yayın."""
    if not content or not content.get("title") or not content.get("body"):
        raise HTTPException(status_code=400, detail="content.title ve content.body gerekli")

    targets = platforms or ["medium", "wordpress", "blogger"]
    results: list[dict[str, Any]] = []

    for plat in targets:
        p = plat.lower().strip()
        try:
            if p == "medium":
                results.append(_publish_medium(content))
            elif p in ("wordpress", "wordpress_com", "wp"):
                results.append(_publish_wordpress(content))
            elif p == "blogger":
                results.append(_publish_blogger(content))
            else:
                results.append({"success": False, "platform": p, "error": "bilinmeyen platform"})
        except HTTPException as exc:
            results.append({"success": False, "platform": p, "error": exc.detail})
        except Exception as exc:
            results.append({"success": False, "platform": p, "error": str(exc)})

    ok = [r for r in results if r.get("success")]
    log_entry = {
        "target_domain": content.get("target_domain"),
        "title": content.get("title"),
        "published_at": simdi(),
        "platforms": results,
        "success_count": len(ok),
    }
    db = _load_log()
    db.append(log_entry)
    _save_log(db)

    return {
        "success": len(ok) > 0,
        "published_count": len(ok),
        "failed_count": len(results) - len(ok),
        "results": results,
        "disclaimer": DISCLAIMER,
        "log": log_entry,
    }


def run_campaign(target_domain: str, keywords: list[str] | None = None, platforms: list[str] | None = None) -> dict[str, Any]:
    """Üret + yayınla — tek adım."""
    gen = generate_negative_content(target_domain, keywords)
    pub = publish_to_platforms(gen["content"], platforms)
    return {
        "success": pub.get("success"),
        "content": gen["content"],
        "publish": pub,
        "disclaimer": DISCLAIMER,
    }


def health() -> dict[str, Any]:
    medium_ok = bool((config.get("MEDIUM_TOKEN") or "").strip())
    wp_ok = bool((config.get("WP_URL") or "").strip())
    blogger_ok = bool(
        (config.get("GOOGLE_CLIENT_ID") or "").strip()
        and (config.get("GOOGLE_REFRESH_TOKEN") or "").strip()
    )
    return {
        "success": True,
        "module": "seo_poisoning",
        "medium_configured": medium_ok,
        "wordpress_configured": wp_ok,
        "blogger_configured": blogger_ok,
        "campaigns_logged": len(_load_log()),
        "disclaimer": DISCLAIMER,
    }


def list_campaigns(limit: int = 30) -> dict[str, Any]:
    rows = _load_log()
    rows.sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return {"success": True, "total": len(rows), "campaigns": rows[:limit]}
