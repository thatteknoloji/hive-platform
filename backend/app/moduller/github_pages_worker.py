"""
GitHub Pages Worker V1 — gerçek GitHub REST API ile static site yayını.

Authority Mesh github_pages provider'ı için repo oluşturma, dosya yükleme,
Pages etkinleştirme ve entegrasyon bildirimleri.
"""

from __future__ import annotations

import base64
import html
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("hive.github_pages_worker")

STATE_FILE = Path(__file__).resolve().parent.parent / "github_pages_worker_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

GITHUB_API = "https://api.github.com"
ALLOWED_FILE_PATHS = frozenset({
    "README.md", "index.html", "style.css", "sitemap.xml", "robots.txt",
})
ALLOWED_PREFIXES = ("pages/",)

ROLES = (
    "faq_hub", "geo_hub", "entity_hub", "blog_hub", "support_hub", "citation_hub",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("sites", [])
                data.setdefault("history", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"sites": [], "history": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _config() -> dict[str, str]:
    return {
        "token": (os.environ.get("GITHUB_TOKEN") or "").strip(),
        "owner": (os.environ.get("GITHUB_OWNER") or "").strip(),
        "visibility": (os.environ.get("GITHUB_DEFAULT_VISIBILITY") or "public").strip().lower(),
        "branch": (os.environ.get("GITHUB_PAGES_BRANCH") or "main").strip(),
    }


def _provider_ready() -> tuple[bool, str | None]:
    cfg = _config()
    if not cfg["token"]:
        return False, "provider_missing — GITHUB_TOKEN yapılandırılmadı"
    return True, None


def _github_request(
    method: str,
    path: str,
    *,
    json_body: dict | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    ready, err = _provider_ready()
    if not ready:
        return {"success": False, "error": "provider_missing", "message": err}

    cfg = _config()
    url = path if path.startswith("http") else f"{GITHUB_API}{path}"
    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        import requests
        resp = requests.request(method, url, headers=headers, json=json_body, params=params, timeout=60)
    except ImportError:
        return {"success": False, "error": "requests_not_installed"}
    except Exception as exc:
        return {"success": False, "error": "github_request_failed", "message": str(exc)}

    try:
        data = resp.json() if resp.content else {}
    except Exception:
        data = {"raw": resp.text[:500]}

    if resp.status_code >= 400:
        msg = data.get("message") if isinstance(data, dict) else resp.text[:200]
        errors = data.get("errors") if isinstance(data, dict) else None
        return {
            "success": False,
            "error": "github_api_error",
            "status_code": resp.status_code,
            "message": msg,
            "errors": errors,
        }
    return {"success": True, "data": data, "status_code": resp.status_code}


def sanitize_repo_name(name: str) -> str:
    """GitHub repo adı — yalnızca a-z0-9- ve . (tek segment)."""
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z0-9._-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-._")
    if not s:
        s = f"hive-pages-{uuid.uuid4().hex[:8]}"
    return s[:100]


def sanitize_file_path(path: str) -> str | None:
    """Path traversal engeli — yalnızca izinli yollar."""
    p = (path or "").replace("\\", "/").strip().lstrip("/")
    if ".." in p or p.startswith("."):
        return None
    if p in ALLOWED_FILE_PATHS:
        return p
    if any(p.startswith(pref) for pref in ALLOWED_PREFIXES):
        slug = p.split("/", 1)[-1]
        if re.match(r"^[a-z0-9-]+\.html$", slug):
            return p
    return None


def _escape(text: str) -> str:
    return html.escape(text or "")


def _apply_link_policy_html(link: dict[str, Any]) -> str:
    if not link or link.get("link_type") == "no_link":
        return ""
    url = link.get("target_url") or ""
    anchor = link.get("anchor") or url
    if not url:
        return ""
    return f'<p class="link-policy"><a href="{_escape(url)}" rel="noopener">{_escape(anchor)}</a></p>'


def _build_index_html(
    *,
    site_title: str,
    target_keyword: str,
    target_money_site: str,
    pages: list[dict] | None = None,
    link_policies: list[dict] | None = None,
    canonical_url: str = "",
) -> str:
    kw = target_keyword.strip()
    title = site_title.strip() or kw or "Rehber"
    desc = f"{kw} hakkında güncel rehber, SSS ve pratik bilgiler." if kw else f"{title} — güncel rehber."
    canonical = canonical_url or ""

    extra_sections = ""
    for pg in pages or []:
        body = pg.get("content_html") or ""
        if body and pg.get("slug") not in ("index", "", None):
            extra_sections += f'<section class="content-block"><h2>{_escape(pg.get("title", ""))}</h2>{body}</section>\n'

    link_html = ""
    used_anchors: set[str] = set()
    for lp in link_policies or []:
        anchor = (lp.get("anchor") or "").strip().lower()
        if anchor and anchor in used_anchors:
            continue
        if anchor:
            used_anchors.add(anchor)
        block = _apply_link_policy_html(lp)
        if block:
            link_html += block + "\n"

    faq_items = [
        {"q": f"{kw} nedir?" if kw else "Bu rehber ne hakkında?", "a": f"{kw} konusunda güncel ve pratik bilgiler sunan kapsamlı bir kaynaktır." if kw else "Güncel ve pratik bilgiler sunan kapsamlı bir kaynaktır."},
        {"q": f"{kw} için en iyi kaynak hangisi?" if kw else "Daha fazla bilgi nerede?", "a": "Bu sayfa temel rehberlik sağlar; detaylı içerik bölümlerde yer alır."},
    ]
    faq_html = "".join(
        f'<details class="faq-item"><summary>{_escape(f["q"])}</summary><p>{_escape(f["a"])}</p></details>'
        for f in faq_items
    )

    schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "description": desc,
        "keywords": kw,
        "mainEntity": {
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faq_items],
        },
    }
    schema_json = json.dumps(schema, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)}</title>
  <meta name="description" content="{_escape(desc)}">
  {f'<link rel="canonical" href="{_escape(canonical)}">' if canonical else ''}
  <link rel="stylesheet" href="style.css">
  <script type="application/ld+json">{schema_json}</script>
</head>
<body>
  <header><h1>{_escape(title)}</h1></header>
  <main>
    <section class="answer-box" role="doc-abstract">
      <p><strong>{_escape(kw or title)}</strong> — {_escape(desc)}</p>
    </section>
    <section class="content">
      <h2>Genel Bakış</h2>
      <p>{_escape(kw)} hakkında derlenmiş güncel bilgiler, pratik öneriler ve sık sorulan sorular.</p>
      {extra_sections}
    </section>
    {link_html}
    <section class="faq"><h2>Sık Sorulan Sorular</h2>{faq_html}</section>
  </main>
  <footer><p>© {datetime.now(timezone.utc).year} {_escape(title)} — destekleyici otorite içeriği</p></footer>
</body>
</html>"""


def _build_style_css() -> str:
    return """body{font-family:system-ui,sans-serif;line-height:1.6;max-width:720px;margin:0 auto;padding:1rem;color:#1a1a1a}
header h1{font-size:1.75rem;margin-bottom:.5rem}
.answer-box{background:#f0f7ff;border-left:4px solid #2563eb;padding:1rem;margin:1rem 0;border-radius:4px}
.faq-item{margin:.75rem 0;padding:.5rem 0;border-bottom:1px solid #e5e7eb}
.link-policy a{color:#2563eb}
footer{margin-top:2rem;font-size:.875rem;color:#6b7280}
.content-block{margin:1.5rem 0}
"""


def _build_robots_txt(pages_url: str = "") -> str:
    sitemap = f"\nSitemap: {pages_url.rstrip('/')}/sitemap.xml" if pages_url else ""
    return f"User-agent: *\nAllow: /{sitemap}\n"


def _build_sitemap_xml(pages_url: str, slugs: list[str] | None = None) -> str:
    base = pages_url.rstrip("/") if pages_url else ""
    urls = [base + "/"] if base else ["/"]
    for slug in slugs or []:
        if slug and slug != "index":
            urls.append(f"{base}/{slug}.html" if base else f"/pages/{slug}.html")
    entries = "\n".join(f"  <url><loc>{_escape(u)}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'


def generate_site_files(
    *,
    site_title: str,
    target_keyword: str,
    target_money_site: str,
    pages: list[dict] | None = None,
    link_policy: dict | list | None = None,
    pages_url: str = "",
) -> dict[str, str]:
    from app.moduller.authority_mesh_engine import generate_link_policy

    policies: list[dict] = []
    if isinstance(link_policy, list):
        policies = link_policy
    elif isinstance(link_policy, dict) and link_policy:
        policies = [link_policy]
    else:
        policies = generate_link_policy(target_keyword, target_money_site)

    files: dict[str, str] = {}
    files["README.md"] = f"# {site_title}\n\n{target_keyword} — GitHub Pages authority site.\n"
    files["index.html"] = _build_index_html(
        site_title=site_title,
        target_keyword=target_keyword,
        target_money_site=target_money_site,
        pages=pages,
        link_policies=policies,
        canonical_url=pages_url,
    )
    files["style.css"] = _build_style_css()
    files["robots.txt"] = _build_robots_txt(pages_url)

    slugs: list[str] = []
    for pg in pages or []:
        slug = (pg.get("slug") or "").strip()
        if not slug or slug == "index":
            continue
        safe = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
        if safe:
            path = f"pages/{safe}.html"
            if sanitize_file_path(path):
                slugs.append(safe)
                body = pg.get("content_html") or f"<p>{_escape(pg.get('title', target_keyword))}</p>"
                files[path] = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8"><title>{_escape(pg.get('title', ''))}</title><link rel="stylesheet" href="../style.css"></head><body><main>{body}</main></body></html>"""

    files["sitemap.xml"] = _build_sitemap_xml(pages_url, slugs)
    return files


def _resolve_owner() -> tuple[str | None, str | None]:
    cfg = _config()
    if cfg["owner"]:
        return cfg["owner"], None
    res = _github_request("GET", "/user")
    if not res.get("success"):
        return None, res.get("message") or res.get("error")
    login = (res.get("data") or {}).get("login")
    if not login:
        return None, "GITHUB_OWNER belirlenemedi — GITHUB_OWNER env ayarlayın"
    return login, None


def _create_repo(owner: str, repo_name: str, visibility: str) -> dict[str, Any]:
    private = visibility == "private"
    body = {
        "name": repo_name,
        "description": f"HIVE GitHub Pages — {repo_name}",
        "private": private,
        "auto_init": False,
    }
    return _github_request("POST", "/user/repos", json_body=body)


def _put_file(owner: str, repo: str, path: str, content: str, branch: str, message: str, sha: str | None = None) -> dict[str, Any]:
    safe = sanitize_file_path(path)
    if not safe:
        return {"success": False, "error": "invalid_file_path", "path": path}
    payload: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    return _github_request("PUT", f"/repos/{owner}/{repo}/contents/{safe}", json_body=payload)


def _get_file_sha(owner: str, repo: str, path: str, branch: str) -> str | None:
    safe = sanitize_file_path(path)
    if not safe:
        return None
    res = _github_request("GET", f"/repos/{owner}/{repo}/contents/{safe}", params={"ref": branch})
    if res.get("success") and isinstance(res.get("data"), dict):
        return res["data"].get("sha")
    return None


def _enable_pages(owner: str, repo: str, branch: str) -> dict[str, Any]:
    return _github_request("POST", f"/repos/{owner}/{repo}/pages", json_body={
        "source": {"branch": branch, "path": "/"},
    })


def _get_pages_info(owner: str, repo: str) -> dict[str, Any]:
    return _github_request("GET", f"/repos/{owner}/{repo}/pages")


def _record_brain(event_type: str, *, domain: str = "", keyword: str = "", result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            "module_action",
            "github_pages_worker",
            domain=domain,
            keyword=keyword,
            result=result or {},
            reason=reason,
            metadata={"engine": "github_pages_worker", "gh_event": event_type},
        )
    except Exception as exc:
        logger.debug("brain: %s", exc)


def _notify_integrations(site: dict[str, Any], *, network_id: str = "") -> dict[str, Any]:
    url = site.get("pages_url") or ""
    keyword = site.get("target_keyword") or ""
    role = site.get("role") or "support_hub"
    out: dict[str, Any] = {}

    if url:
        try:
            from app.moduller.authority_mesh_engine import register_external_publish
            out["authority_mesh"] = register_external_publish(
                "github_pages",
                url=url,
                keyword=keyword,
                money_site=site.get("target_money_site", ""),
                role=role,
                network_id=network_id,
                repo_name=site.get("repo_name", ""),
            )
        except Exception as exc:
            out["authority_mesh"] = {"success": False, "error": str(exc)}

        try:
            from app.moduller.rank_index_watcher import register_project, track_keyword
            domain = urlparse(url).netloc
            if domain:
                pid = f"ghp-{site.get('site_id', uuid.uuid4().hex[:8])}"
                register_project(pid, domain, source="github_pages_worker")
                out["rank_watcher"] = track_keyword(keyword, domain, project_id=pid)
        except Exception as exc:
            out["rank_watcher"] = {"success": False, "error": str(exc)}

        _record_brain("authority_source_created", domain=url, keyword=keyword, result={"site_id": site.get("site_id")}, reason=site.get("repo_name", ""))

    return out


def _site_model(
    *,
    repo_name: str,
    owner: str,
    target_keyword: str = "",
    target_money_site: str = "",
    role: str = "support_hub",
    visibility: str = "public",
    status: str = "planned",
) -> dict[str, Any]:
    return {
        "site_id": f"ghp-{uuid.uuid4().hex[:10]}",
        "repo_name": repo_name,
        "owner": owner,
        "visibility": visibility,
        "target_keyword": target_keyword,
        "target_money_site": target_money_site,
        "role": role if role in ROLES else "support_hub",
        "status": status,
        "repo_url": "",
        "pages_url": "",
        "published_at": "",
        "files": [],
        "linked_targets": [],
        "authority_score": 0,
        "created_at": _now(),
    }


def create_site(
    *,
    repo_name: str = "",
    site_title: str = "",
    target_keyword: str = "",
    target_money_site: str = "",
    role: str = "support_hub",
    pages: list[dict] | None = None,
    link_policy: dict | list | None = None,
    visibility: str = "",
    network_id: str = "",
) -> dict[str, Any]:
    ready, err = _provider_ready()
    if not ready:
        return {"success": False, "error": "provider_missing", "message": err}

    cfg = _config()
    owner, owner_err = _resolve_owner()
    if not owner:
        return {"success": False, "error": "provider_missing", "message": owner_err}

    title = (site_title or target_keyword or repo_name or "").strip()
    if not title and not repo_name:
        return {"success": False, "error": "validation_error", "message": "repo_name veya site_title gerekli"}

    repo = sanitize_repo_name(repo_name or title)
    vis = (visibility or cfg["visibility"] or "public").lower()
    if vis not in ("public", "private"):
        vis = "public"
    branch = cfg["branch"] or "main"

    site = _site_model(
        repo_name=repo,
        owner=owner,
        target_keyword=target_keyword,
        target_money_site=target_money_site,
        role=role,
        visibility=vis,
        status="planned",
    )

    repo_res = _create_repo(owner, repo, vis)
    if not repo_res.get("success"):
        site["status"] = "failed"
        site["error"] = repo_res.get("message") or repo_res.get("error")
        st = _load_state()
        st.setdefault("sites", []).insert(0, site)
        _save_state(st)
        _record_brain("github_pages_failed", keyword=target_keyword, result=repo_res, reason=repo)
        return {"success": False, "error": site["error"], "site": site}

    repo_data = repo_res.get("data") or {}
    site["status"] = "repo_created"
    site["repo_url"] = repo_data.get("html_url") or f"https://github.com/{owner}/{repo}"
    _record_brain("github_repo_created", domain=site["repo_url"], keyword=target_keyword, result={"repo": repo}, reason=title)

    files = generate_site_files(
        site_title=title,
        target_keyword=target_keyword,
        target_money_site=target_money_site,
        pages=pages,
        link_policy=link_policy,
    )

    uploaded: list[str] = []
    for path, content in files.items():
        put_res = _put_file(owner, repo, path, content, branch, f"Add {path}")
        if not put_res.get("success"):
            site["status"] = "failed"
            site["error"] = put_res.get("message") or put_res.get("error")
            st = _load_state()
            st.setdefault("sites", []).insert(0, site)
            _save_state(st)
            _record_brain("github_pages_failed", keyword=target_keyword, result=put_res, reason=f"upload {path}")
            return {"success": False, "error": site["error"], "site": site, "uploaded": uploaded}
        uploaded.append(path)

    site["files"] = uploaded

    pages_res = _enable_pages(owner, repo, branch)
    if not pages_res.get("success"):
        err_msg = pages_res.get("message") or ""
        if pages_res.get("status_code") != 409 and "already exists" not in (err_msg or "").lower():
            site["status"] = "failed"
            site["error"] = err_msg or pages_res.get("error")
            st = _load_state()
            st.setdefault("sites", []).insert(0, site)
            _save_state(st)
            _record_brain("github_pages_failed", keyword=target_keyword, result=pages_res, reason="enable pages")
            return {"success": False, "error": site["error"], "site": site}

    site["status"] = "pages_enabled"

    pub = publish_site(site["site_id"], network_id=network_id, site=site)
    if pub.get("site"):
        site = pub["site"]

    st = _load_state()
    sites = st.setdefault("sites", [])
    idx = next((i for i, s in enumerate(sites) if s.get("site_id") == site["site_id"]), None)
    if idx is not None:
        sites[idx] = site
    else:
        sites.insert(0, site)
    st.setdefault("history", []).insert(0, {"type": "create_site", "site_id": site["site_id"], "at": _now()})
    _save_state(st)

    return {"success": site["status"] == "published", "site": site, "uploaded": uploaded}


def publish_site(site_id: str, *, network_id: str = "", site: dict | None = None) -> dict[str, Any]:
    ready, err = _provider_ready()
    if not ready:
        return {"success": False, "error": "provider_missing", "message": err}

    st = _load_state()
    if not site:
        site = next((s for s in st.get("sites") or [] if s.get("site_id") == site_id), None)
    if not site:
        return {"success": False, "error": "site_not_found"}

    owner = site.get("owner", "")
    repo = site.get("repo_name", "")
    if not owner or not repo:
        return {"success": False, "error": "invalid_site", "message": "owner/repo eksik"}

    info = _get_pages_info(owner, repo)
    if not info.get("success"):
        if site.get("status") in ("repo_created", "planned"):
            branch = _config()["branch"] or "main"
            enable = _enable_pages(owner, repo, branch)
            if not enable.get("success") and enable.get("status_code") != 409:
                site["status"] = "failed"
                site["error"] = enable.get("message") or enable.get("error")
                _save_state(st)
                _record_brain("github_pages_failed", keyword=site.get("target_keyword", ""), result=enable, reason="publish enable")
                return {"success": False, "error": site["error"], "site": site}
            info = _get_pages_info(owner, repo)

    if not info.get("success"):
        site["status"] = "failed"
        site["error"] = info.get("message") or info.get("error") or "pages_info_unavailable"
        _save_state(st)
        _record_brain("github_pages_failed", keyword=site.get("target_keyword", ""), result=info, reason="pages info")
        return {"success": False, "error": site["error"], "site": site}

    pdata = info.get("data") or {}
    html_url = pdata.get("html_url") or ""
    gh_status = pdata.get("status") or ""

    if not html_url:
        site["status"] = "pages_enabled"
        site["error"] = "pages_url_not_ready — GitHub henüz html_url döndürmedi"
        _save_state(st)
        return {"success": False, "error": "pages_url_not_ready", "site": site, "github_status": gh_status}

    site["pages_url"] = html_url
    site["github_pages_status"] = gh_status

    if gh_status == "built":
        site["status"] = "published"
        site["published_at"] = _now()
        site["error"] = None
        _record_brain("github_pages_published", domain=html_url, keyword=site.get("target_keyword", ""), result={"repo": repo}, reason=site.get("repo_name", ""))
        integrations = _notify_integrations(site, network_id=network_id)
    else:
        site["status"] = "pages_enabled"
        integrations = {}

    for i, s in enumerate(st.get("sites") or []):
        if s.get("site_id") == site.get("site_id"):
            st["sites"][i] = site
            break
    else:
        st.setdefault("sites", []).insert(0, site)
    _save_state(st)

    return {
        "success": site["status"] == "published",
        "site": site,
        "github_status": gh_status,
        "integrations": integrations,
    }


def update_site(
    site_id: str,
    *,
    files: dict[str, str] | None = None,
    pages: list[dict] | None = None,
    site_title: str = "",
) -> dict[str, Any]:
    ready, err = _provider_ready()
    if not ready:
        return {"success": False, "error": "provider_missing", "message": err}

    st = _load_state()
    site = next((s for s in st.get("sites") or [] if s.get("site_id") == site_id), None)
    if not site:
        return {"success": False, "error": "site_not_found"}

    owner = site["owner"]
    repo = site["repo_name"]
    branch = _config()["branch"] or "main"

    to_upload = files or {}
    if pages or site_title:
        generated = generate_site_files(
            site_title=site_title or site.get("target_keyword", ""),
            target_keyword=site.get("target_keyword", ""),
            target_money_site=site.get("target_money_site", ""),
            pages=pages,
            pages_url=site.get("pages_url", ""),
        )
        to_upload = {**generated, **to_upload}

    updated: list[str] = []
    for path, content in to_upload.items():
        sha = _get_file_sha(owner, repo, path, branch)
        put_res = _put_file(owner, repo, path, content, branch, f"Update {path}", sha=sha)
        if not put_res.get("success"):
            return {"success": False, "error": put_res.get("message") or put_res.get("error"), "updated": updated}
        updated.append(path)

    site["files"] = list(set((site.get("files") or []) + updated))
    site["updated_at"] = _now()
    _save_state(st)
    return {"success": True, "site": site, "updated": updated}


def list_sites(limit: int = 50) -> dict[str, Any]:
    st = _load_state()
    sites = list(st.get("sites") or [])[:max(1, min(200, limit))]
    return {"success": True, "count": len(sites), "sites": sites}


def get_site(site_id: str) -> dict[str, Any]:
    if not site_id:
        return {"success": False, "error": "site_id gerekli"}
    st = _load_state()
    site = next((s for s in st.get("sites") or [] if s.get("site_id") == site_id), None)
    if not site:
        return {"success": False, "error": "site_not_found"}
    return {"success": True, "site": site}


def export_report(report_type: str = "overview") -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = list_sites(200) if report_type == "sites" else {"health": health(), "sites": list_sites(100)}
    path = REPORTS_DIR / f"github-pages-{report_type}-{uuid.uuid4().hex[:8]}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "report_type": report_type, "path": str(path), "data": payload}


def health() -> dict[str, Any]:
    ready, err = _provider_ready()
    cfg = _config()
    st = _load_state()
    user_ok = False
    if ready:
        res = _github_request("GET", "/user")
        user_ok = res.get("success", False)
    return {
        "success": True,
        "module": "github_pages_worker",
        "provider_ready": ready and user_ok,
        "error": None if (ready and user_ok) else (err or "github_auth_failed"),
        "owner_configured": bool(cfg["owner"]),
        "visibility_default": cfg["visibility"],
        "pages_branch": cfg["branch"],
        "sites_count": len(st.get("sites") or []),
        "published_count": sum(1 for s in st.get("sites") or [] if s.get("status") == "published"),
    }


def create_site_from_mesh_item(
    *,
    title: str,
    keyword: str,
    money_site: str,
    role: str = "support_hub",
    link_policy: dict | None = None,
    network_id: str = "",
) -> dict[str, Any]:
    """Authority Mesh process_plan delegasyonu."""
    slug = sanitize_repo_name(title or keyword)
    return create_site(
        repo_name=slug,
        site_title=title,
        target_keyword=keyword,
        target_money_site=money_site,
        role=role,
        link_policy=link_policy,
        network_id=network_id,
    )
