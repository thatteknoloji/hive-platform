"""
HIVE V3 Astro Build Validator — static pre-build validation (no npm/shell).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.moduller import astro_export_engine

_REQUIRED_FILES = (
    ("package_json_exists", "package.json", "error"),
    ("astro_config_exists", "astro.config.mjs", "error"),
    ("index_astro_exists", "src/pages/index.astro", "error"),
    ("slug_astro_exists", "src/pages/[slug].astro", "error"),
    ("base_layout_exists", "src/layouts/BaseLayout.astro", "error"),
    ("page_renderer_exists", "src/components/PageRenderer.astro", "error"),
    ("global_css_exists", "src/styles/global.css", "error"),
    ("robots_txt_exists", "public/robots.txt", "error"),
    ("sitemap_xml_exists", "public/sitemap.xml", "error"),
)

_PAGE_REQUIRED_FIELDS = ("title", "slug", "type", "status")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _check(name: str, ok: bool, severity: str, message: str = "") -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "severity": severity,
        "message": message,
    }


def resolve_export_path(project_id: str, project: dict[str, Any] | None = None) -> Path | None:
    """Resolve export directory with path-traversal protection."""
    candidates: list[Path] = []
    if project:
        meta_path = ((project.get("metadata") or {}).get("astro_export") or {}).get("export_path")
        if meta_path:
            candidates.append(Path(meta_path))
        site_path = (project.get("site") or {}).get("astro_export_path")
        if site_path:
            candidates.append(Path(site_path))

    try:
        candidates.append(astro_export_engine.EXPORT_ROOT / astro_export_engine.sanitize_project_id(project_id))
    except ValueError:
        pass

    base = astro_export_engine.EXPORT_ROOT.resolve()
    for raw in candidates:
        try:
            target = raw.resolve()
        except (OSError, RuntimeError):
            continue
        if not str(target).startswith(str(base)):
            continue
        if target.is_dir():
            return target
    return None


def _validate_package_json(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    pkg_path = root / "package.json"
    if not pkg_path.is_file():
        return None
    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        checks.append(_check("package_json_parseable", False, "error", str(exc)))
        return None
    checks.append(_check("package_json_parseable", True, "error"))

    deps = data.get("dependencies") or {}
    has_astro = "astro" in deps
    checks.append(_check(
        "package_json_astro_dependency",
        has_astro,
        "error",
        "" if has_astro else "dependencies.astro eksik",
    ))

    scripts = data.get("scripts") or {}
    has_build = "build" in scripts
    checks.append(_check(
        "package_json_build_script",
        has_build,
        "error",
        "" if has_build else "scripts.build eksik",
    ))
    return data


def _validate_site_json(root: Path, checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    site_path = root / "src" / "data" / "site.json"
    if not site_path.is_file():
        checks.append(_check("site_json_exists", False, "error", "src/data/site.json bulunamadı"))
        return None
    checks.append(_check("site_json_exists", True, "error"))
    try:
        data = json.loads(site_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        checks.append(_check("site_json_parseable", False, "error", str(exc)))
        return None
    checks.append(_check("site_json_parseable", True, "error"))

    pages = data.get("pages")
    has_pages = isinstance(pages, list) and len(pages) > 0
    checks.append(_check(
        "site_json_pages_list",
        has_pages,
        "error",
        "" if has_pages else "pages listesi boş veya yok",
    ))
    if not has_pages:
        return data

    missing_fields = 0
    for idx, page in enumerate(pages):
        if not isinstance(page, dict):
            missing_fields += 1
            continue
        for field in _PAGE_REQUIRED_FIELDS:
            if field not in page:
                missing_fields += 1
                break
    ok = missing_fields == 0
    checks.append(_check(
        "site_json_page_fields",
        ok,
        "error",
        "" if ok else "Bazı sayfalarda title/slug/type/status eksik",
    ))
    has_base = bool(data.get("base_url"))
    checks.append(_check(
        "site_json_base_url",
        has_base,
        "error",
        "" if has_base else "base_url eksik",
    ))
    return data


def _validate_global_css(root: Path, checks: list[dict[str, Any]]) -> None:
    css_path = root / "src" / "styles" / "global.css"
    if not css_path.is_file():
        return
    try:
        text = css_path.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(_check("global_css_readable", False, "error", str(exc)))
        return
    has_primary = "--hive-primary" in text
    checks.append(_check(
        "global_css_hive_primary",
        has_primary,
        "error",
        "" if has_primary else "--hive-primary CSS değişkeni yok",
    ))


def _validate_base_layout(root: Path, checks: list[dict[str, Any]]) -> None:
    layout_path = root / "src" / "layouts" / "BaseLayout.astro"
    if not layout_path.is_file():
        return
    try:
        text = layout_path.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(_check("base_layout_readable", False, "error", str(exc)))
        return
    has_title = "<title>" in text or "{title}" in text
    has_desc = 'meta name="description"' in text or "description" in text
    checks.append(_check(
        "base_layout_title_render",
        has_title,
        "error",
        "" if has_title else "title render placeholder yok",
    ))
    checks.append(_check(
        "base_layout_meta_description",
        has_desc,
        "error",
        "" if has_desc else "meta description placeholder yok",
    ))
    has_canonical = 'rel="canonical"' in text or "canonical" in text
    checks.append(_check(
        "base_layout_canonical_tag",
        has_canonical,
        "error",
        "" if has_canonical else "canonical link yok",
    ))


def _validate_canonical_base(root: Path, checks: list[dict[str, Any]]) -> None:
    index_path = root / "src" / "pages" / "index.astro"
    if not index_path.is_file():
        return
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(_check("index_astro_readable", False, "error", str(exc)))
        return
    uses_base = "base_url" in text
    checks.append(_check(
        "base_layout_canonical_base",
        uses_base,
        "error",
        "" if uses_base else "index.astro base_url kullanmıyor",
    ))


def _validate_sitemap(root: Path, checks: list[dict[str, Any]]) -> None:
    sitemap_path = root / "public" / "sitemap.xml"
    if not sitemap_path.is_file():
        return
    try:
        text = sitemap_path.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(_check("sitemap_readable", False, "error", str(exc)))
        return
    has_urlset = "<urlset" in text and "xmlns=" in text
    checks.append(_check(
        "sitemap_contains_urlset",
        has_urlset,
        "error",
        "" if has_urlset else "sitemap urlset eksik",
    ))


def _validate_robots_sitemap(root: Path, checks: list[dict[str, Any]]) -> None:
    robots_path = root / "public" / "robots.txt"
    if not robots_path.is_file():
        return
    try:
        text = robots_path.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(_check("robots_readable", False, "error", str(exc)))
        return
    has_sitemap = "Sitemap:" in text and "sitemap.xml" in text
    checks.append(_check(
        "robots_contains_sitemap",
        has_sitemap,
        "error",
        "" if has_sitemap else "robots.txt Sitemap satırı eksik",
    ))


def _validate_page_renderer(root: Path, checks: list[dict[str, Any]]) -> None:
    renderer_path = root / "src" / "components" / "PageRenderer.astro"
    if not renderer_path.is_file():
        return
    try:
        text = renderer_path.read_text(encoding="utf-8")
    except OSError as exc:
        checks.append(_check("page_renderer_readable", False, "error", str(exc)))
        return
    has_hero = "hero" in text.lower()
    has_fallback = "ContentBlock" in text
    checks.append(_check(
        "page_renderer_block_switch",
        has_hero,
        "error",
        "" if has_hero else "block type switch bulunamadı",
    ))
    checks.append(_check(
        "page_renderer_content_fallback",
        has_fallback,
        "error",
        "" if has_fallback else "ContentBlock fallback yok",
    ))


def validate_export_dir(export_path: Path) -> dict[str, Any]:
    """Run all static checks on an export directory."""
    checks: list[dict[str, Any]] = []

    if not export_path.is_dir():
        checks.append(_check("export_dir_exists", False, "error", "Export klasörü bulunamadı"))
        return _build_result(export_path, checks)

    checks.append(_check("export_dir_exists", True, "error"))

    for name, rel, severity in _REQUIRED_FILES:
        ok = (export_path / rel).is_file()
        checks.append(_check(name, ok, severity, "" if ok else f"{rel} bulunamadı"))

    _validate_package_json(export_path, checks)
    _validate_site_json(export_path, checks)
    _validate_global_css(export_path, checks)
    _validate_base_layout(export_path, checks)
    _validate_page_renderer(export_path, checks)
    _validate_canonical_base(export_path, checks)
    _validate_sitemap(export_path, checks)
    _validate_robots_sitemap(export_path, checks)

    return _build_result(export_path, checks)


def _build_result(export_path: Path, checks: list[dict[str, Any]]) -> dict[str, Any]:
    errors_count = sum(1 for c in checks if not c["ok"] and c["severity"] == "error")
    warnings_count = sum(1 for c in checks if not c["ok"] and c["severity"] == "warning")
    valid = errors_count == 0
    return {
        "success": True,
        "export_path": str(export_path),
        "valid": valid,
        "checks": checks,
        "errors_count": errors_count,
        "warnings_count": warnings_count,
        "validated_at": _now(),
        "checks_count": len(checks),
    }


def validate_project_export(project_id: str, project: dict[str, Any]) -> dict[str, Any]:
    pid = (project_id or "").strip()
    export_path = resolve_export_path(pid, project)
    if export_path is None:
        return {
            "success": False,
            "error": "no_export",
            "project_id": pid,
            "message": "Önce Generate Astro Site ile export oluşturun.",
        }
    result = validate_export_dir(export_path)
    result["project_id"] = pid
    return result


def validation_status(project: dict[str, Any]) -> dict[str, Any]:
    stored = (project.get("metadata") or {}).get("astro_export_validation") or {}
    return {
        "success": True,
        "project_id": project.get("id"),
        "validated": bool(stored.get("validated_at")),
        "valid": stored.get("valid"),
        "errors_count": stored.get("errors_count"),
        "warnings_count": stored.get("warnings_count"),
        "validated_at": stored.get("validated_at"),
        "checks_count": stored.get("checks_count"),
    }
