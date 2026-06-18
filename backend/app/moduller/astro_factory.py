"""Astro Site Factory — Talon + LLM ile SEO uyumlu statik Astro siteler."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.moduller.modul_base import simdi
from app.moduller.sss_generator import build_html, generate_sss_page
from app.moduller.storyforge_categories import _slugify

logger = logging.getLogger("hive.astro_factory")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
GENERATED_DIR = ROOT / "generated-sites"
TEMPLATE_DIR = ROOT / "sites" / "astro-templates" / "default"
STATE_FILE = Path(__file__).resolve().parent.parent / "astro_factory_state.json"

DEPLOYMENT_TARGETS = ["cloudflare_pages", "github_pages", "vps"]
BUILD_TIMEOUT_SEC = 300


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip()
    if not d:
        return ""
    if not d.startswith("http://") and not d.startswith("https://"):
        d = f"https://{d}"
    return d.rstrip("/")


def _check_npm() -> dict[str, Any]:
    try:
        r = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=10, shell=False)
        return {"available": r.returncode == 0, "version": (r.stdout or "").strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"available": False, "version": ""}


def _dist_ready(project_path: Path) -> bool:
    dist = project_path / "dist"
    return dist.is_dir() and (dist / "index.html").is_file()


def _safe_slug(raw: str) -> str:
    text = (raw or "").strip()
    if ".." in text or "/" in text or "\\" in text:
        raise ValueError("Geçersiz slug")
    slug = _slugify(text or "astro-site")
    return slug[:80] or "astro-site"


def _project_path(slug: str) -> Path:
    """Path traversal korumalı proje dizini."""
    safe = _safe_slug(slug)
    base = GENERATED_DIR.resolve()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    target = (GENERATED_DIR / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Geçersiz proje yolu")
    return target


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"projects": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_project(project_id: str) -> dict[str, Any]:
    state = _load_state()
    proj = state.get("projects", {}).get(project_id)
    if not proj:
        raise ValueError(f"Proje bulunamadı: {project_id}")
    return proj


def _update_project(project_id: str, **fields: Any) -> dict[str, Any]:
    state = _load_state()
    projects = state.setdefault("projects", {})
    if project_id not in projects:
        raise ValueError(f"Proje bulunamadı: {project_id}")
    projects[project_id].update(fields)
    projects[project_id]["updated_at"] = _now()
    _save_state(state)
    return projects[project_id]


def _talon_keywords(seed: str, location: str, limit: int = 20) -> tuple[list[str], dict[str, Any]]:
    keywords: list[str] = []
    meta: dict[str, Any] = {
        "favorites": 0, "generated": 0, "orchestrator": False, "errors": [],
        "geo_pages": [], "content_briefs": [], "astro_factory_ready": [],
    }
    if seed:
        try:
            from app.moduller.talon_orchestrator import get_astro_plan_data
            orch = get_astro_plan_data(seed, location or "Kuşadası", page_count=limit)
            if orch.get("success"):
                meta["orchestrator"] = True
                meta["research_id"] = orch.get("research_id")
                meta["geo_pages"] = orch.get("geo_pages", [])
                meta["astro_factory_ready"] = orch.get("astro_factory_ready", [])
                meta["content_briefs"] = [
                    r.get("content_brief", {})
                    for r in orch.get("astro_factory_ready", [])
                    if r.get("content_brief")
                ]
                meta["providers"] = orch.get("talon_meta", {}).get("providers", {})
                for r in orch.get("astro_factory_ready", []):
                    kw = (r.get("keyword") or "").strip()
                    if kw:
                        keywords.append(kw)
                for gp in orch.get("geo_pages", []):
                    kw = (gp.get("keyword") or gp.get("title") or "").strip()
                    if kw:
                        keywords.append(kw)
                for kw in orch.get("keywords", []):
                    if kw and kw not in keywords:
                        keywords.append(kw)
        except Exception as e:
            meta["errors"].append(f"orchestrator: {e}")

    if len(keywords) < 2:
        try:
            from app.moduller.category_hub import talon_keywords as tk
            fav = tk(limit=limit).get("keywords") or []
            keywords.extend(fav)
            meta["favorites"] = len(fav)
        except Exception as e:
            meta["errors"].append(f"talon_favorites: {e}")
        try:
            from app.moduller.talon import anahtar_kelime_uret
            generated, _ = anahtar_kelime_uret(
                seed or location, min(limit, 15), location or "kuşadası", sektor="gece_hayati"
            )
            if isinstance(generated, list):
                for item in generated:
                    if isinstance(item, dict):
                        keywords.append(str(item.get("kelime") or item.get("keyword") or item.get("text") or ""))
                    else:
                        keywords.append(str(item))
                meta["generated"] = len(generated)
        except Exception as e:
            meta["errors"].append(f"talon_generate: {e}")

    if seed:
        keywords.insert(0, seed)
    seen: set[str] = set()
    out: list[str] = []
    for kw in keywords:
        text = str(kw or "").strip()
        if not text:
            continue
        key = text.lower()
        if key not in seen:
            seen.add(key)
            out.append(text)
    return out[:limit], meta


def _generate_landing_content(keyword: str, location: str, niche: str, source_site: str) -> dict[str, Any]:
    from app.moduller.page_hub import _generate_landing_html
    city = "Aydın"
    district = location or "Kuşadası"
    landing = _generate_landing_html(keyword, city, district)
    intro = (
        f"<p>{district} bölgesinde {keyword} hakkında yerel rehber bilgileri. "
        f"Daha fazla içerik için ana kaynağımızı ziyaret edin: "
        f'<a href="{source_site}" rel="noopener">{source_site}</a>.</p>'
    )
    html = intro + (landing.get("html") or "")
    return {
        "title": landing.get("seo_title") or f"{district} {keyword.title()} Rehberi",
        "description": landing.get("meta_description") or f"{district} {keyword} rehberi",
        "slug": _safe_slug(keyword),
        "content_html": html,
        "schema_type": "WebPage",
    }


def _main_site(project: dict[str, Any]) -> str:
    return (project.get("main_site_url") or project.get("source_site") or "https://www.balkutusu.com").strip()


def _generate_blog_content(topic: str, location: str, source_site: str) -> dict[str, Any]:
    from app.moduller import llm_router
    prompt = f"""BalKutusu kaynaklı bir blog yazısı yaz.
Konu: {topic}
Lokasyon: {location}
Ana site referansı: {source_site}

Format:
Başlık: (max 70 karakter)
Özet: (max 155 karakter)
İçerik: (HTML <h2> ve <p>, 250-400 kelime, özgün, bilgilendirici)
Kaynak paragrafı sonunda ana site linki ekle."""
    raw, engine = llm_router.generate(prompt, max_tokens=2000, min_length=200)
    if not raw or len(raw.strip()) < 80:
        raise RuntimeError(f"LLM blog içeriği üretemedi: {topic}")
    title = topic.title()[:70]
    excerpt = f"{location} bölgesinde {topic} hakkında yerel rehber."[:155]
    body = ""
    if raw:
        m = re.search(r"Başlık\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            title = m.group(1).strip()[:70]
        m = re.search(r"Özet\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            excerpt = m.group(1).strip()[:155]
        m = re.search(r"İçerik\s*[:\-]\s*(.+)", raw, re.S | re.I)
        if m:
            body = m.group(1).strip()
    if source_site and source_site not in body:
        body += f'<p class="source-ref">Kaynak: <a href="{source_site}" rel="noopener">{source_site}</a></p>'
    return {
        "title": title,
        "description": excerpt,
        "slug": _safe_slug(topic),
        "content_html": body,
        "schema_type": "Article",
        "ai_engine": engine or "",
    }


def health() -> dict[str, Any]:
    npm = _check_npm()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "success": True,
        "status": "ok",
        "template_exists": TEMPLATE_DIR.is_dir(),
        "template_path": str(TEMPLATE_DIR),
        "generated_dir": str(GENERATED_DIR.resolve()),
        "generated_dir_writable": os.access(GENERATED_DIR, os.W_OK) if GENERATED_DIR.exists() else False,
        "npm": npm,
        "project_count": len(_load_state().get("projects", {})),
        "deployment_targets": DEPLOYMENT_TARGETS,
    }


def create_project(payload: dict[str, Any]) -> dict[str, Any]:
    site_name = (payload.get("site_name") or "").strip()
    raw_domain = (payload.get("domain") or "").strip()
    seed = (payload.get("seed_keyword") or site_name).strip()
    if not site_name:
        return {"success": False, "error": "Site adı gerekli"}

    slug = _safe_slug(payload.get("slug") or site_name)
    project_id = str(uuid.uuid4())[:12]
    project_path = _project_path(slug)
    domain = _normalize_domain(raw_domain) or f"https://{slug}.com"
    main_site = (
        payload.get("main_site_url") or payload.get("source_site") or "https://www.balkutusu.com"
    ).strip()

    project = {
        "id": project_id,
        "slug": slug,
        "site_name": site_name,
        "domain": domain,
        "seed_keyword": seed,
        "location": (payload.get("location") or "Kuşadası").strip(),
        "niche": (payload.get("niche") or "Yerel rehber").strip(),
        "language": (payload.get("language") or "tr").strip(),
        "main_site_url": main_site,
        "source_site": main_site,
        "deploy_target": (payload.get("deploy_target") or "cloudflare_pages").strip(),
        "status": "draft",
        "plan": None,
        "pages": [],
        "created_at": _now(),
        "updated_at": _now(),
        "path": f"generated-sites/{slug}",
        "build_log": "",
        "export_path": "",
        "dist_exists": False,
        "cloudflare": None,
        "deployments": [],
    }

    _scaffold_project(project_path, project)

    state = _load_state()
    state.setdefault("projects", {})[project_id] = project
    _save_state(state)
    watcher_hook: dict[str, Any] = {}
    try:
        from app.moduller.rank_index_watcher import on_astro_project_created
        watcher_hook = on_astro_project_created(project_id, domain)
    except Exception as exc:
        logger.debug("Rank watcher hook atlandı: %s", exc)
    return {
        "success": True,
        "project": project,
        "filesystem_path": str(project_path.resolve()),
        "package_json_exists": (project_path / "package.json").is_file(),
        "rank_watcher": watcher_hook,
    }


def generate_site_plan(
    seed_keyword: str,
    location: str = "Kuşadası",
    niche: str = "Yerel rehber",
    page_count: int = 10,
    project_id: str = "",
    domain: str = "",
) -> dict[str, Any]:
    seed = (seed_keyword or "").strip()
    if not seed:
        return {"success": False, "error": "seed_keyword gerekli"}

    keywords, talon_meta = _talon_keywords(seed, location, limit=max(page_count, 10))
    if len(keywords) < 1:
        return {"success": False, "error": "Talon kelime üretilemedi", "talon": talon_meta}

    main_pages = [
        {"title": "Ana Sayfa", "slug": "", "type": "home"},
        {"title": "Hakkında", "slug": "hakkimizda", "type": "about"},
        {"title": "İletişim", "slug": "iletisim", "type": "contact"},
    ]
    orch_geo = talon_meta.get("geo_pages") or []
    if orch_geo:
        geo_pages = [
            {
                "title": (gp.get("title") or f"{location} {gp.get('keyword', '')}").strip(),
                "slug": gp.get("slug") or _safe_slug(gp.get("keyword") or gp.get("title") or ""),
                "keyword": gp.get("keyword") or gp.get("title") or "",
                "type": "geo",
            }
            for gp in orch_geo[: max(3, page_count - 5)]
        ]
    else:
        geo_pages = [
            {"title": f"{location} {kw.title()}", "slug": _safe_slug(kw), "keyword": kw, "type": "geo"}
            for kw in keywords[: max(3, page_count - 5)]
        ]

    graph_hints: dict[str, Any] = {}
    try:
        from app.moduller.entity_geo_graph import get_astro_plan_suggestions
        graph_hints = get_astro_plan_suggestions(seed, location, project_id=project_id)
        for rec in graph_hints.get("recommended_pages") or []:
            slug = rec.get("slug") or _safe_slug(rec.get("target_keyword") or rec.get("title") or "")
            if slug and not any(g.get("slug") == slug for g in geo_pages):
                geo_pages.append({
                    "title": rec.get("title") or slug.replace("-", " ").title(),
                    "slug": slug,
                    "keyword": rec.get("target_keyword") or rec.get("entity") or "",
                    "type": "geo",
                    "source": "entity_geo_graph",
                })
    except Exception as exc:
        logger.debug("Entity GEO Graph plan önerisi atlandı: %s", exc)

    briefs = talon_meta.get("content_briefs") or []
    faq_kw: list[str] = []
    for b in briefs:
        faq_kw.extend(b.get("faq_questions", [])[:2])
    if not faq_kw:
        faq_kw = keywords[:3]
    faq_pages = [
        {"title": f"{(kw if isinstance(kw, str) else str(kw)).rstrip('?').title()} SSS",
         "slug": _safe_slug(f"{kw}-sss"), "keyword": kw, "type": "faq"}
        for kw in faq_kw[:3]
    ]
    blog_posts = [
        {"title": f"{location} — {kw.title()}", "slug": _safe_slug(f"blog-{kw}"), "topic": kw, "type": "blog"}
        for kw in keywords[3:6]
    ]

    clusters: list[dict[str, Any]] = []
    if geo_pages:
        clusters.append({
            "pillar": geo_pages[0]["slug"],
            "cluster": [p["slug"] for p in geo_pages[1:4]],
            "topic": seed,
        })

    internal_link_map: list[dict[str, str]] = []
    for i, gp in enumerate(geo_pages):
        if i + 1 < len(geo_pages):
            internal_link_map.append({"from": gp["slug"], "to": geo_pages[i + 1]["slug"], "anchor": geo_pages[i + 1]["title"]})
        if faq_pages:
            internal_link_map.append({"from": gp["slug"], "to": faq_pages[0]["slug"], "anchor": "Sık Sorulan Sorular"})

    schema_plan = [
        {"page": "home", "schema": "WebSite"},
        {"page": "geo", "schema": "WebPage"},
        {"page": "faq", "schema": "FAQPage"},
        {"page": "blog", "schema": "Article"},
    ]

    site_name = f"{location} {seed.title()}"
    plan = {
        "project_id": project_id,
        "site_name": site_name,
        "domain": domain or f"https://{_safe_slug(site_name)}.example.com",
        "seed_keyword": seed,
        "locations": [location],
        "main_pages": main_pages,
        "geo_pages": geo_pages,
        "faq_pages": faq_pages,
        "blog_posts": blog_posts,
        "content_clusters": clusters,
        "internal_link_map": internal_link_map,
        "schema_plan": schema_plan,
        "deployment_targets": DEPLOYMENT_TARGETS,
        "talon_keywords_used": keywords,
        "talon_meta": talon_meta,
    }

    if project_id:
        _update_project(project_id, plan=plan, status="planned")

    return {"success": True, "plan": plan, "entity_geo_graph": graph_hints}


def _apply_template_vars(project_path: Path, project: dict[str, Any]) -> None:
    domain = _normalize_domain(project.get("domain", "")) or "https://example.com"
    cfg = project_path / "astro.config.mjs"
    if cfg.exists():
        text = cfg.read_text(encoding="utf-8")
        text = text.replace("{{SITE_URL}}", domain)
        text = text.replace("{{SITE_NAME}}", project.get("site_name", "HIVE Site"))
        cfg.write_text(text, encoding="utf-8")


def _copy_template(project_path: Path, project: dict[str, Any]) -> None:
    if not TEMPLATE_DIR.is_dir():
        raise FileNotFoundError(f"Astro şablonu yok: {TEMPLATE_DIR}")
    if project_path.exists():
        shutil.rmtree(project_path)
    shutil.copytree(TEMPLATE_DIR, project_path)
    _apply_template_vars(project_path, project)


def _scaffold_project(project_path: Path, project: dict[str, Any]) -> None:
    """create-project anında gerçek Astro klasörü oluştur."""
    _copy_template(project_path, project)
    home = {
        "title": project.get("site_name"),
        "description": f"{project.get('location')} — {project.get('seed_keyword')}",
        "content_html": (
            f"<h1>{project.get('site_name')}</h1>"
            f"<p>{project.get('location')} bölgesinde {project.get('seed_keyword')} rehberi hazırlanıyor.</p>"
            f'<p>Kaynak: <a href="{_main_site(project)}" rel="noopener">{_main_site(project)}</a></p>'
        ),
    }
    _write_project_data(project_path, project, home_page=home, geo_pages=[], faq_pages=[], blog_pages=[])


def _write_project_data(
    project_path: Path,
    project: dict[str, Any],
    home_page: dict[str, Any],
    geo_pages: list[dict[str, Any]],
    faq_pages: list[dict[str, Any]],
    blog_pages: list[dict[str, Any]],
) -> None:
    data_dir = project_path / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    domain = _normalize_domain(project.get("domain", ""))
    main_site = _main_site(project)

    pages_json = {
        "site_name": project.get("site_name"),
        "domain": domain,
        "main_site_url": main_site,
        "language": project.get("language", "tr"),
        "home": {
            "title": home_page.get("title"),
            "description": home_page.get("description", ""),
            "content_html": home_page.get("content_html", ""),
        },
        "geo": [
            {
                "slug": p["slug"],
                "title": p.get("title", ""),
                "description": p.get("description", ""),
                "content_html": p.get("content_html", ""),
                "schema": p.get("schema"),
                "keyword": p.get("keyword", ""),
            }
            for p in geo_pages
        ],
    }
    faqs_json = [
        {
            "slug": p["slug"],
            "title": p.get("title", ""),
            "description": p.get("description", ""),
            "content_html": p.get("content_html", ""),
            "schema": p.get("schema"),
            "keyword": p.get("keyword", ""),
        }
        for p in faq_pages
    ]
    blog_json = [
        {
            "slug": p["slug"],
            "title": p.get("title", ""),
            "description": p.get("description", ""),
            "content_html": p.get("content_html", ""),
            "ai_engine": p.get("ai_engine", ""),
            "topic": p.get("topic", p.get("keyword", "")),
        }
        for p in blog_pages
    ]

    (data_dir / "pages.json").write_text(json.dumps(pages_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "faqs.json").write_text(json.dumps(faqs_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "blog.json").write_text(json.dumps(blog_json, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_geo_pages(project_id: str, keywords: list[str] | None = None, locations: list[str] | None = None) -> dict[str, Any]:
    project = _get_project(project_id)
    plan = project.get("plan") or {}
    loc = (locations or plan.get("locations") or [project.get("location", "Kuşadası")])[0]
    kws = keywords or [p.get("keyword", "") for p in plan.get("geo_pages", []) if p.get("keyword")]
    if not kws:
        kws, _ = _talon_keywords(project.get("seed_keyword", ""), loc, 5)

    pages = list(project.get("pages") or [])
    created: list[dict[str, Any]] = []
    source = _main_site(project)
    niche = project.get("niche", "Yerel rehber")

    for kw in kws:
        if not kw:
            continue
        page = _generate_landing_content(kw, loc, niche, source)
        page["type"] = "geo"
        page["keyword"] = kw
        pages = [p for p in pages if p.get("slug") != page["slug"]]
        pages.append(page)
        created.append(page)

    _update_project(project_id, pages=pages, status="generated")
    return {"success": True, "created": len(created), "pages": created}


def generate_faq_pages(project_id: str, questions: list[str] | None = None) -> dict[str, Any]:
    project = _get_project(project_id)
    plan = project.get("plan") or {}
    loc = project.get("location", "Kuşadası")
    city = "Aydın"
    category = project.get("niche", "Gece Hayatı")
    kws = questions or [p.get("keyword", "") for p in plan.get("faq_pages", []) if p.get("keyword")]
    if not kws:
        kws = [project.get("seed_keyword", "yerel rehber")]

    pages = list(project.get("pages") or [])
    created: list[dict[str, Any]] = []

    for kw in kws:
        if not kw:
            continue
        sss = generate_sss_page(city, loc, category, category, kw)
        page = {
            "title": sss.get("seo_title") or f"{kw} SSS",
            "description": sss.get("meta_description", ""),
            "slug": sss.get("slug") or _safe_slug(f"{kw}-sss"),
            "content_html": sss.get("html") or build_html(sss),
            "schema_type": "FAQPage",
            "schema": sss.get("schema"),
            "type": "faq",
            "keyword": kw,
        }
        pages = [p for p in pages if p.get("slug") != page["slug"]]
        pages.append(page)
        created.append(page)

    _update_project(project_id, pages=pages, status="generated")
    return {"success": True, "created": len(created), "pages": created}


def generate_blog_posts(project_id: str, topics: list[str] | None = None) -> dict[str, Any]:
    project = _get_project(project_id)
    plan = project.get("plan") or {}
    loc = project.get("location", "Kuşadası")
    source = _main_site(project)
    topic_list = topics or [p.get("topic", "") for p in plan.get("blog_posts", []) if p.get("topic")]
    if not topic_list:
        topic_list, _ = _talon_keywords(project.get("seed_keyword", ""), loc, 3)

    pages = list(project.get("pages") or [])
    created: list[dict[str, Any]] = []

    errors: list[str] = []
    for topic in topic_list:
        if not topic:
            continue
        try:
            blog = _generate_blog_content(topic, loc, source)
            blog["type"] = "blog"
            blog["slug"] = _safe_slug(topic)
            blog["topic"] = topic
            pages = [p for p in pages if p.get("slug") != blog["slug"]]
            pages.append(blog)
            created.append(blog)
        except RuntimeError as e:
            errors.append(str(e))

    _update_project(project_id, pages=pages, status="generated")
    return {"success": len(created) > 0 or not errors, "created": len(created), "pages": created, "errors": errors}


def generate_internal_links(project_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    plan = project.get("plan") or {}
    pages = list(project.get("pages") or [])
    link_map = list(plan.get("internal_link_map") or [])

    if not link_map and len(pages) > 1:
        for i, p in enumerate(pages[:-1]):
            nxt = pages[i + 1]
            link_map.append({"from": p.get("slug", ""), "to": nxt.get("slug", ""), "anchor": nxt.get("title", "")})

    slug_to_page = {p.get("slug"): p for p in pages}
    for link in link_map:
        src = slug_to_page.get(link.get("from", ""))
        if not src:
            continue
        href = f"/{link['to']}" if link.get("to") else "/"
        block = f'<p class="internal-link"><a href="{href}">{link.get("anchor", link["to"])}</a></p>'
        html = src.get("content_html") or ""
        if href not in html:
            src["content_html"] = html + block

    _update_project(project_id, pages=pages, plan={**plan, "internal_link_map": link_map})
    return {"success": True, "internal_link_map": link_map, "updated_pages": len(pages)}


def generate_schema_files(project_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    project_path = _project_path(project["slug"])
    public = project_path / "public"
    public.mkdir(parents=True, exist_ok=True)

    domain = (project.get("domain") or "").rstrip("/")
    schemas: list[dict[str, Any]] = []

    website_schema = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": project.get("site_name"),
        "url": domain,
        "potentialAction": {"@type": "SearchAction", "target": f"{domain}/?q={{search_term_string}}"},
    }
    schemas.append(website_schema)

    for page in project.get("pages") or []:
        if page.get("schema"):
            schemas.append(page["schema"])
            continue
        st = page.get("schema_type", "WebPage")
        entry: dict[str, Any] = {
            "@context": "https://schema.org",
            "@type": st,
            "name": page.get("title"),
            "description": page.get("description"),
            "url": f"{domain}/{page.get('slug', '')}".rstrip("/") or domain,
        }
        if st == "Article":
            entry["author"] = {"@type": "Organization", "name": project.get("site_name")}
        schemas.append(entry)

    (public / "schema.json").write_text(json.dumps(schemas, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_project(project_id, schemas_count=len(schemas))
    return {"success": True, "schemas": len(schemas), "path": str(public / "schema.json")}


def generate_sitemap(project_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    project_path = _project_path(project["slug"])
    public = project_path / "public"
    public.mkdir(parents=True, exist_ok=True)

    domain = _normalize_domain(project.get("domain", ""))
    urls = [
        f"  <url><loc>{domain}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>",
        f"  <url><loc>{domain}/sss</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>",
        f"  <url><loc>{domain}/blog</loc><changefreq>weekly</changefreq><priority>0.7</priority></url>",
    ]
    for page in project.get("pages") or []:
        slug = page.get("slug", "")
        ptype = page.get("type", "")
        if not slug:
            continue
        prefix = {"geo": "geo", "faq": "sss", "blog": "blog"}.get(ptype, "")
        path = f"{prefix}/{slug}" if prefix else slug
        urls.append(
            f"  <url><loc>{domain}/{path}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>"
        )
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += "\n".join(urls) + "\n</urlset>\n"
    (public / "sitemap.xml").write_text(xml, encoding="utf-8")
    return {"success": True, "url_count": len(urls), "path": str(public / "sitemap.xml")}


def generate_robots(project_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    project_path = _project_path(project["slug"])
    public = project_path / "public"
    public.mkdir(parents=True, exist_ok=True)

    domain = (project.get("domain") or "").rstrip("/")
    robots = f"User-agent: *\nAllow: /\nSitemap: {domain}/sitemap.xml\n"
    (public / "robots.txt").write_text(robots, encoding="utf-8")
    return {"success": True, "path": str(public / "robots.txt")}


def generate_pages(project_id: str) -> dict[str, Any]:
    """Plan + tüm içerik + gerçek Astro dosyaları."""
    project = _get_project(project_id)
    if not project.get("plan"):
        plan_res = generate_site_plan(
            project.get("seed_keyword", ""),
            project.get("location", "Kuşadası"),
            project.get("niche", ""),
            page_count=10,
            project_id=project_id,
            domain=project.get("domain", ""),
        )
        if not plan_res.get("success"):
            return plan_res

    geo_res = generate_geo_pages(project_id)
    faq_res = generate_faq_pages(project_id)
    blog_res = generate_blog_posts(project_id)
    generate_internal_links(project_id)

    project = _get_project(project_id)
    project_path = _project_path(project["slug"])
    if not project_path.is_dir():
        _scaffold_project(project_path, project)

    home_page = {
        "title": project.get("site_name"),
        "description": f"{project.get('location')} — {project.get('seed_keyword')} yerel rehber",
        "slug": "",
        "content_html": (
            f"<h1>{project.get('site_name')}</h1>"
            f"<p>{project.get('location')} bölgesinde {project.get('seed_keyword')} hakkında özgün yerel içerikler.</p>"
            f'<p>Kaynak: <a href="{_main_site(project)}" rel="noopener">{_main_site(project)}</a></p>'
        ),
        "type": "home",
        "schema_type": "WebSite",
    }

    all_pages = list(project.get("pages") or [])
    geo_pages = [p for p in all_pages if p.get("type") == "geo"]
    faq_pages = [p for p in all_pages if p.get("type") == "faq"]
    blog_pages = [p for p in all_pages if p.get("type") == "blog"]

    _write_project_data(project_path, project, home_page, geo_pages, faq_pages, blog_pages)
    _apply_template_vars(project_path, project)

    generate_schema_files(project_id)
    generate_sitemap(project_id)
    generate_robots(project_id)

    readme = _build_readme(project)
    (project_path / "README.md").write_text(readme, encoding="utf-8")

    files_written = [
        "package.json", "astro.config.mjs", "src/data/pages.json",
        "src/data/faqs.json", "src/data/blog.json", "public/robots.txt",
        "public/sitemap.xml", "README.md",
    ]
    _update_project(project_id, status="generated", pages=[home_page, *all_pages], dist_exists=False)
    return {
        "success": True,
        "project_id": project_id,
        "path": str(project_path.resolve()),
        "page_count": len(all_pages) + 1,
        "geo_count": len(geo_pages),
        "faq_count": len(faq_pages),
        "blog_count": len(blog_pages),
        "files_written": files_written,
        "content_errors": (blog_res.get("errors") or []) if isinstance(blog_res, dict) else [],
    }


def build_astro_project(project_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    project_path = _project_path(project["slug"])
    if not project_path.is_dir() or not (project_path / "package.json").is_file():
        return {"success": False, "error": "Proje klasörü yok — önce generate-pages çalıştırın"}

    npm = _check_npm()
    if not npm.get("available"):
        return {"success": False, "error": "npm bulunamadı — Node.js kurulu olmalı"}

    log_lines: list[str] = []
    for cmd in (
        ["npm", "install", "--no-audit"],
        ["npm", "run", "build"],
    ):
        try:
            r = subprocess.run(
                cmd,
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=BUILD_TIMEOUT_SEC,
                shell=False,
            )
            log_lines.append(f"$ {' '.join(cmd)}\nexit={r.returncode}\n--- stdout ---\n{r.stdout[-2000:]}\n--- stderr ---\n{r.stderr[-2000:]}")
            if r.returncode != 0:
                log_text = "\n".join(log_lines)[-8000:]
                _update_project(project_id, status="generated", build_log=log_text, dist_exists=False)
                return {
                    "success": False,
                    "error": f"Komut başarısız: {' '.join(cmd)} (exit {r.returncode})",
                    "build_log": log_text,
                    "dist_exists": False,
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Build zaman aşımı ({BUILD_TIMEOUT_SEC}s)", "dist_exists": False}

    dist_ok = _dist_ready(project_path)
    log_text = "\n".join(log_lines)[-8000:]
    if not dist_ok:
        _update_project(project_id, status="generated", build_log=log_text, dist_exists=False)
        return {
            "success": False,
            "error": "npm run build tamamlandı ama dist/index.html bulunamadı",
            "build_log": log_text,
            "dist_exists": False,
            "dist_path": str(project_path / "dist"),
        }

    _update_project(project_id, status="built", build_log=log_text, dist_exists=True)
    return {
        "success": True,
        "status": "built",
        "dist": str((project_path / "dist").resolve()),
        "dist_exists": True,
        "build_log": log_text,
    }


def export_project(project_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    project_path = _project_path(project["slug"])
    if not project_path.is_dir():
        return {"success": False, "error": "Proje dosyaları yok — önce generate-pages çalıştırın"}

    export_name = f"{project['slug']}-export"
    zip_base = GENERATED_DIR / export_name
    zip_path = GENERATED_DIR / f"{export_name}.zip"

    if zip_path.exists():
        zip_path.unlink()

    shutil.make_archive(str(zip_base), "zip", root_dir=str(project_path))

    deploy_notes = _deploy_instructions(project)
    _update_project(project_id, status="exported", export_path=str(zip_path))

    return {
        "success": True,
        "export_path": str(zip_path),
        "deploy_instructions": deploy_notes,
        "targets": DEPLOYMENT_TARGETS,
    }


def _deploy_instructions(project: dict[str, Any]) -> dict[str, str]:
    slug = project.get("slug", "site")
    domain = project.get("domain", "")
    return {
        "cloudflare_pages": (
            f"Cloudflare Pages → Create project → Upload dist/ veya Git repo bağla.\n"
            f"Build: npm run build | Output: dist | Root: generated-sites/{slug}"
        ),
        "github_pages": (
            f"GitHub repo oluştur → generated-sites/{slug} push → "
            f"Settings → Pages → Source: GitHub Actions veya /docs (dist içeriği)"
        ),
        "vps": (
            f"rsync -avz dist/ user@server:/var/www/{slug}/\n"
            f"Nginx server_name {domain.replace('https://', '')}; root /var/www/{slug};"
        ),
    }


def _build_readme(project: dict[str, Any]) -> str:
    slug = project.get("slug", "site")
    domain = project.get("domain", "https://example.com")
    return f"""# {project.get('site_name')}

HIVE Astro Site Factory ile üretilmiş SEO uyumlu statik site.

## Yerel çalıştırma

```bash
cd generated-sites/{slug}
npm install
npm run dev
```

## Production build

```bash
npm run build
# Çıktı: dist/
```

## Deploy

### Cloudflare Pages
- Build command: `npm run build`
- Output directory: `dist`
- Site URL: {domain}

### GitHub Pages
- `dist/` içeriğini `gh-pages` branch'e push edin veya GitHub Actions kullanın.

### VPS
```bash
npm run build
rsync -avz dist/ user@server:/var/www/{slug}/
```

## SEO
- canonical, OpenGraph, JSON-LD schema
- robots.txt ve sitemap.xml → public/
- Ana kaynak: {_main_site(project)}

Üretim: HIVE Astro Site Factory — {simdi()}
"""


def list_projects() -> dict[str, Any]:
    state = _load_state()
    projects: list[dict[str, Any]] = []
    for p in state.get("projects", {}).values():
        row = dict(p)
        try:
            path = _project_path(row["slug"])
            row["filesystem_path"] = str(path.resolve())
            row["dist_exists"] = _dist_ready(path)
        except ValueError:
            row["dist_exists"] = False
        projects.append(row)
    projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    return {"success": True, "projects": projects, "count": len(projects)}


def get_project(project_id: str) -> dict[str, Any]:
    proj = _get_project(project_id)
    try:
        path = _project_path(proj["slug"])
        proj = {
            **proj,
            "filesystem_path": str(path.resolve()),
            "dist_exists": _dist_ready(path),
            "package_json_exists": (path / "package.json").is_file(),
        }
    except ValueError:
        pass
    return {"success": True, "project": proj}


def delete_project(project_id: str) -> dict[str, Any]:
    state = _load_state()
    proj = state.get("projects", {}).pop(project_id, None)
    if not proj:
        return {"success": False, "error": "Proje bulunamadı"}
    _save_state(state)
    try:
        path = _project_path(proj["slug"])
        if path.is_dir():
            shutil.rmtree(path)
    except (ValueError, OSError) as e:
        logger.warning("Proje dizini silinemedi: %s", e)
    zip_path = GENERATED_DIR / f"{proj['slug']}-export.zip"
    if zip_path.exists():
        zip_path.unlink(missing_ok=True)
    return {"success": True, "deleted": project_id}


def cloudflare_status() -> dict[str, Any]:
    from app.moduller.cloudflare_pages_deploy import cf_status
    return cf_status()


def cloudflare_create_project(local_project_id: str, cloudflare_project_name: str = "") -> dict[str, Any]:
    from app.moduller.cloudflare_pages_deploy import create_pages_project
    return create_pages_project(local_project_id, cloudflare_project_name)


def cloudflare_deploy(local_project_id: str) -> dict[str, Any]:
    from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare
    return deploy_to_cloudflare(local_project_id)


def cloudflare_deployments(local_project_id: str) -> dict[str, Any]:
    from app.moduller.cloudflare_pages_deploy import get_deployments
    return get_deployments(local_project_id)


astro_factory = type("AstroFactory", (), {
    "health": staticmethod(health),
    "create_project": staticmethod(create_project),
    "generate_site_plan": staticmethod(generate_site_plan),
    "generate_geo_pages": staticmethod(generate_geo_pages),
    "generate_faq_pages": staticmethod(generate_faq_pages),
    "generate_blog_posts": staticmethod(generate_blog_posts),
    "generate_internal_links": staticmethod(generate_internal_links),
    "generate_schema_files": staticmethod(generate_schema_files),
    "generate_sitemap": staticmethod(generate_sitemap),
    "generate_robots": staticmethod(generate_robots),
    "generate_pages": staticmethod(generate_pages),
    "build_astro_project": staticmethod(build_astro_project),
    "export_project": staticmethod(export_project),
    "list_projects": staticmethod(list_projects),
    "get_project": staticmethod(get_project),
    "delete_project": staticmethod(delete_project),
    "cloudflare_status": staticmethod(cloudflare_status),
    "cloudflare_create_project": staticmethod(cloudflare_create_project),
    "cloudflare_deploy": staticmethod(cloudflare_deploy),
    "cloudflare_deployments": staticmethod(cloudflare_deployments),
})()
