"""
Publisher Hub V1 — merkezi çok kanallı yayın orkestrasyonu.

Mevcut entegrasyonları sarmalar; duplicate WP/Tumblr/Blogger API yazmaz.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from app import config

logger = logging.getLogger("hive.publisher_hub")

_CHANNELS_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_CHANNELS_TTL_SEC = 60

STATE_FILE = Path(__file__).resolve().parent.parent / "publisher_hub_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

MIN_QUALITY_SCORE = 85

SOURCE_KEYS = (
    "astro_factory",
    "place_seo_pipeline",
    "entity_detail_generator",
    "question_intelligence_engine",
    "content_refresh_engine",
    "listing_hub",
    "network_replicator",
)

CONTENT_TYPES = (
    "blog",
    "faq",
    "entity_page",
    "geo_page",
    "comparison",
    "best_of",
    "ai_overview",
    "listing_landing",
    "category_landing",
)

PUBLISH_STATUSES = ("draft", "queued", "published", "failed", "review_required")

CHANNELS: dict[str, dict[str, Any]] = {
    "wordpress": {"label": "WordPress", "layer": 1, "mode": "api"},
    "ghost": {"label": "Ghost", "layer": 1, "mode": "api"},
    "hashnode": {"label": "Hashnode", "layer": 1, "mode": "api"},
    "devto": {"label": "Dev.to", "layer": 1, "mode": "api"},
    "medium": {"label": "Medium", "layer": 2, "mode": "draft"},
    "linkedin": {"label": "LinkedIn", "layer": 2, "mode": "draft"},
    "quora": {"label": "Quora", "layer": 2, "mode": "draft"},
    "tumblr": {"label": "Tumblr", "layer": 3, "mode": "api"},
    "blogger": {"label": "Blogger", "layer": 3, "mode": "api"},
    "google_sites": {"label": "Google Sites", "layer": 3, "mode": "automation"},
}

# Yeni kurulumlarda varsayılan açık kanallar (mevcut state merge ile korunur)
DEFAULT_ACTIVE_CHANNELS = frozenset({"wordpress", "blogger", "tumblr", "devto"})


def _default_channels() -> dict[str, bool]:
    """Varsayılan kanal bayrakları — yalnızca yeni kurulum / eksik anahtarlar için."""
    channels = {cid: cid in DEFAULT_ACTIVE_CHANNELS for cid in CHANNELS}
    try:
        from app.moduller.blogger_api import get_status, is_configured

        if is_configured() and get_status().get("connected"):
            channels["blogger"] = True
    except Exception as exc:
        logger.debug("blogger default channel check: %s", exc)
    return channels


DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "auto_publish": False,
    "publish_mode": "manual",
    "min_quality_score": MIN_QUALITY_SCORE,
    "require_quality_gate": True,
    "max_items_per_run": 25,
    "channels": _default_channels(),
    "sources": {k: True for k in SOURCE_KEYS},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _new_id(prefix: str = "pub") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                s = data["settings"]
                s["channels"] = {**_default_channels(), **(s.get("channels") or {})}
                s["sources"] = {**DEFAULT_SETTINGS["sources"], **(s.get("sources") or {})}
                data.setdefault("queue", [])
                data.setdefault("drafts", [])
                data.setdefault("published", [])
                data.setdefault("jobs", {})
                data.setdefault("running_job", "")
                data.setdefault("channel_stats", {})
                data.setdefault("network_dispatch", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    fresh = dict(DEFAULT_SETTINGS)
    fresh["channels"] = _default_channels()
    return {
        "settings": fresh,
        "queue": [],
        "drafts": [],
        "published": [],
        "jobs": {},
        "running_job": "",
        "channel_stats": {},
        "network_dispatch": [],
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    for key, val in patch.items():
        if key in ("channels", "sources") and isinstance(val, dict):
            cur[key] = {**cur.get(key, {}), **val}
        else:
            cur[key] = val
    _save_state(st)
    return dict(cur)


def _quality_check(item: dict[str, Any]) -> dict[str, Any]:
    from app.moduller.seo_quality_gate import seo_quality_gate

    analysis = seo_quality_gate.analyze_page(
        item.get("content_html") or "",
        item.get("keyword") or item.get("title") or "",
        title=item.get("title") or "",
    )
    score = int(analysis.get("overall_score") or 0)
    settings = get_settings()
    min_score = int(settings.get("min_quality_score") or MIN_QUALITY_SCORE)
    passed = bool(analysis.get("pass")) and score >= min_score
    publisher_allowed = bool(analysis.get("publisher_hub_allowed", score >= 70))
    return {
        "passed": passed,
        "score": score,
        "publisher_hub_allowed": publisher_allowed,
        "analysis": analysis,
        "min_required": min_score,
    }


def _channel_status(channel_id: str) -> dict[str, Any]:
    meta = dict(CHANNELS.get(channel_id, {}))
    meta["id"] = channel_id
    meta["configured"] = False
    meta["connected"] = False
    try:
        if channel_id == "wordpress":
            from app.moduller.wordpress_api import wp_api
            api = wp_api()
            meta["configured"] = True
            meta["connected"] = bool(api.connected)
        elif channel_id == "tumblr":
            from app.moduller.tumblr_api import connection_status
            cs = connection_status()
            meta["configured"] = cs.get("has_consumer_keys", False)
            meta["connected"] = cs.get("connected", False)
        elif channel_id == "blogger":
            from app.moduller.blogger_api import is_configured, get_status
            meta["configured"] = is_configured()
            meta["connected"] = get_status().get("connected", False) if meta["configured"] else False
        elif channel_id == "ghost":
            meta["configured"] = bool(config.get("GHOST_ADMIN_API_KEY") and config.get("GHOST_API_URL"))
            meta["connected"] = meta["configured"]
        elif channel_id == "hashnode":
            meta["configured"] = bool(config.get("HASHNODE_API_TOKEN"))
            meta["connected"] = meta["configured"]
        elif channel_id == "devto":
            meta["configured"] = bool(config.get("DEVTO_API_KEY"))
            meta["connected"] = meta["configured"]
        elif channel_id in ("medium", "linkedin", "quora"):
            meta["configured"] = True
            meta["connected"] = True
        elif channel_id == "google_sites":
            meta["configured"] = bool(config.get("SELENIUM_DRIVER"))
            meta["connected"] = meta["configured"]
    except Exception as exc:
        meta["error"] = str(exc)
    return meta


def list_channels() -> list[dict[str, Any]]:
    import time
    now = time.monotonic()
    cached = _CHANNELS_CACHE.get("data")
    if cached is not None and (now - _CHANNELS_CACHE["at"]) < _CHANNELS_TTL_SEC:
        return [dict(c) for c in cached]

    settings = get_settings()
    out = []
    for cid, meta in CHANNELS.items():
        st = _channel_status(cid)
        st["enabled"] = bool(settings.get("channels", {}).get(cid))
        out.append(st)
    _CHANNELS_CACHE["at"] = now
    _CHANNELS_CACHE["data"] = out
    return [dict(c) for c in out]


def _normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": raw.get("source", ""),
        "source_id": raw.get("source_id", ""),
        "content_type": raw.get("content_type") or "blog",
        "title": (raw.get("title") or "").strip(),
        "content_html": raw.get("content_html") or raw.get("content") or "",
        "slug": (raw.get("slug") or "").strip(),
        "keyword": (raw.get("keyword") or raw.get("target_keyword") or "").strip(),
        "canonical_url": raw.get("canonical_url") or "",
        "tags": raw.get("tags") or raw.get("labels") or [],
        "project_id": raw.get("project_id") or "",
        "network_id": raw.get("network_id") or "",
        "domain": raw.get("domain") or "",
        "channels": list(raw.get("channels") or []),
        "metadata": raw.get("metadata") or {},
    }


# ── Source scanners (read-only, no duplicate publish) ─────────────────────────

def _scan_astro_factory() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        from app.moduller.astro_factory import list_projects, GENERATED_DIR
        for proj in list_projects().get("projects") or []:
            pid = proj.get("id", "")
            slug = proj.get("slug", "")
            data_dir = GENERATED_DIR / slug / "src" / "data"
            if not data_dir.exists():
                continue
            pages_path = data_dir / "pages.json"
            if pages_path.exists():
                data = json.loads(pages_path.read_text(encoding="utf-8"))
                home = data.get("home") or {}
                if home.get("content_html"):
                    items.append({
                        "source": "astro_factory",
                        "source_id": f"{pid}:home",
                        "content_type": "blog",
                        "title": home.get("title") or proj.get("site_name", ""),
                        "content_html": home.get("content_html", ""),
                        "slug": "home",
                        "keyword": data.get("seed_keyword") or proj.get("seed_keyword", ""),
                        "project_id": pid,
                        "domain": proj.get("domain", ""),
                    })
            faqs_path = data_dir / "faqs.json"
            if faqs_path.exists():
                for faq in json.loads(faqs_path.read_text(encoding="utf-8")):
                    if not isinstance(faq, dict) or not faq.get("content_html"):
                        continue
                    items.append({
                        "source": "astro_factory",
                        "source_id": f"{pid}:faq:{faq.get('slug', '')}",
                        "content_type": "faq",
                        "title": faq.get("title", ""),
                        "content_html": faq.get("content_html", ""),
                        "slug": faq.get("slug", ""),
                        "keyword": faq.get("keyword", ""),
                        "project_id": pid,
                        "domain": proj.get("domain", ""),
                    })
    except Exception as exc:
        logger.debug("astro_factory scan: %s", exc)
    return items


def _scan_content_refresh() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cre_path = Path(__file__).resolve().parent.parent / "content_refresh_engine_state.json"
    if not cre_path.exists():
        return items
    try:
        data = json.loads(cre_path.read_text(encoding="utf-8"))
        for q in data.get("queue") or []:
            if q.get("status") not in ("queued", "completed"):
                continue
            pid = q.get("project_id", "")
            page_id = q.get("page_id", "")
            items.append({
                "source": "content_refresh_engine",
                "source_id": f"{pid}:{page_id}",
                "content_type": "blog",
                "title": q.get("title") or page_id,
                "content_html": q.get("content_html") or "",
                "slug": page_id.split(":")[-1] if ":" in page_id else page_id,
                "keyword": q.get("keyword", ""),
                "project_id": pid,
                "metadata": {"refresh_priority": q.get("priority"), "actions": q.get("actions")},
            })
        for pid, cands in (data.get("candidates") or {}).items():
            for c in cands or []:
                if not c.get("refresh_needed"):
                    continue
                items.append({
                    "source": "content_refresh_engine",
                    "source_id": f"{pid}:{c.get('page_id', '')}",
                    "content_type": "blog",
                    "title": c.get("title", ""),
                    "content_html": c.get("content_html") or "",
                    "slug": c.get("slug", ""),
                    "keyword": c.get("keyword", ""),
                    "project_id": pid,
                    "metadata": {"refresh_needed": True, "priority": c.get("priority_label")},
                })
    except Exception as exc:
        logger.debug("content_refresh scan: %s", exc)
    return items


def _scan_entity_detail() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    path = Path(__file__).resolve().parent.parent / "entity_detail_generator_state.json"
    if not path.exists():
        return items
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for job in (data.get("jobs") or {}).values():
            for ent in job.get("entities") or []:
                if not ent.get("content_html"):
                    continue
                items.append({
                    "source": "entity_detail_generator",
                    "source_id": ent.get("entity_id") or ent.get("slug", ""),
                    "content_type": "entity_page",
                    "title": ent.get("title", ""),
                    "content_html": ent.get("content_html", ""),
                    "slug": ent.get("slug", ""),
                    "keyword": ent.get("keyword", ""),
                    "project_id": job.get("project_id", ""),
                })
    except Exception as exc:
        logger.debug("entity_detail scan: %s", exc)
    return items


def _scan_listing_hub() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    path = Path(__file__).resolve().parent.parent / "listing_hub_state.json"
    if not path.exists():
        return items
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for lid, listing in (data.get("listings") or {}).items():
            if listing.get("wp_published"):
                continue
            desc = listing.get("description") or listing.get("description_html") or ""
            if not desc:
                continue
            items.append({
                "source": "listing_hub",
                "source_id": lid,
                "content_type": "listing_landing",
                "title": listing.get("title") or listing.get("name", ""),
                "content_html": desc,
                "slug": listing.get("slug", lid),
                "keyword": listing.get("keyword", ""),
                "metadata": {"city": listing.get("city"), "category": listing.get("category")},
            })
    except Exception as exc:
        logger.debug("listing_hub scan: %s", exc)
    return items


def _scan_qie() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    path = Path(__file__).resolve().parent.parent / "question_intelligence_engine_state.json"
    if not path.exists():
        return items
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for job in (data.get("jobs") or {}).values():
            for it in job.get("items") or []:
                html = it.get("content_html") or it.get("content") or ""
                if not html and it.get("content_outline"):
                    html = "<p>" + "</p><p>".join(it["content_outline"]) + "</p>"
                if not html:
                    continue
                ctype = "faq"
                t = (it.get("type") or "").lower()
                if "comparison" in t:
                    ctype = "comparison"
                elif "best" in t:
                    ctype = "best_of"
                elif "overview" in t:
                    ctype = "ai_overview"
                items.append({
                    "source": "question_intelligence_engine",
                    "source_id": it.get("slug") or it.get("job_id", ""),
                    "content_type": ctype,
                    "title": it.get("title", ""),
                    "content_html": html,
                    "slug": it.get("slug", ""),
                    "keyword": it.get("keyword", ""),
                    "tags": it.get("tags") or [],
                })
    except Exception as exc:
        logger.debug("qie scan: %s", exc)
    return items


def _scan_place_seo() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    path = Path(__file__).resolve().parent.parent / "place_seo_pipeline_state.json"
    if not path.exists():
        return items
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for page in data.get("pages") or []:
            if not page.get("content_html"):
                continue
            ptype = page.get("type", "geo_page")
            items.append({
                "source": "place_seo_pipeline",
                "source_id": page.get("slug") or page.get("page_id", ""),
                "content_type": "geo_page" if "geo" in ptype else "category_landing",
                "title": page.get("title", ""),
                "content_html": page.get("content_html", ""),
                "slug": page.get("slug", ""),
                "keyword": page.get("keyword", ""),
                "project_id": data.get("project_id", ""),
            })
    except Exception as exc:
        logger.debug("place_seo scan: %s", exc)
    return items


def _scan_network_replicator() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        from app.moduller.network_replicator import list_networks
        for net in list_networks().get("networks") or []:
            nid = net.get("network_id", "")
            for d in net.get("domains") or []:
                items.append({
                    "source": "network_replicator",
                    "source_id": f"{nid}:{d.get('project_id', '')}",
                    "content_type": "blog",
                    "title": f"Network variant — {d.get('domain', '')}",
                    "content_html": d.get("content_preview") or "<p>Network site content</p>",
                    "slug": d.get("slug", ""),
                    "keyword": d.get("seed_keyword", ""),
                    "project_id": d.get("project_id", ""),
                    "network_id": nid,
                    "domain": d.get("domain", ""),
                })
    except Exception as exc:
        logger.debug("network_replicator scan: %s", exc)
    return items


SOURCE_SCANNERS = {
    "astro_factory": _scan_astro_factory,
    "place_seo_pipeline": _scan_place_seo,
    "entity_detail_generator": _scan_entity_detail,
    "question_intelligence_engine": _scan_qie,
    "content_refresh_engine": _scan_content_refresh,
    "listing_hub": _scan_listing_hub,
    "network_replicator": _scan_network_replicator,
}


def scan_sources(source: str = "") -> dict[str, Any]:
    settings = get_settings()
    enabled = settings.get("sources") or {}
    items: list[dict[str, Any]] = []
    keys = [source] if source and source in SOURCE_SCANNERS else list(SOURCE_SCANNERS.keys())
    for key in keys:
        if not enabled.get(key, True):
            continue
        items.extend(SOURCE_SCANNERS[key]())
    dedup: dict[str, dict] = {}
    for it in items:
        k = f"{it.get('source')}:{it.get('source_id')}"
        dedup[k] = _normalize_item(it)
    normalized = list(dedup.values())
    return {"success": True, "count": len(normalized), "items": normalized}


# ── Channel adapters (wrap existing integrations) ───────────────────────────

def _publish_wordpress(item: dict[str, Any]) -> dict[str, Any]:
    from app.moduller.wordpress_api import wp_api
    from app.moduller.indexnow import bildirim_gonder

    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok — /api/wp/connect"}
    tags = item.get("tags") or []
    res = api.create_post(
        item["title"],
        item["content_html"],
        status="publish",
        slug=item.get("slug") or None,
        tags=tags if tags else None,
    )
    if not res.get("success") and not res.get("id"):
        return {"success": False, "error": res.get("error", "WordPress yayın hatası")}
    link = res.get("link") or ""
    indexnow = bildirim_gonder(link) if link else {}
    return {"success": True, "post_id": res.get("id"), "url": link, "indexnow": indexnow}


def _publish_ghost(item: dict[str, Any]) -> dict[str, Any]:
    api_url = (config.get("GHOST_API_URL") or "").rstrip("/")
    admin_key = (config.get("GHOST_ADMIN_API_KEY") or "").strip()
    if not api_url or not admin_key:
        return {"success": False, "error": "Ghost yapılandırılmamış (GHOST_API_URL, GHOST_ADMIN_API_KEY)"}
    try:
        import jwt as pyjwt
        key_id, secret = admin_key.split(":", 1)
        iat = int(datetime.now(timezone.utc).timestamp())
        token = pyjwt.encode(
            {"iat": iat, "exp": iat + 300, "aud": "/admin/"},
            bytes.fromhex(secret),
            algorithm="HS256",
            headers={"kid": key_id},
        )
    except Exception as exc:
        return {"success": False, "error": f"Ghost JWT hatası: {exc}"}

    payload = {
        "posts": [{
            "title": item["title"],
            "html": item["content_html"],
            "status": "published",
            "slug": item.get("slug") or None,
            "tags": [{"name": t} for t in (item.get("tags") or [])[:10]],
        }]
    }
    url = f"{api_url}/ghost/api/admin/posts/?source=html"
    resp = requests.post(
        url,
        headers={"Authorization": f"Ghost {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        return {"success": False, "error": f"Ghost API: {resp.text[:500]}"}
    posts = (resp.json().get("posts") or [{}])
    post = posts[0] if posts else {}
    return {"success": True, "post_id": post.get("id"), "url": post.get("url")}


def _publish_hashnode(item: dict[str, Any]) -> dict[str, Any]:
    token = (config.get("HASHNODE_API_TOKEN") or "").strip()
    pub_id = (config.get("HASHNODE_PUBLICATION_ID") or "").strip()
    if not token or not pub_id:
        return {"success": False, "error": "Hashnode yapılandırılmamış (HASHNODE_API_TOKEN, HASHNODE_PUBLICATION_ID)"}
    query = """
    mutation PublishPost($input: PublishPostInput!) {
      publishPost(input: $input) { post { _id slug url } }
    }
    """
    variables = {
        "input": {
            "title": item["title"],
            "contentMarkdown": re.sub(r"<[^>]+>", "", item["content_html"])[:50000],
            "tags": [{"slug": re.sub(r"[^a-z0-9-]", "-", t.lower())[:40]} for t in (item.get("tags") or [])[:5]],
            "publicationId": pub_id,
        }
    }
    resp = requests.post(
        "https://gql.hashnode.com",
        headers={"Authorization": token, "Content-Type": "application/json"},
        json={"query": query, "variables": variables},
        timeout=60,
    )
    if resp.status_code != 200:
        return {"success": False, "error": f"Hashnode HTTP {resp.status_code}"}
    body = resp.json()
    if body.get("errors"):
        return {"success": False, "error": str(body["errors"][:2])}
    post = (body.get("data") or {}).get("publishPost", {}).get("post") or {}
    return {"success": True, "post_id": post.get("_id"), "url": post.get("url")}


def _publish_devto(item: dict[str, Any]) -> dict[str, Any]:
    api_key = (config.get("DEVTO_API_KEY") or "").strip()
    if not api_key:
        return {"success": False, "error": "Dev.to yapılandırılmamış (DEVTO_API_KEY)"}
    body = {
        "article": {
            "title": item["title"],
            "body_markdown": re.sub(r"<[^>]+>", "", item["content_html"])[:50000],
            "published": True,
            "tags": [re.sub(r"[^a-z0-9_]", "", t.lower().replace(" ", "_"))[:30] for t in (item.get("tags") or [])[:4]],
        }
    }
    resp = requests.post(
        "https://dev.to/api/articles",
        headers={"api-key": api_key, "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        return {"success": False, "error": f"Dev.to API: {resp.text[:500]}"}
    data = resp.json()
    return {"success": True, "post_id": data.get("id"), "url": data.get("url")}


def _publish_draft_channel(item: dict[str, Any], channel: str) -> dict[str, Any]:
    """Katman 2 — taslak; kullanıcı onayı gerekir."""
    return {
        "success": True,
        "draft": True,
        "channel": channel,
        "status": "review_required",
        "title": item["title"],
        "content_html": item["content_html"],
        "instructions": f"{CHANNELS[channel]['label']} için taslak oluşturuldu — panelden onaylayın veya kopyalayın.",
    }


def _publish_tumblr(item: dict[str, Any]) -> dict[str, Any]:
    from app.moduller.tumblr_api import post_to_tumblr, load_tokens
    tokens = load_tokens() or {}
    blog = (config.get("TUMBLR_DEFAULT_BLOG") or tokens.get("blog_name") or "").strip()
    if not blog:
        return {"success": False, "error": "Tumblr blog tanımlı değil"}
    resp = post_to_tumblr(
        blog_name=blog,
        content=item["content_html"],
        title=item["title"],
        tags=item.get("tags") or [],
        state="published",
    )
    post_id = (resp.get("response") or {}).get("id")
    return {"success": True, "post_id": post_id, "url": ""}


def _publish_blogger(item: dict[str, Any]) -> dict[str, Any]:
    from app.moduller.blogger_api import create_post, is_configured
    if not is_configured():
        return {"success": False, "error": "Blogger OAuth yapılandırılmamış"}
    res = create_post(
        title=item["title"],
        content=item["content_html"],
        labels=item.get("tags") or [],
        publish=True,
    )
    return res


def _publish_google_sites(item: dict[str, Any]) -> dict[str, Any]:
    from app.moduller.zeus import parazit_yerlestir
    res = parazit_yerlestir("Google Sites", item["title"], item.get("canonical_url") or "")
    if res.get("durum") in ("yayında", "selenium_ile_olusturuldu"):
        return {"success": True, "url": res.get("url", ""), "mode": res.get("durum")}
    return {
        "success": True,
        "draft": True,
        "status": "review_required",
        "channel": "google_sites",
        "instructions": res.get("uyari") or "Google Sites otomasyonu — SELENIUM_DRIVER gerekli veya manuel yayın",
        "zeus_result": res,
    }


CHANNEL_PUBLISHERS = {
    "wordpress": _publish_wordpress,
    "ghost": _publish_ghost,
    "hashnode": _publish_hashnode,
    "devto": _publish_devto,
    "medium": lambda i: _publish_draft_channel(i, "medium"),
    "linkedin": lambda i: _publish_draft_channel(i, "linkedin"),
    "quora": lambda i: _publish_draft_channel(i, "quora"),
    "tumblr": _publish_tumblr,
    "blogger": _publish_blogger,
    "google_sites": _publish_google_sites,
}


def _notify_rank_watcher(item: dict[str, Any], channel: str, url: str) -> None:
    if not url or not item.get("keyword"):
        return
    try:
        from app.moduller.rank_index_watcher import register_project, track_keyword
        domain = urlparse(url).netloc or item.get("domain", "")
        if not domain:
            return
        pid = f"pub-{channel}-{item.get('publish_id', _new_id())[:16]}"
        register_project(pid, domain, source=f"publisher_hub:{channel}")
        track_keyword(item["keyword"], domain, project_id=pid)
    except Exception as exc:
        logger.warning("Rank watcher notify: %s", exc)


def _notify_network(item: dict[str, Any], channel: str, url: str, success: bool) -> None:
    if not item.get("network_id"):
        return
    st = _load_state()
    st["network_dispatch"].append({
        "network_id": item["network_id"],
        "project_id": item.get("project_id", ""),
        "domain": item.get("domain", ""),
        "channel": channel,
        "url": url,
        "success": success,
        "source": item.get("source", ""),
        "source_id": item.get("source_id", ""),
        "at": _now(),
    })
    st["network_dispatch"] = st["network_dispatch"][-500:]
    _save_state(st)


def _publish_to_channel(item: dict[str, Any], channel: str) -> dict[str, Any]:
    fn = CHANNEL_PUBLISHERS.get(channel)
    if not fn:
        return {"success": False, "error": f"Bilinmeyen kanal: {channel}"}
    meta = CHANNELS.get(channel, {})
    if meta.get("mode") == "draft":
        result = fn(item)
        result["review_required"] = True
        return result
    st = _channel_status(channel)
    if not st.get("connected") and channel not in ("medium", "linkedin", "quora"):
        return {"success": False, "error": f"{meta.get('label', channel)} bağlı değil"}
    result = fn(item)
    if result.get("success") and result.get("url"):
        _notify_rank_watcher(item, channel, result["url"])
    _notify_network(item, channel, result.get("url", ""), bool(result.get("success")))
    st = _load_state()
    ch = st.setdefault("channel_stats", {}).setdefault(channel, {"published": 0, "failed": 0})
    if result.get("success"):
        ch["published"] = ch.get("published", 0) + 1
    else:
        ch["failed"] = ch.get("failed", 0) + 1
    _save_state(st)
    return result


def enqueue(
    item: dict[str, Any],
    channels: list[str] | None = None,
    *,
    skip_quality: bool = False,
) -> dict[str, Any]:
    norm = _normalize_item(item)
    if not norm["title"] or not norm["content_html"]:
        return {"success": False, "error": "title ve content_html gerekli"}

    settings = get_settings()
    target_channels = channels or norm.get("channels") or [
        c for c, on in (settings.get("channels") or {}).items() if on
    ]
    if not target_channels:
        return {"success": False, "error": "En az bir kanal seçin"}

    quality = _quality_check(norm)
    publish_id = _new_id()
    record = {
        "publish_id": publish_id,
        **norm,
        "channels": target_channels,
        "status": "queued",
        "quality_score": quality["score"],
        "quality_passed": quality["passed"],
        "quality_analysis": {"overall_score": quality["score"], "pass": quality["passed"]},
        "channel_results": {},
        "created_at": _now(),
        "updated_at": _now(),
    }

    if settings.get("require_quality_gate") and not skip_quality and not quality["passed"]:
        record["status"] = "review_required"
        record["error"] = f"Quality Gate fail — skor {quality['score']} < {quality['min_required']}"
        st = _load_state()
        st["drafts"].append(record)
        _save_state(st)
        return {
            "success": False,
            "publish_id": publish_id,
            "status": "review_required",
            "quality_gate": quality,
            "error": record["error"],
        }

    st = _load_state()
    st["queue"].append(record)
    _save_state(st)
    return {"success": True, "publish_id": publish_id, "status": "queued", "quality_gate": quality}


def approve_draft(publish_id: str, channels: list[str] | None = None) -> dict[str, Any]:
    st = _load_state()
    draft = next((d for d in st["drafts"] if d["publish_id"] == publish_id), None)
    if not draft:
        return {"success": False, "error": "Taslak bulunamadı"}
    if channels:
        draft["channels"] = channels
    draft["status"] = "queued"
    draft["updated_at"] = _now()
    st["drafts"] = [d for d in st["drafts"] if d["publish_id"] != publish_id]
    st["queue"].append(draft)
    _save_state(st)
    return {"success": True, "publish_id": publish_id, "status": "queued"}


def publish_item(publish_id: str, channels: list[str] | None = None) -> dict[str, Any]:
    st = _load_state()
    item = next(
        (q for q in st["queue"] if q["publish_id"] == publish_id),
        None,
    ) or next((d for d in st["drafts"] if d["publish_id"] == publish_id), None)
    if not item:
        return {"success": False, "error": "Yayın kaydı bulunamadı"}

    if item.get("status") == "review_required" and not channels:
        return {"success": False, "error": "Onay gerekli — approve_draft veya channels ile yayınlayın"}

    target = channels or item.get("channels") or []
    results: dict[str, Any] = {}
    any_ok = False
    any_review = False
    for ch in target:
        if not get_settings().get("channels", {}).get(ch, True):
            results[ch] = {"success": False, "error": "Kanal devre dışı"}
            continue
        res = _publish_to_channel(item, ch)
        results[ch] = res
        if res.get("success"):
            any_ok = True
        if res.get("review_required") or res.get("draft"):
            any_review = True

    item["channel_results"] = results
    item["updated_at"] = _now()
    if any_ok and not any_review:
        item["status"] = "published"
    elif any_review:
        item["status"] = "review_required"
    else:
        item["status"] = "failed"

    st["queue"] = [q for q in st["queue"] if q["publish_id"] != publish_id]
    if item["status"] == "published":
        st["published"].append(item)
        st["published"] = st["published"][-1000:]
    elif item["status"] == "review_required":
        st["drafts"].append(item)
    else:
        st["published"].append({**item, "status": "failed"})
    _save_state(st)
    return {"success": any_ok, "publish_id": publish_id, "status": item["status"], "channel_results": results}


def process_queue(max_items: int | None = None) -> dict[str, Any]:
    settings = get_settings()
    limit = max_items or int(settings.get("max_items_per_run") or 25)
    st = _load_state()
    job_id = _new_id("pubjob")
    job = {
        "job_id": job_id,
        "type": "process_queue",
        "status": "running",
        "started_at": _now(),
        "finished_at": "",
        "summary": {"processed": 0, "published": 0, "failed": 0, "review_required": 0},
        "items": [],
    }
    st["jobs"][job_id] = job
    st["running_job"] = job_id
    _save_state(st)

    queue = list(st.get("queue") or [])[:limit]
    for item in queue:
        res = publish_item(item["publish_id"])
        job["items"].append({"publish_id": item["publish_id"], **res})
        job["summary"]["processed"] += 1
        status = res.get("status", "")
        if status == "published":
            job["summary"]["published"] += 1
        elif status == "review_required":
            job["summary"]["review_required"] += 1
        else:
            job["summary"]["failed"] += 1

    st = _load_state()
    job["status"] = "completed"
    job["finished_at"] = _now()
    st["jobs"][job_id] = job
    st["running_job"] = ""
    _save_state(st)
    return {"success": True, "job_id": job_id, "summary": job["summary"], "items": job["items"]}


def requeue_from_refresh(project_id: str = "", page_id: str = "") -> dict[str, Any]:
    """Content Refresh Engine yenilenen içerikleri Publisher kuyruğuna al."""
    items = _scan_content_refresh()
    matched = [
        it for it in items
        if it.get("source") == "content_refresh_engine"
        and (not project_id or it.get("project_id") == project_id)
        and (not page_id or page_id in (it.get("source_id") or ""))
    ]
    queued = []
    for it in matched:
        res = enqueue(it)
        if res.get("success") or res.get("status") == "review_required":
            queued.append(res.get("publish_id"))
    return {"success": True, "queued": len(queued), "publish_ids": queued}


def get_queue() -> dict[str, Any]:
    st = _load_state()
    return {"success": True, "count": len(st.get("queue") or []), "queue": st.get("queue") or []}


def get_drafts() -> dict[str, Any]:
    st = _load_state()
    return {"success": True, "count": len(st.get("drafts") or []), "drafts": st.get("drafts") or []}


def get_published(limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    items = (st.get("published") or [])[-limit:]
    return {"success": True, "count": len(items), "published": list(reversed(items))}


def get_jobs(limit: int = 30) -> dict[str, Any]:
    st = _load_state()
    jobs = sorted(
        (st.get("jobs") or {}).values(),
        key=lambda j: j.get("started_at", ""),
        reverse=True,
    )[:limit]
    return {"success": True, "jobs": jobs}


def export_report(job_id: str = "", publish_id: str = "") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    st = _load_state()
    payload = {
        "exported_at": _now(),
        "settings": st.get("settings"),
        "channel_stats": st.get("channel_stats"),
        "network_dispatch": st.get("network_dispatch", [])[-100:],
        "queue_size": len(st.get("queue") or []),
        "drafts_size": len(st.get("drafts") or []),
        "published_size": len(st.get("published") or []),
    }
    if job_id:
        payload["job"] = (st.get("jobs") or {}).get(job_id)
    if publish_id:
        for coll in ("queue", "drafts", "published"):
            for it in st.get(coll) or []:
                if it.get("publish_id") == publish_id:
                    payload["item"] = it
    path = REPORTS_DIR / f"publisher_hub_{job_id or publish_id or 'report'}_{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path)}


def health(*, lite: bool = False) -> dict[str, Any]:
    st = _load_state()
    settings = st.get("settings") or DEFAULT_SETTINGS
    published = [p for p in (st.get("published") or []) if p.get("status") == "published"]
    if lite:
        channels = None
        connected = _connected_channel_count_fast()
    else:
        channels = list_channels()
        connected = sum(1 for c in channels if c.get("connected"))
    payload = {
        "success": True,
        "enabled": settings.get("enabled", False),
        "publish_mode": settings.get("publish_mode", "manual"),
        "min_quality_score": settings.get("min_quality_score", MIN_QUALITY_SCORE),
        "channels_total": len(CHANNELS),
        "channels_connected": connected,
        "queue_size": len(st.get("queue") or []),
        "drafts_size": len(st.get("drafts") or []),
        "published_count": len(published),
        "running_job": st.get("running_job", ""),
        "dashboard": {
            "queued": len(st.get("queue") or []),
            "drafts": len(st.get("drafts") or []),
            "published": len(published),
            "review_required": len([d for d in st.get("drafts") or [] if d.get("status") == "review_required"]),
            "channel_stats": st.get("channel_stats") or {},
            "sources_enabled": sum(1 for v in (settings.get("sources") or {}).values() if v),
        },
    }
    if channels is not None:
        payload["channels"] = channels
    return payload


def _connected_channel_count_fast() -> int:
    """Mission Control için — canlı OAuth/API çağrısı yapmadan tahmini bağlantı sayısı."""
    count = 0
    try:
        from app.moduller.wordpress_api import wp_api
        if wp_api().connected:
            count += 1
    except Exception:
        pass
    try:
        from app.moduller.tumblr_api import connection_status
        if connection_status().get("connected"):
            count += 1
    except Exception:
        pass
    try:
        from app.moduller.blogger_api import is_configured, get_status
        if is_configured() and get_status().get("connected"):
            count += 1
    except Exception:
        pass
    for key in ("GHOST_ADMIN_API_KEY", "HASHNODE_API_TOKEN", "DEVTO_API_KEY"):
        if config.get(key):
            count += 1
    return count


def health_summary() -> dict[str, Any]:
    return health(lite=True)
