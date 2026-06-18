"""Astro Auto Publisher / Site Sync Engine — gerçek tarama, build, deploy."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.astro_auto_publisher")

STATE_FILE = Path(__file__).resolve().parent.parent / "astro_auto_publisher_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

SOURCE_KEYS = (
    "page_hub",
    "sss_automation",
    "place_seo_pipeline",
    "entity_detail_generator",
    "listing_hub",
    "wordpress",
    "network_replicator",
)

LEGACY_SOURCE_MAP = {
    "sss": "sss_automation",
    "place_seo": "place_seo_pipeline",
    "entity_detail": "entity_detail_generator",
    "listing": "listing_hub",
}

DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "interval_minutes": 360,
    "auto_build": True,
    "auto_deploy": False,
    "require_quality_gate_pass": True,
    "min_quality_score": 85,
    "max_items_per_run": 50,
    "target_project_id": "",
    "sources": {
        "page_hub": True,
        "sss_automation": True,
        "place_seo_pipeline": True,
        "entity_detail_generator": True,
        "listing_hub": False,
        "wordpress": False,
        "network_replicator": True,
    },
}

_job_lock = threading.Lock()
_scheduler_thread: threading.Thread | None = None
_scheduler_stop = threading.Event()

DATA_FILES = {
    "landing": "pages.json",
    "category": "pages.json",
    "geo": "pages.json",
    "faq": "faqs.json",
    "blog": "blog.json",
    "entity": "entity_pages.json",
    "listing": "listing_pages.json",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _normalize_sources(raw: dict[str, Any] | None) -> dict[str, bool]:
    merged = {**DEFAULT_SETTINGS["sources"], **(raw or {})}
    out: dict[str, bool] = {}
    for key in SOURCE_KEYS:
        if key in merged:
            out[key] = bool(merged[key])
    for legacy, modern in LEGACY_SOURCE_MAP.items():
        if legacy in merged and modern not in merged:
            out[modern] = bool(merged[legacy])
    return out


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_SETTINGS))
                data["settings"]["sources"] = _normalize_sources(data["settings"].get("sources"))
                data.setdefault("queue", [])
                data.setdefault("jobs", {})
                data.setdefault("running_job", "")
                data.setdefault("last_scan_at", "")
                data.setdefault("last_process_at", "")
                data.setdefault("last_build_at", "")
                data.setdefault("last_deploy_url", "")
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "settings": dict(DEFAULT_SETTINGS),
        "queue": [],
        "jobs": {},
        "running_job": "",
        "last_scan_at": "",
        "last_process_at": "",
        "last_build_at": "",
        "last_deploy_url": "",
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_slug(slug: str) -> str:
    s = (slug or "").strip().replace("\\", "").replace("..", "")
    s = re.sub(r"[^a-zA-Z0-9/_-]", "-", s)
    return s.strip("/-")


def _content_hash(content: str) -> str:
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()[:16]


def _normalize_item(
    source: str,
    source_id: str,
    title: str,
    slug: str,
    content: str,
    page_type: str,
    *,
    project_id: str = "",
    target_keyword: str = "",
    updated_at: str = "",
    location: str = "Kuşadası",
    sync_status: str = "missing",
    quality_report_id: str | None = None,
    quality_score: int | None = None,
) -> dict[str, Any]:
    slug = _safe_slug(slug) or _safe_slug(title)
    return {
        "source": source,
        "source_id": str(source_id),
        "project_id": project_id,
        "title": (title or "").strip(),
        "slug": slug,
        "type": page_type,
        "content": content or "",
        "target_keyword": target_keyword or title,
        "updated_at": updated_at or _now(),
        "quality_report_id": quality_report_id,
        "quality_score": quality_score,
        "sync_status": sync_status,
        "location": location,
        "content_hash": _content_hash(content),
    }


def get_settings() -> dict[str, Any]:
    st = _load_state()
    settings = {**DEFAULT_SETTINGS, **(st.get("settings") or {})}
    settings["sources"] = _normalize_sources(settings.get("sources"))
    return settings


def update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    st = _load_state()
    cur = get_settings()
    for key in (
        "enabled", "interval_minutes", "auto_build", "auto_deploy",
        "require_quality_gate_pass", "min_quality_score", "max_items_per_run",
        "target_project_id",
    ):
        if key in payload:
            cur[key] = payload[key]
    if "sources" in payload and isinstance(payload["sources"], dict):
        cur["sources"] = _normalize_sources({**cur["sources"], **payload["sources"]})
    st["settings"] = cur
    _save_state(st)
    return {"success": True, "settings": cur}


def _get_project_paths(project_id: str) -> tuple[dict[str, Any], Path]:
    from app.moduller.astro_factory import GENERATED_DIR, _get_project, _project_path
    project = _get_project(project_id)
    path = _project_path(project["slug"])
    base = GENERATED_DIR.resolve()
    if not str(path.resolve()).startswith(str(base)):
        raise ValueError("generated-sites dışına yazma yasak")
    return project, path


def _read_astro_index(project_id: str) -> dict[str, dict[str, Any]]:
    _, project_path = _get_project_paths(project_id)
    data_dir = project_path / "src" / "data"
    index: dict[str, dict[str, Any]] = {}

    def add_entries(filename: str, entries: list[dict[str, Any]], key_prefix: str = "") -> None:
        for entry in entries:
            slug = _safe_slug(entry.get("slug") or entry.get("title", ""))
            if key_prefix and slug and not slug.startswith(key_prefix):
                slug = f"{key_prefix}/{slug}" if key_prefix else slug
            content = entry.get("content_html") or entry.get("content") or ""
            index[slug] = {
                "file": filename,
                "entry": entry,
                "hash": _content_hash(content),
                "updated_at": entry.get("updated_at", ""),
            }

    pages_file = data_dir / "pages.json"
    if pages_file.exists():
        try:
            pages = json.loads(pages_file.read_text(encoding="utf-8"))
            home = pages.get("home") or {}
            if home.get("content_html"):
                add_entries("pages.json", [{"slug": "", "title": home.get("title", ""), **home}])
            add_entries("pages.json", pages.get("geo") or [], "geo")
            add_entries("pages.json", pages.get("categories") or [], "category")
        except (json.JSONDecodeError, OSError):
            pass

    for fname in ("faqs.json", "blog.json", "entity_pages.json", "listing_pages.json"):
        fp = data_dir / fname
        if not fp.exists():
            continue
        try:
            items = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(items, list):
                add_entries(fname, items)
        except (json.JSONDecodeError, OSError):
            pass

    return index


def _scan_page_hub() -> list[dict[str, Any]]:
    from app.moduller.page_hub import get_page_detail, get_tree
    items: list[dict[str, Any]] = []
    for kind, ptype in (("landing", "landing"), ("gece", "category"), ("sss", "faq")):
        tree = get_tree(kind)
        for page in tree.get("pages") or []:
            detail = get_page_detail(kind, page["id"])
            if not detail.get("success"):
                continue
            p = detail.get("page") or page
            content = p.get("content") or p.get("html") or ""
            if isinstance(content, dict):
                content = content.get("rendered", "")
            items.append(_normalize_item(
                "page_hub", p.get("id", page["id"]),
                p.get("title", page.get("title", "")),
                p.get("slug", page.get("slug", "")),
                content, ptype,
                target_keyword=p.get("keyword", p.get("title", "")),
                updated_at=p.get("modified", p.get("date", "")),
            ))
    return items


def _scan_sss_automation() -> list[dict[str, Any]]:
    from app.moduller.sss_automation import sss_automation
    report = sss_automation.get_report()
    items: list[dict[str, Any]] = []
    for p in report.get("last_pages") or report.get("pages") or []:
        items.append(_normalize_item(
            "sss_automation", p.get("slug", p.get("keyword", "")),
            p.get("seo_title", p.get("title", "")),
            p.get("slug", ""),
            p.get("html", ""),
            "faq",
            target_keyword=p.get("keyword", ""),
            updated_at=p.get("published_at", ""),
        ))
    return items


def _scan_place_seo_pipeline() -> list[dict[str, Any]]:
    from app.moduller.place_seo_pipeline import place_seo_pipeline
    items: list[dict[str, Any]] = []
    jobs = place_seo_pipeline.list_jobs(limit=50).get("jobs") or []
    for job in jobs:
        plan = job.get("plan") or {}
        jid = job.get("id", "")
        for key, ptype in (
            ("category_pages", "category"), ("geo_pages", "geo"),
            ("faq_pages", "faq"), ("blog_posts", "blog"),
        ):
            for page in plan.get(key) or []:
                html = page.get("html") or page.get("content_html") or ""
                if not html and page.get("title"):
                    html = f"<h1>{page['title']}</h1>"
                items.append(_normalize_item(
                    "place_seo_pipeline", f"{jid}:{page.get('slug', '')}",
                    page.get("title", ""),
                    page.get("slug", ""),
                    html, ptype,
                    target_keyword=page.get("target_keyword", page.get("title", "")),
                    updated_at=job.get("updated_at", job.get("created_at", "")),
                    location=page.get("location", "Kuşadası"),
                ))
        astro = plan.get("astro_support_site") or {}
        for page in astro.get("pages") or []:
            html = page.get("html") or page.get("content_html") or ""
            items.append(_normalize_item(
                "place_seo_pipeline", f"{jid}:astro:{page.get('slug', '')}",
                page.get("title", ""),
                page.get("slug", ""),
                html, page.get("type", "landing"),
                target_keyword=page.get("target_keyword", page.get("title", "")),
                updated_at=job.get("updated_at", ""),
            ))
    return items


def _scan_entity_detail_generator() -> list[dict[str, Any]]:
    from app.moduller.entity_detail_generator import entity_detail_generator
    items: list[dict[str, Any]] = []
    jobs = entity_detail_generator.list_jobs(limit=30).get("jobs") or []
    for job in jobs:
        for ent in job.get("entities") or []:
            if not ent.get("tier1_selected") or not ent.get("page"):
                continue
            page = ent["page"]
            items.append(_normalize_item(
                "entity_detail_generator", ent.get("id", ""),
                f"{ent.get('name', '')} Kuşadası rehberi",
                ent.get("slug", "").replace("rehber/", ""),
                page.get("html", ""),
                "entity",
                target_keyword=(ent.get("target_keywords") or [""])[0],
                updated_at=job.get("updated_at", ""),
                location=ent.get("location", "Kuşadası"),
            ))
    return items


def _scan_listing_hub() -> list[dict[str, Any]]:
    from app.moduller.listing_hub import listing_hub, listing_to_html
    result = listing_hub.list_listings(status="publish", limit=200)
    items: list[dict[str, Any]] = []
    for lst in result.get("listings") or []:
        html = listing_to_html(lst)
        items.append(_normalize_item(
            "listing_hub", lst.get("id", ""),
            lst.get("title", ""),
            lst.get("slug", ""),
            html, "listing",
            target_keyword=lst.get("target_keyword", lst.get("title", "")),
            updated_at=lst.get("updated_at", ""),
            location=lst.get("city", "Kuşadası"),
        ))
    return items


def _scan_wordpress() -> list[dict[str, Any]]:
    from app.moduller.page_hub import get_page_detail, get_tree
    items: list[dict[str, Any]] = []
    tree = get_tree("page")
    for page in tree.get("pages") or []:
        detail = get_page_detail("page", page["id"])
        if not detail.get("success"):
            continue
        p = detail.get("page") or page
        content = p.get("content") or ""
        if isinstance(content, dict):
            content = content.get("rendered", "")
        items.append(_normalize_item(
            "wordpress", p.get("id", page["id"]),
            p.get("title", ""),
            p.get("slug", ""),
            content, "landing",
            target_keyword=p.get("title", ""),
            updated_at=p.get("modified", ""),
        ))
    return items


def _scan_network_replicator() -> list[dict[str, Any]]:
    from app.moduller.network_replicator import list_networks
    items: list[dict[str, Any]] = []
    networks = list_networks().get("networks") or []
    for net in networks:
        nid = net.get("id", "")
        for d in net.get("domains") or []:
            pid = d.get("project_id", "")
            domain = d.get("domain", "")
            if not pid:
                continue
            items.append(_normalize_item(
                "network_replicator", f"{nid}:{domain}",
                f"{domain} varyant",
                domain.replace(".", "-"),
                f"<h1>{domain}</h1><p>Network domain varyantı — {domain}</p>",
                "landing",
                project_id=pid,
                target_keyword=domain,
                updated_at=net.get("updated_at", ""),
            ))
    return items


def scan_all_sources(settings: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    sources = _normalize_sources(settings.get("sources"))
    items: list[dict[str, Any]] = []
    scanners = {
        "page_hub": _scan_page_hub,
        "sss_automation": _scan_sss_automation,
        "place_seo_pipeline": _scan_place_seo_pipeline,
        "entity_detail_generator": _scan_entity_detail_generator,
        "listing_hub": _scan_listing_hub,
        "wordpress": _scan_wordpress,
        "network_replicator": _scan_network_replicator,
    }
    for name, fn in scanners.items():
        if not sources.get(name):
            continue
        try:
            found = fn()
            items.extend(found)
            logger.info("Astro auto scan %s: %d items", name, len(found))
        except Exception as exc:
            logger.warning("Scan source %s failed: %s", name, exc)
    return items


def _classify_items(
    project_id: str,
    items: list[dict[str, Any]],
    settings: dict[str, Any],
    *,
    include_outdated: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    index = _read_astro_index(project_id)
    missing: list[dict[str, Any]] = []
    outdated: list[dict[str, Any]] = []
    synced: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for item in items:
        target_pid = item.get("project_id") or project_id
        if item.get("project_id") and item["project_id"] != project_id:
            continue
        slug = _safe_slug(item["slug"])
        existing = index.get(slug)
        if not existing:
            item["sync_status"] = "missing"
            missing.append(item)
            continue
        if include_outdated and existing.get("hash") != item.get("content_hash"):
            item["sync_status"] = "outdated"
            outdated.append(item)
        else:
            item["sync_status"] = "synced"
            synced.append(item)

    if settings.get("require_quality_gate_pass"):
        for item in missing + outdated:
            gate = _run_quality_gate(item, settings)
            item["quality"] = gate
            item["quality_report_id"] = gate.get("report_id")
            item["quality_score"] = gate.get("score")
            if not gate.get("passed"):
                item["sync_status"] = "blocked"
                blocked.append(item)

    blocked_ids = {id(x) for x in blocked}
    missing = [x for x in missing if id(x) not in blocked_ids]
    outdated = [x for x in outdated if id(x) not in blocked_ids]

    return {"missing": missing, "outdated": outdated, "synced": synced, "blocked": blocked}


def scan_missing(
    project_id: str,
    *,
    sources: dict[str, bool] | None = None,
    include_outdated: bool = True,
) -> dict[str, Any]:
    if not project_id:
        return {"success": False, "error": "project_id gerekli"}
    try:
        _get_project_paths(project_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    settings = get_settings()
    if sources:
        settings = {**settings, "sources": _normalize_sources({**settings.get("sources", {}), **sources})}
    items = scan_all_sources(settings)
    classified = _classify_items(project_id, items, settings, include_outdated=include_outdated)

    st = _load_state()
    st["last_scan_at"] = _now()
    _save_state(st)

    return {
        "success": True,
        "project_id": project_id,
        "scanned": len(items),
        **classified,
        "already_synced": classified["synced"],
        "blocked_by_quality": classified["blocked"],
    }


def _run_quality_gate(
    item: dict[str, Any],
    settings: dict[str, Any],
    *,
    ignore_warning: bool = False,
) -> dict[str, Any]:
    from app.moduller.seo_quality_gate import seo_quality_gate
    analysis = seo_quality_gate.analyze_page(
        item.get("content", ""),
        item.get("target_keyword", ""),
        location=item.get("location", "Kuşadası"),
        title=item.get("title", ""),
    )
    score = analysis.get("overall_score") or analysis.get("seo_score") or 0
    min_score = settings.get("min_quality_score", 85)
    critical = analysis.get("critical_issues") or [
        i for i in (analysis.get("issues") or []) if i.get("severity") == "critical"
    ]
    passed = bool(analysis.get("pass")) and score >= min_score
    if not settings.get("require_quality_gate_pass"):
        passed = True
    elif critical:
        passed = False
    elif ignore_warning and not critical:
        passed = True
    report_id = f"qg-{uuid.uuid4().hex[:10]}"
    return {
        "report_id": report_id,
        "passed": passed,
        "score": score,
        "critical_count": len(critical),
        "analysis": analysis,
    }


def get_queue() -> dict[str, Any]:
    st = _load_state()
    return {"success": True, "queue": st.get("queue") or [], "count": len(st.get("queue") or [])}


def _queue_key(project_id: str, item: dict[str, Any]) -> tuple[str, str, str]:
    return (project_id, item.get("source", ""), item.get("source_id", ""))


def _refresh_signals_for_item(item: dict[str, Any], project_id: str) -> dict[str, Any]:
    """Content Refresh Engine hazırlığı — rank + quality sinyalleri."""
    signals: dict[str, Any] = {
        "refresh_priority": 30,
        "citation_loss": 0,
        "entity_loss": 0,
        "ai_visibility_loss": 0,
        "decay_detected": False,
    }
    kw = (item.get("target_keyword") or item.get("title") or "").strip().lower()
    try:
        from app.moduller.rank_index_watcher import get_project
        proj = get_project(project_id)
        if proj.get("success") and kw:
            for entry in proj["project"].get("keywords") or []:
                if (entry.get("keyword") or "").lower() != kw:
                    continue
                decay = int(entry.get("ranking_decay_score") or 0)
                if decay >= 36:
                    signals["decay_detected"] = True
                signals["refresh_priority"] = min(
                    100, max(signals["refresh_priority"], 40 + decay // 2),
                )
                strength = int(entry.get("keyword_strength_score") or 50)
                if strength < 45:
                    signals["refresh_priority"] = max(signals["refresh_priority"], 75)
                break
    except Exception:
        pass
    qscore = item.get("quality_score")
    if qscore is not None:
        qs = int(qscore)
        if qs < 85:
            signals["citation_loss"] = max(0, 85 - qs)
            signals["ai_visibility_loss"] = max(0, 70 - qs)
            signals["entity_loss"] = max(0, 60 - qs)
            signals["refresh_priority"] = max(signals["refresh_priority"], 80 - qs)
    if item.get("sync_status") == "outdated":
        signals["refresh_priority"] = max(signals["refresh_priority"], 65)
    return signals


def queue_missing(
    project_id: str,
    items: list[dict[str, Any]] | None = None,
    *,
    include_outdated: bool = True,
) -> dict[str, Any]:
    if not items:
        scan = scan_missing(project_id, include_outdated=include_outdated)
        if not scan.get("success"):
            return scan
        items = list(scan.get("missing") or [])
        if include_outdated:
            items.extend(scan.get("outdated") or [])

    settings = get_settings()
    max_items = int(settings.get("max_items_per_run", 50))
    items = items[:max_items]

    st = _load_state()
    queue = st.get("queue") or []
    existing_keys = {
        _queue_key(q.get("project_id", ""), q.get("content_item") or q)
        for q in queue
        if q.get("status") in ("queued", "processing", "pending")
    }
    added = 0
    for item in items:
        key = _queue_key(project_id, item)
        if key in existing_keys:
            continue
        refresh = _refresh_signals_for_item(item, project_id)
        queue.append({
            "queue_id": f"q-{uuid.uuid4().hex[:10]}",
            "project_id": project_id,
            "content_item": item,
            "status": "queued",
            "created_at": _now(),
            "quality_score": item.get("quality_score"),
            "ignore_warning": False,
            **refresh,
        })
        existing_keys.add(key)
        added += 1

    st["queue"] = queue
    _save_state(st)
    return {"success": True, "queued": added, "queue_size": len(queue)}


def ignore_queue_warning(queue_id: str) -> dict[str, Any]:
    st = _load_state()
    for q in st.get("queue") or []:
        if q.get("queue_id") != queue_id:
            continue
        item = q.get("content_item") or {}
        gate = _run_quality_gate(item, get_settings())
        if gate.get("critical_count", 0) > 0:
            return {"success": False, "error": "Critical fail override edilemez"}
        q["ignore_warning"] = True
        _save_state(st)
        return {"success": True, "queue_id": queue_id}
    return {"success": False, "error": "Kuyruk öğesi bulunamadı"}


def _write_item_to_astro(project_path: Path, item: dict[str, Any]) -> None:
    data_dir = project_path / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    ptype = item.get("type", "landing")
    slug = _safe_slug(item.get("slug", ""))

    entry = {
        "slug": slug.replace("rehber/", "").replace("geo/", "").replace("sss/", "").replace("category/", ""),
        "title": item.get("title", ""),
        "description": (item.get("content") or "")[:200],
        "content_html": item.get("content", ""),
        "keyword": item.get("target_keyword", ""),
        "updated_at": item.get("updated_at", _now()),
    }

    if ptype in ("landing", "geo", "category"):
        fp = data_dir / "pages.json"
        data = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {"geo": [], "categories": [], "home": {}}
        if ptype == "geo":
            geo = [g for g in (data.get("geo") or []) if _safe_slug(g.get("slug", "")) != entry["slug"]]
            geo.append(entry)
            data["geo"] = geo
        elif ptype == "category":
            cats = [g for g in (data.get("categories") or []) if _safe_slug(g.get("slug", "")) != entry["slug"]]
            cats.append(entry)
            data["categories"] = cats
        else:
            data["home"] = {**entry, "content_html": entry["content_html"]}
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif ptype == "faq":
        fp = data_dir / "faqs.json"
        arr = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        arr = [x for x in arr if _safe_slug(x.get("slug", "")) != entry["slug"]]
        arr.append(entry)
        fp.write_text(json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8")
    elif ptype == "blog":
        fp = data_dir / "blog.json"
        arr = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        arr = [x for x in arr if _safe_slug(x.get("slug", "")) != entry["slug"]]
        arr.append({**entry, "topic": entry.get("keyword", ""), "ai_engine": "astro_auto_publisher"})
        fp.write_text(json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8")
    elif ptype == "listing":
        fp = data_dir / "listing_pages.json"
        arr = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        arr = [x for x in arr if _safe_slug(x.get("slug", "")) != entry["slug"]]
        arr.append({**entry, "listing_id": item.get("source_id", "")})
        fp.write_text(json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        fp = data_dir / "entity_pages.json"
        arr = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        arr = [x for x in arr if _safe_slug(x.get("slug", "")) != entry["slug"]]
        arr.append({**entry, "entity_name": item.get("title", ""), "location": item.get("location", "")})
        fp.write_text(json.dumps(arr, ensure_ascii=False, indent=2), encoding="utf-8")


def _new_job_id() -> str:
    return f"aap-{uuid.uuid4().hex[:12]}"


def _start_job(job_type: str, project_id: str) -> dict[str, Any] | None:
    with _job_lock:
        st = _load_state()
        if st.get("running_job"):
            return None
        jid = _new_job_id()
        job = {
            "job_id": jid,
            "type": job_type,
            "project_id": project_id,
            "status": "running",
            "started_at": _now(),
            "finished_at": "",
            "summary": {
                "scanned": 0, "missing": 0, "outdated": 0, "queued": 0,
                "written": 0, "quality_failed": 0, "built": False, "deployed": False,
            },
            "errors": [],
            "items": [],
        }
        st["jobs"][jid] = job
        st["running_job"] = jid
        _save_state(st)
        return job


def _finish_job(job_id: str, status: str, **extra: Any) -> dict[str, Any]:
    with _job_lock:
        st = _load_state()
        job = st["jobs"].get(job_id, {})
        job["status"] = status
        job["finished_at"] = _now()
        job.update(extra)
        st["jobs"][job_id] = job
        st["running_job"] = ""
        _save_state(st)
        return job


def _has_quality_failed_in_queue(project_id: str) -> bool:
    st = _load_state()
    for q in st.get("queue") or []:
        if q.get("project_id") != project_id:
            continue
        if q.get("status") == "quality_failed":
            return True
    return False


def process_queue(
    project_id: str,
    *,
    auto_deploy: bool | None = None,
    auto_build: bool | None = None,
    manage_job: bool = True,
    existing_job_id: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    if auto_deploy is None:
        auto_deploy = settings.get("auto_deploy", False)
    if auto_build is None:
        auto_build = settings.get("auto_build", True)

    job_id = existing_job_id
    if manage_job:
        job = _start_job("process", project_id)
        if not job:
            return {"success": False, "error": "Başka bir sync job çalışıyor — bekleyin"}
        job_id = job["job_id"]
    try:
        _, project_path = _get_project_paths(project_id)
    except ValueError as e:
        if manage_job:
            _finish_job(job_id, "failed", errors=[str(e)])
        return {"success": False, "error": str(e)}

    st = _load_state()
    queue = [
        q for q in (st.get("queue") or [])
        if q.get("project_id") == project_id and q.get("status") in ("queued", "pending")
    ]
    max_items = int(settings.get("max_items_per_run", 50))
    queue = queue[:max_items]

    written = quality_failed = 0
    processed_items: list[dict[str, Any]] = []

    for qitem in queue:
        qitem["status"] = "processing"
        item = qitem.get("content_item") or qitem
        ignore = bool(qitem.get("ignore_warning"))
        gate = _run_quality_gate(item, settings, ignore_warning=ignore)
        item["quality"] = gate
        item["quality_report_id"] = gate.get("report_id")
        item["quality_score"] = gate.get("score")
        qitem["quality_score"] = gate.get("score")

        if settings.get("require_quality_gate_pass") and not gate.get("passed"):
            quality_failed += 1
            qitem["status"] = "quality_failed"
            item["sync_status"] = "blocked"
            processed_items.append(item)
            continue

        slug = _safe_slug(item.get("slug", ""))
        index = _read_astro_index(project_id)
        is_new = slug not in index
        _write_item_to_astro(project_path, item)
        written += 1
        qitem["status"] = "written"
        item["sync_status"] = "synced"
        processed_items.append(item)

    st = _load_state()
    st["last_process_at"] = _now()
    _save_state(st)

    built = deployed = False
    deploy_url = ""
    build_result: dict[str, Any] = {}
    deploy_result: dict[str, Any] = {}

    if auto_build and written > 0:
        from app.moduller.astro_factory import build_astro_project, generate_pages
        generate_pages(project_id)
        build_result = build_astro_project(project_id)
        built = bool(build_result.get("success"))
        if built:
            st = _load_state()
            st["last_build_at"] = _now()
            for qitem in queue:
                if qitem.get("status") == "written":
                    qitem["status"] = "built"
            _save_state(st)

    if auto_deploy and built and not _has_quality_failed_in_queue(project_id):
        from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare
        deploy_result = deploy_to_cloudflare(project_id)
        deployed = bool(deploy_result.get("success"))
        deploy_url = deploy_result.get("url") or deploy_result.get("deployment_url") or ""
        if deployed:
            st = _load_state()
            st["last_deploy_url"] = deploy_url
            for qitem in queue:
                if qitem.get("status") == "built":
                    qitem["status"] = "deployed"
            _save_state(st)
            _notify_rank_watcher(project_id, processed_items, deploy_url)
    elif auto_deploy and _has_quality_failed_in_queue(project_id):
        deploy_result = {"success": False, "error": "Quality Gate fail — deploy engellendi"}

    summary = {
        "scanned": len(queue),
        "missing": written,
        "outdated": 0,
        "queued": len(queue),
        "written": written,
        "created": written,
        "updated": 0,
        "quality_failed": quality_failed,
        "built": built,
        "deployed": deployed,
        "deploy_url": deploy_url,
    }
    if manage_job:
        job = _finish_job(job_id, "completed", summary=summary, items=processed_items, build=build_result, deploy=deploy_result)
        return {"success": True, "job_id": job_id, "summary": summary, "job": job}
    return {"success": True, "job_id": job_id, "summary": summary, "items": processed_items, "build": build_result, "deploy": deploy_result}


def _notify_rank_watcher(project_id: str, items: list[dict[str, Any]], deploy_url: str) -> None:
    try:
        from app.moduller.astro_factory import _get_project
        from app.moduller.rank_index_watcher import register_project, track_keyword
        project = _get_project(project_id)
        domain = (project.get("domain") or deploy_url or "").replace("https://", "").replace("http://", "").split("/")[0]
        if domain:
            register_project(project_id, domain, source="astro_auto_publisher")
        for item in items:
            if item.get("sync_status") == "blocked":
                continue
            kw = (item.get("target_keyword") or item.get("title") or "").strip()
            if kw and domain:
                track_keyword(kw.lower(), domain, save=True, project_id=project_id)
    except Exception as exc:
        logger.warning("Rank watcher notify: %s", exc)


def sync_all(
    project_id: str,
    *,
    auto_deploy: bool = False,
    auto_build: bool | None = None,
    max_items: int | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    if auto_build is None:
        auto_build = settings.get("auto_build", True)
    if max_items is None:
        max_items = int(settings.get("max_items_per_run", 50))

    job = _start_job("sync_all", project_id)
    if not job:
        return {"success": False, "error": "Başka bir sync job çalışıyor"}

    job_id = job["job_id"]
    try:
        items = scan_all_sources(settings)
        classified = _classify_items(project_id, items, settings)
        to_sync = (classified.get("missing") or []) + (classified.get("outdated") or [])
        to_sync = to_sync[:max_items]

        queue_missing(project_id, to_sync, include_outdated=False)
        result = process_queue(
            project_id,
            auto_deploy=auto_deploy,
            auto_build=auto_build,
            manage_job=False,
            existing_job_id=job_id,
        )

        summary = {
            "scanned": len(items),
            "missing": len(classified.get("missing") or []),
            "outdated": len(classified.get("outdated") or []),
            "synced": len(classified.get("synced") or []),
            "blocked": len(classified.get("blocked") or []),
            **(result.get("summary") or {}),
        }
        job = _finish_job(
            job_id,
            "completed" if result.get("success") else "failed",
            summary=summary,
            scan=classified,
            items=result.get("items", []),
        )
        return {"success": result.get("success", False), "job_id": job_id, "summary": summary, "job": job}
    except Exception as exc:
        _finish_job(job_id, "failed", errors=[str(exc)])
        return {"success": False, "error": str(exc), "job_id": job_id}


def deploy(project_id: str) -> dict[str, Any]:
    if _has_quality_failed_in_queue(project_id):
        return {"success": False, "error": "Quality Gate fail içerik var — deploy engellendi"}

    from app.moduller.astro_factory import build_astro_project
    from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare

    try:
        project, _ = _get_project_paths(project_id)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    if not project.get("dist_exists"):
        build_res = build_astro_project(project_id)
        if not build_res.get("success"):
            return {"success": False, "error": build_res.get("error", "Build başarısız")}

    result = deploy_to_cloudflare(project_id)
    if result.get("success"):
        url = result.get("url") or result.get("deployment_url") or ""
        st = _load_state()
        st["last_deploy_url"] = url
        _save_state(st)
        _notify_rank_watcher(project_id, [], url)
    return result


def network_sync_all(network_id: str, *, auto_deploy: bool = False) -> dict[str, Any]:
    from app.moduller.network_replicator import build_network, deploy_network, get_network
    network = get_network(network_id)
    if not network.get("success"):
        return network

    project_results: list[dict[str, Any]] = []
    for d in network["network"].get("domains") or []:
        pid = d.get("project_id")
        if not pid:
            continue
        res = sync_all(pid, auto_deploy=False, max_items=int(get_settings().get("max_items_per_run", 50)))
        project_results.append({"domain": d.get("domain"), "project_id": pid, **res})

    build_res = build_network(network_id)
    deploy_res: dict[str, Any] = {}
    if auto_deploy:
        deploy_res = deploy_network(network_id)

    return {
        "success": True,
        "network_id": network_id,
        "projects": project_results,
        "build": build_res,
        "deploy": deploy_res,
    }


def network_scan_missing(network_id: str) -> dict[str, Any]:
    from app.moduller.network_replicator import get_network
    network = get_network(network_id)
    if not network.get("success"):
        return network
    results: list[dict[str, Any]] = []
    for d in network["network"].get("domains") or []:
        pid = d.get("project_id")
        if not pid:
            continue
        scan = scan_missing(pid)
        results.append({"domain": d.get("domain"), "project_id": pid, **scan})
    return {"success": True, "network_id": network_id, "results": results}


def network_process_queue(network_id: str, *, auto_deploy: bool = False) -> dict[str, Any]:
    from app.moduller.network_replicator import build_network, deploy_network, get_network
    network = get_network(network_id)
    if not network.get("success"):
        return network
    results: list[dict[str, Any]] = []
    for d in network["network"].get("domains") or []:
        pid = d.get("project_id")
        if not pid:
            continue
        queue_missing(pid)
        res = process_queue(pid, auto_deploy=False, auto_build=True)
        results.append({"domain": d.get("domain"), "project_id": pid, **res})
    build_res = build_network(network_id)
    deploy_res = deploy_network(network_id) if auto_deploy else {}
    return {"success": True, "network_id": network_id, "results": results, "build": build_res, "deploy": deploy_res}


def get_dashboard() -> dict[str, Any]:
    st = _load_state()
    queue = st.get("queue") or []
    return {
        "missing": sum(1 for q in queue if (q.get("content_item") or {}).get("sync_status") == "missing"),
        "outdated": sum(1 for q in queue if (q.get("content_item") or {}).get("sync_status") == "outdated"),
        "queued": sum(1 for q in queue if q.get("status") in ("queued", "pending")),
        "quality_failed": sum(1 for q in queue if q.get("status") == "quality_failed"),
        "last_build_at": st.get("last_build_at", ""),
        "last_deploy_url": st.get("last_deploy_url", ""),
        "last_scan_at": st.get("last_scan_at", ""),
        "last_process_at": st.get("last_process_at", ""),
    }


def export_report(project_id: str = "", job_id: str = "") -> dict[str, Any]:
    st = _load_state()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if job_id:
        job = (st.get("jobs") or {}).get(job_id)
        if not job:
            return {"success": False, "error": "Job bulunamadı"}
        path = REPORTS_DIR / f"astro-auto-job-{job_id}.json"
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "path": str(path), "job_id": job_id}
    payload = {
        "exported_at": _now(),
        "settings": get_settings(),
        "dashboard": get_dashboard(),
        "queue": st.get("queue") or [],
        "jobs": list((st.get("jobs") or {}).values())[-20:],
        "project_id": project_id,
    }
    suffix = project_id or "all"
    path = REPORTS_DIR / f"astro-auto-publisher-{suffix}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "path": str(path)}


def list_jobs(limit: int = 20) -> dict[str, Any]:
    jobs = list((_load_state().get("jobs") or {}).values())
    jobs.sort(key=lambda j: j.get("started_at", ""), reverse=True)
    return {"success": True, "jobs": jobs[:limit]}


def get_job_detail(job_id: str) -> dict[str, Any]:
    job = (_load_state().get("jobs") or {}).get(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    return {"success": True, "job": job}


def health() -> dict[str, Any]:
    st = _load_state()
    settings = get_settings()
    cf_ok = False
    try:
        from app.moduller.cloudflare_pages_deploy import cf_status
        cf_ok = bool(cf_status().get("configured"))
    except Exception:
        pass
    return {
        "success": True,
        "module": "astro_auto_publisher",
        "running_job": st.get("running_job") or "",
        "queue_size": len(st.get("queue") or []),
        "last_scan_at": st.get("last_scan_at", ""),
        "last_process_at": st.get("last_process_at", ""),
        "last_build_at": st.get("last_build_at", ""),
        "last_deploy_url": st.get("last_deploy_url", ""),
        "cloudflare_configured": cf_ok,
        "settings": settings,
        "scheduler_active": _scheduler_thread is not None and _scheduler_thread.is_alive(),
        "dashboard": get_dashboard(),
    }


def _scheduler_tick() -> None:
    settings = get_settings()
    if not settings.get("enabled"):
        return
    project_id = (settings.get("target_project_id") or "").strip()
    if not project_id:
        return
    st = _load_state()
    if st.get("running_job"):
        return
    try:
        sync_all(
            project_id,
            auto_deploy=settings.get("auto_deploy", False),
            auto_build=settings.get("auto_build", True),
        )
    except Exception as exc:
        logger.warning("Scheduler tick failed: %s", exc)


def _scheduler_loop() -> None:
    while not _scheduler_stop.is_set():
        try:
            _scheduler_tick()
        except Exception as exc:
            logger.warning("Scheduler loop error: %s", exc)
        settings = get_settings()
        interval = max(60, int(settings.get("interval_minutes", 360)) * 60)
        _scheduler_stop.wait(interval)


def start_scheduler() -> None:
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, name="astro-auto-publisher", daemon=True)
    _scheduler_thread.start()
    st = _load_state()
    st["scheduler_started_at"] = _now()
    _save_state(st)
    logger.info("Astro Auto Publisher scheduler started")


def stop_scheduler() -> None:
    _scheduler_stop.set()


astro_auto_publisher = type("AstroAutoPublisher", (), {
    "health": staticmethod(health),
    "get_settings": staticmethod(get_settings),
    "update_settings": staticmethod(update_settings),
    "scan_missing": staticmethod(scan_missing),
    "queue_missing": staticmethod(queue_missing),
    "process_queue": staticmethod(process_queue),
    "sync_all": staticmethod(sync_all),
    "deploy": staticmethod(deploy),
    "list_jobs": staticmethod(list_jobs),
    "get_job_detail": staticmethod(get_job_detail),
    "get_queue": staticmethod(get_queue),
    "get_dashboard": staticmethod(get_dashboard),
    "export_report": staticmethod(export_report),
    "ignore_queue_warning": staticmethod(ignore_queue_warning),
    "network_sync_all": staticmethod(network_sync_all),
    "network_scan_missing": staticmethod(network_scan_missing),
    "network_process_queue": staticmethod(network_process_queue),
    "start_scheduler": staticmethod(start_scheduler),
    "stop_scheduler": staticmethod(stop_scheduler),
})()
