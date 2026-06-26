"""StoryForge V3 — fastCRW scrape + Ollama rewrite + WordPress publish."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from app import config
from app.moduller import llm_router
from app.moduller.storyforge_v2 import storyforge as storyforge_v2
from app.moduller.storyforge_bulk import load_rules
from app.moduller.storyforge_categories import (
    _slugify,
    pick_categories,
    resolve_category_assignment,
    resolve_term_ids,
)
from app.moduller.wordpress_api import wp_api

logger = logging.getLogger("hive.storyforge_v3")

HISTORY_FILE = Path(__file__).resolve().parent.parent / "storyforge_v3_history.json"
SCRAPE_TIMEOUT = 90
CRW_MIN_CHARS = 150
SCRAPE_MAX_CHARS = 80000

KUSADASI_LOCATIONS = [
    "Kadınlar Denizi", "Yılancı Burnu", "Atatürk Bulvarı", "Liman Caddesi",
    "Güvercinada", "Davutlar", "Kuşadası Marina", "Kuşadası Merkez",
]

CHARACTER_NAMES = ["Aylin", "Ceyda", "Derya", "Emre", "Can", "Mert", "Elif", "Selin"]

REWRITE_SYSTEM = (
    "Sen Kuşadası gece hayatı ve escort temalı yetişkin hikaye editörüsün. "
    "Özgün, akıcı Türkçe yaz; HTML paragraf etiketleri kullanabilirsin."
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _crw_url() -> str:
    return (config.get("CRW_URL") or "http://localhost:3000").strip().rstrip("/")


def _crw_api_key() -> str:
    return (config.get("CRW_API_KEY") or "").strip()


def _ollama_model() -> str:
    return (config.get("OLLAMA_MODEL") or "llama3").strip()


def _load_history() -> list[dict[str, Any]]:
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_history(entry: dict[str, Any]) -> None:
    rows = _load_history()
    rows.insert(0, entry)
    HISTORY_FILE.write_text(json.dumps(rows[:100], ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_url(url: str) -> str:
    text = (url or "").strip()
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Geçersiz URL — http veya https ile başlamalı")
    return text


def _text_to_html(text: str) -> str:
    body = (text or "").strip()
    if not body:
        return ""
    if body.lstrip().startswith("<"):
        return body
    parts = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if not parts:
        parts = [body]
    return "".join(f"<p>{p}</p>" for p in parts)


def _extract_scrape_content(payload: dict[str, Any]) -> tuple[str, str]:
    data = payload.get("data") or {}
    content = (
        data.get("markdown")
        or data.get("plainText")
        or data.get("content")
        or data.get("html")
        or ""
    )
    content = re.sub(r"\n{3,}", "\n\n", str(content)).strip()
    meta = data.get("metadata") or {}
    title = str(meta.get("title") or "").strip()
    return content, title


def _check_crw() -> dict[str, Any]:
    crw_base = _crw_url()
    try:
        headers: dict[str, str] = {}
        key = _crw_api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        resp = requests.get(f"{crw_base}/health", headers=headers, timeout=8)
        if resp.status_code == 200:
            try:
                body = resp.json()
                version = body.get("version", "")
            except ValueError:
                version = ""
            return {"url": crw_base, "available": True, "error": "", "version": version}
        return {"url": crw_base, "available": False, "error": f"HTTP {resp.status_code}", "version": ""}
    except requests.RequestException as exc:
        return {
            "url": crw_base,
            "available": False,
            "error": str(exc),
            "version": "",
            "hint": "npm run docker:crw",
        }


def _check_ollama() -> dict[str, Any]:
    model = _ollama_model()
    base = (config.get("OLLAMA_URL") or "http://127.0.0.1:11434").strip()
    if base.endswith("/api/generate"):
        base = base.rsplit("/api/", 1)[0]
    tags_url = f"{base.rstrip('/')}/api/tags"
    try:
        resp = requests.get(tags_url, timeout=5)
        if resp.status_code == 200:
            models = [m.get("name", "") for m in (resp.json().get("models") or [])]
            return {
                "available": True,
                "model": model,
                "models": models[:5],
                "error": "",
                "url": base,
            }
    except requests.RequestException as exc:
        pass
    started = bool(llm_router.ensure_ollama_running())
    if started:
        return {"available": True, "model": model, "error": "", "url": base, "auto_started": True}
    return {
        "available": False,
        "model": model,
        "error": "Ollama yanıt vermiyor — ollama serve veya docker",
        "url": base,
        "hint": "ollama serve",
    }


def _check_wordpress() -> dict[str, Any]:
    from app.moduller.wordpress_api import ensure_wp_connected

    url = (config.get("WP_URL") or "").strip()
    user_ok = bool((config.get("WP_USERNAME") or "").strip())
    pass_ok = bool((config.get("WP_APP_PASSWORD") or config.get("WP_PASSWORD") or "").strip())
    wp_st = ensure_wp_connected(verify=True)
    return {
        "connected": bool(wp_st.get("connected")),
        "url": url,
        "username_present": user_ok,
        "password_present": pass_ok,
        "auto_connected": bool(wp_st.get("auto_connected")),
        "error": wp_st.get("error", ""),
        "wp_user": wp_st.get("user", ""),
    }


def health() -> dict[str, Any]:
    crw = _check_crw()
    ollama = _check_ollama()
    wordpress = _check_wordpress()
    ready = crw["available"] and ollama["available"] and wordpress["connected"]
    return {
        "success": True,
        "checked_at": _now(),
        "crw": crw,
        "ollama": ollama,
        "wordpress": wordpress,
        "ready": ready,
    }


def smoke_test() -> dict[str, Any]:
    """Gerçek fastCRW scrape kanıtı — example.com üzerinden."""
    status = health()
    proof: dict[str, Any] = {"success": False}
    if not status["crw"]["available"]:
        return {
            "success": False,
            "error": "fastCRW çalışmıyor",
            "health": status,
            "proof": proof,
        }
    scraped = scrape_url("https://example.com")
    if not scraped.get("success"):
        return {
            "success": False,
            "error": scraped.get("error", "Scrape başarısız"),
            "health": status,
            "proof": proof,
        }
    proof = {
        "success": True,
        "source_url": scraped["source_url"],
        "title": scraped.get("title", ""),
        "char_count": scraped.get("char_count", 0),
        "preview": scraped["text"][:400],
    }
    return {
        "success": True,
        "message": "fastCRW gerçek scrape kanıtlandı",
        "health": status,
        "proof": proof,
    }


def scrape_url(url: str) -> dict[str, Any]:
    safe_url = _validate_url(url)
    base = _crw_url()
    headers = {"Content-Type": "application/json"}
    key = _crw_api_key()
    if key:
        headers["Authorization"] = f"Bearer {key}"

    body = {
        "url": safe_url,
        "formats": ["markdown", "plainText"],
        "onlyMainContent": True,
    }
    try:
        resp = requests.post(
            f"{base}/v1/scrape",
            json=body,
            headers=headers,
            timeout=SCRAPE_TIMEOUT,
        )
    except requests.RequestException as exc:
        return {"success": False, "error": f"fastCRW bağlantı hatası: {exc}"}

    if resp.status_code != 200:
        detail = resp.text[:400]
        return {
            "success": False,
            "error": f"fastCRW HTTP {resp.status_code}: {detail}",
        }

    try:
        payload = resp.json()
    except ValueError:
        return {"success": False, "error": "fastCRW geçersiz JSON yanıtı"}

    if not payload.get("success"):
        return {"success": False, "error": "fastCRW scrape başarısız", "raw": payload}

    content, scraped_title = _extract_scrape_content(payload)
    if len(content) < CRW_MIN_CHARS:
        return {
            "success": False,
            "error": f"İçerik çok kısa ({len(content)} karakter) — sayfa yapısı desteklenmiyor olabilir",
        }

    if len(content) > SCRAPE_MAX_CHARS:
        content = content[:SCRAPE_MAX_CHARS] + "…"

    return {
        "success": True,
        "source_url": safe_url,
        "title": scraped_title,
        "text": content,
        "char_count": len(content),
        "word_count": _word_count(content),
    }


def _merge_rules(rules: dict[str, Any] | None = None, custom_rules: str = "") -> dict[str, Any]:
    base = load_rules()
    if rules:
        base = {**base, **{k: v for k, v in rules.items() if v is not None}}
    if custom_rules.strip():
        base["custom_rules"] = custom_rules.strip()
    return base


def _build_rewrite_prompt(
    original_text: str,
    source_title: str = "",
    rules: dict[str, Any] | None = None,
    *,
    source_word_target: int = 0,
) -> str:
    r = _merge_rules(rules)
    locs = ", ".join(r.get("locations") or KUSADASI_LOCATIONS)
    names = ", ".join(r.get("character_names") or CHARACTER_NAMES)
    keywords = ", ".join(r.get("keywords") or ["kuşadası", "gece hayatı", "escort"])
    city = r.get("city") or "Kuşadası"
    custom = (r.get("custom_rules") or "").strip()
    src_wc = source_word_target or _word_count(original_text)
    title_line = f"\nKaynak başlık: {source_title}" if source_title else ""
    custom_block = f"\nEk kurallar:\n{custom}" if custom else ""
    length_rule = (
        f"- Orijinal metinde yaklaşık {src_wc} kelime var; yeniden yazım EN AZ {src_wc} kelime olmalı\n"
        f"- KISALTMA YASAK — olay örgüsünü atlama, tüm sahneleri koru ve tamamla"
        if src_wc >= 80
        else "- Hikayeyi tam ve eksiksiz yaz, yarım bırakma"
    )
    return f"""Aşağıdaki hikayeyi al ve şu kurallara göre yeniden yaz:
- Şehir/bölge: {city}
- Tüm mekan isimlerini Kuşadası'ndaki gerçek mekanlarla değiştir ({locs})
- Tüm karakter isimlerini Türkçe isimlerle değiştir ({names})
- Hikayenin ana duygusunu ve olay örgüsünü koru
- SEO için şu kelimeleri doğal yerleştir: {keywords}
- Hikaye 18+ yetişkinlere yöneliktir, uygun dili kullan
{length_rule}
- Çıktı HTML <p> paragrafları ile gelsin
- Son paragrafta {r.get('site_url') or ''} kaynağına doğal referans ver{custom_block}{title_line}

Orijinal Hikaye:
{original_text}

Yeniden yazılmış hikaye:"""


def rewrite_story(
    original_text: str,
    source_title: str = "",
    rules: dict[str, Any] | None = None,
    custom_rules: str = "",
) -> dict[str, Any]:
    text = (original_text or "").strip()
    if len(text) < 80:
        return {"success": False, "error": "Yeniden yazılacak metin çok kısa"}

    merged_rules = _merge_rules(rules, custom_rules)
    source_wc = _word_count(text)
    llm_router.ensure_ollama_running()
    prompt = _build_rewrite_prompt(
        text, source_title, merged_rules, source_word_target=source_wc,
    )[:120000]
    max_tokens = min(16000, max(2500, int(source_wc * 2.8)))
    min_length = max(400, int(len(text) * 0.35))
    rewritten, engine = llm_router.generate(
        prompt,
        system=REWRITE_SYSTEM,
        max_tokens=max_tokens,
        min_length=min_length,
    )

    if not rewritten or len(rewritten.strip()) < 200:
        return {
            "success": False,
            "error": "Ollama yeniden yazma başarısız — Ollama çalışıyor mu? (OLLAMA_URL / OLLAMA_MODEL)",
            "engine": engine or "",
        }

    html = _text_to_html(rewritten)
    out_wc = _word_count(html)
    if source_wc >= 200 and out_wc < int(source_wc * 0.75):
        expand_prompt = f"""Aşağıdaki hikaye çok kısa kaldı ({out_wc} kelime). Orijinal {source_wc} kelimeydi.
EN AZ {source_wc} kelime olacak şekilde UZAT — yeni sahne uydurma, mevcut olay örgüsünü genişlet.
HTML <p> koru, başlık yazma.

{html[:100000]}

Genişletilmiş TAM hikaye:"""
        expanded, exp_engine = llm_router.generate(
            expand_prompt,
            system=REWRITE_SYSTEM,
            max_tokens=max_tokens,
            min_length=min_length,
        )
        if expanded and _word_count(expanded) > out_wc:
            html = _text_to_html(expanded)
            engine = f"{engine}+{exp_engine}" if exp_engine else engine
            out_wc = _word_count(html)
    suggested_title = storyforge_v2._suggest_title(source_title, html)
    lokasyon = storyforge_v2._suggest_lokasyon(html)
    excerpt = storyforge_v2._suggest_excerpt(suggested_title, lokasyon)
    cats = pick_categories(title=suggested_title, content=html, lokasyon=lokasyon)

    return {
        "success": True,
        "content": html,
        "suggested_title": suggested_title,
        "suggested_lokasyon": lokasyon,
        "suggested_excerpt": excerpt,
        "suggested_categories": cats,
        "engine": engine or "ollama",
        "word_count": out_wc,
        "source_word_count": source_wc,
        "rules_applied": {
            "city": merged_rules.get("city"),
            "custom_rules": merged_rules.get("custom_rules", "")[:200],
            "source_word_target": source_wc,
        },
    }


def _word_count(html: str) -> int:
    plain = re.sub(r"<[^>]+>", " ", html or "")
    return len(re.findall(r"\w+", plain, re.UNICODE))


def preview_publish(
    title: str,
    content: str,
    lokasyon: str = "",
    excerpt: str = "",
    category_slug: str = "gece-hikaye",
) -> dict[str, Any]:
    """Yayın öncesi — nereye nasıl gideceğini göster (gerçek WP bağlantısı gerekli)."""
    api = wp_api()
    if not api.connected:
        from app.moduller.wordpress_api import ensure_wp_connected
        st = ensure_wp_connected(verify=True)
        if not st.get("connected"):
            return {"success": False, "error": st.get("error") or "WordPress bağlantısı yok"}

    final_title = (title or "").strip() or "Hikaye"
    slug = _slugify(final_title)
    wp_base = (config.get("WP_URL") or "").strip().rstrip("/")

    wp_terms: list[dict[str, Any]] = []
    listed = api.list_story_categories()
    if listed.get("success"):
        wp_terms = listed.get("terms", [])

    cat_info = resolve_category_assignment(
        category_slug=category_slug,
        title=final_title,
        content=content,
        lokasyon=lokasyon,
        wp_terms=wp_terms,
    )
    term_ids = resolve_term_ids(api, cat_info)

    estimated_url = f"{wp_base}/?post_type=erotic_story&name={slug}"
    if wp_base:
        estimated_url = f"{wp_base}/erotic_story/{slug}/"

    return {
        "success": True,
        "preview": True,
        "post_type": "erotic_story",
        "rest_endpoint": "/wp-json/wp/v2/erotic_story",
        "wp_site": wp_base,
        "title": final_title,
        "slug": slug,
        "estimated_url": estimated_url,
        "category_slug": cat_info.get("main_slug", category_slug),
        "sub_category": cat_info.get("sub_slug", ""),
        "categories": cat_info,
        "category_term_ids": term_ids,
        "lokasyon": lokasyon,
        "excerpt": (excerpt or "")[:160],
        "word_count": _word_count(content),
        "status_planned": "publish",
        "message": f"WordPress'te erotic_story olarak yayınlanacak — tahmini URL: {estimated_url}",
    }


def verify_publication(post_id: int, link: str = "") -> dict[str, Any]:
    """Yayın sonrası kanıt — WP API + canlı URL kontrolü."""
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    wp_post: dict[str, Any] = {}
    if post_id:
        res = api._request("GET", f"/wp-json/wp/v2/erotic_story/{post_id}")
        if res.get("success") and res.get("id"):
            wp_post = res

    actual_link = link or wp_post.get("link") or ""
    live = storyforge_v2.verify_live_url(actual_link) if actual_link else {
        "live": False, "status_code": 0, "error": "link yok",
    }

    status = wp_post.get("status", "")
    published = status == "publish" or live.get("live")

    return {
        "success": True,
        "verified": published,
        "post_id": post_id or wp_post.get("id"),
        "link": actual_link,
        "display_url": storyforge_v2.format_display_url(actual_link),
        "wp_status": status,
        "live": live.get("live", False),
        "http_status": live.get("status_code", 0),
        "final_url": live.get("final_url", actual_link),
        "proof": {
            "wp_api_ok": bool(wp_post.get("id")),
            "http_ok": live.get("live", False),
            "title": wp_post.get("title", {}).get("rendered") if isinstance(wp_post.get("title"), dict) else wp_post.get("title", ""),
            "checked_at": _now(),
        },
        "message": (
            "Yayın doğrulandı ✓" if published
            else f"Yayın şüpheli — WP: {status}, HTTP: {live.get('status_code', 0)}"
        ),
    }


def publish_story(
    title: str,
    content: str,
    lokasyon: str = "",
    excerpt: str = "",
    category_slug: str = "gece-hikaye",
    source_url: str = "",
) -> dict[str, Any]:
    pub = publish_to_wordpress(
        title=title,
        content=content,
        lokasyon=lokasyon,
        excerpt=excerpt,
        category_slug=category_slug,
        status="publish",
    )
    if not pub.get("success"):
        return pub

    verification = verify_publication(int(pub.get("post_id") or 0), pub.get("link", ""))
    result = {
        **pub,
        "published": True,
        "verification": verification,
        "verified": verification.get("verified", False),
        "proof_message": verification.get("message", ""),
    }

    _save_history({
        "at": _now(),
        "source_url": source_url,
        "title": title,
        "post_id": pub.get("post_id"),
        "link": pub.get("link"),
        "display_url": pub.get("display_url"),
        "live": pub.get("live"),
        "verified": verification.get("verified"),
        "engine": "manual_publish",
    })
    return result


def get_rules() -> dict[str, Any]:
    return {"success": True, "rules": load_rules()}


def publish_to_wordpress(
    title: str,
    content: str,
    lokasyon: str = "",
    excerpt: str = "",
    category_slug: str = "gece-hikaye",
    status: str = "publish",
) -> dict[str, Any]:
    return storyforge_v2.publish_to_wordpress(
        title=title,
        content=content,
        lokasyon=lokasyon,
        excerpt=excerpt,
        category_slug=category_slug,
        status=status,
        featured_media_id=storyforge_v2.pick_photo_media_id(0),
    )


def process_story(
    url: str,
    title: str = "",
    auto_publish: bool = True,
    category_slug: str = "gece-hikaye",
) -> dict[str, Any]:
    scraped = scrape_url(url)
    if not scraped.get("success"):
        return scraped

    rewritten = rewrite_story(scraped["text"], scraped.get("title") or title)
    if not rewritten.get("success"):
        return {**rewritten, "source_url": scraped.get("source_url"), "original_preview": scraped["text"][:500]}

    final_title = (title or "").strip() or rewritten["suggested_title"] or scraped.get("title") or "Hikaye"
    result: dict[str, Any] = {
        "success": True,
        "status": "rewritten",
        "title": final_title,
        "content": rewritten["content"],
        "content_preview": rewritten["content"][:500],
        "source_url": scraped["source_url"],
        "original_preview": scraped["text"][:500],
        "engine": rewritten.get("engine"),
        "suggested_lokasyon": rewritten.get("suggested_lokasyon"),
        "suggested_categories": rewritten.get("suggested_categories"),
        "published": False,
    }

    if not auto_publish:
        return result

    pub = publish_to_wordpress(
        title=final_title,
        content=rewritten["content"],
        lokasyon=rewritten.get("suggested_lokasyon", ""),
        excerpt=rewritten.get("suggested_excerpt", ""),
        category_slug=category_slug,
        status="publish",
    )
    if not pub.get("success"):
        result["status"] = "publish_failed"
        result["publish_error"] = pub.get("error", "WordPress yayın hatası")
        return result

    result.update({
        "status": "published",
        "published": True,
        "post_id": pub.get("post_id"),
        "link": pub.get("link"),
        "display_url": pub.get("display_url"),
        "live": pub.get("live"),
    })

    _save_history({
        "at": _now(),
        "source_url": scraped["source_url"],
        "title": final_title,
        "post_id": pub.get("post_id"),
        "link": pub.get("link"),
        "engine": rewritten.get("engine"),
    })
    return result


def list_history(limit: int = 20) -> dict[str, Any]:
    rows = _load_history()[:limit]
    return {"success": True, "history": rows, "count": len(rows)}


storyforge_v3 = type("StoryForgeV3", (), {
    "health": staticmethod(health),
    "smoke_test": staticmethod(smoke_test),
    "scrape_url": staticmethod(scrape_url),
    "rewrite_story": staticmethod(rewrite_story),
    "preview_publish": staticmethod(preview_publish),
    "publish_story": staticmethod(publish_story),
    "verify_publication": staticmethod(verify_publication),
    "get_rules": staticmethod(get_rules),
    "publish_to_wordpress": staticmethod(publish_to_wordpress),
    "process_story": staticmethod(process_story),
    "list_history": staticmethod(list_history),
})()
