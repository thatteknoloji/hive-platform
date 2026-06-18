"""
Crawl & Gap Engine V1 — site crawl ve içerik/entity/FAQ/GEO/cluster gap analizi.

İçerik üretmez; mevcut modülleri okuyarak crawl + gap tespiti yapar.
"""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .scrape_utils import fetch_html, normalize_url, parse_page, robots_allowed, same_domain

logger = logging.getLogger("hive.crawl_gap")

STATE_FILE = Path(__file__).resolve().parent.parent / "crawl_gap_engine_state.json"
OPPORTUNITY_STATE_FILE = Path(__file__).resolve().parent.parent / "opportunity_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

HISTORY_LIMIT = 500
ACTIVE_CRAWLS: set[str] = set()
GEO_LEVELS = ("city", "district", "neighborhood", "region", "nearby")
GEO_KEYWORDS = {
    "city": ("şehir", "il ", " province", " city"),
    "district": ("ilçe", "district", " semt"),
    "neighborhood": ("mahalle", "neighborhood", " sokak", " cadde"),
    "region": ("bölge", "region", " kıyı", " sahil"),
    "nearby": ("yakın", "nearby", " çevre", " komşu", " ulaşım"),
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": True,
    "max_pages_per_domain": 100,
    "max_crawl_depth": 3,
    "crawl_timeout_seconds": 20,
    "respect_robots_txt": True,
    "allow_competitor_crawl": True,
    "critical_gap_threshold": 65,
    "auto_send_to_opportunity": False,
    "auto_send_to_serp_defense": False,
    "export_to_opportunity_on_analyze": False,
}

GAP_TYPES = ("entity", "faq", "geo", "cluster", "ai", "authority")

ACTION_TYPES = (
    "new_faq", "new_entity", "new_geo_page", "new_cluster",
    "new_astro_site", "new_support_site", "new_publisher_content",
    "content_refresh", "internal_link_plan",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for key, default in (
                    ("settings", dict(DEFAULT_SETTINGS)),
                    ("jobs", []),
                    ("analyses", {}),
                    ("domain_analyses", {}),
                    ("project_analyses", {}),
                    ("competitor_analyses", {}),
                    ("gap_reports", {}),
                    ("latest", {}),
                    ("crawl_history", []),
                    ("gap_history", []),
                    ("domains", {}),
                    ("exportable_opportunities", []),
                ):
                    data.setdefault(key, default if not isinstance(default, dict) else dict(default))
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "jobs": [],
        "analyses": {},
        "domain_analyses": {},
        "project_analyses": {},
        "competitor_analyses": {},
        "gap_reports": {},
        "latest": {},
        "crawl_history": [],
        "gap_history": [],
        "domains": {},
        "exportable_opportunities": [],
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


def _append_history(state: dict[str, Any], key: str, entry: dict[str, Any]) -> None:
    lst = state.setdefault(key, [])
    lst.insert(0, entry)
    state[key] = lst[:HISTORY_LIMIT]


def _record_brain(event_type: str, *, project_id: str = "", domain: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            "module_action",
            "crawl_gap_engine",
            project_id=project_id,
            domain=domain,
            result=result or {},
            reason=reason,
            metadata={"engine": "crawl_gap_engine", "crawl_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain record: %s", exc)


def _host_key(domain: str) -> str:
    return urlparse(normalize_url(domain)).netloc.lower().replace("www.", "")


def _url_crawl_allowed(url: str) -> tuple[bool, str | None]:
    parsed = urlparse(normalize_url(url))
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "invalid_host"
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return False, "private_ip_blocked"
    if host.endswith(".local") or host.endswith(".internal"):
        return False, "private_ip_blocked"
    try:
        for info in socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False, "private_ip_blocked"
    except socket.gaierror:
        pass
    return True, None


def _fetch_page(url: str) -> tuple[str | None, str | None]:
    settings = get_settings()
    allowed, reason = _url_crawl_allowed(url)
    if not allowed:
        return None, reason or "url_blocked"
    target = normalize_url(url)
    if settings.get("respect_robots_txt", True):
        ok, robots_err = robots_allowed(target)
        if not ok:
            return None, robots_err or "robots.txt engeli"
    return fetch_html(target)


def _build_gap_item(
    gap_type: str,
    title: str,
    description: str,
    *,
    our_coverage: int = 0,
    competitor_coverage: int = 0,
    evidence: list | None = None,
    recommended_action: str = "",
) -> dict[str, Any]:
    importance = min(100, max(0, competitor_coverage * 12 + max(0, 100 - our_coverage) // 3))
    difficulty = min(100, max(20, 35 + our_coverage // 3))
    estimated_gain = max(0, min(100, importance - difficulty // 3))
    overall = int(round(importance * 0.45 + estimated_gain * 0.35 + max(0, 100 - difficulty) * 0.20))
    return {
        "gap_id": f"cge-gap-{uuid.uuid4().hex[:10]}",
        "type": gap_type,
        "title": title,
        "description": description,
        "competitor_evidence": evidence or [],
        "our_coverage": our_coverage,
        "competitor_coverage": competitor_coverage,
        "importance_score": importance,
        "difficulty_score": difficulty,
        "estimated_gain": estimated_gain,
        "overall_gap_score": overall,
        "recommended_action": recommended_action,
    }


def _start_job(job_type: str, domain: str = "", project_id: str = "") -> dict[str, Any]:
    job_id = f"cge-job-{uuid.uuid4().hex[:10]}"
    job = {
        "job_id": job_id,
        "type": job_type,
        "domain": domain,
        "project_id": project_id,
        "status": "running",
        "started_at": _now(),
        "finished_at": "",
        "pages_crawled": 0,
        "errors": [],
    }
    st = _load_state()
    st.setdefault("jobs", []).insert(0, job)
    st["jobs"] = st["jobs"][:200]
    _save_state(st)
    return job


def _finish_job(job_id: str, status: str, *, pages_crawled: int = 0, errors: list | None = None, result: dict | None = None) -> dict[str, Any]:
    st = _load_state()
    job = next((j for j in st.get("jobs") or [] if j.get("job_id") == job_id), None)
    if not job:
        return {"success": False, "error": "job_not_found"}
    job["status"] = status
    job["finished_at"] = _now()
    job["pages_crawled"] = pages_crawled
    if errors:
        job["errors"] = errors
    if result:
        job["result"] = result
    _save_state(st)
    return job


_INTEGRATION_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_INTEGRATION_TTL_SEC = 90


def _integration_status() -> dict[str, Any]:
    import time
    now = time.monotonic()
    cached = _INTEGRATION_CACHE.get("data")
    if cached is not None and (now - _INTEGRATION_CACHE["at"]) < _INTEGRATION_TTL_SEC:
        return dict(cached)

    checks: dict[str, Any] = {}

    def _chk(name: str, fn):
        try:
            res = fn()
            ok = bool(res.get("success", True)) if isinstance(res, dict) else bool(res)
            checks[name] = {"ok": ok, "detail": res}
        except Exception as exc:
            checks[name] = {"ok": False, "error": str(exc)}

    _chk("support_network_engine", lambda: __import__(
        "app.moduller.support_network_engine", fromlist=["health"]
    ).health())
    _chk("publisher_hub", lambda: __import__(
        "app.moduller.publisher_hub", fromlist=["health_summary"]
    ).health_summary())
    _chk("rank_index_watcher", lambda: __import__(
        "app.moduller.rank_index_watcher", fromlist=["health"]
    ).health())
    _chk("entity_geo_graph", lambda: __import__(
        "app.moduller.entity_geo_graph", fromlist=["health"]
    ).health())
    _chk("opportunity_engine", lambda: __import__(
        "app.moduller.opportunity_engine", fromlist=["health"]
    ).health())
    _chk("serp_defense_engine", lambda: __import__(
        "app.moduller.serp_defense_engine", fromlist=["health"]
    ).health())
    _chk("hive_brain_engine", lambda: __import__(
        "app.moduller.hive_brain_engine", fromlist=["health"]
    ).health())

    try:
        from app.moduller.rank_index_watcher import _dataforseo_configured
        checks["dataforseo_ai"] = {
            "ok": _dataforseo_configured(),
            "error": None if _dataforseo_configured() else "provider_missing — AI Overview gap için DataForSEO gerekli",
        }
    except Exception as exc:
        checks["dataforseo_ai"] = {"ok": False, "error": str(exc)}

    _INTEGRATION_CACHE["at"] = now
    _INTEGRATION_CACHE["data"] = checks
    return checks


def _extract_schema(soup_html: str) -> list[dict[str, Any]]:
    schemas: list[dict] = []
    for m in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', soup_html or "", re.I | re.S):
        try:
            data = json.loads(m.group(1).strip())
            if isinstance(data, list):
                schemas.extend(data)
            elif isinstance(data, dict):
                schemas.append(data)
        except json.JSONDecodeError:
            continue
    return schemas[:20]


def _extract_dates(soup_html: str) -> dict[str, str]:
    dates: dict[str, str] = {}
    for prop, key in (
        ("article:published_time", "publish_date"),
        ("datePublished", "publish_date"),
        ("article:modified_time", "updated_date"),
        ("dateModified", "updated_date"),
    ):
        m = re.search(rf'{prop}["\']?\s*content=["\']([^"\']+)', soup_html or "", re.I)
        if m and key not in dates:
            dates[key] = m.group(1)[:30]
    for tag in re.finditer(r"<time[^>]+datetime=[\"']([^\"']+)", soup_html or "", re.I):
        if "publish_date" not in dates:
            dates["publish_date"] = tag.group(1)[:30]
        break
    return dates


def _extract_faqs(schemas: list[dict], headings: list[dict], plain: str) -> list[str]:
    faqs: list[str] = []
    for sch in schemas:
        if sch.get("@type") in ("FAQPage", "Question"):
            for ent in sch.get("mainEntity") or []:
                if isinstance(ent, dict):
                    q = ent.get("name") or ent.get("text")
                    if q:
                        faqs.append(str(q)[:240])
    for h in headings:
        t = h.get("text", "")
        if "?" in t and len(t) > 8:
            faqs.append(t[:240])
    for m in re.finditer(r"(?:Sıkça Sorulan|S\.S\.S|FAQ)[:\s]+(.{10,120})", plain or "", re.I):
        faqs.append(m.group(1).strip())
    return list(dict.fromkeys(faqs))[:40]


def _extract_entities(schemas: list[dict], headings: list[dict], title: str) -> list[str]:
    entities: list[str] = []
    entity_types = {"LocalBusiness", "Restaurant", "Place", "Organization", "Product", "Event", "Person"}
    for sch in schemas:
        if sch.get("@type") in entity_types:
            name = sch.get("name")
            if name:
                entities.append(str(name)[:120])
    for h in headings:
        if h.get("level") in ("h1", "h2") and 3 < len(h.get("text", "")) < 80:
            entities.append(h["text"])
    if title:
        entities.append(title[:120])
    return list(dict.fromkeys(entities))[:50]


def _extract_videos(soup_html: str, page_url: str) -> list[dict[str, str]]:
    videos: list[dict] = []
    for m in re.finditer(r'<(?:video|iframe)[^>]+src=["\']([^"\']+)', soup_html or "", re.I):
        src = m.group(1)
        if "youtube" in src or "vimeo" in src or src.endswith((".mp4", ".webm")):
            videos.append({"src": src, "page": page_url})
        if len(videos) >= 10:
            break
    return videos


def _extract_meta_robots(soup_html: str) -> dict[str, Any]:
    noindex = False
    canonical = ""
    m = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', soup_html or "", re.I)
    if m and "noindex" in m.group(1).lower():
        noindex = True
    c = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)', soup_html or "", re.I)
    if c:
        canonical = c.group(1).strip()
    return {"noindex": noindex, "canonical": canonical}


def _enrich_page(html: str, url: str) -> dict[str, Any]:
    parsed = parse_page(html, url)
    schemas = _extract_schema(html)
    dates = _extract_dates(html)
    meta_robots = _extract_meta_robots(html)
    h1 = [h["text"] for h in parsed.get("headings") or [] if h.get("level") == "h1"]
    h2 = [h["text"] for h in parsed.get("headings") or [] if h.get("level") == "h2"]
    h3 = [h["text"] for h in parsed.get("headings") or [] if h.get("level") == "h3"]
    plain = parsed.get("text_excerpt") or ""
    faqs = _extract_faqs(schemas, parsed.get("headings") or [], plain)
    entities = _extract_entities(schemas, parsed.get("headings") or [], parsed.get("title", ""))
    videos = _extract_videos(html, url)
    schema_types = list({s.get("@type") for s in schemas if s.get("@type")})
    outbound = [l["href"] for l in parsed.get("links") or [] if not same_domain(url, l.get("href", ""))]
    return {
        **parsed,
        "url": url,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "schema": schemas,
        "schema_types": schema_types,
        "entities": entities,
        "faqs": faqs,
        "has_faq": bool(faqs),
        "internal_links": parsed.get("internal_links") or [],
        "outbound_links": outbound[:40],
        "images": parsed.get("images") or [],
        "videos": videos,
        "publish_date": dates.get("publish_date", ""),
        "updated_date": dates.get("updated_date", ""),
        "canonical": meta_robots.get("canonical", ""),
        "noindex": meta_robots.get("noindex", False),
    }


def crawl_site(domain: str, *, role: str = "own", max_pages: int | None = None, depth: int | None = None, job_id: str = "") -> dict[str, Any]:
    settings = get_settings()
    if role == "competitor" and not settings.get("allow_competitor_crawl", True):
        return {"success": False, "error": "competitor_crawl_disabled", "message": "Rakip crawl ayarlardan kapalı"}

    start = normalize_url(domain)
    if not start:
        return {"success": False, "error": "domain_gecersiz", "message": "Geçerli domain/URL gerekli"}

    ok, block_reason = _url_crawl_allowed(start)
    if not ok:
        return {"success": False, "error": block_reason or "url_blocked", "message": "Private/localhost URL crawl engellendi"}

    host = _host_key(start)
    if host in ACTIVE_CRAWLS:
        return {"success": False, "error": "crawl_in_progress", "message": f"Aynı domain için crawl zaten çalışıyor: {host}"}

    page_limit = max(1, min(500, int(max_pages or settings.get("max_pages_per_domain") or 100)))
    depth_limit = max(1, min(5, int(depth or settings.get("max_crawl_depth") or 3)))

    ACTIVE_CRAWLS.add(host)
    _record_brain("crawl_started", domain=start, result={"role": role, "job_id": job_id}, reason=f"Crawl başladı: {host}")

    queue: list[tuple[str, int]] = [(start, 0)]
    visited: set[str] = set()
    pages: list[dict] = []
    errors: list[dict] = []

    try:
        while queue and len(pages) < page_limit:
            cur, d = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)

            html, err = _fetch_page(cur)
            if err or not html:
                errors.append({"url": cur, "error": err or "fetch_failed"})
                continue

            try:
                page = _enrich_page(html, cur)
                page["role"] = role
                page["domain"] = urlparse(start).netloc
                pages.append(page)
            except Exception as exc:
                errors.append({"url": cur, "error": str(exc)})
                continue

            if d < depth_limit:
                for link in page.get("internal_links") or []:
                    link_ok, _ = _url_crawl_allowed(link)
                    if link_ok and link not in visited:
                        queue.append((link, d + 1))
    finally:
        ACTIVE_CRAWLS.discard(host)

    if not pages and errors:
        _record_brain("crawl_failed", domain=start, result={"errors": errors[:5], "job_id": job_id}, reason="Crawl başarısız")
        if job_id:
            _finish_job(job_id, "failed", errors=errors)
        return {
            "success": False,
            "error": "crawl_failed",
            "message": errors[0].get("error", "Site crawl başarısız"),
            "errors": errors,
            "domain": domain,
            "role": role,
        }

    _record_brain("crawl_completed", domain=start, result={"pages_crawled": len(pages), "job_id": job_id}, reason=f"Crawl tamamlandı: {len(pages)} sayfa")
    if job_id:
        _finish_job(job_id, "completed", pages_crawled=len(pages), errors=errors)

    return {
        "success": True,
        "domain": domain,
        "role": role,
        "pages_crawled": len(pages),
        "pages": pages,
        "errors": errors,
        "crawled_at": _now(),
        "job_id": job_id,
    }


def _collect_sources(
    project_id: str = "",
    own_domain: str = "",
    competitor_domains: list[str] | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    sources: list[dict[str, str]] = []
    warnings: list[str] = []

    if own_domain:
        sources.append({"domain": own_domain, "role": "own", "source_type": "owned_site"})

    for dom in competitor_domains or []:
        if dom:
            sources.append({"domain": dom, "role": "competitor", "source_type": "competitor"})

    if project_id:
        try:
            from app.moduller.rank_index_watcher import get_project
            proj = get_project(project_id)
            if proj.get("success"):
                p = proj.get("project") or {}
                dom = p.get("domain") or ""
                if dom and not any(s["domain"] == dom for s in sources):
                    sources.append({"domain": dom, "role": "own", "source_type": "rank_watcher_project"})
        except Exception as exc:
            warnings.append(f"rank_watcher: {exc}")

    try:
        from app.moduller.support_network_engine import list_domains
        res = list_domains()
        for d in res.get("domains") or []:
            dom = d.get("domain") or ""
            if dom:
                sources.append({
                    "domain": dom,
                    "role": "support" if d.get("role") != "primary" else "own",
                    "source_type": "support_network",
                })
    except Exception as exc:
        warnings.append(f"support_network: {exc}")

    try:
        from app.moduller.publisher_hub import scan_sources
        pub = scan_sources()
        for item in pub.get("items") or []:
            url = item.get("url") or item.get("link") or ""
            if url:
                host = urlparse(normalize_url(url)).netloc
                if host:
                    sources.append({"domain": host, "role": "publisher", "source_type": "publisher_hub"})
    except Exception as exc:
        warnings.append(f"publisher_hub: {exc}")

    try:
        from app.moduller.wordpress_manager import site_listele
        wp = site_listele()
        for site in wp.get("siteler") or wp.get("sites") or []:
            url = site.get("url") or site.get("domain") or ""
            if url:
                host = urlparse(normalize_url(url)).netloc or url
                sources.append({"domain": host, "role": "own", "source_type": "wordpress"})
    except Exception as exc:
        warnings.append(f"wordpress: {exc}")

    try:
        from app.moduller.astro_factory import list_projects
        astro = list_projects()
        for p in astro.get("projects") or []:
            dom = p.get("domain") or p.get("url") or ""
            if dom:
                host = urlparse(normalize_url(dom)).netloc or dom
                sources.append({"domain": host, "role": "own", "source_type": "astro_site"})
    except Exception as exc:
        warnings.append(f"astro_factory: {exc}")

    try:
        from app.moduller.blogger_api import list_blogs, is_configured
        if is_configured():
            blogs = list_blogs()
            for b in blogs.get("blogs") or []:
                url = b.get("url") or ""
                if url:
                    sources.append({"domain": urlparse(normalize_url(url)).netloc, "role": "publisher", "source_type": "blogger"})
    except Exception as exc:
        warnings.append(f"blogger: {exc}")

    try:
        from app.moduller.network_replicator import list_networks
        nets = list_networks()
        for net in nets.get("networks") or []:
            for d in net.get("domains") or []:
                dom = d.get("domain") or ""
                if dom:
                    sources.append({"domain": dom, "role": "network", "source_type": "network_replicator"})
    except Exception as exc:
        warnings.append(f"network_replicator: {exc}")

    if project_id:
        try:
            from app.moduller.rank_index_watcher import get_project
            proj = get_project(project_id)
            if proj.get("success"):
                for kw in (proj.get("project") or {}).get("keywords") or []:
                    for row in kw.get("serp_snapshot") or []:
                        url = row.get("url") or row.get("link") or ""
                        if url:
                            host = urlparse(normalize_url(url)).netloc
                            if host and not any(s["domain"] == host for s in sources):
                                sources.append({"domain": host, "role": "competitor", "source_type": "rank_watcher_serp"})
        except Exception as exc:
            warnings.append(f"rank_serp: {exc}")

    try:
        from app.moduller.opportunity_engine import _get_cached_opportunities
        opps = _get_cached_opportunities(project_id, "")
        for o in opps:
            dom = o.get("domain") or o.get("competitor_domain") or ""
            if dom:
                sources.append({"domain": dom, "role": "competitor", "source_type": "opportunity_engine"})
    except Exception as exc:
        warnings.append(f"opportunity_engine: {exc}")

    # dedupe by domain+role
    seen: set[str] = set()
    unique: list[dict] = []
    for s in sources:
        key = f"{s['domain']}:{s['role']}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(s)

    if not unique:
        warnings.append("crawl_source_missing — en az bir domain veya proje gerekli")

    return unique, warnings


def _norm_set(items: list[str]) -> set[str]:
    return {i.lower().strip() for i in items if i and len(i.strip()) > 2}


def _geo_tokens(pages: list[dict]) -> dict[str, set[str]]:
    buckets: dict[str, set[str]] = {k: set() for k in GEO_LEVELS}
    for p in pages:
        text = " ".join([
            p.get("title", ""),
            " ".join(p.get("h2") or []),
            p.get("text_excerpt", "")[:800],
        ]).lower()
        for level, kws in GEO_KEYWORDS.items():
            for kw in kws:
                if kw.strip() in text:
                    for h in p.get("h2") or p.get("h3") or []:
                        if kw.strip() in h.lower():
                            buckets[level].add(h[:100])
        for ent in p.get("entities") or []:
            if any(x in ent.lower() for x in ("mahalle", "ilçe", "bölge", "yakın")):
                buckets["neighborhood"].add(ent[:100])
    return buckets


def _cluster_topics(pages: list[dict]) -> set[str]:
    topics: set[str] = set()
    for p in pages:
        for h in p.get("h2") or []:
            if len(h) > 4:
                topics.add(h.lower().strip())
        if p.get("title"):
            topics.add(p["title"].lower().strip())
    return topics


def _entity_counts(pages: list[dict]) -> Counter:
    c: Counter = Counter()
    for p in pages:
        for e in p.get("entities") or []:
            key = e.lower().strip()
            if len(key) > 2:
                c[key] += 1
    return c


def _faq_counts(pages: list[dict]) -> Counter:
    c: Counter = Counter()
    for p in pages:
        for f in p.get("faqs") or []:
            key = f.lower().strip()
            if len(key) > 5:
                c[key] += 1
    return c


def _authority_gaps(own_pages: list[dict], competitor_pages: list[dict]) -> list[dict]:
    own_internal = sum(len(p.get("internal_links") or []) for p in own_pages)
    comp_internal = sum(len(p.get("internal_links") or []) for p in competitor_pages)
    own_words = sum(int(p.get("word_count") or 0) for p in own_pages)
    comp_words = sum(int(p.get("word_count") or 0) for p in competitor_pages)
    own_out = sum(len(p.get("outbound_links") or []) for p in own_pages)
    comp_out = sum(len(p.get("outbound_links") or []) for p in competitor_pages)

    gaps: list[dict] = []
    if comp_internal > own_internal + 5:
        gaps.append(_build_gap_item(
            "authority", "Internal link yoğunluğu", "Rakip daha güçlü iç link ağına sahip",
            our_coverage=min(100, own_internal), competitor_coverage=min(100, comp_internal),
            evidence=[{"metric": "internal_links", "ours": own_internal, "competitor": comp_internal}],
            recommended_action="internal_link_plan",
        ))
    if comp_words > own_words * 1.3 and comp_words > 500:
        gaps.append(_build_gap_item(
            "authority", "İçerik yoğunluğu", "Rakip daha fazla kelime/hacim ile authority sinyali üretiyor",
            our_coverage=min(100, own_words // 50), competitor_coverage=min(100, comp_words // 50),
            evidence=[{"metric": "word_count", "ours": own_words, "competitor": comp_words}],
            recommended_action="content_refresh",
        ))
    if comp_out > own_out + 3:
        gaps.append(_build_gap_item(
            "authority", "External mention / outbound pattern", "Rakip daha geniş citation/outbound pattern kullanıyor",
            our_coverage=min(100, own_out * 5), competitor_coverage=min(100, comp_out * 5),
            recommended_action="new_publisher_content",
        ))
    return gaps


def _compute_gaps(own_pages: list[dict], competitor_pages: list[dict]) -> dict[str, Any]:
    own_entity_c = _entity_counts(own_pages)
    comp_entity_c = _entity_counts(competitor_pages)
    entity_gaps: list[dict] = []
    for ent, comp_count in comp_entity_c.most_common(60):
        our_count = own_entity_c.get(ent, 0)
        if comp_count <= our_count:
            continue
        gap_score = min(100, (comp_count - our_count) * 10 + 30)
        item = _build_gap_item(
            "entity", f"Entity gap: {ent[:60]}", f"Rakipte {comp_count} kez geçiyor, bizde {our_count}",
            our_coverage=min(100, our_count * 15), competitor_coverage=min(100, comp_count * 15),
            evidence=[{"entity": ent, "competitor_mentions": comp_count, "our_mentions": our_count}],
            recommended_action="new_entity",
        )
        entity_gaps.append({
            "entity": ent,
            "competitor_mentions": comp_count,
            "our_mentions": our_count,
            "gap_score": gap_score,
            "priority": "high" if gap_score >= 60 else "medium",
            **item,
        })

    own_faq_c = _faq_counts(own_pages)
    comp_faq_c = _faq_counts(competitor_pages)
    faq_gaps: list[dict] = []
    for q, comp_count in comp_faq_c.most_common(60):
        our_count = own_faq_c.get(q, 0)
        if our_count >= comp_count:
            continue
        item = _build_gap_item(
            "faq", f"FAQ gap: {q[:60]}", "Rakipte soru var, bizde eksik veya zayıf",
            our_coverage=min(100, our_count * 25), competitor_coverage=min(100, comp_count * 25),
            evidence=[{"question": q, "competitor_count": comp_count, "our_count": our_count}],
            recommended_action="new_faq",
        )
        faq_gaps.append({"question": q, "priority": "high", "found_on": "competitor", **item})

    own_geo = _geo_tokens(own_pages)
    comp_geo = _geo_tokens(competitor_pages)
    geo_gaps: list[dict] = []
    for level in GEO_LEVELS:
        missing = comp_geo[level] - own_geo[level]
        for g in sorted(missing)[:15]:
            item = _build_gap_item(
                "geo", f"GEO gap ({level}): {g[:50]}", f"Rakipte {level} seviyesinde lokasyon kapsamı var",
                our_coverage=20, competitor_coverage=75,
                evidence=[{"location": g, "level": level}],
                recommended_action="new_geo_page",
            )
            geo_gaps.append({"location": g, "level": level, "priority": "high" if level in ("city", "district") else "medium", **item})

    own_topics = _cluster_topics(own_pages)
    comp_topics = _cluster_topics(competitor_pages)
    cluster_gaps: list[dict] = []
    missing_topics = comp_topics - own_topics
    for t in sorted(missing_topics)[:40]:
        gap_type = "pillar" if len(t.split()) <= 3 else "cluster"
        item = _build_gap_item(
            "cluster", f"Cluster gap: {t[:60]}", f"Eksik {'pillar' if gap_type == 'pillar' else 'cluster'} konusu",
            our_coverage=15, competitor_coverage=70,
            evidence=[{"topic": t, "cluster_type": gap_type}],
            recommended_action="new_cluster",
        )
        cluster_gaps.append({"topic": t, "type": gap_type, "priority": "high" if gap_type == "pillar" else "medium", **item})
    if len(own_topics) < 3:
        cluster_gaps.append({"topic": "pillar content", "type": "missing_pillar", "priority": "critical",
                               **_build_gap_item("cluster", "Missing pillar", "Pillar içerik eksik", recommended_action="new_astro_site")})

    authority_gaps = _authority_gaps(own_pages, competitor_pages)

    scored_gaps = entity_gaps + faq_gaps + geo_gaps + cluster_gaps + authority_gaps
    critical_gaps = [g for g in scored_gaps if g.get("overall_gap_score", 0) >= int(get_settings().get("critical_gap_threshold") or 65)]
    quick_wins = sorted(
        [g for g in scored_gaps if g.get("difficulty_score", 100) <= 45 and g.get("estimated_gain", 0) >= 50],
        key=lambda x: x.get("estimated_gain", 0), reverse=True,
    )[:20]

    return {
        "entity_gaps": entity_gaps,
        "faq_gaps": faq_gaps,
        "geo_gaps": geo_gaps,
        "cluster_gaps": cluster_gaps,
        "authority_gaps": authority_gaps,
        "scored_gaps": scored_gaps,
        "critical_gaps": critical_gaps,
        "quick_wins": quick_wins,
        "stats": {
            "own_entities": len(own_entity_c),
            "competitor_entities": len(comp_entity_c),
            "entity_gap_count": len(entity_gaps),
            "faq_gap_count": len(faq_gaps),
            "geo_gap_count": len(geo_gaps),
            "cluster_gap_count": len(cluster_gaps),
            "authority_gap_count": len(authority_gaps),
            "critical_gap_count": len(critical_gaps),
            "quick_win_count": len(quick_wins),
        },
    }


def _page_gap_scores(page: dict, gaps: dict[str, Any]) -> dict[str, int]:
    url = (page.get("url") or "").lower()
    ent_count = len(page.get("entities") or [])
    faq_count = len(page.get("faqs") or [])
    geo_hits = sum(1 for g in gaps.get("geo_gaps") or [] if g.get("location", "").lower() in url)
    internal = len(page.get("internal_links") or [])
    schema_n = len(page.get("schema") or [])
    cluster_hits = sum(1 for c in gaps.get("cluster_gaps") or [] if (c.get("topic") or "").lower() in url)

    entity_gap_score = max(0, min(100, 100 - ent_count * 8))
    faq_gap_score = max(0, min(100, 100 - faq_count * 10))
    geo_gap_score = max(0, min(100, 50 + geo_hits * 15))
    cluster_gap_score = max(0, min(100, 60 + cluster_hits * 10))
    ai_gap_score = max(0, min(100, 70 if not page.get("has_faq") else 40))
    authority_gap_score = max(0, min(100, 100 - schema_n * 12 - min(internal, 10)))
    coverage_score = max(0, min(100, ent_count * 5 + faq_count * 8 + schema_n * 10 + min(internal, 20)))
    overall = int(round(
        coverage_score * 0.20
        + (100 - entity_gap_score) * 0.15
        + (100 - faq_gap_score) * 0.15
        + (100 - geo_gap_score) * 0.12
        + (100 - cluster_gap_score) * 0.12
        + (100 - ai_gap_score) * 0.10
        + (100 - authority_gap_score) * 0.16
    ))
    overall_gap_score = 100 - overall
    return {
        "url": page.get("url"),
        "coverage_score": coverage_score,
        "entity_gap_score": entity_gap_score,
        "faq_gap_score": faq_gap_score,
        "geo_gap_score": geo_gap_score,
        "cluster_gap_score": cluster_gap_score,
        "ai_gap_score": ai_gap_score,
        "authority_gap_score": authority_gap_score,
        "overall_gap_score": overall_gap_score,
    }


def _ai_overview_gaps(keywords: list[str]) -> dict[str, Any]:
    try:
        from app.moduller.rank_index_watcher import _dataforseo_configured, ai_overview
        if not _dataforseo_configured():
            return {
                "success": False,
                "error": "provider_missing",
                "message": "AI Overview gap için DataForSEO yapılandırılmalı",
                "gaps": [],
            }
        gaps: list[dict] = []
        for kw in keywords[:5]:
            res = ai_overview(kw)
            if not res.get("success"):
                continue
            sources = res.get("sources") or []
            gaps.append({
                "keyword": kw,
                "ai_overview_present": bool(res.get("has_ai_overview")),
                "competitor_answer_blocks": len(sources),
                "citation_patterns": [s.get("source") or s.get("url") for s in sources[:5]],
                "our_visibility": "unknown",
                "priority": "high" if res.get("has_ai_overview") else "medium",
            })
        return {"success": True, "gaps": gaps, "count": len(gaps)}
    except Exception as exc:
        return {"success": False, "error": str(exc), "gaps": []}


def _build_action_plan(gaps: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict] = []
    if gaps.get("faq_gaps"):
        actions.append({"action": "new_faq", "count": len(gaps["faq_gaps"]), "priority": "high"})
    if gaps.get("entity_gaps"):
        actions.append({"action": "new_entity", "count": len(gaps["entity_gaps"]), "priority": "high"})
    if gaps.get("geo_gaps"):
        actions.append({"action": "new_geo_page", "count": len(gaps["geo_gaps"]), "priority": "medium"})
    if gaps.get("cluster_gaps"):
        actions.append({"action": "new_cluster", "count": len(gaps["cluster_gaps"]), "priority": "medium"})
    if gaps.get("authority_gaps"):
        for ag in gaps["authority_gaps"]:
            act = ag.get("recommended_action") or "internal_link_plan"
            if act not in [a["action"] for a in actions]:
                actions.append({"action": act, "count": 1, "priority": "medium"})
    if len(gaps.get("entity_gaps") or []) > 10:
        actions.append({"action": "new_support_site", "count": 1, "priority": "low"})
    if gaps.get("faq_gaps") or gaps.get("cluster_gaps"):
        actions.append({"action": "new_publisher_content", "count": 1, "priority": "medium"})
    if any(g.get("type") == "missing_pillar" for g in gaps.get("cluster_gaps") or []):
        actions.append({"action": "new_astro_site", "count": 1, "priority": "low"})
    if gaps.get("critical_gaps"):
        actions.append({"action": "content_refresh", "count": len(gaps["critical_gaps"]), "priority": "high"})
    if gaps.get("authority_gaps"):
        actions.append({"action": "internal_link_plan", "count": 1, "priority": "medium"})
    return actions


def _qie_questions(gaps: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict] = []
    for fg in gaps.get("faq_gaps") or []:
        q = fg.get("question") or fg.get("title", "")
        if not q:
            continue
        intent = "informational" if "nedir" in q.lower() else "comparison" if " mı " in q.lower() else "local"
        engine = "comparison" if intent == "comparison" else "objection" if "?" in q and "nasıl" in q.lower() else "faq"
        out.append({
            "question": q,
            "intent": intent,
            "source": "crawl_gap",
            "recommended_engine": engine,
        })
    return out[:50]


def _content_refresh_recommendations(own_pages: list[dict], gaps: dict[str, Any]) -> list[dict[str, Any]]:
    recs: list[dict] = []
    for p in own_pages:
        score = _page_gap_scores(p, gaps)
        if score.get("overall_gap_score", 0) >= 40:
            recs.append({
                "page_url": p.get("url"),
                "project_id_hint": "",
                "overall_gap_score": score["overall_gap_score"],
                "recommended_actions": ["refresh_content", "add_faq"] if score.get("faq_gap_score", 0) > 60 else ["refresh_content"],
                "plan_only": True,
                "source": "crawl_gap_engine",
            })
    return recs[:30]


def _entity_geo_recommendations(project_id: str, gaps: dict[str, Any]) -> list[dict[str, Any]]:
    recs: list[dict] = []
    for eg in gaps.get("entity_gaps") or []:
        recs.append({
            "recommendation_type": "add_entity_node",
            "entity": eg.get("entity"),
            "gap_score": eg.get("gap_score") or eg.get("overall_gap_score"),
            "project_id": project_id,
            "plan_only": True,
            "source": "crawl_gap_engine",
        })
    for gg in gaps.get("geo_gaps") or []:
        recs.append({
            "recommendation_type": "expand_geo",
            "location": gg.get("location"),
            "level": gg.get("level"),
            "project_id": project_id,
            "plan_only": True,
            "source": "crawl_gap_engine",
        })
    return recs[:40]


def _to_opportunities(gaps: dict[str, Any], project_id: str = "", domain: str = "") -> list[dict[str, Any]]:
    opps: list[dict] = []
    for eg in gaps.get("entity_gaps") or []:
        opps.append({
            "id": f"cge-entity-{uuid.uuid4().hex[:8]}",
            "type": "crawl_gap_opportunity",
            "subtype": "entity_gap",
            "title": f"Entity gap: {(eg.get('entity') or '')[:60]}",
            "source": "crawl_gap_engine",
            "project_id": project_id,
            "domain": domain,
            "keyword": eg.get("entity", ""),
            "opportunity_score": eg.get("overall_gap_score") or 75,
            "traffic_score": 60,
            "difficulty_score": eg.get("difficulty_score") or 40,
            "estimated_gain": eg.get("estimated_gain") or 70,
            "gap_score": eg.get("gap_score"),
            "action_plan": ["new_entity"],
        })
    for fg in gaps.get("faq_gaps") or []:
        opps.append({
            "id": f"cge-faq-{uuid.uuid4().hex[:8]}",
            "type": "crawl_gap_opportunity",
            "subtype": "faq_gap",
            "title": f"FAQ gap: {(fg.get('question') or fg.get('title') or '')[:60]}",
            "source": "crawl_gap_engine",
            "project_id": project_id,
            "domain": domain,
            "keyword": (fg.get("question") or "")[:80],
            "opportunity_score": fg.get("overall_gap_score") or 72,
            "traffic_score": 55,
            "difficulty_score": fg.get("difficulty_score") or 35,
            "estimated_gain": fg.get("estimated_gain") or 65,
            "action_plan": ["new_faq"],
        })
    for gg in gaps.get("geo_gaps") or []:
        opps.append({
            "id": f"cge-geo-{uuid.uuid4().hex[:8]}",
            "type": "crawl_gap_opportunity",
            "subtype": "geo_gap",
            "title": f"GEO gap ({gg.get('level')}): {(gg.get('location') or '')[:50]}",
            "source": "crawl_gap_engine",
            "project_id": project_id,
            "domain": domain,
            "opportunity_score": gg.get("overall_gap_score") or 68,
            "estimated_gain": gg.get("estimated_gain") or 60,
            "action_plan": ["new_geo_page"],
        })
    for cg in gaps.get("cluster_gaps") or []:
        opps.append({
            "id": f"cge-cluster-{uuid.uuid4().hex[:8]}",
            "type": "crawl_gap_opportunity",
            "subtype": cg.get("type", "cluster"),
            "title": f"Cluster gap: {(cg.get('topic') or '')[:60]}",
            "source": "crawl_gap_engine",
            "project_id": project_id,
            "domain": domain,
            "opportunity_score": cg.get("overall_gap_score") or (70 if cg.get("priority") == "high" else 50),
            "action_plan": ["new_cluster"],
        })
    for qw in gaps.get("quick_wins") or []:
        opps.append({
            "id": f"cge-qw-{uuid.uuid4().hex[:8]}",
            "type": "crawl_gap_opportunity",
            "subtype": "quick_win",
            "title": f"Quick win: {(qw.get('title') or '')[:60]}",
            "source": "crawl_gap_engine",
            "project_id": project_id,
            "domain": domain,
            "opportunity_score": qw.get("overall_gap_score") or 80,
            "estimated_gain": qw.get("estimated_gain") or 75,
            "action_plan": [qw.get("recommended_action") or "new_faq"],
        })
    return opps


def _export_to_opportunity_state(project_id: str, opps: list[dict]) -> dict[str, Any]:
    if not opps:
        return {"success": False, "error": "no_opportunities", "message": "Aktarılacak gap fırsatı yok"}
    if not OPPORTUNITY_STATE_FILE.exists():
        return {
            "success": False,
            "error": "opportunity_state_missing",
            "message": "Opportunity Engine state dosyası yok — önce Opportunity analizi çalıştırın",
        }
    try:
        data = json.loads(OPPORTUNITY_STATE_FILE.read_text(encoding="utf-8"))
        key = f"project:{project_id}" if project_id else "latest"
        analyses = data.setdefault("analyses", {})
        block = analyses.setdefault(key, {"opportunities": [], "analyzed_at": _now()})
        existing_ids = {o.get("id") for o in block.get("opportunities") or []}
        merged = list(block.get("opportunities") or [])
        for o in opps:
            if o.get("id") not in existing_ids:
                merged.append(o)
        block["opportunities"] = merged[-500:]
        block["crawl_gap_import_at"] = _now()
        OPPORTUNITY_STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "imported": len(opps), "total": len(block["opportunities"])}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _serp_defense_risks(project_id: str, gaps: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
    critical: list[dict] = []
    threshold = int(get_settings().get("critical_gap_threshold") or 65)
    attack_surface_boost = 0
    if gaps.get("stats", {}).get("entity_gap_count", 0) >= 5:
        critical.append({"type": "entity_gap", "severity": "high", "count": gaps["stats"]["entity_gap_count"]})
        attack_surface_boost += 12
    if gaps.get("stats", {}).get("faq_gap_count", 0) >= 3:
        critical.append({"type": "faq_gap", "severity": "high", "count": gaps["stats"]["faq_gap_count"]})
        attack_surface_boost += 15
    if gaps.get("stats", {}).get("cluster_gap_count", 0) >= 4:
        critical.append({"type": "cluster_gap", "severity": "medium", "count": gaps["stats"]["cluster_gap_count"]})
        attack_surface_boost += 8

    defense_links: list[dict] = []
    if project_id and keywords:
        try:
            from app.moduller.serp_defense_engine import analyze_keyword
            for kw in keywords[:3]:
                res = analyze_keyword(kw, project_id=project_id)
                if res.get("success"):
                    r = res["report"]
                    boosted_as = min(100, int(r.get("attack_surface_score") or 0) + attack_surface_boost)
                    if r.get("pressure_level") in ("HIGH", "CRITICAL") or r.get("fortress_score", 100) < threshold or attack_surface_boost > 0:
                        defense_links.append({
                            "keyword": kw,
                            "fortress_score": r.get("fortress_score"),
                            "pressure_level": r.get("pressure_level"),
                            "attack_surface_score": r.get("attack_surface_score"),
                            "boosted_attack_surface_score": boosted_as,
                            "linked_from": "crawl_gap_critical",
                            "gap_driven": attack_surface_boost > 0,
                        })
        except Exception as exc:
            return {"success": False, "error": str(exc), "critical_gaps": critical, "attack_surface_boost": attack_surface_boost}

    payload = {
        "success": True,
        "critical_gaps": critical,
        "defense_keywords": defense_links,
        "attack_surface_boost": attack_surface_boost,
        "serp_defense_payload": {
            "source": "crawl_gap_engine",
            "project_id": project_id,
            "critical_gap_count": len(gaps.get("critical_gaps") or []),
            "attack_surface_delta": attack_surface_boost,
            "recommended_defense": attack_surface_boost >= 10,
        },
    }
    return payload


def _entity_geo_hints(project_id: str, seed_keyword: str = "") -> tuple[list[dict], list[str]]:
    hints: list[dict] = []
    errs: list[str] = []
    if not project_id:
        return hints, errs
    try:
        from app.moduller.entity_geo_graph import missing_entities
        res = missing_entities(project_id=project_id, seed_keyword=seed_keyword)
        if res.get("success"):
            for m in res.get("missing_entities") or []:
                hints.append({"entity": m.get("entity"), "source": "entity_geo_graph", "type": m.get("type")})
        else:
            errs.append(res.get("error") or "entity_geo_graph okunamadı")
    except Exception as exc:
        errs.append(str(exc))
    return hints, errs


def analyze_domain(
    own_domain: str = "",
    competitor_domains: list[str] | None = None,
    *,
    project_id: str = "",
    export_to_opportunity: bool = False,
) -> dict[str, Any]:
    if not own_domain and not competitor_domains:
        return {"success": False, "error": "domain_gerekli", "message": "own_domain veya competitor_domains gerekli"}

    settings = get_settings()
    job = _start_job("analyze_domain", domain=own_domain, project_id=project_id)
    crawl_results: list[dict] = []
    all_errors: list[dict] = []

    if own_domain:
        cr = crawl_site(own_domain, role="own", job_id=job["job_id"])
        if not cr.get("success"):
            _finish_job(job["job_id"], "failed", errors=cr.get("errors") or [{"error": cr.get("message")}])
            return cr
        crawl_results.append(cr)

    for dom in competitor_domains or []:
        cr = crawl_site(dom, role="competitor", job_id=job["job_id"])
        if cr.get("success"):
            crawl_results.append(cr)
            _record_brain("competitor_analyzed", domain=dom, project_id=project_id, result={"pages": cr.get("pages_crawled")}, reason=f"Rakip analiz: {dom}")
        else:
            all_errors.append({"domain": dom, "error": cr.get("message") or cr.get("error")})

    if not crawl_results:
        _finish_job(job["job_id"], "failed", errors=all_errors)
        return {
            "success": False,
            "error": "crawl_failed",
            "message": "Hiçbir domain crawl edilemedi",
            "errors": all_errors,
            "job_id": job["job_id"],
        }

    own_pages = [p for cr in crawl_results if cr.get("role") == "own" for p in cr.get("pages") or []]
    comp_pages = [p for cr in crawl_results if cr.get("role") == "competitor" for p in cr.get("pages") or []]

    gaps = _compute_gaps(own_pages, comp_pages)
    entity_hints, hint_errs = _entity_geo_hints(project_id)
    for h in entity_hints:
        ent = (h.get("entity") or "").lower()
        if ent and not any(g.get("entity", "").lower() == ent for g in gaps["entity_gaps"]):
            item = _build_gap_item("entity", f"Entity gap: {h.get('entity')}", "Entity GEO Graph önerisi", recommended_action="new_entity")
            gaps["entity_gaps"].append({"entity": h.get("entity"), "priority": "medium", "found_on": h.get("source"), **item})

    keywords = [own_pages[0].get("title", "")[:40]] if own_pages else []
    if project_id:
        try:
            from app.moduller.rank_index_watcher import get_project
            pr = get_project(project_id)
            if pr.get("success"):
                for kw in (pr.get("project") or {}).get("keywords") or []:
                    if kw.get("keyword"):
                        keywords.append(kw["keyword"])
        except Exception:
            pass
    ai_gaps = _ai_overview_gaps(list(dict.fromkeys(keywords))[:5])
    page_scores = [_page_gap_scores(p, gaps) for p in own_pages[:50]]
    actions = _build_action_plan(gaps)
    qie_questions = _qie_questions(gaps)
    refresh_recs = _content_refresh_recommendations(own_pages, gaps)
    geo_recs = _entity_geo_recommendations(project_id, gaps)
    opps = _to_opportunities(gaps, project_id=project_id, domain=own_domain)
    defense = _serp_defense_risks(project_id, gaps, keywords)

    analysis_id = f"cge-{uuid.uuid4().hex[:10]}"
    pages_crawled = sum(c.get("pages_crawled", 0) for c in crawl_results)
    analysis = {
        "analysis_id": analysis_id,
        "job_id": job["job_id"],
        "project_id": project_id,
        "own_domain": own_domain,
        "competitor_domains": competitor_domains or [],
        "crawl_results": [{"domain": c["domain"], "role": c["role"], "pages_crawled": c["pages_crawled"]} for c in crawl_results],
        "pages_crawled_total": pages_crawled,
        "domains_crawled": len(crawl_results),
        "gaps": gaps,
        "ai_gaps": ai_gaps,
        "page_scores": page_scores,
        "action_plan": actions,
        "defense_risks": defense,
        "entity_geo_hints": entity_hints,
        "entity_geo_recommendations": geo_recs,
        "qie_questions": qie_questions,
        "content_refresh_recommendations": refresh_recs,
        "errors": all_errors + [{"source": "entity_geo", "error": e} for e in hint_errs],
        "analyzed_at": _now(),
    }

    st = _load_state()
    key = project_id or own_domain or analysis_id
    st.setdefault("analyses", {})[key] = analysis
    if own_domain:
        st.setdefault("domain_analyses", {})[own_domain] = analysis
    if project_id:
        st.setdefault("project_analyses", {})[project_id] = analysis
    for dom in competitor_domains or []:
        st.setdefault("competitor_analyses", {})[dom] = {"analysis_id": analysis_id, "domain": dom, "linked_analysis": key, "at": _now()}
    st.setdefault("gap_reports", {})[analysis_id] = {"gaps": gaps, "analysis_id": analysis_id, "at": _now()}
    st["latest"] = {"analysis_id": analysis_id, "project_id": project_id, "own_domain": own_domain, "at": _now()}
    st.setdefault("domains", {})[own_domain or key] = {
        "own_domain": own_domain,
        "competitors": competitor_domains or [],
        "last_analysis_id": analysis_id,
        "updated_at": _now(),
    }
    st["exportable_opportunities"] = opps
    _append_history(st, "crawl_history", {"analysis_id": analysis_id, "job_id": job["job_id"], "domains": [c["domain"] for c in crawl_results], "pages_crawled": pages_crawled, "at": _now()})
    _append_history(st, "gap_history", {"analysis_id": analysis_id, "stats": gaps.get("stats"), "gap_count": len(gaps.get("scored_gaps") or []), "at": _now()})
    _save_state(st)

    export_result = None
    auto_opp = export_to_opportunity or settings.get("export_to_opportunity_on_analyze") or settings.get("auto_send_to_opportunity")
    if auto_opp:
        export_result = _export_to_opportunity_state(project_id or "latest", opps)

    if settings.get("auto_send_to_serp_defense") and project_id and defense.get("serp_defense_payload"):
        _record_brain("gap_found", project_id=project_id, domain=own_domain, result=defense["serp_defense_payload"], reason="SERP Defense gap payload üretildi")

    _finish_job(job["job_id"], "completed", pages_crawled=pages_crawled, result={"analysis_id": analysis_id})
    _record_brain("gap_report_created", project_id=project_id, domain=own_domain, result={"analysis_id": analysis_id, "gap_stats": gaps.get("stats"), "job_id": job["job_id"]}, reason="Gap raporu oluşturuldu")
    for g in (gaps.get("critical_gaps") or [])[:10]:
        _record_brain("gap_found", project_id=project_id, domain=own_domain, result={"gap_id": g.get("gap_id"), "type": g.get("type")}, reason=g.get("title", "Kritik gap"))

    return {
        "success": True,
        "analysis": analysis,
        "opportunities": opps,
        "opportunity_export": export_result,
        "job_id": job["job_id"],
    }


def analyze_project(
    project_id: str,
    competitor_domains: list[str] | None = None,
    *,
    export_to_opportunity: bool = False,
) -> dict[str, Any]:
    if not project_id:
        return {"success": False, "error": "project_id gerekli"}

    own_domain = ""
    try:
        from app.moduller.rank_index_watcher import get_project
        res = get_project(project_id)
        if res.get("success"):
            own_domain = (res.get("project") or {}).get("domain") or ""
    except Exception as exc:
        return {"success": False, "error": "rank_watcher_unavailable", "message": str(exc)}

    sources, warnings = _collect_sources(project_id, own_domain, competitor_domains)
    if not sources:
        return {
            "success": False,
            "error": "crawl_source_missing",
            "message": "Crawl kaynağı bulunamadı — domain veya proje yapılandırın",
            "warnings": warnings,
        }

    own = own_domain or next((s["domain"] for s in sources if s["role"] == "own"), "")
    comps = competitor_domains or [s["domain"] for s in sources if s["role"] == "competitor"]
    if not comps:
        comps = [s["domain"] for s in sources if s["role"] == "support"][:2]

    result = analyze_domain(
        own_domain=own,
        competitor_domains=comps[:5] if comps else None,
        project_id=project_id,
        export_to_opportunity=export_to_opportunity,
    )
    if result.get("success") and warnings:
        result.setdefault("warnings", warnings)
    return result


def analyze_competitor(
    competitor_domain: str,
    *,
    own_domain: str = "",
    project_id: str = "",
) -> dict[str, Any]:
    if not competitor_domain.strip():
        return {"success": False, "error": "competitor_domain gerekli"}
    own = own_domain.strip()
    if not own and project_id:
        try:
            from app.moduller.rank_index_watcher import get_project
            res = get_project(project_id)
            if res.get("success"):
                own = (res.get("project") or {}).get("domain") or ""
        except Exception:
            pass
    if not own:
        return {"success": False, "error": "own_domain gerekli", "message": "Karşılaştırma için own domain veya project_id gerekli"}
    return analyze_domain(own_domain=own, competitor_domains=[competitor_domain], project_id=project_id)


def compare_domain(
    own_domain: str,
    competitor_domain: str,
    *,
    project_id: str = "",
) -> dict[str, Any]:
    if not own_domain or not competitor_domain:
        return {"success": False, "error": "own_domain ve competitor_domain gerekli"}
    res = analyze_domain(own_domain=own_domain, competitor_domains=[competitor_domain], project_id=project_id)
    if not res.get("success"):
        return res
    analysis = res["analysis"]
    gaps = analysis.get("gaps") or {}
    return {
        "success": True,
        "own_domain": own_domain,
        "competitor_domain": competitor_domain,
        "comparison": {
            "pages_crawled_own": next((c["pages_crawled"] for c in analysis.get("crawl_results") or [] if c.get("role") == "own"), 0),
            "pages_crawled_competitor": next((c["pages_crawled"] for c in analysis.get("crawl_results") or [] if c.get("role") == "competitor"), 0),
            "gap_stats": gaps.get("stats"),
            "critical_gaps": gaps.get("critical_gaps") or [],
            "quick_wins": gaps.get("quick_wins") or [],
        },
        "analysis_id": analysis.get("analysis_id"),
        "analysis": analysis,
    }


def list_jobs(limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    jobs = list(st.get("jobs") or [])[:max(1, min(200, limit))]
    return {"success": True, "count": len(jobs), "jobs": jobs}


def get_job(job_id: str) -> dict[str, Any]:
    if not job_id:
        return {"success": False, "error": "job_id gerekli"}
    st = _load_state()
    job = next((j for j in st.get("jobs") or [] if j.get("job_id") == job_id), None)
    if not job:
        return {"success": False, "error": "job_not_found"}
    return {"success": True, "job": job}


def list_authority(project_id: str = "", domain: str = "") -> dict[str, Any]:
    a = _latest_analysis(project_id, domain)
    if not a:
        return {"success": False, "error": "analysis_missing", "message": "Önce crawl analizi çalıştırın"}
    gaps = (a.get("gaps") or {}).get("authority_gaps") or []
    return {"success": True, "count": len(gaps), "authority_gaps": gaps}


def _latest_analysis(project_id: str = "", domain: str = "") -> dict[str, Any] | None:
    st = _load_state()
    key = project_id or domain
    if key and key in st.get("analyses", {}):
        return st["analyses"][key]
    analyses = st.get("analyses") or {}
    if analyses:
        return next(iter(analyses.values()))
    return None


def list_entities(project_id: str = "", domain: str = "") -> dict[str, Any]:
    a = _latest_analysis(project_id, domain)
    if not a:
        return {"success": False, "error": "analysis_missing", "message": "Önce crawl analizi çalıştırın"}
    gaps = (a.get("gaps") or {}).get("entity_gaps") or []
    return {"success": True, "count": len(gaps), "entities": gaps}


def list_faqs(project_id: str = "", domain: str = "") -> dict[str, Any]:
    a = _latest_analysis(project_id, domain)
    if not a:
        return {"success": False, "error": "analysis_missing", "message": "Önce crawl analizi çalıştırın"}
    gaps = (a.get("gaps") or {}).get("faq_gaps") or []
    return {"success": True, "count": len(gaps), "faqs": gaps}


def list_geo(project_id: str = "", domain: str = "") -> dict[str, Any]:
    a = _latest_analysis(project_id, domain)
    if not a:
        return {"success": False, "error": "analysis_missing", "message": "Önce crawl analizi çalıştırın"}
    gaps = (a.get("gaps") or {}).get("geo_gaps") or []
    return {"success": True, "count": len(gaps), "geo": gaps}


def list_clusters(project_id: str = "", domain: str = "") -> dict[str, Any]:
    a = _latest_analysis(project_id, domain)
    if not a:
        return {"success": False, "error": "analysis_missing", "message": "Önce crawl analizi çalıştırın"}
    gaps = (a.get("gaps") or {}).get("cluster_gaps") or []
    return {"success": True, "count": len(gaps), "clusters": gaps}


def list_ai(project_id: str = "", domain: str = "") -> dict[str, Any]:
    a = _latest_analysis(project_id, domain)
    if not a:
        return {"success": False, "error": "analysis_missing", "message": "Önce crawl analizi çalıştırın"}
    ai = a.get("ai_gaps") or {}
    if not ai.get("success") and ai.get("error"):
        return {"success": False, "error": ai.get("error"), "message": ai.get("message", "AI gap verisi yok")}
    return {"success": True, "count": ai.get("count", 0), "ai_gaps": ai.get("gaps") or []}


def list_opportunities(project_id: str = "", export: bool = False) -> dict[str, Any]:
    st = _load_state()
    opps = st.get("exportable_opportunities") or []
    if project_id:
        opps = [o for o in opps if not o.get("project_id") or o.get("project_id") == project_id]
    result: dict[str, Any] = {"success": True, "count": len(opps), "opportunities": opps}
    if export and project_id:
        result["export"] = _export_to_opportunity_state(project_id, opps)
    return result


def export_report(report_type: str = "overview", project_id: str = "", domain: str = "") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generators = {
        "entity": lambda: list_entities(project_id, domain),
        "faq": lambda: list_faqs(project_id, domain),
        "geo": lambda: list_geo(project_id, domain),
        "cluster": lambda: list_clusters(project_id, domain),
        "ai": lambda: list_ai(project_id, domain),
        "authority": lambda: list_authority(project_id, domain),
        "competitor": lambda: _latest_analysis(project_id, domain) or {"success": False},
        "quick_win": lambda: {"success": True, "quick_wins": (_latest_analysis(project_id, domain) or {}).get("gaps", {}).get("quick_wins") or []},
        "overview": lambda: dashboard(project_id),
    }
    fn = generators.get(report_type, generators["overview"])
    payload = fn() if callable(fn) else fn
    path = REPORTS_DIR / f"crawl-gap-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _record_brain("gap_report_created", project_id=project_id, domain=domain, result={"report_type": report_type, "path": str(path)}, reason=f"Rapor dışa aktarıldı: {report_type}")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def dashboard(project_id: str = "") -> dict[str, Any]:
    st = _load_state()
    a = _latest_analysis(project_id)
    stats = (a or {}).get("gaps", {}).get("stats") or {}
    integrations = _integration_status()
    errors = [k for k, v in integrations.items() if not v.get("ok")]
    return {
        "success": True,
        "analysis_id": (a or {}).get("analysis_id"),
        "own_domain": (a or {}).get("own_domain"),
        "domains_crawled": (a or {}).get("domains_crawled") or 0,
        "pages_crawled": (a or {}).get("pages_crawled_total") or 0,
        "gap_stats": stats,
        "entity_gaps": stats.get("entity_gap_count", 0),
        "faq_gaps": stats.get("faq_gap_count", 0),
        "geo_gaps": stats.get("geo_gap_count", 0),
        "critical_gaps": stats.get("critical_gap_count", 0),
        "quick_wins": stats.get("quick_win_count", 0),
        "action_plan": (a or {}).get("action_plan") or [],
        "defense_risks": (a or {}).get("defense_risks"),
        "integrations": integrations,
        "integration_errors": errors,
        "crawl_history_count": len(st.get("crawl_history") or []),
        "gap_history_count": len(st.get("gap_history") or []),
        "jobs_count": len(st.get("jobs") or []),
        "opportunity_count": len(st.get("exportable_opportunities") or []),
        "last_analyzed_at": (a or {}).get("analyzed_at"),
        "latest": st.get("latest") or {},
    }


def health() -> dict[str, Any]:
    st = _load_state()
    integrations = _integration_status()
    errors = [{"module": k, "error": v.get("error") or "not ready"} for k, v in integrations.items() if not v.get("ok")]
    return {
        "success": True,
        "module": "crawl_gap_engine",
        "enabled": get_settings().get("enabled", True),
        "engine": "requests+beautifulsoup",
        "integrations": integrations,
        "integration_errors": errors,
        "analyses_count": len(st.get("analyses") or {}),
        "jobs_count": len(st.get("jobs") or []),
        "active_crawls": list(ACTIVE_CRAWLS),
        "history_counts": {
            "crawl_history": len(st.get("crawl_history") or []),
            "gap_history": len(st.get("gap_history") or []),
        },
    }
