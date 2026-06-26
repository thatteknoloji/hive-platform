"""
Authority Mesh Engine V1 — otorite kaynakları orkestrasyon katmanı.

Blogger, Tumblr, Dev.to, Google Sites, Medium, Quora vb. platformları tek authority
ağı altında planlar. İçerik üretmez; Publisher Hub ve browser worker'ları delegasyon ile kullanır.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("hive.authority_mesh")

STATE_FILE = Path(__file__).resolve().parent.parent / "authority_mesh_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 500

PROVIDER_TYPES = ("api", "browser", "manual")

PROVIDERS: dict[str, dict[str, Any]] = {
    "wordpress": {"label": "WordPress", "provider_type": "api", "publisher_channel": "wordpress"},
    "blogger": {"label": "Blogger", "provider_type": "api", "publisher_channel": "blogger"},
    "tumblr": {"label": "Tumblr", "provider_type": "api", "publisher_channel": "tumblr"},
    "devto": {"label": "Dev.to", "provider_type": "api", "publisher_channel": "devto"},
    "github_pages": {"label": "GitHub Pages", "provider_type": "api", "publisher_channel": None},
    "ghost": {"label": "Ghost", "provider_type": "api", "publisher_channel": "ghost"},
    "hashnode": {"label": "Hashnode", "provider_type": "api", "publisher_channel": "hashnode"},
    "google_sites": {"label": "Google Sites", "provider_type": "browser", "publisher_channel": "google_sites"},
    "medium": {"label": "Medium", "provider_type": "browser", "publisher_channel": "medium"},
    "quora": {"label": "Quora", "provider_type": "browser", "publisher_channel": "quora"},
    "linkedin": {"label": "LinkedIn", "provider_type": "browser", "publisher_channel": "linkedin"},
    "astro": {"label": "Astro Support", "provider_type": "api", "publisher_channel": None},
}

ROLES = (
    "faq_hub", "geo_hub", "entity_hub", "blog_hub", "support_hub", "citation_hub",
)

DEFAULT_MESH_COUNTS: dict[str, int] = {
    "google_sites": 1,
    "blogger": 2,
    "tumblr": 2,
    "devto": 1,
    "github_pages": 1,
    "medium": 1,
    "quora": 3,
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "default_money_site": "",
    "default_network_id": "",
    "max_exact_match_anchor_ratio": 0.15,
    "max_links_per_content": 2,
    "duplicate_content_block": False,
    "duplicate_site_block": False,
    "auto_track_rank_watcher": True,
    "auto_register_support_network": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data.setdefault("authority_sites", [])
                data.setdefault("mesh_plans", [])
                data.setdefault("tasks", [])
                data.setdefault("google_sites_tasks", [])
                data.setdefault("link_policies", [])
                data.setdefault("support_network_sources", [])
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "authority_sites": [],
        "mesh_plans": [],
        "tasks": [],
        "google_sites_tasks": [],
        "link_policies": [],
        "support_network_sources": [],
        "history": [],
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_settings() -> dict[str, Any]:
    return dict(_load_state().get("settings") or DEFAULT_SETTINGS)


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = st.setdefault("settings", dict(DEFAULT_SETTINGS))
    cur.update(patch)
    _save_state(st)
    return dict(cur)


def _append_history(state: dict[str, Any], entry: dict[str, Any]) -> None:
    lst = state.setdefault("history", [])
    lst.insert(0, entry)
    state["history"] = lst[:HISTORY_LIMIT]


def _record_brain(event_type: str, *, domain: str = "", keyword: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            "module_action",
            "authority_mesh_engine",
            domain=domain,
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "authority_mesh_engine", "mesh_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _content_fingerprint(title: str, provider: str, keyword: str) -> str:
    raw = f"{provider}:{keyword}:{title}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _audit_log(action: str, **meta: Any) -> None:
    """Provider/API işlem audit kaydı — secret/token/key değerleri asla loglanmaz."""
    blocked = ("key", "token", "secret", "password", "credential", "authorization")
    safe = {}
    for k, v in meta.items():
        kl = k.lower()
        if any(b in kl for b in blocked):
            safe[k] = "[redacted]"
        elif isinstance(v, dict):
            safe[k] = {sk: ("[redacted]" if any(b in sk.lower() for b in blocked) else sv)
                       for sk, sv in v.items()}
        else:
            safe[k] = v
    logger.info("authority_mesh.%s %s", action, json.dumps(safe, ensure_ascii=False, default=str))
    try:
        st = _load_state()
        _append_history(st, {"type": "audit", "action": action, "meta": safe, "at": _now()})
        _save_state(st)
    except Exception:
        pass


def _browser_worker_status() -> dict[str, Any]:
    selenium_ok = False
    try:
        from app.moduller.api_key_manager import get_key
        selenium_ok = get_key("selenium") == "chrome"
    except Exception:
        pass
    playwright_ok = False
    try:
        import playwright  # noqa: F401
        playwright_ok = True
    except ImportError:
        pass
    openclaw_ok = bool(os.environ.get("OPENCLAW_BROWSER_WORKER_URL", "").strip())
    available = selenium_ok or openclaw_ok or playwright_ok
    return {
        "available": available,
        "selenium": selenium_ok,
        "playwright": playwright_ok,
        "openclaw": openclaw_ok,
        "error": None if available else "provider_missing — browser automation worker yapılandırılmadı (Playwright, OPENCLAW_BROWSER_WORKER_URL veya SELENIUM)",
    }


def _publisher_channel_ready(channel: str) -> tuple[bool, str | None]:
    try:
        from app.moduller.publisher_hub import _channel_status
        st = _channel_status(channel)
        if st.get("connected") or st.get("configured"):
            return True, None
        return False, st.get("error") or f"{channel} yapılandırılmadı"
    except Exception as exc:
        return False, str(exc)


_INTEGRATION_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_INTEGRATION_TTL_SEC = 90


def _integration_status() -> dict[str, Any]:
    import time
    now = time.monotonic()
    cached = _INTEGRATION_CACHE.get("data")
    if cached is not None and (now - _INTEGRATION_CACHE["at"]) < _INTEGRATION_TTL_SEC:
        return dict(cached)

    checks: dict[str, Any] = {}
    for name, fn in (
        ("publisher_hub", lambda: __import__("app.moduller.publisher_hub", fromlist=["health_summary"]).health_summary()),
        ("support_network_engine", lambda: __import__("app.moduller.support_network_engine", fromlist=["health"]).health()),
        ("rank_index_watcher", lambda: __import__("app.moduller.rank_index_watcher", fromlist=["health"]).health()),
        ("hive_brain_engine", lambda: __import__("app.moduller.hive_brain_engine", fromlist=["health"]).health()),
        ("opportunity_engine", lambda: __import__("app.moduller.opportunity_engine", fromlist=["health"]).health()),
        ("serp_defense_engine", lambda: __import__("app.moduller.serp_defense_engine", fromlist=["health"]).health()),
        ("crawl_gap_engine", lambda: __import__("app.moduller.crawl_gap_engine", fromlist=["health"]).health()),
    ):
        try:
            res = fn()
            checks[name] = {"ok": bool(res.get("success", True)), "detail": res}
        except Exception as exc:
            checks[name] = {"ok": False, "error": str(exc)}
    checks["browser_worker"] = _browser_worker_status()
    checks["browser_worker"]["ok"] = checks["browser_worker"].get("available", False)
    _INTEGRATION_CACHE["at"] = now
    _INTEGRATION_CACHE["data"] = checks
    return checks


def generate_link_policy(
    keyword: str,
    money_site: str,
    *,
    category_url: str = "",
) -> list[dict[str, Any]]:
    """Spam pattern üretmez — anchor çeşitliliği."""
    settings = get_settings()
    kw = keyword.strip()
    money = money_site.strip() or settings.get("default_money_site", "")
    brand = ""
    m = re.search(r"https?://(?:www\.)?([^/]+)", money)
    if m:
        brand = m.group(1).split(".")[0].capitalize()

    cat = category_url or (money.rstrip("/") + f"/{kw.replace(' ', '-').lower()}/" if kw else money)
    policies = [
        {"anchor": brand, "target_url": money, "link_type": "brand"},
        {"anchor": money.replace("https://", "").replace("http://", ""), "target_url": money, "link_type": "url"},
        {"anchor": f"{kw} rehberi" if kw else "rehber", "target_url": cat, "link_type": "category"},
        {"anchor": kw[:40] if kw else "konu", "target_url": cat, "link_type": "partial"},
        {"anchor": brand, "target_url": money, "link_type": "homepage"},
        {"anchor": "", "target_url": "", "link_type": "no_link"},
    ]
    max_exact = int(settings.get("max_exact_match_anchor_ratio", 0.15) * 100)
    out: list[dict] = []
    exact_count = 0
    for p in policies:
        if p["link_type"] == "partial" and kw and p["anchor"].lower() == kw.lower():
            exact_count += 1
            if exact_count > max(1, max_exact // 10):
                continue
        out.append(p)
    limit = int(settings.get("max_links_per_content", 2)) + 2
    sliced = out[:limit]
    if not any(p["link_type"] == "no_link" for p in sliced):
        sliced.append({"anchor": "", "target_url": "", "link_type": "no_link"})
    return sliced


def _authority_site(
    provider: str,
    *,
    role: str = "support_hub",
    target_money_site: str = "",
    target_keyword_cluster: str = "",
    account_profile: str = "default",
    domain_or_url: str = "",
    status: str = "planned",
    authority_score: int = 0,
    published_urls: list[str] | None = None,
    linked_targets: list[str] | None = None,
) -> dict[str, Any]:
    meta = PROVIDERS.get(provider, {"provider_type": "manual", "label": provider})
    return {
        "authority_id": f"ame-auth-{uuid.uuid4().hex[:10]}",
        "provider": provider,
        "provider_type": meta.get("provider_type", "manual"),
        "account_profile": account_profile,
        "domain_or_url": domain_or_url,
        "role": role if role in ROLES else "support_hub",
        "target_money_site": target_money_site,
        "target_keyword_cluster": target_keyword_cluster,
        "status": status,
        "authority_score": authority_score,
        "last_publish_at": "",
        "published_urls": published_urls or [],
        "linked_targets": linked_targets or [],
        "created_at": _now(),
    }


def compute_authority_score(site: dict[str, Any]) -> int:
    score = 30
    score += min(25, len(site.get("published_urls") or []) * 8)
    score += min(15, site.get("publish_count", 0) * 3)
    if site.get("index_status") == "indexed":
        score += 15
    if site.get("rank_watcher_signal"):
        score += min(15, int(site.get("rank_watcher_signal") or 0))
    score += min(10, int(site.get("topical_relevance") or 0))
    score += min(10, int(site.get("freshness") or 0))
    score += min(10, int(site.get("provider_trust") or 0))
    score += min(10, int(site.get("link_diversity") or 0))
    outbound = int(site.get("outbound_balance") or 50)
    score += min(10, outbound // 10)
    return max(0, min(100, score))


def create_site_plan(
    keyword: str,
    *,
    money_site: str = "",
    project_id: str = "",
    network_id: str = "",
    mesh_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    kw = (keyword or "").strip()
    if not kw:
        return {"success": False, "error": "keyword gerekli"}

    settings = get_settings()
    money = (money_site or settings.get("default_money_site") or "").strip()
    counts = dict(DEFAULT_MESH_COUNTS)
    if mesh_counts:
        counts.update(mesh_counts)

    link_policy = generate_link_policy(kw, money)
    items: list[dict] = []
    for provider, count in counts.items():
        if count <= 0 or provider not in PROVIDERS:
            continue
        meta = PROVIDERS[provider]
        for i in range(count):
            title = f"{kw} — {meta['label']}" + (f" #{i + 1}" if count > 1 else "")
            items.append({
                "item_id": f"ame-item-{uuid.uuid4().hex[:8]}",
                "provider": provider,
                "provider_type": meta["provider_type"],
                "title": title,
                "role": "blog_hub" if provider in ("blogger", "tumblr", "medium", "devto") else "support_hub",
                "status": "planned",
                "link_policy": link_policy[i % len(link_policy)] if link_policy else {"link_type": "no_link"},
            })

    plan_id = f"ame-plan-{uuid.uuid4().hex[:10]}"
    plan = {
        "plan_id": plan_id,
        "keyword": kw,
        "target_money_site": money,
        "project_id": project_id,
        "network_id": network_id or settings.get("default_network_id", ""),
        "items": items,
        "link_policy": link_policy,
        "mesh_counts": counts,
        "created_at": _now(),
    }

    st = _load_state()
    st.setdefault("mesh_plans", []).insert(0, plan)
    st["mesh_plans"] = st["mesh_plans"][:200]
    st.setdefault("link_policies", []).insert(0, {"plan_id": plan_id, "policies": link_policy, "at": _now()})
    _append_history(st, {"type": "mesh_plan_created", "plan_id": plan_id, "keyword": kw, "at": _now()})
    _save_state(st)

    _record_brain("mesh_plan_created", keyword=kw, domain=money, result={"plan_id": plan_id, "items": len(items)}, reason=f"Mesh plan: {kw}")
    _audit_log("mesh_plan_created", plan_id=plan_id, keyword=kw, money_site=money, item_count=len(items))

    opp_hint = _opportunity_mesh_hint(project_id, kw)
    defense_hint = _serp_defense_mesh_hint(project_id, kw)
    gap_hint = _crawl_gap_authority_hint(project_id)

    return {
        "success": True,
        "plan": plan,
        "opportunity_hint": opp_hint,
        "defense_hint": defense_hint,
        "crawl_gap_hint": gap_hint,
    }


def _opportunity_mesh_hint(project_id: str, keyword: str) -> dict[str, Any]:
    try:
        from app.moduller.opportunity_engine import _get_cached_opportunities
        opps = _get_cached_opportunities(project_id, "")
        for o in opps:
            okw = (o.get("keyword") or "").lower()
            if keyword.lower() in okw or okw in keyword.lower():
                return {"found": True, "opportunity_score": o.get("opportunity_score"), "item": o}
        return {"found": False}
    except Exception as exc:
        return {"found": False, "error": str(exc)}


def _serp_defense_mesh_hint(project_id: str, keyword: str) -> dict[str, Any]:
    if not project_id or not keyword:
        return {"found": False}
    try:
        from app.moduller.serp_defense_engine import analyze_keyword
        res = analyze_keyword(keyword, project_id=project_id)
        if not res.get("success"):
            return {"found": False, "error": res.get("error")}
        report = res["report"]
        needs_boost = report.get("pressure_level") in ("HIGH", "CRITICAL") or report.get("fortress_score", 100) < 55
        actions = [a.get("action") for a in report.get("recommended_actions") or []]
        return {
            "found": True,
            "needs_authority_boost": needs_boost or "support_network_boost" in actions or "publisher_boost" in actions,
            "pressure_level": report.get("pressure_level"),
            "fortress_score": report.get("fortress_score"),
        }
    except Exception as exc:
        return {"found": False, "error": str(exc)}


def _crawl_gap_authority_hint(project_id: str) -> dict[str, Any]:
    try:
        from app.moduller.crawl_gap_engine import _latest_analysis
        a = _latest_analysis(project_id)
        if not a:
            return {"found": False}
        gaps = a.get("gaps") or {}
        auth_gaps = gaps.get("authority_gaps") or []
        return {"found": bool(auth_gaps), "authority_gap_count": len(auth_gaps), "gaps": auth_gaps[:5]}
    except Exception as exc:
        return {"found": False, "error": str(exc)}


def create_publisher_plan(
    plan_id: str = "",
    keyword: str = "",
    *,
    money_site: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    st = _load_state()
    plan = None
    if plan_id:
        plan = next((p for p in st.get("mesh_plans") or [] if p.get("plan_id") == plan_id), None)
    if not plan and keyword:
        res = create_site_plan(keyword, money_site=money_site, project_id=project_id)
        if not res.get("success"):
            return res
        plan = res["plan"]

    if not plan:
        return {"success": False, "error": "plan_id veya keyword gerekli"}

    api_items = [it for it in plan.get("items") or [] if PROVIDERS.get(it.get("provider"), {}).get("provider_type") == "api"]
    browser_items = [it for it in plan.get("items") or [] if PROVIDERS.get(it.get("provider"), {}).get("provider_type") == "browser"]
    manual_items = [it for it in plan.get("items") or [] if PROVIDERS.get(it.get("provider"), {}).get("provider_type") == "manual"]

    pub_plan_id = f"ame-pub-{uuid.uuid4().hex[:10]}"
    pub_plan = {
        "publisher_plan_id": pub_plan_id,
        "mesh_plan_id": plan.get("plan_id"),
        "api_items": api_items,
        "browser_items": browser_items,
        "manual_items": manual_items,
        "created_at": _now(),
    }
    plan["publisher_plan"] = pub_plan
    _save_state(st)
    return {"success": True, "publisher_plan": pub_plan, "plan": plan}


def _duplicate_blocked(fingerprint: str, provider: str) -> bool:
    settings = get_settings()
    if not settings.get("duplicate_content_block", True):
        return False
    st = _load_state()
    for site in st.get("authority_sites") or []:
        if site.get("content_fingerprint") == fingerprint and site.get("provider") == provider:
            return True
    for task in st.get("google_sites_tasks") or []:
        if task.get("content_fingerprint") == fingerprint:
            return True
    return False


def _build_content_html(title: str, keyword: str, link: dict[str, Any]) -> str:
    parts = [f"<h1>{title}</h1>", f"<p>{keyword} hakkında güncel rehber içeriği.</p>"]
    if link.get("link_type") != "no_link" and link.get("target_url"):
        parts.append(f'<p><a href="{link["target_url"]}">{link.get("anchor") or link["target_url"]}</a></p>')
    return "\n".join(parts)


def register_external_publish(
    provider: str,
    *,
    url: str,
    keyword: str = "",
    money_site: str = "",
    role: str = "support_hub",
    network_id: str = "",
    repo_name: str = "",
) -> dict[str, Any]:
    """Harici worker (github_pages_worker vb.) yayın sonrası authority kaydı."""
    st = _load_state()
    site = _authority_site(
        provider,
        role=role,
        target_money_site=money_site,
        target_keyword_cluster=keyword,
        domain_or_url=url,
        status="published",
        published_urls=[url] if url else [],
    )
    site["publish_count"] = 1
    site["authority_score"] = compute_authority_score({**site, "publish_count": 1, "provider_trust": 75})
    site["last_publish_at"] = _now()
    if repo_name:
        site["metadata"] = {"repo_name": repo_name}
    st.setdefault("authority_sites", []).append(site)
    _save_state(st)
    sn = _register_support_network_source(url, role, network_id, keyword)
    rw = {}
    if get_settings().get("auto_track_rank_watcher", True):
        rw = _track_rank_watcher(url, keyword, provider)
    return {"success": True, "authority_id": site["authority_id"], "support_network": sn, "rank_watcher": rw}


def _register_support_network_source(domain_or_url: str, role: str, network_id: str, keyword: str) -> dict[str, Any]:
    settings = get_settings()
    if not settings.get("auto_register_support_network", True):
        return {"success": False, "skipped": True}
    host = urlparse(domain_or_url if "://" in domain_or_url else f"https://{domain_or_url}").netloc or domain_or_url
    entry = {"domain": host, "role": role, "source": "authority_mesh_engine", "keyword": keyword, "at": _now()}
    st = _load_state()
    st.setdefault("support_network_sources", []).insert(0, entry)
    st["support_network_sources"] = st["support_network_sources"][:500]
    _save_state(st)
    if network_id:
        try:
            from app.moduller.network_replicator import add_domain
            return add_domain(network_id, host, role=role)
        except Exception as exc:
            return {"success": False, "error": str(exc), "local_registered": True}
    return {"success": True, "local_registered": True, "domain": host}


def _track_rank_watcher(url: str, keyword: str, provider: str) -> dict[str, Any]:
    if not url or not keyword:
        return {"success": False, "skipped": True}
    try:
        from app.moduller.rank_index_watcher import register_project, track_keyword
        domain = urlparse(url).netloc
        if not domain:
            return {"success": False, "error": "domain_missing"}
        pid = f"ame-{provider}-{uuid.uuid4().hex[:8]}"
        register_project(pid, domain, source=f"authority_mesh:{provider}")
        return track_keyword(keyword, domain, project_id=pid)
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def process_plan(plan_id: str, *, auto_publish: bool = True) -> dict[str, Any]:
    st = _load_state()
    plan = next((p for p in st.get("mesh_plans") or [] if p.get("plan_id") == plan_id), None)
    if not plan:
        return {"success": False, "error": "plan_not_found"}

    results: list[dict] = []
    keyword = plan.get("keyword", "")
    money = plan.get("target_money_site", "")
    network_id = plan.get("network_id", "")

    for item in plan.get("items") or []:
        provider = item.get("provider", "")
        meta = PROVIDERS.get(provider, {})
        ptype = meta.get("provider_type", "manual")
        title = item.get("title", keyword)
        fp = _content_fingerprint(title, provider, keyword)

        if _duplicate_blocked(fp, provider):
            results.append({**item, "success": False, "error": "duplicate_content_blocked"})
            continue

        if ptype == "api":
            channel = meta.get("publisher_channel")
            if provider == "github_pages":
                try:
                    from app.moduller.github_pages_worker import create_site_from_mesh_item
                    link = item.get("link_policy") or {}
                    ghp = create_site_from_mesh_item(
                        title=title,
                        keyword=keyword,
                        money_site=money,
                        role=item.get("role", "support_hub"),
                        link_policy=link,
                        network_id=network_id,
                    )
                    if ghp.get("success") or ghp.get("site", {}).get("status") in ("published", "pages_enabled", "repo_created"):
                        results.append({**item, **ghp})
                    else:
                        results.append({**item, "success": False, **ghp})
                        _record_brain("publish_failed", keyword=keyword, result=ghp, reason="github_pages")
                except Exception as exc:
                    results.append({**item, "success": False, "error": str(exc)})
                    _record_brain("publish_failed", keyword=keyword, result={"error": str(exc)}, reason="github_pages")
                continue
            if not channel:
                site = _authority_site(provider, role=item.get("role", "support_hub"), target_money_site=money,
                                       target_keyword_cluster=keyword, status="review_required")
                site["content_fingerprint"] = fp
                site["manual_checklist"] = [f"{provider} API entegrasyonu yok — manuel yayın"]
                st.setdefault("authority_sites", []).append(site)
                results.append({**item, "success": True, "status": "review_required", "authority_id": site["authority_id"]})
                continue
            ready, err = _publisher_channel_ready(channel)
            if not ready:
                results.append({**item, "success": False, "error": "provider_missing", "message": err})
                continue
            link = item.get("link_policy") or {}
            html = _build_content_html(title, keyword, link)
            try:
                from app.moduller.publisher_hub import enqueue, publish_item
                enq = enqueue({
                    "title": title,
                    "content_html": html,
                    "keyword": keyword,
                    "source": "authority_mesh_engine",
                    "channels": [channel],
                })
                if not enq.get("success"):
                    results.append({**item, "success": False, **enq})
                    _record_brain("publish_failed", keyword=keyword, result=enq, reason=f"{provider} enqueue fail")
                    continue
                pub = {"status": "queued", "publish_id": enq["publish_id"]}
                if auto_publish:
                    pub = publish_item(enq["publish_id"], channels=[channel])
                status = pub.get("status", "failed")
                url = ""
                for ch_res in (pub.get("channel_results") or {}).values():
                    if isinstance(ch_res, dict) and ch_res.get("url"):
                        url = ch_res["url"]
                site = _authority_site(provider, role=item.get("role", "support_hub"), target_money_site=money,
                                       target_keyword_cluster=keyword, domain_or_url=url or "",
                                       status="published" if status == "published" else pub.get("status", "failed"),
                                       published_urls=[url] if url else [])
                site["content_fingerprint"] = fp
                site["publish_count"] = 1 if status == "published" else 0
                site["authority_score"] = compute_authority_score(site)
                site["last_publish_at"] = _now() if status == "published" else ""
                st.setdefault("authority_sites", []).append(site)
                if url:
                    _register_support_network_source(url, item.get("role", "support_hub"), network_id, keyword)
                    if get_settings().get("auto_track_rank_watcher", True):
                        _track_rank_watcher(url, keyword, provider)
                event = "publish_success" if status == "published" else "review_required"
                _record_brain(event, keyword=keyword, domain=url, result={"provider": provider, "publish_id": enq["publish_id"]}, reason=title)
                results.append({**item, "success": status in ("published", "queued", "review_required"), "publish": pub, "authority_id": site["authority_id"]})
            except Exception as exc:
                results.append({**item, "success": False, "error": str(exc)})
                _record_brain("publish_failed", keyword=keyword, result={"error": str(exc)}, reason=provider)

        elif ptype == "browser":
            if provider == "google_sites":
                task_res = create_google_site_task(
                    site_title=title,
                    target_keyword=keyword,
                    target_money_site=money,
                    account_profile=item.get("account_profile", "default"),
                    link_policy=item.get("link_policy"),
                    content_fingerprint=fp,
                )
                results.append({**item, **task_res})
            else:
                site = _authority_site(provider, role=item.get("role", "support_hub"), target_money_site=money,
                                       target_keyword_cluster=keyword, status="review_required")
                site["content_fingerprint"] = fp
                site["manual_checklist"] = [f"{provider} browser automation — task queue veya manuel yayın"]
                st.setdefault("authority_sites", []).append(site)
                results.append({**item, "success": True, "status": "review_required", "authority_id": site["authority_id"]})
        else:
            site = _authority_site(provider, role=item.get("role", "support_hub"), target_money_site=money,
                                   target_keyword_cluster=keyword, status="review_required")
            site["manual_checklist"] = ["Manuel review gerekli"]
            st.setdefault("authority_sites", []).append(site)
            results.append({**item, "success": True, "status": "review_required", "authority_id": site["authority_id"]})

    plan["processed_at"] = _now()
    plan["process_results"] = results
    _append_history(st, {"type": "plan_processed", "plan_id": plan_id, "results_count": len(results), "at": _now()})
    _save_state(st)
    success_count = sum(1 for r in results if r.get("success"))
    return {"success": success_count > 0, "plan_id": plan_id, "results": results, "success_count": success_count, "fail_count": len(results) - success_count}


def create_google_site_task(
    *,
    site_title: str = "",
    target_keyword: str = "",
    target_money_site: str = "",
    account_profile: str = "default",
    link_policy: dict | None = None,
    pages: list | None = None,
    content_fingerprint: str = "",
) -> dict[str, Any]:
    title = (site_title or target_keyword or "").strip()
    if not title:
        return {"success": False, "error": "site_title gerekli"}

    settings = get_settings()
    money = (target_money_site or settings.get("default_money_site") or "").strip()
    fp = content_fingerprint or _content_fingerprint(title, "google_sites", target_keyword)

    if _duplicate_blocked(fp, "google_sites"):
        return {"success": False, "error": "duplicate_task_blocked", "message": "Aynı içerik fingerprint mevcut"}

    st = _load_state()
    if settings.get("duplicate_site_block", True):
        for t in st.get("google_sites_tasks") or []:
            if t.get("site_title", "").lower() == title.lower() and t.get("status") not in ("failed",):
                return {"success": False, "error": "duplicate_site_blocked", "message": "Aynı başlıkta Google Sites task var"}

    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:40].strip("-")
    task = {
        "task_id": f"ame-gs-{uuid.uuid4().hex[:10]}",
        "provider": "google_sites",
        "status": "queued",
        "account_profile": account_profile,
        "site_title": title,
        "site_slug": slug,
        "pages": pages or [{"title": title, "body_html": _build_content_html(title, target_keyword, link_policy or {})}],
        "target_money_site": money,
        "target_keyword": target_keyword,
        "link_policy": link_policy or generate_link_policy(target_keyword, money)[0],
        "published_url": None,
        "error": None,
        "content_fingerprint": fp,
        "created_at": _now(),
    }
    st.setdefault("google_sites_tasks", []).insert(0, task)
    st.setdefault("tasks", []).insert(0, task)
    _save_state(st)
    _record_brain("google_sites_task_created", keyword=target_keyword, domain=money, result={"task_id": task["task_id"]}, reason=title)
    _audit_log("google_sites_task_created", task_id=task["task_id"], site_title=title, keyword=target_keyword)
    return {"success": True, "task": task}


def _run_google_sites_browser_worker(task: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.moduller.google_sites_worker import run_task_automation
        return run_task_automation(task)
    except ImportError:
        return {"success": False, "error": "provider_missing", "message": "google_sites_worker modülü yüklenemedi"}


def process_google_sites_task(task_id: str) -> dict[str, Any]:
    st = _load_state()
    task = next((t for t in st.get("google_sites_tasks") or [] if t.get("task_id") == task_id), None)
    if not task:
        task = next((t for t in st.get("tasks") or [] if t.get("task_id") == task_id), None)
    if not task:
        return {"success": False, "error": "task_not_found"}

    if task.get("status") == "published" and task.get("published_url"):
        return {"success": True, "task": task, "note": "already_published"}

    task["status"] = "processing"
    task["updated_at"] = _now()
    _save_state(st)

    worker_res = _run_google_sites_browser_worker(task)
    st = _load_state()
    task = next((t for t in st.get("google_sites_tasks") or [] if t.get("task_id") == task_id), task)

    if worker_res.get("status") == "login_required":
        task["status"] = "login_required"
        task["error"] = worker_res.get("message")
        _record_brain("login_required", keyword=task.get("target_keyword", ""), result={"task_id": task_id}, reason="Google Sites login")
    elif worker_res.get("status") == "published" and worker_res.get("published_url"):
        task["status"] = "published"
        task["published_url"] = worker_res["published_url"]
        task["error"] = None
        url = worker_res["published_url"]
        site = _authority_site("google_sites", role="support_hub", target_money_site=task.get("target_money_site", ""),
                               target_keyword_cluster=task.get("target_keyword", ""), domain_or_url=url,
                               status="published", published_urls=[url])
        site["authority_score"] = compute_authority_score({**site, "publish_count": 1, "provider_trust": 70})
        site["last_publish_at"] = _now()
        st.setdefault("authority_sites", []).append(site)
        _register_support_network_source(url, "support_hub", get_settings().get("default_network_id", ""), task.get("target_keyword", ""))
        if get_settings().get("auto_track_rank_watcher", True):
            _track_rank_watcher(url, task.get("target_keyword", ""), "google_sites")
        _record_brain("publish_success", keyword=task.get("target_keyword", ""), domain=url, result={"task_id": task_id}, reason=task.get("site_title", ""))
    elif worker_res.get("success") and worker_res.get("status") == "review_required":
        task["status"] = "review_required"
        task["error"] = None
        task["worker_result"] = worker_res.get("worker_result")
        _record_brain("review_required", keyword=task.get("target_keyword", ""), result={"task_id": task_id}, reason=task.get("site_title", ""))
    else:
        task["status"] = "failed"
        task["error"] = worker_res.get("message") or worker_res.get("error")
        _record_brain("publish_failed", keyword=task.get("target_keyword", ""), result=worker_res, reason=task.get("site_title", ""))

    task["finished_at"] = _now()
    _append_history(st, {"type": "google_sites_processed", "task_id": task_id, "status": task["status"], "at": _now()})
    _audit_log("google_sites_processed", task_id=task_id, status=task["status"], published_url=task.get("published_url"))
    _save_state(st)
    return {"success": task["status"] in ("published", "review_required", "login_required"), "task": task, "worker": worker_res}


def list_sites(project_id: str = "", keyword: str = "") -> dict[str, Any]:
    st = _load_state()
    sites = list(st.get("authority_sites") or [])
    if keyword:
        kw = keyword.lower()
        sites = [s for s in sites if kw in (s.get("target_keyword_cluster") or "").lower()]
    for s in sites:
        if not s.get("authority_score"):
            s["authority_score"] = compute_authority_score(s)
    return {"success": True, "count": len(sites), "sites": sites}


def list_tasks(limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    tasks = list(st.get("tasks") or [])[:max(1, min(200, limit))]
    return {"success": True, "count": len(tasks), "tasks": tasks}


def get_task(task_id: str) -> dict[str, Any]:
    if not task_id:
        return {"success": False, "error": "task_id gerekli"}
    st = _load_state()
    task = next((t for t in (st.get("tasks") or []) + (st.get("google_sites_tasks") or []) if t.get("task_id") == task_id), None)
    if not task:
        return {"success": False, "error": "task_not_found"}
    return {"success": True, "task": task}


def list_reports() -> dict[str, Any]:
    st = _load_state()
    return {
        "success": True,
        "mesh_plans": len(st.get("mesh_plans") or []),
        "authority_sites": len(st.get("authority_sites") or []),
        "google_sites_tasks": len(st.get("google_sites_tasks") or []),
        "support_network_sources": len(st.get("support_network_sources") or []),
        "history_count": len(st.get("history") or []),
    }


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "overview": dashboard,
        "sites": list_sites,
        "plans": lambda: {"success": True, "plans": _load_state().get("mesh_plans", [])[:50]},
        "tasks": lambda: list_tasks(100),
        "link_policy": lambda: {"success": True, "policies": _load_state().get("link_policies", [])[:50]},
    }
    fn = generators.get(report_type, dashboard)
    payload = fn() if callable(fn) else fn
    path = REPORTS_DIR / f"authority-mesh-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def dashboard() -> dict[str, Any]:
    st = _load_state()
    sites = st.get("authority_sites") or []
    tasks = st.get("google_sites_tasks") or []
    integrations = _integration_status()
    by_provider: dict[str, int] = {}
    for s in sites:
        by_provider[s.get("provider", "?")] = by_provider.get(s.get("provider", "?"), 0) + 1
    published = sum(1 for s in sites if s.get("status") == "published")
    return {
        "success": True,
        "authority_sites_count": len(sites),
        "published_count": published,
        "mesh_plans_count": len(st.get("mesh_plans") or []),
        "recent_mesh_plans": (st.get("mesh_plans") or [])[:20],
        "google_sites_tasks_count": len(tasks),
        "recent_tasks": tasks[:20],
        "queued_tasks": sum(1 for t in tasks if t.get("status") == "queued"),
        "login_required_tasks": sum(1 for t in tasks if t.get("status") == "login_required"),
        "by_provider": by_provider,
        "browser_worker": _browser_worker_status(),
        "integrations": integrations,
        "integration_errors": [k for k, v in integrations.items() if not v.get("ok")],
        "support_network_sources": len(st.get("support_network_sources") or []),
    }


def health() -> dict[str, Any]:
    st = _load_state()
    integrations = _integration_status()
    errors = [{"module": k, "error": v.get("error") or "not ready"} for k, v in integrations.items() if not v.get("ok")]
    return {
        "success": True,
        "module": "authority_mesh_engine",
        "enabled": get_settings().get("enabled", True),
        "providers": {k: v["provider_type"] for k, v in PROVIDERS.items()},
        "integrations": integrations,
        "integration_errors": errors,
        "authority_sites_count": len(st.get("authority_sites") or []),
        "mesh_plans_count": len(st.get("mesh_plans") or []),
        "tasks_count": len(st.get("tasks") or []),
        "browser_worker": _browser_worker_status(),
    }
