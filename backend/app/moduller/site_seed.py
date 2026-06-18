"""
HIVE V3 Site Skeleton Seed — sector pack → pages, theme, navigation.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.moduller import sector_packs

_SERIF_DNA = frozenset({
    "luxury", "premium", "hotel_luxury", "fashion_elegant", "editorial",
})
_PREMIUM_RADIUS = frozenset({
    "luxury", "premium", "hotel_luxury", "ultra_luks", "fashion_elegant",
})


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _slugify(text: str) -> str:
    tr_map = str.maketrans({
        "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
        "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u",
    })
    s = (text or "").translate(tr_map).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:64]


def get_sector_page_blueprints(sector: str) -> list[dict[str, Any]]:
    return sector_packs.get_default_pages(sector)


def _build_sections(section_types: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, stype in enumerate(section_types):
        out.append({
            "id": _new_id("sec"),
            "type": stype,
            "status": "draft",
            "blocks": [],
        })
    return out


def _build_page(blueprint: dict[str, Any], *, project_name: str) -> dict[str, Any]:
    title = blueprint["title"]
    slug = blueprint.get("slug", _slugify(title))
    page_type = blueprint.get("type", "page")
    section_types = blueprint.get("sections") or ["hero", "content"]
    if len(section_types) < 2:
        section_types = section_types + ["content"]

    return {
        "id": _new_id("page"),
        "title": title,
        "slug": slug,
        "type": page_type,
        "status": "draft",
        "sections": _build_sections(section_types),
        "seo": {
            "title": f"{title} | {project_name}" if title != "Ana Sayfa" else project_name,
            "description": "",
            "index": True,
        },
    }


def build_theme(design: dict[str, Any] | None) -> dict[str, Any]:
    d = design or {}
    design_dna = d.get("design_dna") or ""
    font_style = "serif" if design_dna in _SERIF_DNA else "sans"
    radius = "premium" if design_dna in _PREMIUM_RADIUS else "standard"
    if "ultra_luks" in (d.get("brand_personality") or []):
        radius = "premium"
    return {
        "design_dna": design_dna,
        "color_identity": d.get("color_identity") or "",
        "custom_color": d.get("custom_color") or "",
        "brand_personality": list(d.get("brand_personality") or []),
        "conversion_goal": d.get("conversion_goal") or "",
        "font_style": font_style,
        "radius": radius,
        "spacing": "comfortable",
    }


def build_navigation(pages: list[dict[str, Any]]) -> list[dict[str, str]]:
    nav: list[dict[str, str]] = []
    for page in pages:
        slug = page.get("slug") or ""
        href = "/" if slug == "" else f"/{slug}"
        nav.append({
            "label": page.get("title") or "",
            "href": href,
        })
    return nav


def build_site_record(*, pages_count: int) -> dict[str, Any]:
    return {
        "site_id": _new_id("site"),
        "engine": "astro",
        "status": "draft",
        "language": "tr",
        "pages_count": pages_count,
    }


def build_site_skeleton(
    *,
    sector: str,
    design: dict[str, Any] | None = None,
    project_name: str = "",
) -> dict[str, Any]:
    """Return site, pages, theme, navigation for a new project."""
    blueprints = get_sector_page_blueprints(sector)
    name = (project_name or "Site").strip() or "Site"
    pages = [_build_page(bp, project_name=name) for bp in blueprints]
    site = build_site_record(pages_count=len(pages))
    theme = build_theme(design)
    navigation = build_navigation(pages)
    return {
        "site": site,
        "pages": pages,
        "theme": theme,
        "navigation": navigation,
    }


def content_count_from_pages(pages: list[dict[str, Any]]) -> int:
    return sum(len(p.get("sections") or []) for p in pages)
