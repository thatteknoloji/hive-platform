"""
HIVE V3 Astro Export Engine — project → gerçek Astro dosyaları (MVP, no npm).
"""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.moduller import block_engine

APP_DIR = Path(__file__).resolve().parent.parent
EXPORT_ROOT = APP_DIR / "generated_sites"

_BLOCK_TYPES = frozenset({
    "hero", "cta", "faq", "faq_preview", "content", "blog_list", "contact_form", "map",
})

_COLOR_PALETTES: dict[str, dict[str, str]] = {
    "gold_luxury": {"primary": "#c9a962", "bg": "#1a1410", "text": "#f5f0e8", "accent": "#c9a962"},
    "midnight_black": {"primary": "#6366f1", "bg": "#0a0a0f", "text": "#e2e8f0", "accent": "#6366f1"},
    "emerald_green": {"primary": "#10b981", "bg": "#064e3b", "text": "#ecfdf5", "accent": "#10b981"},
    "ocean_blue": {"primary": "#0ea5e9", "bg": "#0c4a6e", "text": "#e0f2fe", "accent": "#0ea5e9"},
    "sunset_orange": {"primary": "#f97316", "bg": "#7c2d12", "text": "#fff7ed", "accent": "#f97316"},
    "royal_purple": {"primary": "#a855f7", "bg": "#3b0764", "text": "#faf5ff", "accent": "#a855f7"},
    "titanium_gray": {"primary": "#6b7280", "bg": "#1f2937", "text": "#f3f4f6", "accent": "#6b7280"},
    "pure_white": {"primary": "#0f172a", "bg": "#ffffff", "text": "#0f172a", "accent": "#0f172a"},
    "custom": {"primary": "#6366f1", "bg": "#0f172a", "text": "#f8fafc", "accent": "#6366f1"},
}

_DEFAULT_PALETTE = {"primary": "#6366f1", "bg": "#0f172a", "text": "#f8fafc", "accent": "#8b5cf6"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def sanitize_project_id(project_id: str) -> str:
    pid = (project_id or "").strip()
    if not re.fullmatch(r"prj-[a-z0-9]{6,32}", pid):
        raise ValueError("invalid_project_id")
    return pid


def _export_dir(project_id: str) -> Path:
    safe = sanitize_project_id(project_id)
    base = EXPORT_ROOT.resolve()
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    target = (base / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("path_traversal")
    return target


def _slug_class(value: str, prefix: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (value or "default").lower()).strip("-")
    return f"{prefix}-{s or 'default'}"


def _theme_css(theme: dict[str, Any]) -> str:
    color_id = theme.get("color_identity") or ""
    custom = (theme.get("custom_color") or "").strip()
    palette = dict(_COLOR_PALETTES.get(color_id, _DEFAULT_PALETTE))
    if color_id == "custom" and custom.startswith("#"):
        palette["primary"] = custom
        palette["accent"] = custom
    lines = [
        ":root {",
        f"  --hive-primary: {palette['primary']};",
        f"  --hive-bg: {palette['bg']};",
        f"  --hive-text: {palette['text']};",
        f"  --hive-accent: {palette['accent']};",
        "}",
        "",
        "*, *::before, *::after { box-sizing: border-box; }",
        "body {",
        "  margin: 0;",
        "  font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;",
        "  background: var(--hive-bg);",
        "  color: var(--hive-text);",
        "  line-height: 1.6;",
        "}",
        "a { color: var(--hive-accent); text-decoration: none; }",
        "a:hover { text-decoration: underline; }",
        ".site-header, .site-footer {",
        "  padding: 1rem 1.5rem;",
        "  border-bottom: 1px solid rgba(255,255,255,0.08);",
        "}",
        ".site-footer { border-bottom: none; border-top: 1px solid rgba(255,255,255,0.08); font-size: 0.875rem; opacity: 0.85; }",
        ".site-nav { display: flex; flex-wrap: wrap; gap: 1rem; list-style: none; margin: 0; padding: 0; }",
        ".site-nav a { color: var(--hive-text); }",
        ".brand { font-weight: 700; margin-right: auto; }",
        "main { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }",
        ".block { margin: 2rem 0; }",
        ".hero { padding: 3rem 1.5rem; border-radius: 12px; background: rgba(0,0,0,0.2); }",
        ".hero .eyebrow { text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.8rem; opacity: 0.8; }",
        ".hero h1 { font-size: clamp(1.75rem, 4vw, 2.75rem); margin: 0.5rem 0; }",
        ".cta-band { padding: 2rem; text-align: center; background: rgba(255,255,255,0.04); border-radius: 8px; }",
        ".btn { display: inline-block; margin: 0.25rem; padding: 0.65rem 1.25rem; border-radius: 6px; background: var(--hive-primary); color: var(--hive-bg); font-weight: 600; }",
        ".btn-secondary { background: transparent; border: 1px solid var(--hive-primary); color: var(--hive-primary); }",
        ".faq-item { margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.08); }",
        ".map-placeholder, .form-placeholder { padding: 2rem; border: 1px dashed rgba(255,255,255,0.2); border-radius: 8px; text-align: center; }",
    ]
    return "\n".join(lines)


def _normalize_base_url(project: dict[str, Any]) -> str:
    domain = (project.get("domain") or "").strip()
    if domain and not domain.startswith("http"):
        domain = f"https://{domain}"
    if not domain:
        domain = "https://example.com"
    return domain.rstrip("/")


def _serialize_site_payload(project: dict[str, Any]) -> dict[str, Any]:
    base_url = _normalize_base_url(project)
    return {
        "project_id": project.get("id"),
        "site_name": project.get("name"),
        "domain": base_url,
        "base_url": base_url,
        "language": (project.get("site") or {}).get("language", "tr"),
        "theme": project.get("theme") or {},
        "navigation": project.get("navigation") or [],
        "pages": project.get("pages") or [],
    }


def _package_json(project_id: str) -> str:
    return json.dumps({
        "name": f"hive-export-{project_id}",
        "type": "module",
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "dev": "astro dev",
            "build": "astro build",
            "preview": "astro preview",
        },
        "dependencies": {
            "astro": "^4.16.0",
        },
    }, indent=2)


def _astro_config(domain: str) -> str:
    site = domain or "https://example.com"
    return f"""import {{ defineConfig }} from 'astro/config';

export default defineConfig({{
  site: '{site}',
}});
"""


def _robots_txt(domain: str) -> str:
    base = (domain or "https://example.com").rstrip("/")
    return f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n"


def _page_in_sitemap(page: dict[str, Any]) -> bool:
    if page.get("status") == "draft":
        return (page.get("seo") or {}).get("index", True) is True
    return True


def _sitemap_priority(page: dict[str, Any]) -> str:
    ptype = page.get("type", "")
    slug = page.get("slug") or ""
    if slug == "" or ptype == "homepage":
        return "1.0"
    if ptype in ("blog", "category", "product"):
        return "0.8"
    if ptype in ("contact", "landing"):
        return "0.7"
    if ptype == "legal":
        return "0.3"
    return "0.6"


def _sitemap_changefreq(page: dict[str, Any]) -> str:
    ptype = page.get("type", "")
    if ptype in ("blog", "homepage"):
        return "weekly"
    if ptype == "legal":
        return "yearly"
    return "monthly"


def _sitemap_xml(pages: list[dict[str, Any]], base_url: str, lastmod: str) -> str:
    base = base_url.rstrip("/")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for page in pages:
        if not _page_in_sitemap(page):
            continue
        slug = page.get("slug") or ""
        loc = f"{base}/" if slug == "" else f"{base}/{slug}"
        lines.extend([
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            f"    <changefreq>{_sitemap_changefreq(page)}</changefreq>",
            f"    <priority>{_sitemap_priority(page)}</priority>",
            "  </url>",
        ])
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def _base_layout_astro() -> str:
    return """---
import '../styles/global.css';
import NavHeader from '../components/NavHeader.astro';
import NavFooter from '../components/NavFooter.astro';
import site from '../data/site.json';

const { title, description, canonical, robots, schemaType, schemaJson } = Astro.props;
const theme = site.theme || {};
const designClass = theme.design_dna ? `design-${String(theme.design_dna).replace(/_/g, '-')}` : 'design-default';
const colorClass = theme.color_identity ? `theme-${String(theme.color_identity).replace(/_/g, '-')}` : 'theme-default';
---
<!DOCTYPE html>
<html lang={site.language || 'tr'}>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <meta name="description" content={description} />
    <link rel="canonical" href={canonical} />
    <meta name="robots" content={robots || 'index, follow'} />
    {schemaJson && (
      <script type="application/ld+json" set:html={schemaJson} />
    )}
  </head>
  <body class:list={[designClass, colorClass]}>
    <NavHeader />
    <main>
      <slot />
    </main>
    <NavFooter />
  </body>
</html>
"""


def _nav_header_astro() -> str:
    return """---
import site from '../data/site.json';
const nav = site.navigation || [];
---
<header class="site-header">
  <nav class="site-nav" aria-label="Ana menü">
    <span class="brand">{site.site_name}</span>
    {nav.map((item) => (
      <a href={item.href}>{item.label}</a>
    ))}
  </nav>
</header>
"""


def _nav_footer_astro() -> str:
    return """---
import site from '../data/site.json';
const nav = site.navigation || [];
---
<footer class="site-footer">
  <nav class="site-nav" aria-label="Alt menü">
    {nav.map((item) => (
      <a href={item.href}>{item.label}</a>
    ))}
  </nav>
  <p>&copy; {new Date().getFullYear()} {site.site_name}</p>
</footer>
"""


def _page_renderer_astro() -> str:
    return """---
import Hero from './blocks/Hero.astro';
import Cta from './blocks/Cta.astro';
import Faq from './blocks/Faq.astro';
import ContentBlock from './blocks/ContentBlock.astro';
import BlogList from './blocks/BlogList.astro';
import ContactForm from './blocks/ContactForm.astro';
import MapBlock from './blocks/MapBlock.astro';

const { page } = Astro.props;
const sections = page?.sections || [];
---
{sections.map((section) => (
  <section class={`section section-${section.type || 'default'}`}>
    {(section.blocks || []).map((block) => (
      <>
        {block.type === 'hero' && <Hero block={block} />}
        {block.type === 'cta' && <Cta block={block} />}
        {(block.type === 'faq' || block.type === 'faq_preview') && <Faq block={block} />}
        {block.type === 'blog_list' && <BlogList block={block} />}
        {(block.type === 'contact_form' || block.type === 'form') && <ContactForm block={block} />}
        {block.type === 'map' && <MapBlock block={block} />}
        {!['hero','cta','faq','faq_preview','blog_list','contact_form','form','map'].includes(block.type) && (
          <ContentBlock block={block} />
        )}
      </>
    ))}
  </section>
))}
"""


def _hero_astro() -> str:
    return """---
const { block } = Astro.props;
const c = block?.content || block?.props || {};
---
<section class="block hero">
  {c.eyebrow && <p class="eyebrow">{c.eyebrow}</p>}
  <h1>{c.title || c.headline || ''}</h1>
  {(c.subtitle || c.subheadline) && <p>{c.subtitle || c.subheadline}</p>}
  <div class="hero-ctas">
    {(c.primary_cta || c.cta_label) && <a class="btn" href="#">{c.primary_cta || c.cta_label}</a>}
    {c.secondary_cta && <a class="btn btn-secondary" href="#">{c.secondary_cta}</a>}
  </div>
</section>
"""


def _cta_astro() -> str:
    return """---
const { block } = Astro.props;
const c = block?.content || block?.props || {};
---
<section class="block cta-band">
  <h2>{c.title || c.headline || 'Hemen başlayın'}</h2>
  {c.body && <p>{c.body}</p>}
  <div>
    {(c.primary_cta || c.cta_label) && <a class="btn" href="#">{c.primary_cta || c.cta_label}</a>}
    {c.secondary_cta && <a class="btn btn-secondary" href="#">{c.secondary_cta}</a>}
  </div>
</section>
"""


def _faq_astro() -> str:
    return """---
const { block } = Astro.props;
const c = block?.content || block?.props || {};
const items = c.items || [];
---
<section class="block faq">
  <h2>{c.title || c.headline || 'Sık sorulan sorular'}</h2>
  {items.map((item) => (
    <div class="faq-item">
      <h3>{item.question || item.q}</h3>
      <p>{item.answer || item.a}</p>
    </div>
  ))}
</section>
"""


def _content_block_astro() -> str:
    return """---
const { block } = Astro.props;
const c = block?.content || block?.props || {};
---
<section class="block content">
  <h2>{c.title || c.headline || ''}</h2>
  {c.body && <p>{c.body}</p>}
  {c.caption && <p class="caption">{c.caption}</p>}
</section>
"""


def _blog_list_astro() -> str:
    return """---
const { block } = Astro.props;
const c = block?.content || block?.props || {};
---
<section class="block blog-list">
  <h2>{c.title || 'Blog'}</h2>
  <p>{c.empty_message || 'Yakında yeni içerikler.'}</p>
</section>
"""


def _contact_form_astro() -> str:
    return """---
const { block } = Astro.props;
const c = block?.content || block?.props || {};
const fields = c.fields || ['name', 'email', 'message'];
---
<section class="block form-placeholder">
  <h2>{c.title || c.headline || 'İletişim'}</h2>
  <p>Form alanları: {fields.join(', ')}</p>
  <button type="button" class="btn">{c.submit_label || 'Gönder'}</button>
</section>
"""


def _map_block_astro() -> str:
    return """---
const { block } = Astro.props;
const c = block?.content || block?.props || {};
---
<section class="block map-placeholder">
  <h2>{c.title || 'Konum'}</h2>
  <p>{c.location_label || 'Harita yüklenecek'}</p>
</section>
"""


def _index_astro() -> str:
    return """---
import BaseLayout from '../layouts/BaseLayout.astro';
import PageRenderer from '../components/PageRenderer.astro';
import site from '../data/site.json';

const page = (site.pages || []).find((p) => (p.slug || '') === '') || site.pages?.[0];
const seo = page?.seo || {};
const base = (site.base_url || site.domain || '').replace(/\\/$/, '');
const canonical = base ? `${base}/` : '/';
const schema = {
  '@context': 'https://schema.org',
  '@type': seo.schema_type || 'WebSite',
  name: site.site_name,
  url: base || undefined,
  description: seo.description || '',
};
const schemaJson = JSON.stringify(schema);
---
<BaseLayout
  title={seo.title || site.site_name}
  description={seo.description || ''}
  canonical={canonical}
  robots="index, follow"
  schemaType={seo.schema_type || 'WebSite'}
  schemaJson={schemaJson}
>
  {page ? <PageRenderer page={page} /> : <p>Sayfa bulunamadı.</p>}
</BaseLayout>
"""


def _slug_page_astro(slugs: list[str]) -> str:
    paths = ",\n    ".join(f'{{ params: {{ slug: "{s}" }} }}' for s in slugs if s)
    if not paths:
        paths = '{ params: { slug: "placeholder" } }'
    return f"""---
import BaseLayout from '../layouts/BaseLayout.astro';
import PageRenderer from '../components/PageRenderer.astro';
import site from '../data/site.json';

export function getStaticPaths() {{
  return [
    {paths}
  ];
}}

const {{ slug }} = Astro.params;
const page = (site.pages || []).find((p) => p.slug === slug);
if (!page) throw new Error(`Page not found: ${{slug}}`);
const seo = page.seo || {{}};
const base = (site.base_url || site.domain || '').replace(/\\/$/, '');
const canonical = base ? `${{base}}/${{slug}}` : `/${{slug}}`;
const schema = {{
  '@context': 'https://schema.org',
  '@type': seo.schema_type || 'WebPage',
  name: seo.title || page.title,
  url: canonical,
  description: seo.description || '',
}};
const schemaJson = JSON.stringify(schema);
---
<BaseLayout
  title={{seo.title || page.title}}
  description={{seo.description || ''}}
  canonical={{canonical}}
  robots="index, follow"
  schemaType={{seo.schema_type || 'WebPage'}}
  schemaJson={{schemaJson}}
>
  <PageRenderer page={{page}} />
</BaseLayout>
"""


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _count_files(root: Path) -> int:
    return sum(1 for p in root.rglob("*") if p.is_file())


def validate_project_for_export(project: dict[str, Any]) -> str | None:
    if not project:
        return "not_found"
    site = project.get("site")
    pages = project.get("pages")
    if not site or not isinstance(site, dict) or not site.get("site_id"):
        return "no_site_skeleton"
    if not pages or not isinstance(pages, list):
        return "no_pages"
    return None


def export_status(project: dict[str, Any]) -> dict[str, Any]:
    meta = (project.get("metadata") or {}).get("astro_export") or {}
    export_path = meta.get("export_path")
    exists = bool(export_path and Path(export_path).is_dir())
    return {
        "success": True,
        "project_id": project.get("id"),
        "exported": exists,
        "export_path": export_path,
        "files_count": meta.get("files_count"),
        "entry": meta.get("entry"),
        "generated_at": meta.get("generated_at"),
    }


def export_project(project: dict[str, Any]) -> dict[str, Any]:
    """Generate Astro site files for a v3 project. No npm install/build."""
    project_id = project.get("id") or ""
    err = validate_project_for_export(project)
    if err:
        return {"success": False, "error": err, "project_id": project_id}

    try:
        safe_id = sanitize_project_id(project_id)
    except ValueError as e:
        return {"success": False, "error": str(e), "project_id": project_id}

    if not block_engine.count_blocks(project.get("pages") or []):
        return {"success": False, "error": "no_blocks", "project_id": project_id}

    export_dir = _export_dir(safe_id)
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True)

    payload = _serialize_site_payload(project)
    theme = payload.get("theme") or {}
    base_url = payload.get("base_url") or "https://example.com"
    lastmod = (project.get("updated_at") or _now())[:10]

    files: list[tuple[str, str]] = [
        ("package.json", _package_json(safe_id)),
        ("astro.config.mjs", _astro_config(base_url)),
        ("public/robots.txt", _robots_txt(base_url)),
        ("public/sitemap.xml", _sitemap_xml(payload.get("pages") or [], base_url, lastmod)),
        ("src/styles/global.css", _theme_css(theme)),
        ("src/data/site.json", json.dumps(payload, ensure_ascii=False, indent=2)),
        ("src/layouts/BaseLayout.astro", _base_layout_astro()),
        ("src/components/NavHeader.astro", _nav_header_astro()),
        ("src/components/NavFooter.astro", _nav_footer_astro()),
        ("src/components/PageRenderer.astro", _page_renderer_astro()),
        ("src/components/blocks/Hero.astro", _hero_astro()),
        ("src/components/blocks/Cta.astro", _cta_astro()),
        ("src/components/blocks/Faq.astro", _faq_astro()),
        ("src/components/blocks/ContentBlock.astro", _content_block_astro()),
        ("src/components/blocks/BlogList.astro", _blog_list_astro()),
        ("src/components/blocks/ContactForm.astro", _contact_form_astro()),
        ("src/components/blocks/MapBlock.astro", _map_block_astro()),
        ("src/pages/index.astro", _index_astro()),
    ]

    slugs = [p.get("slug") or "" for p in payload.get("pages") or [] if (p.get("slug") or "")]
    files.append(("src/pages/[slug].astro", _slug_page_astro(slugs)))

    for rel, content in files:
        _write_file(export_dir / rel, content)

    files_count = _count_files(export_dir)
    generated_at = _now()
    entry = "src/pages/index.astro"

    return {
        "success": True,
        "project_id": safe_id,
        "export_path": str(export_dir),
        "files_count": files_count,
        "entry": entry,
        "generated_at": generated_at,
        "design_class": _slug_class(theme.get("design_dna", ""), "design"),
        "theme_class": _slug_class(theme.get("color_identity", ""), "theme"),
    }
