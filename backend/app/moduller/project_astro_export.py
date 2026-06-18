"""HIVE V3 → Astro fiziksel site export."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.moduller.block_engine import blocks_to_html
from app.moduller.astro_factory import BUILD_TIMEOUT_SEC, GENERATED_DIR, TEMPLATE_DIR, _check_npm, _dist_ready

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _safe_slug(name: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosucgiosu")
    s = (name or "site").translate(tr).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s[:48] or "hive-site")


def _page_content_html(page: dict[str, Any]) -> str:
    parts: list[str] = []
    for section in page.get("sections") or []:
        html = blocks_to_html(section.get("blocks") or [])
        if html:
            parts.append(html)
    if parts:
        return "\n".join(parts)
    title = page.get("title", "")
    return f"<h1>{title}</h1><p>İçerik hazırlanıyor.</p>"


def export_v3_project(project: dict[str, Any], *, build: bool = False) -> dict[str, Any]:
    slug = _safe_slug(project.get("name") or project.get("id", "site"))
    project_path = GENERATED_DIR / slug
    if project_path.exists():
        shutil.rmtree(project_path)
    if not TEMPLATE_DIR.is_dir():
        return {"success": False, "error": "astro_template_missing", "path": str(TEMPLATE_DIR)}

    shutil.copytree(TEMPLATE_DIR, project_path)
    pages = project.get("pages") or []
    theme = project.get("theme") or {}
    domain = project.get("domain") or f"https://{slug}.example.com"
    if domain and not domain.startswith("http"):
        domain = f"https://{domain}"

    home = next((p for p in pages if (p.get("slug") or "") == ""), pages[0] if pages else None)
    faq_pages = []
    blog_pages = []
    geo_pages = []

    for page in pages:
        slug_p = page.get("slug") or ""
        entry = {
            "slug": slug_p or "index",
            "title": page.get("title", ""),
            "description": (page.get("seo") or {}).get("description", ""),
            "content_html": _page_content_html(page),
        }
        ptype = page.get("type", "")
        if ptype == "faq" or slug_p == "sss":
            faq_pages.append(entry)
        elif ptype == "blog":
            blog_pages.append(entry)
        elif ptype in ("landing", "location"):
            geo_pages.append(entry)

    data_dir = project_path / "src" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    pages_json = {
        "site_name": project.get("name"),
        "domain": domain,
        "main_site_url": domain,
        "language": (project.get("site") or {}).get("language", "tr"),
        "home": {
            "title": home.get("title", project.get("name")) if home else project.get("name"),
            "description": (home.get("seo") or {}).get("description", "") if home else "",
            "content_html": _page_content_html(home) if home else f"<h1>{project.get('name')}</h1>",
        },
        "geo": geo_pages,
        "cms_pages": [
            {
                "slug": p.get("slug") or "",
                "title": p.get("title"),
                "type": p.get("type"),
                "content_html": _page_content_html(p),
            }
            for p in pages
        ],
    }
    (data_dir / "pages.json").write_text(json.dumps(pages_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "faqs.json").write_text(json.dumps(faq_pages, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "blog.json").write_text(json.dumps(blog_pages, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "theme.json").write_text(json.dumps(theme, ensure_ascii=False, indent=2), encoding="utf-8")
    (data_dir / "navigation.json").write_text(
        json.dumps(project.get("navigation") or [], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result: dict[str, Any] = {
        "success": True,
        "slug": slug,
        "path": str(project_path),
        "pages_written": len(pages),
        "built": False,
        "dist_exists": False,
    }

    if build:
        npm = _check_npm()
        if not npm.get("available"):
            result["build_error"] = "npm_not_available"
            return result
        try:
            for cmd in (["npm", "install", "--no-audit"], ["npm", "run", "build"]):
                r = subprocess.run(cmd, cwd=str(project_path), capture_output=True, text=True, timeout=BUILD_TIMEOUT_SEC)
                if r.returncode != 0:
                    result["build_error"] = f"cmd_failed:{cmd[0]}"
                    result["build_stderr"] = (r.stderr or "")[-500:]
                    return result
            result["built"] = _dist_ready(project_path)
            result["dist_exists"] = result["built"]
            result["dist_path"] = str(project_path / "dist")
        except subprocess.TimeoutExpired:
            result["build_error"] = "timeout"

    return result
