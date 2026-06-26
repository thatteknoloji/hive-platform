"""Mekan SEO Content Pipeline — mekan verilerini SEO/GEO/AEO içerik hammaddesine dönüştürür.

ÖNEMLİ: Bu modül Listing Hub ile entegre DEĞİLDİR ve asla ilan oluşturmaz.
Mekan isimleri yalnızca entity/context sinyali olarak kullanılır.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from app.moduller.storyforge_categories import _slugify, normalize_seo_slug

logger = logging.getLogger("hive.place_seo_pipeline")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = Path(__file__).resolve().parent.parent / "place_seo_pipeline_state.json"
UPLOAD_DIR = ROOT / "uploads" / "place-seo"
REPORTS_DIR = ROOT / "reports"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
X_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXT = {".docx", ".csv", ".xlsx", ".xls", ".txt", ".md", ".json"}

LINK_POLICY = {
    "max_links_per_page": 2,
    "homepage_link_ratio": 0.2,
    "category_link_ratio": 0.5,
    "brand_mention_ratio": 0.3,
    "exact_anchor_forbidden": True,
}

CATEGORY_TEMPLATES: dict[str, str] = {
    "gece hayatı": "Kuşadası Gece Hayatı",
    "bar": "Kuşadası Barlar ve Gece Kulüpleri",
    "pub": "Kuşadası Pub Kültürü",
    "restoran": "Kuşadası Restoranlar ve Kafeler",
    "kafe": "Kuşadası Kahvaltı ve Kafe Rehberi",
    "beach club": "Kuşadası Beach Club Rehberi",
    "otel": "Kuşadası Oteller ve Konaklama",
    "canlı müzik": "Kuşadası Canlı Müzik Mekanları",
    "marina": "Kuşadası Marina Çevresi Yeme İçme",
    "kadınlar denizi": "Kuşadası Kadınlar Denizi Rehberi",
    "davutlar": "Kuşadası Davutlar Plaj ve Eğlence",
    "güzelçamlı": "Kuşadası Güzelçamlı Doğa ve Plaj Rehberi",
    "kaleiçi": "Kuşadası Kaleiçi ve Barlar Sokağı",
}

LOCATION_ALIASES = (
    "kuşadası", "kadınlar denizi", "davutlar", "güzelçamlı", "marina",
    "barlar sokağı", "kaleiçi", "long beach", "güvercinada", "merkez",
)

CATEGORY_KEYWORDS = (
    "gece hayatı", "bar", "pub", "kulüp", "beach club", "restoran", "kafe",
    "otel", "canlı müzik", "marina", "plaj", "eğlence", "nightlife",
)

SERVICE_KEYWORDS = (
    "kokteyl", "canlı müzik", "dj", "dans", "happy hour", "brunch",
    "deniz manzarası", "açık hava", "rezervasyon", "vip masa",
)

FAQ_TEMPLATES = [
    "{location} gece hayatı nerede?",
    "{location} Barlar Sokağı nasıl bir yer?",
    "{location} beach club fiyatları nasıl?",
    "{location} restoranları hangi bölgelerde yoğun?",
    "{location} akşamları hareketli mi?",
    "{location} Marina çevresinde ne yapılır?",
    "{category} deneyimi için en iyi zaman ne?",
]

SPAM_LINK_PATTERNS = (
    r"click here", r"buy now", r"best casino", r"\[url\]",
    r"http://http://", r"<script", r"javascript:",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("jobs", {})
                data.setdefault("uploads", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"jobs": {}, "uploads": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_upload_path(filename: str) -> Path:
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Path traversal engellendi")
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Desteklenmeyen uzantı: {ext}")
    base = UPLOAD_DIR.resolve()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(filename).name)[:160]
    target = (base / safe).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal engellendi")
    return target


def _sanitize_text(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"<script[^>]*>.*?</script>", "", t, flags=re.I | re.S)
    t = re.sub(r"javascript:", "", t, flags=re.I)
    return t


def _sanitize_html(html: str) -> str:
    html = _sanitize_text(html)
    for pat in SPAM_LINK_PATTERNS:
        if re.search(pat, html, re.I):
            raise ValueError(f"Spam link pattern engellendi: {pat}")
    return html


def _xml_texts(root: ET.Element, tag: str) -> list[str]:
    texts: list[str] = []
    for el in root.iter(tag):
        if el.text:
            texts.append(el.text)
        for child in el:
            if child.tail:
                texts.append(child.tail)
    return texts


def parse_docx(data: bytes) -> dict[str, Any]:
    """DOCX: paragraflar, başlıklar, tablolar."""
    paragraphs: list[str] = []
    headings: list[str] = []
    tables: list[list[list[str]]] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("Geçersiz DOCX") from exc

    if "word/document.xml" not in zf.namelist():
        raise ValueError("DOCX document.xml bulunamadı")

    root = ET.fromstring(zf.read("word/document.xml"))
    p_tag = f"{{{W_NS}}}p"
    t_tag = f"{{{W_NS}}}t"
    tbl_tag = f"{{{W_NS}}}tbl"
    tr_tag = f"{{{W_NS}}}tr"
    tc_tag = f"{{{W_NS}}}tc"
    pstyle_tag = f"{{{W_NS}}}pStyle"

    for tbl in root.iter(tbl_tag):
        table_rows: list[list[str]] = []
        for tr in tbl.iter(tr_tag):
            row: list[str] = []
            for tc in tr.iter(tc_tag):
                cell_text = "".join(el.text or "" for el in tc.iter(t_tag)).strip()
                if cell_text:
                    row.append(cell_text)
            if row:
                table_rows.append(row)
        if table_rows:
            tables.append(table_rows)

    for p in root.iter(p_tag):
        style_el = p.find(f".//{pstyle_tag}")
        style_val = (style_el.get(f"{{{W_NS}}}val") or "") if style_el is not None else ""
        text = "".join(el.text or "" for el in p.iter(t_tag)).strip()
        if not text:
            continue
        if "Heading" in style_val or style_val.startswith("heading"):
            headings.append(text)
        else:
            paragraphs.append(text)

    return {
        "format": "docx",
        "paragraphs": paragraphs,
        "headings": headings,
        "tables": tables,
        "raw_text": "\n".join(headings + paragraphs + [c for row in tables for r in row for c in r]),
    }


def parse_csv(data: bytes | str) -> dict[str, Any]:
    text = data.decode("utf-8-sig", errors="replace") if isinstance(data, bytes) else data
    rows = [dict(r) for r in csv.DictReader(io.StringIO(text))]
    return {"format": "csv", "rows": rows, "raw_text": text}


def parse_json(data: bytes | str) -> dict[str, Any]:
    text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
    obj = json.loads(text)
    return {"format": "json", "data": obj, "raw_text": text}


def parse_txt(data: bytes | str) -> dict[str, Any]:
    text = data.decode("utf-8-sig", errors="replace") if isinstance(data, bytes) else data
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return {"format": "txt", "lines": lines, "raw_text": text}


def parse_xlsx(data: bytes) -> dict[str, Any]:
    """XLSX — zip+xml (openpyxl bağımlılığı yok)."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ValueError("Geçersiz XLSX") from exc

    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in ss_root.iter(f"{{{X_NS}}}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{{{X_NS}}}t")))

    rows: list[dict[str, str]] = []
    sheet_name = "xl/worksheets/sheet1.xml"
    if sheet_name not in zf.namelist():
        return {"format": "xlsx", "rows": [], "raw_text": ""}

    sheet = ET.fromstring(zf.read(sheet_name))
    grid: dict[int, dict[int, str]] = {}
    for row_el in sheet.iter(f"{{{X_NS}}}row"):
        r_idx = int(row_el.get("r", "0"))
        for cell in row_el.iter(f"{{{X_NS}}}c"):
            ref = cell.get("r", "")
            col = ord(re.match(r"([A-Z]+)", ref).group(1)[0]) - 65 if ref else 0
            v_el = cell.find(f"{{{X_NS}}}v")
            if v_el is None or v_el.text is None:
                continue
            val = v_el.text
            if cell.get("t") == "s":
                val = shared[int(val)] if int(val) < len(shared) else val
            grid.setdefault(r_idx, {})[col] = val

    if not grid:
        return {"format": "xlsx", "rows": [], "raw_text": ""}

    sorted_rows = sorted(grid.items())
    headers = [sorted_rows[0][1].get(i, f"col{i}") for i in sorted(sorted_rows[0][1])]
    for r_idx, cols in sorted_rows[1:]:
        rows.append({headers[i]: cols.get(i, "") for i in range(len(headers))})

    raw = "\n".join(" | ".join(r.values()) for r in rows)
    return {"format": "xlsx", "rows": rows, "raw_text": raw}


def parse_file_content(data: bytes, filename: str) -> dict[str, Any]:
    ext = Path(filename).suffix.lower()
    if ext == ".docx":
        return parse_docx(data)
    if ext == ".csv":
        return parse_csv(data)
    if ext in (".xlsx", ".xls"):
        return parse_xlsx(data)
    if ext == ".json":
        return parse_json(data)
    if ext in (".txt", ".md"):
        return parse_txt(data)
    raise ValueError(f"Desteklenmeyen format: {ext}")


def _collect_text_chunks(parsed: dict[str, Any]) -> list[str]:
    chunks: list[str] = []
    if parsed.get("raw_text"):
        chunks.append(parsed["raw_text"])
    for row in parsed.get("rows") or []:
        if isinstance(row, dict):
            chunks.extend(str(v) for v in row.values() if v)
    for line in parsed.get("lines") or []:
        chunks.append(line)
    for p in parsed.get("paragraphs") or []:
        chunks.append(p)
    for h in parsed.get("headings") or []:
        chunks.append(h)
    for tbl in parsed.get("tables") or []:
        for row in tbl:
            chunks.extend(row)
    return [_sanitize_text(c) for c in chunks if c and len(c.strip()) > 1]


def _find_entities(text: str) -> list[str]:
    """Mekan isimleri — entity sinyali; listing sayfası üretilmez."""
    entities: list[str] = []
    patterns = [
        r"(?:^|[\n,;|])([A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ&'\-\s]{2,40}(?:Club|Bar|Pub|Restaurant|Restoran|Cafe|Kafe|Hotel|Otel|Beach|Lounge|Disco|Kulüp))",
        r'"([^"]{3,50})"',
        r"'([^']{3,50})'",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.M):
            name = m.group(1).strip()
            if len(name) > 2 and name.lower() not in ("kuşadası", "aydın"):
                entities.append(name)
    for part in re.split(r"[,;\n|]", text):
        part = part.strip()
        if re.match(r"^[A-ZÇĞİÖŞÜ]", part) and 3 < len(part) < 50:
            if any(w in part.lower() for w in ("club", "bar", "pub", "irish", "sokağı")):
                entities.append(part.split(" ve ")[0].strip())
    return list(dict.fromkeys(entities))[:80]


def extract_signals(parsed: dict[str, Any], source_files: list[str] | None = None) -> dict[str, Any]:
    chunks = _collect_text_chunks(parsed)
    corpus = "\n".join(chunks).lower()
    full_text = "\n".join(chunks)

    categories = [k for k in CATEGORY_KEYWORDS if k in corpus]
    locations = [loc.title() if loc.islower() else loc for loc in LOCATION_ALIASES if loc in corpus]
    if "kuşadası" in corpus and "Kuşadası" not in locations:
        locations.insert(0, "Kuşadası")

    entities = _find_entities(full_text)
    services = [s for s in SERVICE_KEYWORDS if s in corpus]
    topics: list[str] = []
    for cat in categories:
        for loc in locations[:5] or ["Kuşadası"]:
            topics.append(f"{loc} {cat}")

    faq_candidates: list[str] = []
    for line in chunks:
        if "?" in line and len(line) < 200:
            faq_candidates.append(line.strip())
    loc = locations[0] if locations else "Kuşadası"
    for tpl in FAQ_TEMPLATES:
        cat = categories[0] if categories else "gece hayatı"
        faq_candidates.append(tpl.format(location=loc, category=cat))

    content_angles = [
        f"{loc} bölgesel {cat} deneyimi rehberi" for loc in (locations[:3] or ["Kuşadası"]) for cat in (categories[:4] or ["gece hayatı"])
    ]
    content_angles = list(dict.fromkeys(content_angles))[:20]

    confidence = min(100, 30 + len(categories) * 8 + len(locations) * 6 + len(entities) * 2 + len(chunks))

    return normalize_signals({
        "categories": categories,
        "locations": locations,
        "entities": entities,
        "services": services,
        "topics": topics,
        "faq_candidates": list(dict.fromkeys(faq_candidates))[:30],
        "content_angles": content_angles,
        "source_files": source_files or [],
        "confidence": confidence,
    })


def normalize_signals(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "categories": list(dict.fromkeys(raw.get("categories") or [])),
        "locations": list(dict.fromkeys(raw.get("locations") or [])),
        "entities": list(dict.fromkeys(raw.get("entities") or [])),
        "services": list(dict.fromkeys(raw.get("services") or [])),
        "topics": list(dict.fromkeys(raw.get("topics") or [])),
        "faq_candidates": list(dict.fromkeys(raw.get("faq_candidates") or [])),
        "content_angles": list(dict.fromkeys(raw.get("content_angles") or [])),
        "source_files": raw.get("source_files") or [],
        "confidence": max(0, min(100, int(raw.get("confidence") or 0))),
    }


def _page_slug(title: str) -> str:
    return normalize_seo_slug(title)


def _contextual_entity_mention(entities: list[str], category: str) -> str:
    if not entities:
        return f"Bölgede {category} kültürü gelişmiş bir yapıya sahiptir."
    sample = ", ".join(entities[:3])
    return (
        f"Örneğin {sample} gibi mekanlar bölgenin {category} atmosferini yansıtır — "
        "bu rehber tek tek mekan kataloğu değil, bölgesel deneyim otoritesi kurmayı hedefler."
    )


def _build_page_html(
    title: str,
    location: str,
    category: str,
    entities: list[str],
    services: list[str],
    main_site_url: str,
    links: list[dict[str, str]],
    page_type: str = "guide",
) -> str:
    entity_block = _contextual_entity_mention(entities, category)
    svc = ", ".join(services[:5]) if services else category
    link_html = ""
    for lk in links[:LINK_POLICY["max_links_per_page"]]:
        href = lk.get("url", main_site_url)
        anchor = _sanitize_text(lk.get("anchor", "Kaynak"))
        link_html += f'<p><a href="{href}" rel="noopener">{anchor}</a></p>\n'

    faq_block = ""
    if page_type == "faq":
        faq_block = """
        <section class="faq">
          <h2>Sık Sorulan Sorular</h2>
          <details><summary>Bölge akşamları hareketli mi?</summary><p>Mevsim ve hafta içi/sonu değişkenlik gösterir.</p></details>
        </section>"""

    html = f"""<article>
<h1>{_sanitize_text(title)}</h1>
<div class="answer-box"><p><strong>{_sanitize_text(location)}</strong> bölgesinde {category} hakkında kapsamlı yerel rehber.</p></div>
<p>{entity_block}</p>
<h2>Deneyim ve Hizmetler</h2>
<p>{svc} odaklı ziyaretçiler için pratik bilgiler: ulaşım, sezon, rezervasyon ve bölgesel ipuçları.</p>
<h2>Konum ve GEO</h2>
<p>{location} çevresinde {category} deneyimi arayanlar için mahalle bazlı yönlendirme ve çevre bağlamı.</p>
{faq_block}
<h2>İletişim ve Kaynak</h2>
{link_html}
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": title, "about": location}, ensure_ascii=False)}</script>
</article>"""
    return _sanitize_html(html)


def _generate_main_site_links(
    pages: list[dict[str, Any]],
    main_site_url: str,
    categories: list[str],
) -> list[dict[str, Any]]:
    """Doğal ana site link planı — exact anchor tekrarı yok."""
    main_site_url = (main_site_url or "").strip().rstrip("/")
    if not main_site_url:
        raise ValueError("main_site_url zorunlu")

    parsed = urlparse(main_site_url)
    brand = parsed.netloc.replace("www.", "").split(".")[0].title()
    anchors_used: set[str] = set()
    plan: list[dict[str, Any]] = []

    category_paths = [f"/{_slugify(c)}/" for c in categories[:5]]

    for i, page in enumerate(pages):
        page_links: list[dict[str, str]] = []
        ratio = (i % 10) / 10.0
        anchor_variants = [
            f"{brand} — {page.get('title', 'rehber')[:35]}",
            f"{brand} {categories[i % len(categories)] if categories else 'rehber'} rehberi",
            f"{page.get('slug', 'sayfa')} | {brand}",
            "resmi kaynak site",
            f"{brand} hakkında",
            f"{page.get('type', 'guide')} — detaylı bilgi",
        ]
        if ratio < LINK_POLICY["homepage_link_ratio"]:
            anchor = anchor_variants[i % len(anchor_variants)]
            if LINK_POLICY["exact_anchor_forbidden"]:
                n = 1
                while anchor.lower() in anchors_used:
                    anchor = f"{anchor_variants[i % len(anchor_variants)]} #{n}"
                    n += 1
            anchors_used.add(anchor.lower())
            page_links.append({"url": main_site_url + "/", "anchor": anchor, "type": "homepage"})
        elif ratio < LINK_POLICY["homepage_link_ratio"] + LINK_POLICY["category_link_ratio"]:
            path = category_paths[i % len(category_paths)] if category_paths else "/"
            cat = categories[i % len(categories)] if categories else "rehber"
            anchor = f"{cat} — {page.get('slug', str(i))}"
            if anchor.lower() in anchors_used:
                anchor = f"{cat} rehberi ({page.get('slug', str(i))})"
            anchors_used.add(anchor.lower())
            page_links.append({"url": main_site_url + path, "anchor": anchor, "type": "category"})
        else:
            mention = f"{brand} ({page.get('slug', str(i))})"
            if mention.lower() in anchors_used:
                mention = f"{brand} mention #{i}"
            anchors_used.add(mention.lower())
            page_links.append({"url": main_site_url, "anchor": mention, "type": "brand_mention"})

        plan.append({
            "page_slug": page.get("slug", ""),
            "page_title": page.get("title", ""),
            "links": page_links[:LINK_POLICY["max_links_per_page"]],
        })
    return plan


def generate_content_plan(
    signals: dict[str, Any],
    main_site_url: str,
    job_id: str = "",
) -> dict[str, Any]:
    main_site_url = (main_site_url or "").strip()
    if not main_site_url:
        return {"success": False, "error": "main_site_url zorunlu"}

    locs = signals.get("locations") or ["Kuşadası"]
    cats = signals.get("categories") or ["gece hayatı"]
    entities = signals.get("entities") or []

    category_pages: list[dict[str, Any]] = []
    for key, title in CATEGORY_TEMPLATES.items():
        if key in " ".join(cats).lower() or not cats:
            slug = _page_slug(title)
            category_pages.append({
                "title": title,
                "slug": slug,
                "type": "category",
                "target_keyword": title.lower(),
                "content_angle": f"{title} — bölgesel otorite rehberi (mekan kataloğu değil)",
            })

    geo_pages: list[dict[str, Any]] = []
    for loc in locs[:8]:
        for cat in cats[:6]:
            title = f"{loc} {cat.title()}"
            geo_pages.append({
                "title": title,
                "slug": _page_slug(title),
                "type": "geo",
                "location": loc,
                "category": cat,
                "target_keyword": title.lower(),
            })

    faq_pages: list[dict[str, Any]] = []
    for q in (signals.get("faq_candidates") or [])[:12]:
        title = q.rstrip("?") + " — SSS"
        faq_pages.append({
            "title": title,
            "slug": _page_slug(q[:60]),
            "type": "faq",
            "question": q,
            "target_keyword": q.lower(),
        })

    blog_posts: list[dict[str, Any]] = []
    for angle in (signals.get("content_angles") or [])[:10]:
        blog_posts.append({
            "title": angle.title(),
            "slug": _page_slug(angle),
            "type": "blog",
            "target_keyword": angle.lower(),
        })

    all_pages = category_pages + geo_pages + faq_pages + blog_posts
    main_site_link_plan = _generate_main_site_links(all_pages, main_site_url, cats)
    internal_link_plan = []
    for i, p in enumerate(all_pages[:-1]):
        internal_link_plan.append({
            "from": p["slug"],
            "to": all_pages[i + 1]["slug"],
            "anchor": all_pages[i + 1]["title"][:40],
        })

    primary_loc = locs[0]
    astro_slug = _page_slug(f"{primary_loc}-rehber")
    astro_support_site = {
        "site_name": f"{primary_loc} Rehber",
        "slug": astro_slug,
        "domain": f"https://{astro_slug}.pages.dev",
        "seed_keyword": cats[0] if cats else "gece hayatı",
        "location": primary_loc,
        "niche": "Yerel rehber (mekan listesi değil)",
        "pages": [
            {"slug": "", "title": f"{primary_loc} Rehber", "type": "home"},
            *[{"slug": p["slug"], "title": p["title"], "type": p["type"]} for p in category_pages[:6]],
            *[{"slug": f"sss/{p['slug']}", "title": p["title"], "type": "faq"} for p in faq_pages[:4]],
            *[{"slug": f"blog/{p['slug']}", "title": p["title"], "type": "blog"} for p in blog_posts[:3]],
        ],
        "note": "Mekan listesi/katalog sitesi değil — rehber/bilgi sitesi",
    }

    plan = {
        "job_id": job_id,
        "summary": {
            "signal_confidence": signals.get("confidence", 0),
            "entity_count": len(entities),
            "category_page_count": len(category_pages),
            "geo_page_count": len(geo_pages),
            "faq_page_count": len(faq_pages),
            "blog_count": len(blog_posts),
            "listing_hub_called": False,
        },
        "category_pages": category_pages,
        "geo_pages": geo_pages,
        "faq_pages": faq_pages,
        "blog_posts": blog_posts,
        "astro_support_site": astro_support_site,
        "internal_link_plan": internal_link_plan,
        "main_site_link_plan": main_site_link_plan,
    }
    return {"success": True, "plan": plan}


def _get_job(job_id: str) -> dict[str, Any] | None:
    return (_load_state().get("jobs") or {}).get(job_id)


def _update_job(job_id: str, **fields: Any) -> dict[str, Any]:
    state = _load_state()
    job = state.setdefault("jobs", {}).setdefault(job_id, {"id": job_id, "created_at": _now()})
    job.update(fields)
    job["updated_at"] = _now()
    state["jobs"][job_id] = job
    _save_state(state)
    return job


# ── Public API ──

def health() -> dict[str, Any]:
    state = _load_state()
    wp_st: dict[str, Any] = {"connected": False, "error": ""}
    try:
        from app.moduller.wordpress_api import ensure_wp_connected
        wp_st = ensure_wp_connected(verify=True)
    except Exception as exc:
        wp_st = {"connected": False, "error": str(exc)}
    wp_connected = bool(wp_st.get("connected"))
    return {
        "success": True,
        "module": "Mekan SEO Content Pipeline",
        "jobs_count": len(state.get("jobs") or {}),
        "upload_dir": str(UPLOAD_DIR),
        "listing_hub_integration": False,
        "wordpress_connected": wp_connected,
        "wordpress_url": wp_st.get("url", ""),
        "wordpress_error": "" if wp_connected else (wp_st.get("error") or "Bağlantı kurulamadı"),
        "wordpress_auto_connected": bool(wp_st.get("auto_connected")),
        "supported_formats": sorted(ALLOWED_EXT),
        "link_policy": LINK_POLICY,
        "publish_mode": "real",
    }


def upload_file(filename: str, file_bytes: bytes, mime: str = "") -> dict[str, Any]:
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return {"success": False, "error": f"Maks {MAX_UPLOAD_BYTES // (1024*1024)}MB"}
    path = _safe_upload_path(filename)
    path.write_bytes(file_bytes)
    upload_id = str(uuid.uuid4())[:12]
    state = _load_state()
    state.setdefault("uploads", {})[upload_id] = {
        "id": upload_id,
        "filename": path.name,
        "path": str(path),
        "mime": mime,
        "size": len(file_bytes),
        "uploaded_at": _now(),
    }
    _save_state(state)
    return {"success": True, "upload_id": upload_id, "filename": path.name, "path": str(path)}


def _merge_parsed(parsed_list: list[dict[str, Any]], filenames: list[str]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "format": "batch",
        "paragraphs": [],
        "headings": [],
        "tables": [],
        "rows": [],
        "lines": [],
        "raw_text": "",
        "source_files": filenames,
    }
    raw_parts: list[str] = []
    for p in parsed_list:
        merged["paragraphs"].extend(p.get("paragraphs") or [])
        merged["headings"].extend(p.get("headings") or [])
        merged["tables"].extend(p.get("tables") or [])
        merged["rows"].extend(p.get("rows") or [])
        merged["lines"].extend(p.get("lines") or [])
        if p.get("raw_text"):
            raw_parts.append(p["raw_text"])
    merged["raw_text"] = "\n\n".join(raw_parts)
    return merged


def _parse_stats(parsed: dict[str, Any]) -> dict[str, int]:
    return {
        "paragraphs": len(parsed.get("paragraphs") or []),
        "headings": len(parsed.get("headings") or []),
        "tables": len(parsed.get("tables") or []),
        "rows": len(parsed.get("rows") or []),
        "lines": len(parsed.get("lines") or []),
        "files": len(parsed.get("source_files") or []),
    }


def _job_source_files(job: dict[str, Any]) -> list[str]:
    if job.get("filenames"):
        return list(job["filenames"])
    if job.get("filename"):
        return [job["filename"]]
    return []


def _ensure_job_plan(job_id: str, main_site_url: str = "") -> dict[str, Any] | None:
    job = _get_job(job_id)
    if not job:
        return None
    if job.get("plan"):
        return job
    if not job.get("signals"):
        return job
    url = (main_site_url or job.get("main_site_url") or "").strip()
    if not url:
        return None
    generate_plan(job_id, url)
    return _get_job(job_id)


def process_batch_upload(
    files: list[tuple[str, bytes, str]],
    main_site_url: str = "",
    auto_pipeline: bool = True,
) -> dict[str, Any]:
    """Birden fazla dosyayı yükle, birleştir, parse et; isteğe bağlı tam pipeline."""
    if not files:
        return {"success": False, "error": "En az 1 dosya gerekli"}

    upload_ids: list[str] = []
    parsed_list: list[dict[str, Any]] = []
    filenames: list[str] = []

    for filename, data, mime in files:
        up = upload_file(filename, data, mime)
        if not up.get("success"):
            return up
        upload_ids.append(up["upload_id"])
        filenames.append(up["filename"])
        parsed_list.append(parse_file_content(data, up["filename"]))

    merged = _merge_parsed(parsed_list, filenames)
    job_id = str(uuid.uuid4())[:12]
    job = _update_job(
        job_id,
        status="parsed",
        upload_ids=upload_ids,
        filenames=filenames,
        filename=", ".join(filenames[:3]) + ("…" if len(filenames) > 3 else ""),
        parse=merged,
        parse_stats=_parse_stats(merged),
        main_site_url=(main_site_url or "").strip(),
    )

    result: dict[str, Any] = {
        "success": True,
        "job_id": job_id,
        "upload_ids": upload_ids,
        "filenames": filenames,
        "file_count": len(filenames),
        "parse_stats": job["parse_stats"],
    }

    if auto_pipeline:
        signals = extract_signals(merged, source_files=filenames)
        _update_job(job_id, status="signals", signals=signals)
        result["signals"] = signals
        if main_site_url.strip():
            plan_res = generate_content_plan(signals, main_site_url.strip(), job_id=job_id)
            if plan_res.get("success"):
                _update_job(job_id, status="planned", plan=plan_res["plan"], main_site_url=main_site_url.strip())
                result["plan"] = plan_res["plan"]
                result["plan_summary"] = plan_res["plan"].get("summary")

    return result


def parse_upload(upload_id: str = "", file_path: str = "") -> dict[str, Any]:
    state = _load_state()
    if upload_id:
        up = (state.get("uploads") or {}).get(upload_id)
        if not up:
            return {"success": False, "error": "Upload bulunamadı"}
        file_path = up["path"]
        filename = up["filename"]
    elif file_path:
        filename = Path(file_path).name
    else:
        return {"success": False, "error": "upload_id veya file_path gerekli"}

    data = Path(file_path).read_bytes()
    parsed = parse_file_content(data, filename)
    job_id = str(uuid.uuid4())[:12]
    job = _update_job(
        job_id,
        status="parsed",
        upload_id=upload_id,
        filename=filename,
        parse=parsed,
        parse_stats={
            "paragraphs": len(parsed.get("paragraphs") or []),
            "headings": len(parsed.get("headings") or []),
            "tables": len(parsed.get("tables") or []),
            "rows": len(parsed.get("rows") or []),
            "lines": len(parsed.get("lines") or []),
        },
    )
    return {"success": True, "job_id": job_id, "parse": parsed, "parse_stats": job["parse_stats"]}


def extract_signals_for_job(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job or not job.get("parse"):
        return {"success": False, "error": "Job veya parse verisi yok — önce parse çalıştırın"}
    signals = extract_signals(job["parse"], source_files=_job_source_files(job))
    _update_job(job_id, status="signals", signals=signals)
    return {"success": True, "job_id": job_id, "signals": signals}


def generate_plan(job_id: str, main_site_url: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job or not job.get("signals"):
        return {"success": False, "error": "Sinyaller yok — önce extract-signals çalıştırın"}
    result = generate_content_plan(job["signals"], main_site_url, job_id=job_id)
    if result.get("success"):
        _update_job(job_id, status="planned", plan=result["plan"], main_site_url=main_site_url)
    return result


def _wp_publish_page(
    kind: str,
    page: dict[str, Any],
    html: str,
    signals: dict[str, Any],
    main_site_url: str,
    links: list[dict[str, str]],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """WordPress'e gerçek yayın — draft değil, publish + IndexNow."""
    from app.moduller.page_hub import create_page

    loc = (signals.get("locations") or ["Kuşadası"])[0]
    html = _build_page_html(
        page["title"], page.get("location") or loc,
        page.get("category") or page.get("target_keyword", "rehber"),
        signals.get("entities") or [], signals.get("services") or [],
        main_site_url, links, page.get("type", "guide"),
    ) if not html else html

    title = page.get("question") or page["title"] if kind == "sss" else page["title"]
    res = create_page(
        kind,
        title,
        slug=page["slug"],
        content=html,
        keyword=page.get("target_keyword", ""),
        city=loc,
        district=loc,
        status="publish",
        notify_index=True,
        force=force,
    )
    entry = {
        "title": page["title"],
        "slug": page["slug"],
        "type": kind,
        "published": bool(res.get("success")),
        "wp_page_id": (res.get("page") or {}).get("id"),
        "link": (res.get("page") or {}).get("link", ""),
        "indexnow": res.get("indexnow"),
    }
    if not res.get("success"):
        entry["error"] = res.get("error", "Yayınlanamadı")
    return entry


def create_category_pages(
    job_id: str, main_site_url: str = "", dry_run: bool = False, force: bool = False,
) -> dict[str, Any]:
    job = _ensure_job_plan(job_id, main_site_url)
    if not job:
        return {"success": False, "error": "Job bulunamadı — önce dosya yükleyin"}
    if not job.get("plan"):
        return {"success": False, "error": "İçerik planı yok — önce sinyal çıkarın ve plan üretin"}
    main_site_url = main_site_url or job.get("main_site_url", "")
    signals = job.get("signals") or {}
    link_map = {p["page_slug"]: p["links"] for p in job["plan"].get("main_site_link_plan") or []}
    created, previews = [], []

    for page in job["plan"].get("category_pages") or []:
        links = link_map.get(page["slug"], [])
        html = _build_page_html(
            page["title"], signals.get("locations", ["Kuşadası"])[0],
            page.get("target_keyword", "rehber"), signals.get("entities") or [],
            signals.get("services") or [], main_site_url, links, "guide",
        )
        entry = {"title": page["title"], "slug": page["slug"], "html_len": len(html), "type": "category"}
        if dry_run:
            previews.append(entry)
            continue
        pub = _wp_publish_page(
            "landing", page, html, signals, main_site_url, links, force=force,
        )
        entry.update(pub)
        if pub.get("published"):
            created.append(entry)
        else:
            previews.append(entry)

    if not dry_run:
        _update_job(job_id, status="pages_created", category_pages_created=created, publish_errors=previews)
    return {
        "success": True, "dry_run": dry_run, "created": created, "previews": previews,
        "published_count": len(created), "failed_count": len(previews),
        "listing_hub_called": False,
    }


def create_geo_pages(
    job_id: str, main_site_url: str = "", dry_run: bool = False, force: bool = False,
) -> dict[str, Any]:
    job = _ensure_job_plan(job_id, main_site_url)
    if not job:
        return {"success": False, "error": "Job bulunamadı — önce dosya yükleyin"}
    if not job.get("plan"):
        return {"success": False, "error": "İçerik planı yok — önce sinyal çıkarın ve plan üretin"}
    main_site_url = main_site_url or job.get("main_site_url", "")
    signals = job.get("signals") or {}
    link_map = {p["page_slug"]: p["links"] for p in job["plan"].get("main_site_link_plan") or []}
    created, previews = [], []

    for page in job["plan"].get("geo_pages") or []:
        links = link_map.get(page["slug"], [])
        html = _build_page_html(
            page["title"], page.get("location", "Kuşadası"), page.get("category", "rehber"),
            signals.get("entities") or [], signals.get("services") or [], main_site_url, links, "geo",
        )
        entry = {"title": page["title"], "slug": page["slug"], "html_len": len(html)}
        if dry_run:
            previews.append(entry)
            continue
        pub = _wp_publish_page(
            "landing", {**page, "type": "geo"}, html, signals, main_site_url, links, force=force,
        )
        entry.update(pub)
        if pub.get("published"):
            created.append(entry)
        else:
            previews.append(entry)

    if not dry_run:
        _update_job(job_id, geo_pages_created=created)
    return {
        "success": True, "dry_run": dry_run, "created": created, "previews": previews,
        "published_count": len(created), "failed_count": len(previews),
        "listing_hub_called": False,
    }


def create_faq_pages(
    job_id: str, main_site_url: str = "", dry_run: bool = False, force: bool = False,
) -> dict[str, Any]:
    job = _ensure_job_plan(job_id, main_site_url)
    if not job:
        return {"success": False, "error": "Job bulunamadı — önce dosya yükleyin"}
    if not job.get("plan"):
        return {"success": False, "error": "İçerik planı yok — önce sinyal çıkarın ve plan üretin"}
    main_site_url = main_site_url or job.get("main_site_url", "")
    signals = job.get("signals") or {}
    link_map = {p["page_slug"]: p["links"] for p in job["plan"].get("main_site_link_plan") or []}
    created, previews = [], []

    for page in job["plan"].get("faq_pages") or []:
        links = link_map.get(page["slug"], [])
        html = _build_page_html(
            page["title"], signals.get("locations", ["Kuşadası"])[0], "SSS",
            signals.get("entities") or [], signals.get("services") or [], main_site_url, links, "faq",
        )
        entry = {"title": page["title"], "slug": page["slug"], "html_len": len(html)}
        if dry_run:
            previews.append(entry)
            continue
        pub = _wp_publish_page(
            "sss", page, html, signals, main_site_url, links, force=force,
        )
        entry.update(pub)
        if pub.get("published"):
            created.append(entry)
        else:
            previews.append(entry)

    if not dry_run:
        _update_job(job_id, faq_pages_created=created)
    return {
        "success": True, "dry_run": dry_run, "created": created, "previews": previews,
        "published_count": len(created), "failed_count": len(previews),
        "listing_hub_called": False,
    }


def publish_all_to_wordpress(
    job_id: str,
    main_site_url: str = "",
    *,
    run_gate: bool = True,
    force: bool = False,
    include_astro: bool = True,
) -> dict[str, Any]:
    """Quality Gate → WordPress publish (kategori + GEO + SSS) → IndexNow → Rank Watcher."""
    from app.moduller.wordpress_api import ensure_wp_connected, wp_api

    job = _ensure_job_plan(job_id, main_site_url)
    if not job:
        return {"success": False, "error": "Job bulunamadı — önce dosya yükleyin"}
    if not job.get("plan"):
        return {"success": False, "error": "İçerik planı yok"}

    main_site_url = (main_site_url or job.get("main_site_url", "")).strip()
    wp_st = ensure_wp_connected(verify=True)
    wp = wp_api()
    if not wp_st.get("connected") or not wp.connected:
        err = wp_st.get("error") or "WordPress bağlantısı kurulamadı"
        return {
            "success": False,
            "error": f"WordPress bağlantısı yok — {err}",
            "hint": "backend/.env → WP_URL, WP_USERNAME, WP_APP_PASSWORD kontrol edin veya panelden yeniden bağlanın",
        }

    gate_report: dict[str, Any] = {}
    if run_gate:
        gate = run_quality_gate(job_id)
        gate_report = gate.get("quality_gate") or {}
        if not gate.get("deploy_allowed") and not force:
            return {
                "success": False,
                "error": "Quality Gate engelledi — deploy_allowed false",
                "deploy_allowed": False,
                "quality_gate": gate_report,
                "hint": "force=true ile zorlayabilir veya içeriği düzeltip tekrar deneyin",
            }

    url = main_site_url or job.get("main_site_url", "")
    cat = create_category_pages(job_id, url, dry_run=False, force=force)
    geo = create_geo_pages(job_id, url, dry_run=False, force=force)
    faq = create_faq_pages(job_id, url, dry_run=False, force=force)

    all_created = (cat.get("created") or []) + (geo.get("created") or []) + (faq.get("created") or [])
    all_failed = (cat.get("previews") or []) + (geo.get("previews") or []) + (faq.get("previews") or [])
    links = [p.get("link") for p in all_created if p.get("link")]

    rank_results: list[dict[str, Any]] = []
    try:
        from app.moduller.rank_index_watcher import track_keyword
        domain = urlparse(main_site_url).netloc or ""
        for page in all_created[:20]:
            kw = page.get("title", "")
            if kw:
                rank_results.append(track_keyword(kw.lower(), domain, save=True))
    except Exception as exc:
        rank_results.append({"error": str(exc)})

    astro_result: dict[str, Any] = {}
    if include_astro:
        astro_result = create_astro_support_site(job_id, main_site_url)

    publish_report = {
        "category": {"published": cat.get("published_count", 0), "failed": cat.get("failed_count", 0)},
        "geo": {"published": geo.get("published_count", 0), "failed": geo.get("failed_count", 0)},
        "faq": {"published": faq.get("published_count", 0), "failed": faq.get("failed_count", 0)},
        "total_published": len(all_created),
        "total_failed": len(all_failed),
        "live_links": links,
        "quality_gate": gate_report,
        "rank_watcher": rank_results,
        "astro": astro_result,
        "listing_hub_called": False,
    }
    _update_job(job_id, status="published", publish_report=publish_report, published_at=_now())
    return {
        "success": len(all_created) > 0,
        "job_id": job_id,
        "publish_report": publish_report,
        "created": all_created,
        "errors": all_failed,
    }


def create_astro_support_site(job_id: str, main_site_url: str = "") -> dict[str, Any]:
    job = _get_job(job_id)
    if not job or not job.get("plan"):
        return {"success": False, "error": "İçerik planı yok"}
    main_site_url = main_site_url or job.get("main_site_url", "")
    astro_cfg = job["plan"].get("astro_support_site") or {}

    from app.moduller.astro_factory import create_project, generate_site_plan, _update_project, _get_project, _project_path, _write_project_data

    proj_res = create_project({
        "site_name": astro_cfg.get("site_name", "Kuşadası Rehber"),
        "slug": astro_cfg.get("slug", "kusadasi-rehber"),
        "domain": astro_cfg.get("domain", ""),
        "seed_keyword": astro_cfg.get("seed_keyword", "kuşadası gece hayatı"),
        "location": astro_cfg.get("location", "Kuşadası"),
        "niche": astro_cfg.get("niche", "Yerel rehber"),
        "main_site_url": main_site_url,
    })
    if not proj_res.get("success"):
        return proj_res

    project_id = proj_res["project"]["id"]
    signals = job.get("signals") or {}
    geo_pages = []
    faq_pages = []
    blog_pages = []

    for p in (job["plan"].get("category_pages") or [])[:6]:
        geo_pages.append({
            "title": p["title"], "slug": p["slug"], "type": "geo",
            "content_html": _build_page_html(
                p["title"], astro_cfg.get("location", "Kuşadası"), p.get("target_keyword", ""),
                signals.get("entities") or [], signals.get("services") or [], main_site_url, [], "guide",
            ),
        })
    for p in (job["plan"].get("faq_pages") or [])[:4]:
        faq_pages.append({
            "title": p["title"], "slug": p["slug"].replace("sss/", ""),
            "content_html": _build_page_html(
                p["title"], astro_cfg.get("location", "Kuşadası"), "SSS",
                signals.get("entities") or [], signals.get("services") or [], main_site_url, [], "faq",
            ),
        })
    for p in (job["plan"].get("blog_posts") or [])[:3]:
        blog_pages.append({
            "title": p["title"], "slug": p["slug"],
            "content_html": _build_page_html(
                p["title"], astro_cfg.get("location", "Kuşadası"), "blog",
                signals.get("entities") or [], signals.get("services") or [], main_site_url, [], "guide",
            ),
        })

    plan_res = generate_site_plan(
        astro_cfg.get("seed_keyword", "kuşadası gece hayatı"),
        location=astro_cfg.get("location", "Kuşadası"),
        project_id=project_id,
        domain=astro_cfg.get("domain", ""),
    )

    project = _get_project(project_id)
    project_path = _project_path(project["slug"])
    home = {
        "title": astro_cfg.get("site_name"),
        "description": f"{astro_cfg.get('location')} yerel rehber — mekan kataloğu değil",
        "content_html": _build_page_html(
            astro_cfg.get("site_name", "Rehber"), astro_cfg.get("location", "Kuşadası"),
            "rehber", signals.get("entities") or [], signals.get("services") or [],
            main_site_url, [], "guide",
        ),
    }
    _write_project_data(project_path, project, home_page=home, geo_pages=geo_pages, faq_pages=faq_pages, blog_pages=blog_pages)

    from app.moduller.astro_factory import generate_pages
    gen = generate_pages(project_id)
    if not gen.get("success"):
        logger.warning("Astro generate_pages: %s", gen.get("error"))

    _update_job(job_id, status="astro_created", astro_project_id=project_id, astro_plan=plan_res.get("plan"), astro_generated=gen.get("success", False))

    return {
        "success": True,
        "project_id": project_id,
        "project": proj_res["project"],
        "pages_written": len(geo_pages) + len(faq_pages) + len(blog_pages) + 1,
        "astro_files_generated": gen.get("files_written", []),
        "filesystem_path": proj_res.get("filesystem_path"),
        "note": astro_cfg.get("note"),
        "listing_hub_called": False,
    }


def _push_to_entity_graph(signals: dict[str, Any], job_id: str) -> dict[str, Any]:
    try:
        from app.moduller import entity_geo_graph as egg
        state = egg._load_state()
        graph_id = f"place-pipeline-{job_id}"
        nodes: dict[str, dict] = {}
        edges: list[dict] = []

        def nid(ntype: str, label: str) -> str:
            return egg._node_id(ntype, label)

        for loc in signals.get("locations") or []:
            nodes[nid("location", loc)] = {"id": nid("location", loc), "type": "location", "label": loc, "score": 70}
        for ent in signals.get("entities") or []:
            nodes[nid("entity", ent)] = {"id": nid("entity", ent), "type": "entity", "label": ent, "score": 60, "metadata": {"source": "place_seo_pipeline", "not_a_listing": True}}
        for topic in signals.get("topics") or []:
            nodes[nid("topic", topic)] = {"id": nid("topic", topic), "type": "topic", "label": topic, "score": 65}

        locs = signals.get("locations") or []
        for ent in (signals.get("entities") or [])[:20]:
            if locs:
                edges.append({"source": nid("entity", ent), "target": nid("location", locs[0]), "type": "located_in", "weight": 0.8})

        state.setdefault("graphs", {})[graph_id] = {
            "id": graph_id,
            "source": "place_seo_pipeline",
            "job_id": job_id,
            "nodes": list(nodes.values()),
            "edges": edges,
            "created_at": _now(),
        }
        egg._save_state(state)
        return {"success": True, "graph_id": graph_id, "node_count": len(nodes), "edge_count": len(edges)}
    except Exception as exc:
        logger.warning("Entity graph push: %s", exc)
        return {"success": False, "error": str(exc)}


def _prepare_rank_watcher_keywords(plan: dict[str, Any], domain: str) -> list[dict[str, Any]]:
    results = []
    try:
        from app.moduller.rank_index_watcher import track_keyword
        for section in ("category_pages", "geo_pages", "faq_pages"):
            for page in (plan.get(section) or [])[:15]:
                kw = page.get("target_keyword", "")
                if kw:
                    results.append(track_keyword(kw, domain, save=False))
    except Exception as exc:
        results.append({"error": str(exc)})
    return results


def run_quality_gate(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job or not job.get("plan"):
        return {"success": False, "error": "İçerik planı yok"}

    from app.moduller.seo_quality_gate import seo_quality_gate

    signals = job.get("signals") or {}
    main_site_url = job.get("main_site_url", "")
    results: list[dict[str, Any]] = []
    deploy_allowed = True

    sample_pages = (job["plan"].get("category_pages") or [])[:5] + (job["plan"].get("geo_pages") or [])[:5]
    for page in sample_pages:
        html = _build_page_html(
            page["title"], signals.get("locations", ["Kuşadası"])[0],
            page.get("category") or page.get("target_keyword", "rehber"),
            signals.get("entities") or [], signals.get("services") or [],
            main_site_url, [], page.get("type", "guide"),
        )
        analysis = seo_quality_gate.analyze_page(html, page.get("target_keyword", ""), location=signals.get("locations", ["Kuşadası"])[0], title=page["title"])
        passed = analysis.get("pass", False) and analysis.get("seo_score", 0) >= 70
        if not passed:
            deploy_allowed = False
        results.append({
            "slug": page.get("slug"),
            "title": page.get("title"),
            "seo_score": analysis.get("seo_score"),
            "geo_score": analysis.get("geo_score"),
            "aeo_score": analysis.get("aeo_score"),
            "pass": passed,
            "deploy_allowed": passed,
        })

    entity_push = _push_to_entity_graph(signals, job_id)
    rank_prep = _prepare_rank_watcher_keywords(job["plan"], urlparse(main_site_url).netloc or "")

    gate_report = {"pages": results, "deploy_allowed": deploy_allowed, "entity_graph": entity_push, "rank_watcher_keywords": rank_prep}
    _update_job(job_id, status="gated", quality_gate=gate_report, deploy_allowed=deploy_allowed)
    return {"success": True, "job_id": job_id, "quality_gate": gate_report, "deploy_allowed": deploy_allowed}


def export_report(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"place-seo-pipeline-{job_id}.json"
    report = {
        "job_id": job_id,
        "status": job.get("status"),
        "filename": job.get("filename"),
        "parse_stats": job.get("parse_stats"),
        "signals": job.get("signals"),
        "plan_summary": (job.get("plan") or {}).get("summary"),
        "quality_gate": job.get("quality_gate"),
        "deploy_allowed": job.get("deploy_allowed"),
        "astro_project_id": job.get("astro_project_id"),
        "listing_hub_records_created": 0,
        "exported_at": _now(),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _update_job(job_id, report_path=str(report_path))
    return {"success": True, "report_path": str(report_path), "report": report}


def list_jobs(limit: int = 50) -> dict[str, Any]:
    jobs = list((_load_state().get("jobs") or {}).values())
    jobs.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"success": True, "jobs": jobs[:limit], "total": len(jobs)}


def get_job_detail(job_id: str) -> dict[str, Any]:
    job = _get_job(job_id)
    if not job:
        return {"success": False, "error": "Job bulunamadı"}
    return {"success": True, "job": job}


place_seo_pipeline = type("PlaceSEOPipeline", (), {
    "health": staticmethod(health),
    "upload_file": staticmethod(upload_file),
    "process_batch_upload": staticmethod(process_batch_upload),
    "parse_upload": staticmethod(parse_upload),
    "extract_signals_for_job": staticmethod(extract_signals_for_job),
    "generate_plan": staticmethod(generate_plan),
    "create_category_pages": staticmethod(create_category_pages),
    "create_geo_pages": staticmethod(create_geo_pages),
    "create_faq_pages": staticmethod(create_faq_pages),
    "publish_all_to_wordpress": staticmethod(publish_all_to_wordpress),
    "create_astro_support_site": staticmethod(create_astro_support_site),
    "run_quality_gate": staticmethod(run_quality_gate),
    "export_report": staticmethod(export_report),
    "list_jobs": staticmethod(list_jobs),
    "get_job_detail": staticmethod(get_job_detail),
})()
