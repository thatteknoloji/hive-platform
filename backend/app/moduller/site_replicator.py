"""Site Replicator & Blueprint Engine — owned site clone, domain variant, competitor blueprint."""

from __future__ import annotations

import ipaddress
import json
import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from app.moduller.storyforge_categories import _slugify

logger = logging.getLogger("hive.site_replicator")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
GENERATED_DIR = ROOT / "generated-sites"
STATE_FILE = Path(__file__).resolve().parent.parent / "site_replicator_state.json"
REPORTS_DIR = ROOT / "reports"

COPY_EXCLUDE = {"node_modules", "dist", ".git", ".astro", "__pycache__"}

DOMAIN_ROLES = {
    "faq_center": {"focus": "faq", "niche_suffix": "SSS Merkezi", "seed_suffix": "sık sorulan sorular"},
    "blog_center": {"focus": "blog", "niche_suffix": "Blog Rehberi", "seed_suffix": "blog rehberi"},
    "entity_center": {"focus": "entity", "niche_suffix": "Entity Bilgi Merkezi", "seed_suffix": "entity rehber"},
    "geo_support": {"focus": "geo", "niche_suffix": "GEO Destek", "seed_suffix": "geo rehber"},
    "brand_support": {"focus": "brand", "niche_suffix": "Marka Destek", "seed_suffix": "marka rehberi"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("jobs", {})
                data.setdefault("blueprints", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"jobs": {}, "blueprints": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _new_job_id() -> str:
    return f"sr-{uuid.uuid4().hex[:12]}"


def _safe_slug(raw: str) -> str:
    text = (raw or "").strip()
    if ".." in text or "\\" in text:
        raise ValueError("Path traversal engellendi")
    slug = _slugify(text.replace(".", "-") or "site")
    return slug[:80] or "site"


def _safe_project_path(slug: str) -> Path:
    safe = _safe_slug(slug)
    base = GENERATED_DIR.resolve()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    target = (GENERATED_DIR / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("generated-sites dışına yazılamaz")
    return target


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip()
    if not d:
        return ""
    if not d.startswith("http"):
        d = f"https://{d}"
    return d.rstrip("/")


def _is_blocked_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return "Sadece http/https URL desteklenir"
    host = (parsed.hostname or "").lower()
    if not host:
        return "Geçersiz URL"
    if host in ("localhost", "127.0.0.1", "0.0.0.0") or host.endswith(".local"):
        return "localhost/Private URL analiz engellendi"
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return "Private IP analiz engellendi"
    except ValueError:
        pass
    return None


def _get_source_project(project_id: str) -> tuple[dict[str, Any], Path]:
    from app.moduller.astro_factory import _get_project, _project_path
    project = _get_project(project_id)
    path = _project_path(project["slug"])
    if not path.is_dir():
        raise ValueError(f"Kaynak proje klasörü yok: {path}")
    return project, path


def _create_job(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    jid = _new_job_id()
    job = {
        "job_id": jid,
        "type": job_type,
        "status": "running",
        "started_at": _now(),
        "finished_at": "",
        "payload": payload,
        "summary": {},
        "items": [],
    }
    st = _load_state()
    st["jobs"][jid] = job
    _save_state(st)
    return job


def _finish_job(job_id: str, status: str, **fields: Any) -> dict[str, Any]:
    st = _load_state()
    job = st["jobs"].get(job_id, {})
    job["status"] = status
    job["finished_at"] = _now()
    job.update(fields)
    st["jobs"][job_id] = job
    _save_state(st)
    return job


def _copy_owned_site(source_path: Path, target_path: Path) -> None:
    if target_path.exists():
        shutil.rmtree(target_path)

    def _ignore(_dir: str, names: list[str]) -> list[str]:
        return [n for n in names if n in COPY_EXCLUDE]

    shutil.copytree(source_path, target_path, ignore=_ignore)


def _rewrite_text(text: str, context: str, seed: str = "") -> str:
    if not text or len(text.strip()) < 20:
        return text
    prompt = (
        f"Bağlam: {context}\nSeed: {seed}\n"
        "Aşağıdaki HTML/metni tamamen özgün Türkçe ile yeniden yaz. Marka/kopya tekrarı yapma.\n"
        "Sadece HTML/metin döndür:\n\n" + text[:4000]
    )
    try:
        from app.moduller import llm_router
        out, _ = llm_router.generate(prompt, max_tokens=2500, min_length=100)
        if out and len(out.strip()) > 40:
            return out.strip()
    except Exception as exc:
        logger.warning("LLM rewrite: %s", exc)
    return text


def _update_domain_meta(project_path: Path, domain: str, site_name: str, main_site_url: str) -> None:
    domain = _normalize_domain(domain)
    data_dir = project_path / "src" / "data"
    if not data_dir.is_dir():
        return

    for fname in ("pages.json",):
        fp = data_dir / fname
        if fp.exists():
            data = json.loads(fp.read_text(encoding="utf-8"))
            data["site_name"] = site_name
            data["domain"] = domain
            data["main_site_url"] = main_site_url
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    public = project_path / "public"
    public.mkdir(parents=True, exist_ok=True)
    robots = f"User-agent: *\nAllow: /\nSitemap: {domain}/sitemap.xml\n"
    (public / "robots.txt").write_text(robots, encoding="utf-8")

    sitemap = public / "sitemap.xml"
    if sitemap.exists():
        xml = sitemap.read_text(encoding="utf-8")
        xml = re.sub(r"https?://[^<\"']+", domain, xml)
        sitemap.write_text(xml, encoding="utf-8")
    else:
        sitemap.write_text(
            f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'  <url><loc>{domain}/</loc></url>\n</urlset>\n',
            encoding="utf-8",
        )


def _rewrite_data_files(project_path: Path, site_name: str, seed: str = "") -> int:
    data_dir = project_path / "src" / "data"
    if not data_dir.is_dir():
        return 0
    count = 0
    for fname in ("pages.json", "faqs.json", "blog.json", "entity_pages.json"):
        fp = data_dir / fname
        if not fp.exists():
            continue
        raw = json.loads(fp.read_text(encoding="utf-8"))

        def rewrite_entry(entry: dict[str, Any]) -> None:
            nonlocal count
            for key in ("content_html", "description", "title"):
                if entry.get(key):
                    entry[key] = _rewrite_text(str(entry[key]), f"{site_name} — {entry.get('title', '')}", seed)
                    count += 1

        if isinstance(raw, dict):
            if raw.get("home"):
                rewrite_entry(raw["home"])
            for g in raw.get("geo") or []:
                rewrite_entry(g)
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    rewrite_entry(item)
        fp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    return count


def _apply_theme_variation(project_path: Path) -> None:
    css_candidates = list(project_path.glob("src/**/*.css")) + list(project_path.glob("src/**/*.scss"))
    accent = uuid.uuid4().hex[:6]
    for css in css_candidates[:5]:
        try:
            content = css.read_text(encoding="utf-8")
            content = re.sub(r"--accent:\s*#[0-9a-fA-F]{3,8}", f"--accent: #{accent}", content, count=1)
            if "--accent:" not in content:
                content = f":root {{ --accent: #{accent}; --variant: {accent}; }}\n" + content
            css.write_text(content, encoding="utf-8")
        except OSError:
            pass


def _run_quality_gate_on_project(project_path: Path, min_score: int = 70) -> dict[str, Any]:
    from app.moduller.seo_quality_gate import seo_quality_gate
    data_dir = project_path / "src" / "data"
    results: list[dict[str, Any]] = []
    passed_all = True

    def check(html: str, title: str, kw: str) -> None:
        nonlocal passed_all
        if not html:
            return
        analysis = seo_quality_gate.analyze_page(html, kw or title, title=title)
        score = analysis.get("overall_score") or analysis.get("seo_score") or 0
        ok = bool(analysis.get("pass")) and score >= min_score
        if not ok:
            passed_all = False
        results.append({"title": title, "score": score, "passed": ok, "report_id": f"qg-{uuid.uuid4().hex[:8]}"})

    pages_fp = data_dir / "pages.json"
    if pages_fp.exists():
        pages = json.loads(pages_fp.read_text(encoding="utf-8"))
        home = pages.get("home") or {}
        check(home.get("content_html", ""), home.get("title", ""), pages.get("site_name", ""))
        for g in pages.get("geo") or []:
            check(g.get("content_html", ""), g.get("title", ""), g.get("keyword", ""))

    for fname in ("faqs.json", "blog.json", "entity_pages.json"):
        fp = data_dir / fname
        if not fp.exists():
            continue
        for item in json.loads(fp.read_text(encoding="utf-8")):
            if isinstance(item, dict):
                check(item.get("content_html", ""), item.get("title", ""), item.get("keyword", ""))

    return {"deploy_allowed": passed_all, "reports": results, "passed_count": sum(1 for r in results if r["passed"])}


def _register_astro_project(project: dict[str, Any]) -> None:
    from app.moduller.astro_factory import _load_state, _save_state
    state = _load_state()
    state.setdefault("projects", {})[project["id"]] = project
    _save_state(state)


def clone_owned_site(
    source_project_id: str,
    target_domain: str,
    target_site_name: str,
    *,
    content_strategy: str = "rewrite_all",
    theme_variation: bool = True,
    auto_build: bool = True,
    auto_deploy: bool = False,
    main_site_url: str = "https://www.balkutusu.com",
) -> dict[str, Any]:
    job = _create_job("clone_owned_site", {
        "source_project_id": source_project_id,
        "target_domain": target_domain,
        "target_site_name": target_site_name,
    })
    jid = job["job_id"]

    try:
        source, source_path = _get_source_project(source_project_id)
        target_slug = _safe_slug(target_domain.replace("https://", "").replace("http://", "").split("/")[0])
        target_path = _safe_project_path(target_slug)

        _copy_owned_site(source_path, target_path)

        domain = _normalize_domain(target_domain)
        _update_domain_meta(target_path, domain, target_site_name, main_site_url)

        rewritten = 0
        if content_strategy == "rewrite_all":
            rewritten = _rewrite_data_files(target_path, target_site_name, seed=target_slug)
        if theme_variation:
            _apply_theme_variation(target_path)

        gate = _run_quality_gate_on_project(target_path)

        new_id = str(uuid.uuid4())[:12]
        new_project = {
            **source,
            "id": new_id,
            "slug": target_slug,
            "site_name": target_site_name,
            "domain": domain,
            "main_site_url": main_site_url,
            "source_site": main_site_url,
            "status": "generated",
            "created_at": _now(),
            "updated_at": _now(),
            "path": f"generated-sites/{target_slug}",
            "cloned_from": source_project_id,
            "build_log": "",
            "dist_exists": False,
            "cloudflare": None,
            "deployments": [],
        }
        _register_astro_project(new_project)

        built = deployed = False
        build_result: dict[str, Any] = {}
        deploy_result: dict[str, Any] = {}

        if auto_build and gate.get("deploy_allowed"):
            from app.moduller.astro_factory import build_astro_project, generate_pages
            generate_pages(new_id)
            build_result = build_astro_project(new_id)
            built = bool(build_result.get("success"))

        if auto_deploy and built:
            from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare
            deploy_result = deploy_to_cloudflare(new_id)
            deployed = bool(deploy_result.get("success"))
            if deployed:
                _notify_rank_watcher(new_id, domain)

        summary = {
            "source_project_id": source_project_id,
            "target_project_id": new_id,
            "target_slug": target_slug,
            "target_path": str(target_path),
            "rewritten_fields": rewritten,
            "quality_gate": gate,
            "built": built,
            "deployed": deployed,
        }
        job = _finish_job(jid, "completed", summary=summary, target_project_id=new_id)
        return {"success": True, "job_id": jid, "summary": summary, "job": job, "compliance": {"owned_clone": True, "copied_assets": True}}
    except Exception as exc:
        _finish_job(jid, "failed", error=str(exc))
        return {"success": False, "error": str(exc), "job_id": jid}


def create_domain_variant(
    base_project_id: str,
    domain_role: str,
    target_domain: str,
    main_site_url: str = "https://www.balkutusu.com",
) -> dict[str, Any]:
    role = DOMAIN_ROLES.get(domain_role)
    if not role:
        return {"success": False, "error": f"Geçersiz domain_role: {domain_role}"}

    job = _create_job("create_domain_variant", {
        "base_project_id": base_project_id,
        "domain_role": domain_role,
        "target_domain": target_domain,
    })
    jid = job["job_id"]

    try:
        base, base_path = _get_source_project(base_project_id)
        target_slug = _safe_slug(f"{_safe_slug(base['slug'])}-{domain_role}")
        target_path = _safe_project_path(target_slug)
        _copy_owned_site(base_path, target_path)

        site_name = f"{base.get('site_name', '')} {role['niche_suffix']}".strip()
        domain = _normalize_domain(target_domain)
        _update_domain_meta(target_path, domain, site_name, main_site_url)
        _rewrite_data_files(target_path, site_name, seed=f"{domain_role}-{target_slug}")

        data_dir = target_path / "src" / "data"
        focus = role["focus"]
        if focus == "faq" and (data_dir / "pages.json").exists():
            pass
        elif focus == "entity":
            entity_src = base_path / "src" / "data" / "entity_pages.json"
            if entity_src.exists() and not (data_dir / "entity_pages.json").exists():
                shutil.copy2(entity_src, data_dir / "entity_pages.json")

        gate = _run_quality_gate_on_project(target_path)
        new_id = str(uuid.uuid4())[:12]
        new_project = {
            **base,
            "id": new_id,
            "slug": target_slug,
            "site_name": site_name,
            "domain": domain,
            "main_site_url": main_site_url,
            "niche": role["niche_suffix"],
            "seed_keyword": f"{base.get('seed_keyword', '')} {role['seed_suffix']}".strip(),
            "domain_role": domain_role,
            "status": "generated",
            "created_at": _now(),
            "updated_at": _now(),
            "path": f"generated-sites/{target_slug}",
            "variant_of": base_project_id,
            "dist_exists": False,
        }
        _register_astro_project(new_project)

        summary = {
            "domain_role": domain_role,
            "target_project_id": new_id,
            "target_domain": domain,
            "examples": {
                "faq_center": "balkutusu.info → SSS merkezi",
                "blog_center": "balkutusu.net → Blog rehberi",
                "entity_center": "balkutusu.org → Entity bilgi merkezi",
            }.get(domain_role, domain_role),
            "quality_gate": gate,
        }
        job = _finish_job(jid, "completed", summary=summary, target_project_id=new_id)
        return {"success": True, "job_id": jid, "summary": summary, "job": job}
    except Exception as exc:
        _finish_job(jid, "failed", error=str(exc))
        return {"success": False, "error": str(exc), "job_id": jid}


class _BlueprintParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.headings: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.schemas: list[str] = []
        self.nav_items: list[str] = []
        self.ctas: list[str] = []
        self._in_nav = False
        self._in_script_ld = False
        self._script_buf: list[str] = []
        self._current_tag = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._current_tag = tag
        ad = dict(attrs)
        if tag in ("h1", "h2", "h3", "h4"):
            self.headings.append({"level": tag, "text": ""})
        if tag == "a" and ad.get("href"):
            self.links.append({"href": ad["href"], "text": ""})
            cls = (ad.get("class") or "").lower()
            if "btn" in cls or "cta" in cls or "button" in cls:
                self.ctas.append(ad["href"])
        if tag == "nav":
            self._in_nav = True
        if tag == "script" and ad.get("type") == "application/ld+json":
            self._in_script_ld = True
            self._script_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav":
            self._in_nav = False
        if tag == "script" and self._in_script_ld:
            self._in_script_ld = False
            blob = "".join(self._script_buf).strip()
            if blob:
                self.schemas.append(blob[:500])

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self.headings and not self.headings[-1]["text"]:
            self.headings[-1]["text"] = text[:200]
        if self.links and not self.links[-1]["text"]:
            self.links[-1]["text"] = text[:120]
        if self._in_nav and text:
            self.nav_items.append(text[:80])
        if self._in_script_ld:
            self._script_buf.append(data)


def _fetch_robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        r = requests.get(robots_url, timeout=10, headers={"User-Agent": "HIVE-BlueprintBot/1.0"})
        if r.status_code != 200:
            return True
        path = parsed.path or "/"
        for line in r.text.splitlines():
            line = line.strip()
            if line.lower().startswith("disallow:"):
                dis = line.split(":", 1)[1].strip()
                if dis and path.startswith(dis):
                    return False
    except Exception:
        return True
    return True


def analyze_competitor_blueprint(url: str, *, max_pages: int = 1) -> dict[str, Any]:
    blocked = _is_blocked_url(url)
    if blocked:
        return {"success": False, "error": blocked}

    if not _fetch_robots_allowed(url):
        return {"success": False, "error": "robots.txt bu URL için disallow — analiz yapılmadı"}

    job = _create_job("analyze_competitor_blueprint", {"url": url})
    jid = job["job_id"]

    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "HIVE-BlueprintBot/1.0"})
        r.raise_for_status()
        html = r.text

        parser = _BlueprintParser()
        parser.feed(html[:200_000])

        url_patterns = list(dict.fromkeys(
            re.findall(r'href=["\'](/[^"\']+|https?://[^"\']+)["\']', html[:50_000])[:30]
        ))
        schema_types = []
        for s in parser.schemas:
            for m in re.finditer(r'"@type"\s*:\s*"([^"]+)"', s):
                schema_types.append(m.group(1))

        categories: list[str] = []
        for h in parser.headings:
            if h.get("level") in ("h2", "h3") and h.get("text"):
                categories.append(h["text"])

        blueprint = {
            "page_types": list(dict.fromkeys(re.findall(r"/(blog|sss|faq|geo|rehber|kategori|category)[/\w-]*", url, re.I))),
            "url_patterns": url_patterns[:20],
            "category_structure": categories[:15],
            "heading_structure": parser.headings[:20],
            "schema_patterns": list(dict.fromkeys(schema_types)),
            "internal_link_patterns": [
                {"href": l["href"], "anchor": l["text"][:60]}
                for l in parser.links if l["href"].startswith("/") or urlparse(l["href"]).netloc == urlparse(url).netloc
            ][:25],
            "menu_structure": list(dict.fromkeys(parser.nav_items))[:15],
            "cta_patterns": list(dict.fromkeys(parser.ctas))[:10],
            "content_gaps": [],
        }

        try:
            from app.moduller.entity_geo_graph import entity_geo_graph
            gaps = entity_geo_graph.missing_entities(seed_keyword=urlparse(url).netloc)
            blueprint["content_gaps"] = [p.get("title", "") for p in (gaps.get("recommended_pages") or [])[:8]]
        except Exception:
            pass

        bp_id = f"bp-{uuid.uuid4().hex[:10]}"
        st = _load_state()
        st["blueprints"][bp_id] = {"url": url, "blueprint": blueprint, "created_at": _now()}
        _save_state(st)

        compliance = {
            "copied_content": False,
            "copied_assets": False,
            "blueprint_only": True,
            "html_stored": False,
        }
        summary = {"blueprint_id": bp_id, "url": url}
        job = _finish_job(jid, "completed", summary=summary, blueprint=blueprint, compliance=compliance)
        return {
            "success": True,
            "job_id": jid,
            "blueprint_id": bp_id,
            "blueprint": blueprint,
            "compliance": compliance,
            "job": job,
        }
    except Exception as exc:
        _finish_job(jid, "failed", error=str(exc))
        return {"success": False, "error": str(exc), "job_id": jid}


def generate_original_template(
    blueprint_id: str,
    target_domain: str,
    site_name: str,
    main_site_url: str = "https://www.balkutusu.com",
    *,
    auto_build: bool = False,
) -> dict[str, Any]:
    st = _load_state()
    bp_entry = st.get("blueprints", {}).get(blueprint_id)
    if not bp_entry:
        return {"success": False, "error": "Blueprint bulunamadı"}

    job = _create_job("generate_original_template", {"blueprint_id": blueprint_id, "target_domain": target_domain})
    jid = job["job_id"]
    blueprint = bp_entry.get("blueprint") or {}

    try:
        from app.moduller.astro_factory import create_project, generate_pages, build_astro_project

        domain = _normalize_domain(target_domain)
        slug = _safe_slug(site_name or target_domain)
        seed = f"{site_name} {blueprint.get('category_structure', [''])[0] if blueprint.get('category_structure') else 'rehber'}"

        proj = create_project({
            "site_name": site_name,
            "slug": slug,
            "domain": domain,
            "seed_keyword": seed[:80],
            "main_site_url": main_site_url,
            "niche": "Özgün Blueprint Template",
        })
        if not proj.get("success"):
            return proj

        project_id = proj["project"]["id"]
        project_path = _safe_project_path(slug)

        geo_pages = []
        for i, cat in enumerate((blueprint.get("category_structure") or [])[:6]):
            title = f"{cat} — {site_name}"
            html = _rewrite_text(
                f"<h1>{title}</h1><p>{site_name} özgün {cat} rehberi. Ana otorite: {main_site_url}</p>",
                title, seed=f"bp-{i}",
            )
            geo_pages.append({
                "slug": _slugify(f"{cat}-{site_name}")[:60],
                "title": title,
                "content_html": html,
                "keyword": cat,
            })

        from app.moduller.astro_factory import _get_project, _project_path, _write_project_data
        project = _get_project(project_id)
        home_html = _rewrite_text(
            f"<h1>{site_name}</h1><p>Özgün yapı — rakip içeriği kopyalanmadı.</p>"
            f'<p><a href="{main_site_url}" rel="noopener">Ana site</a></p>',
            site_name, seed="home",
        )
        _write_project_data(
            _project_path(project["slug"]), project,
            home_page={"title": site_name, "description": site_name, "content_html": home_html},
            geo_pages=geo_pages, faq_pages=[], blog_pages=[],
        )
        _apply_theme_variation(project_path)
        gate = _run_quality_gate_on_project(project_path)
        generate_pages(project_id)

        built = False
        if auto_build and gate.get("deploy_allowed"):
            build_result = build_astro_project(project_id)
            built = bool(build_result.get("success"))

        summary = {
            "project_id": project_id,
            "blueprint_id": blueprint_id,
            "quality_gate": gate,
            "built": built,
            "compliance": {"copied_content": False, "copied_assets": False, "original_template": True},
        }
        job = _finish_job(jid, "completed", summary=summary, target_project_id=project_id)
        return {"success": True, "job_id": jid, "summary": summary, "job": job}
    except Exception as exc:
        _finish_job(jid, "failed", error=str(exc))
        return {"success": False, "error": str(exc), "job_id": jid}


def build_project(project_id: str) -> dict[str, Any]:
    from app.moduller.astro_factory import build_astro_project, generate_pages
    generate_pages(project_id)
    return build_astro_project(project_id)


def deploy_cloudflare(project_id: str) -> dict[str, Any]:
    from app.moduller.cloudflare_pages_deploy import deploy_to_cloudflare
    from app.moduller.astro_factory import _get_project
    result = deploy_to_cloudflare(project_id)
    if result.get("success"):
        project = _get_project(project_id)
        domain = project.get("domain", "")
        _notify_rank_watcher(project_id, domain)
    return result


def _notify_rank_watcher(project_id: str, domain: str) -> None:
    try:
        from app.moduller.rank_index_watcher import register_project, track_keyword
        d = urlparse(domain).netloc or domain.replace("https://", "").split("/")[0]
        register_project(project_id, d, source="site_replicator")
        project = __import__("app.moduller.astro_factory", fromlist=["_get_project"])._get_project(project_id)
        kw = project.get("seed_keyword", "")
        if kw:
            track_keyword(kw.lower(), d, save=True, project_id=project_id)
    except Exception as exc:
        logger.warning("Rank watcher: %s", exc)


def list_jobs(limit: int = 20) -> dict[str, Any]:
    jobs = list((_load_state().get("jobs") or {}).values())
    jobs.sort(key=lambda j: j.get("started_at", ""), reverse=True)
    return {"success": True, "jobs": jobs[:limit]}


def get_job_detail(job_id: str) -> dict[str, Any]:
    job = (_load_state().get("jobs") or {}).get(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    return {"success": True, "job": job}


def export_report(job_id: str) -> dict[str, Any]:
    job = (_load_state().get("jobs") or {}).get(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"site-replicator-{job_id}.json"
    report = {"exported_at": _now(), **job}
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_path": str(path), "report": report}


def health() -> dict[str, Any]:
    cf_ok = False
    try:
        from app.moduller.cloudflare_pages_deploy import cf_status
        cf_ok = bool(cf_status().get("configured"))
    except Exception:
        pass
    return {
        "success": True,
        "module": "site_replicator",
        "generated_sites_dir": str(GENERATED_DIR),
        "cloudflare_configured": cf_ok,
        "job_count": len(_load_state().get("jobs") or {}),
        "compliance": {
            "competitor_content_copy": False,
            "competitor_asset_download": False,
            "owned_full_clone": True,
        },
    }


site_replicator = type("SiteReplicator", (), {
    "health": staticmethod(health),
    "clone_owned_site": staticmethod(clone_owned_site),
    "create_domain_variant": staticmethod(create_domain_variant),
    "analyze_competitor_blueprint": staticmethod(analyze_competitor_blueprint),
    "generate_original_template": staticmethod(generate_original_template),
    "build_project": staticmethod(build_project),
    "deploy_cloudflare": staticmethod(deploy_cloudflare),
    "list_jobs": staticmethod(list_jobs),
    "get_job_detail": staticmethod(get_job_detail),
    "export_report": staticmethod(export_report),
})()
