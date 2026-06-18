"""
HIVE V3 Block Engine — section blocks doldurma (delegates to block_seed).
"""

from __future__ import annotations

from typing import Any

from app.moduller import block_seed


def _block_content(blk: dict[str, Any]) -> dict[str, Any]:
    """Read block fields from v3 content schema or legacy props."""
    if isinstance(blk.get("content"), dict):
        return blk["content"]
    return blk.get("props") or {}


def fill_project_blocks(project: dict[str, Any], *, use_llm: bool = False) -> dict[str, Any]:
    """Mutate pages in project dict — returns stats. use_llm ignored (deterministic seed only)."""
    _ = use_llm
    return block_seed.seed_project_blocks(project)


def blocks_to_html(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for blk in blocks:
        content = _block_content(blk)
        btype = blk.get("type", "")
        if btype == "hero":
            parts.append(
                f"<section class='hero'><p class='eyebrow'>{content.get('eyebrow', '')}</p>"
                f"<h1>{content.get('title', content.get('headline', ''))}</h1>"
                f"<p>{content.get('subtitle', content.get('subheadline', ''))}</p>"
                f"<a href='#'>{content.get('primary_cta', content.get('cta_label', ''))}</a>"
                f"<a href='#'>{content.get('secondary_cta', '')}</a></section>"
            )
        elif btype == "cta":
            parts.append(
                f"<section class='cta'><h2>{content.get('title', content.get('headline', ''))}</h2>"
                f"<p>{content.get('body', '')}</p>"
                f"<a href='#'>{content.get('primary_cta', content.get('cta_label', ''))}</a></section>"
            )
        elif btype in ("faq", "faq_preview"):
            items = content.get("items") or []
            qa = ""
            for item in items:
                q = item.get("question") or item.get("q", "")
                a = item.get("answer") or item.get("a", "")
                qa += f"<h3>{q}</h3><p>{a}</p>"
            parts.append(f"<section class='faq'>{qa}</section>")
        elif btype in ("form", "contact_form"):
            parts.append(
                f"<section class='form'><h2>{content.get('title', content.get('headline', ''))}</h2>"
                f"<p>Form alanları: {', '.join(content.get('fields') or [])}</p>"
                f"<button>{content.get('submit_label', '')}</button></section>"
            )
        elif btype == "map":
            parts.append(
                f"<section class='map'><h2>{content.get('title', '')}</h2>"
                f"<p>{content.get('location_label', '')}</p></section>"
            )
        elif btype == "blog_list":
            parts.append(
                f"<section class='blog_list'><h2>{content.get('title', '')}</h2>"
                f"<p>{content.get('empty_message', '')}</p></section>"
            )
        else:
            parts.append(
                f"<section class='{btype}'><h2>{content.get('title', content.get('headline', ''))}</h2>"
                f"<p>{content.get('body', '')}</p></section>"
            )
    return "\n".join(parts)


def count_blocks(pages: list[dict[str, Any]]) -> int:
    total = 0
    for page in pages:
        for section in page.get("sections") or []:
            total += len(section.get("blocks") or [])
    return total
