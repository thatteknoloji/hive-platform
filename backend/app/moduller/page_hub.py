"""Sayfa Merkezi — WP sayfa, gece_hayati, SSS ve SEO landing yönetimi."""

from __future__ import annotations

import difflib
import logging
import re
from typing import Any
from urllib.parse import urljoin

import requests

from app.moduller.category_hub import connect_wordpress, talon_keywords
from app.moduller.indexnow import bildirim_gonder
from app.moduller.sss_generator import build_html, generate_sss_page
from app.moduller.storyforge_categories import _slugify
from app.moduller.wordpress_api import wp_api

logger = logging.getLogger("hive.page_hub")

PAGE_KINDS: dict[str, dict[str, str]] = {
    "page": {
        "rest": "pages",
        "label": "WP Sayfa",
        "queue_rest": "pages",
    },
    "gece": {
        "rest": "gece_hayati",
        "label": "Gece Hayatı",
        "queue_rest": "gece_hayati",
    },
    "sss": {
        "rest": "pages",
        "label": "SSS Sayfası",
        "queue_rest": "pages",
    },
    "landing": {
        "rest": "pages",
        "label": "SEO Landing",
        "queue_rest": "pages",
    },
}

DEFAULT_CITY = "Aydın"
DEFAULT_DISTRICT = "Kuşadası"
DEFAULT_CATEGORY = "Gece Hayatı"
DEFAULT_SUBCATEGORY = "Eğlence"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _cfg(kind: str) -> dict[str, str]:
    k = (kind or "page").strip().lower()
    if k not in PAGE_KINDS:
        raise ValueError(f"Geçersiz sayfa türü: {kind}")
    return PAGE_KINDS[k]


def _parse_page_batch(raw: dict[str, Any]) -> list[dict[str, Any]]:
    batch = raw.get("data") if isinstance(raw.get("data"), list) else []
    if not batch and raw.get("id"):
        batch = [raw]
    out: list[dict[str, Any]] = []
    for p in batch:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        title = p.get("title", "")
        if isinstance(title, dict):
            title = title.get("rendered", "")
        out.append({
            "id": int(p["id"]),
            "title": title,
            "slug": p.get("slug", ""),
            "parent": int(p.get("parent") or 0),
            "status": p.get("status", ""),
            "link": p.get("link") or "",
            "excerpt": _excerpt_text(p.get("excerpt")),
            "content_len": len(_content_text(p.get("content"))),
        })
    return out


def _content_text(content: Any) -> str:
    if isinstance(content, dict):
        return content.get("rendered", "") or ""
    return str(content or "")


def _excerpt_text(excerpt: Any) -> str:
    if isinstance(excerpt, dict):
        return excerpt.get("rendered", "") or ""
    return str(excerpt or "")


def _list_pages(
    api: Any,
    rest: str,
    per_page: int = 100,
    max_pages: int = 3,
    parent: int | None = None,
    search: str = "",
    status: str = "publish,draft,pending,private",
) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    page_num = 1
    while page_num <= max_pages:
        params: dict[str, Any] = {"per_page": per_page, "page": page_num, "status": status}
        if parent is not None:
            params["parent"] = parent
        if search:
            params["search"] = search
        raw = api._request("GET", f"/wp-json/wp/v2/{rest}", params=params)
        if not raw.get("success"):
            break
        batch = _parse_page_batch(raw)
        if not batch:
            break
        pages.extend(batch)
        if len(batch) < per_page:
            break
        page_num += 1
    return pages


def _count_pages(api: Any, rest: str) -> int:
    if not api.connected:
        return 0
    try:
        url = f"{api._base()}/wp-json/wp/v2/{rest}"
        r = requests.get(
            url,
            headers={**api._auth_headers(), "Accept": "application/json"},
            auth=api._auth(),
            params={"per_page": 1, "page": 1, "status": "publish,draft,pending,private"},
            timeout=20,
            verify=False,
        )
        if r.status_code == 200:
            return int(r.headers.get("X-WP-Total", 0) or 0)
    except Exception:
        pass
    return 0


def _build_tree(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for p in pages:
        by_parent.setdefault(p["parent"], []).append(p)
    for kids in by_parent.values():
        kids.sort(key=lambda x: x["title"].lower())

    def nest(parent_id: int) -> list[dict[str, Any]]:
        out = []
        for item in by_parent.get(parent_id, []):
            out.append({**item, "children": nest(item["id"])})
        return out

    return nest(0)


def hub_status() -> dict[str, Any]:
    st = connect_wordpress()
    return {
        "wp_connected": st.get("wp_connected", False),
        "wp_url": st.get("wp_url", ""),
        "kinds": list(PAGE_KINDS.keys()),
        "message": st.get("message", ""),
    }


def get_tree(kind: str = "page", search: str = "") -> dict[str, Any]:
    cfg = _cfg(kind)
    connect_wordpress()
    api = wp_api()
    rest = cfg["rest"]

    if not api.connected:
        return {
            "success": True,
            "kind": kind,
            "rest": rest,
            "pages": [],
            "tree": [],
            "total": 0,
            "wp_connected": False,
            "error": "WordPress bağlantısı yok — .env WP_URL / WP_USERNAME / WP_APP_PASSWORD kontrol et",
        }

    q = (search or "").strip()
    wp_total = _count_pages(api, rest)

    if q:
        pages = _list_pages(api, rest, max_pages=5, search=q)
    else:
        roots = _list_pages(api, rest, max_pages=2, parent=0)
        pages = list(roots)
        for root in roots[:15]:
            children = _list_pages(api, rest, max_pages=1, parent=root["id"])
            pages.extend(children)

    return {
        "success": True,
        "kind": kind,
        "rest": rest,
        "pages": pages,
        "tree": _build_tree(pages),
        "total": len(pages),
        "wp_total": wp_total,
        "truncated": wp_total > len(pages),
        "wp_connected": True,
    }


def check_duplicate(
    kind: str,
    title: str = "",
    slug: str = "",
    parent_id: int = 0,
) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    slug = _slugify(slug or title)
    title_norm = _norm(title)
    pages = _list_pages(api, cfg["rest"], max_pages=5)

    exact_slug = next((p for p in pages if _norm(p["slug"]) == _norm(slug)), None)
    exact_title = next(
        (p for p in pages if _norm(p["title"]) == title_norm and p["parent"] == parent_id),
        None,
    )

    similar: list[dict[str, Any]] = []
    for p in pages:
        if p["parent"] != parent_id:
            continue
        ratio = difflib.SequenceMatcher(None, title_norm, _norm(p["title"])).ratio()
        if ratio >= 0.82 and _norm(p["title"]) != title_norm:
            similar.append({**p, "similarity": round(ratio, 2)})

    warnings: list[str] = []
    blocked = bool(exact_slug)
    if exact_slug:
        warnings.append(f"Aynı slug zaten var: {exact_slug['title']} (#{exact_slug['id']})")
    if exact_title:
        warnings.append(f"Aynı başlık bu üst sayfada var: {exact_title['title']} (#{exact_title['id']})")
    for s in similar[:5]:
        warnings.append(f"Benzer başlık: {s['title']} (%{int(s['similarity']*100)})")

    return {
        "success": True,
        "slug": slug,
        "blocked": blocked,
        "has_warnings": bool(warnings),
        "warnings": warnings,
        "exact_slug": exact_slug,
        "exact_title": exact_title,
        "similar": similar[:5],
        "can_force": not blocked,
    }


def _generate_landing_html(keyword: str, city: str = DEFAULT_CITY, district: str = DEFAULT_DISTRICT) -> dict[str, Any]:
    from app.moduller import llm_router

    prompt = f"""BalKutusu.com için SEO uyumlu bir landing sayfası yaz.

Şehir: {city}
İlçe: {district}
Anahtar kelime: {keyword}

Çıktı formatı (birebir):
SEO Başlığı: (max 60 karakter)
Meta Açıklama: (max 155 karakter)
H1: 
Giriş: (120-180 kelime, yerel ve bilgilendirici)
İçerik: (3-5 H2 bölümü, her bölüm 80-150 kelime, HTML <h2> ve <p> kullan)
SSS: (en az 5 soru-cevap, S: ve C: formatında)

Kurallar: uydurma işletme adı verme, abartılı ifade kullanma, Türkçe yaz."""

    system = "Sen BalKutusu.com için yerel SEO landing sayfası üreten bir içerik motorusun."
    raw, engine = llm_router.generate(prompt, system=system, max_tokens=3500, min_length=200)

    seo_title = keyword.title()[:60]
    meta_desc = f"{district}, {city} bölgesinde {keyword} hakkında kapsamlı rehber ve yerel bilgiler."[:155]
    h1 = f"{district} {keyword.title()} Rehberi"
    intro = f"{district} ve {city} çevresinde {keyword} arayanlar için hazırlanan bu sayfa, yerel planlama ve pratik bilgiler sunar."
    body_html = f"<p>{intro}</p>"

    if raw:
        m = re.search(r"SEO Başlığı\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            seo_title = m.group(1).strip()[:60]
        m = re.search(r"Meta Açıklama\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            meta_desc = m.group(1).strip()[:155]
        m = re.search(r"H1\s*[:\-]\s*(.+)", raw, re.I)
        if m:
            h1 = m.group(1).strip()[:120]

        intro_m = re.search(r"Giriş\s*[:\-]\s*(.+?)(?=\n\s*İçerik|\n\s*SSS|\Z)", raw, re.S | re.I)
        if intro_m:
            intro = intro_m.group(1).strip()
        content_m = re.search(r"İçerik\s*[:\-]\s*(.+?)(?=\n\s*SSS|\Z)", raw, re.S | re.I)
        if content_m:
            body_html = content_m.group(1).strip()
            if "<h2" not in body_html.lower():
                body_html = f"<p>{intro}</p>\n" + "\n".join(
                    f"<h2>{line.strip()}</h2><p>{district} bölgesinde {keyword} ile ilgili yerel bilgiler.</p>"
                    for line in body_html.split("\n") if line.strip()
                )
        else:
            body_html = f"<p>{intro}</p>"

        faq_html = ""
        for block in re.split(r"(?=^S:\s*)", raw, flags=re.M):
            m = re.match(r"S:\s*(.+?)\n+C:\s*(.+)", block.strip(), re.S)
            if m:
                faq_html += f"<h3>{m.group(1).strip()}</h3><p>{m.group(2).strip()}</p>\n"
        if faq_html:
            body_html += "\n<h2>Sık Sorulan Sorular</h2>\n" + faq_html

    if "<p" not in body_html.lower() and "<h" not in body_html.lower():
        body_html = f"<p>{intro}</p>"

    return {
        "seo_title": seo_title,
        "meta_description": meta_desc,
        "h1": h1,
        "html": body_html,
        "ai_engine": engine or "",
    }


def create_page(
    kind: str,
    title: str,
    slug: str = "",
    content: str = "",
    parent_id: int = 0,
    status: str = "draft",
    excerpt: str = "",
    force: bool = False,
    keyword: str = "",
    city: str = DEFAULT_CITY,
    district: str = DEFAULT_DISTRICT,
    category: str = DEFAULT_CATEGORY,
    subcategory: str = DEFAULT_SUBCATEGORY,
    notify_index: bool = False,
) -> dict[str, Any]:
    title = (title or "").strip()
    if not title and not keyword:
        return {"success": False, "error": "Sayfa başlığı gerekli"}

    if kind in ("sss", "landing") and not content:
        kw = (keyword or title).strip()
        if kind == "sss":
            page_data = generate_sss_page(city, district, category, subcategory, kw)
            title = page_data.get("seo_title") or title
            content = page_data.get("html") or build_html(page_data)
            excerpt = page_data.get("meta_description") or excerpt
            slug = page_data.get("slug") or slug
        else:
            landing = _generate_landing_html(kw, city, district)
            title = landing.get("seo_title") or title
            content = landing.get("html") or ""
            excerpt = landing.get("meta_description") or excerpt

    dup = check_duplicate(kind, title, slug, parent_id)
    if not dup.get("success"):
        return dup
    if dup.get("blocked") and not force:
        return {"success": False, "error": dup["warnings"][0], "duplicate": dup}
    if dup.get("has_warnings") and not force and dup.get("exact_title"):
        return {"success": False, "error": dup["warnings"][0], "duplicate": dup, "needs_confirm": True}

    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    final_slug = dup.get("slug") or _slugify(slug or title)
    body: dict[str, Any] = {
        "title": title,
        "content": content,
        "status": status,
        "slug": final_slug,
    }
    if parent_id:
        body["parent"] = parent_id
    if excerpt:
        body["excerpt"] = excerpt

    if cfg["rest"] == "pages":
        res = api.create_page(title, content, status=status, slug=final_slug, parent=parent_id, excerpt=excerpt)
    else:
        res = api._request("POST", f"/wp-json/wp/v2/{cfg['rest']}", json_body=body)

    if not res.get("success") and not res.get("id"):
        return {"success": False, "error": res.get("error", "Oluşturulamadı")}

    page_id = int(res.get("id") or 0)
    link = res.get("link") or ""
    indexnow: dict[str, Any] = {}
    if notify_index and status == "publish" and link:
        indexnow = bildirim_gonder(link)

    return {
        "success": True,
        "created": True,
        "page": {
            "id": page_id,
            "title": title,
            "slug": final_slug,
            "parent": parent_id,
            "status": status,
            "link": link,
        },
        "warnings": dup.get("warnings", []),
        "indexnow": indexnow,
    }


def create_bulk_keywords(
    kind: str,
    keywords: str,
    parent_id: int = 0,
    status: str = "draft",
    force: bool = False,
    city: str = DEFAULT_CITY,
    district: str = DEFAULT_DISTRICT,
    notify_index: bool = False,
) -> dict[str, Any]:
    lines = [ln.strip() for ln in (keywords or "").splitlines() if ln.strip()]
    if not lines:
        return {"success": False, "error": "En az bir kelime girin"}

    created = 0
    errors: list[str] = []
    pages_out: list[dict[str, Any]] = []

    for line in lines:
        title = line.strip().title()
        res = create_page(
            kind=kind,
            title=title,
            keyword=line,
            parent_id=parent_id,
            status=status,
            force=force,
            city=city,
            district=district,
            notify_index=notify_index and status == "publish",
        )
        if res.get("success"):
            created += 1
            pages_out.append(res.get("page") or {})
        else:
            errors.append(f"{line}: {res.get('error', 'hata')}")

    return {
        "success": created > 0 or not errors,
        "created": created,
        "errors": errors,
        "pages": pages_out,
        "total": len(lines),
    }


def list_queue(kind: str = "page", limit: int = 50) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    raw = api._request(
        "GET",
        f"/wp-json/wp/v2/{cfg['queue_rest']}",
        params={"per_page": min(limit, 100), "page": 1, "status": "draft,pending"},
    )
    if not raw.get("success"):
        return raw

    rows = _parse_page_batch(raw)
    queue = [
        p for p in rows
        if p.get("status") in ("draft", "pending") or p.get("content_len", 0) < 50
    ]
    return {"success": True, "items": queue[:limit], "count": len(queue)}


def publish_page(
    kind: str,
    page_id: int,
    status: str = "publish",
    notify_index: bool = True,
) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}
    if not page_id:
        return {"success": False, "error": "Sayfa ID gerekli"}

    if cfg["rest"] == "pages":
        res = api.update_page(page_id, status=status)
    else:
        res = api._request("POST", f"/wp-json/wp/v2/{cfg['rest']}/{page_id}", json_body={"status": status})

    if not res.get("success") and not res.get("id"):
        return {"success": False, "error": res.get("error", "Yayınlanamadı")}

    link = res.get("link") or ""
    indexnow: dict[str, Any] = {}
    if notify_index and status == "publish" and link:
        indexnow = bildirim_gonder(link)

    return {
        "success": True,
        "page_id": page_id,
        "status": status,
        "link": link,
        "indexnow": indexnow,
    }


def bulk_publish(kind: str, page_ids: list[int], notify_index: bool = True) -> dict[str, Any]:
    published = 0
    errors: list[str] = []
    links: list[str] = []
    for pid in page_ids:
        res = publish_page(kind, pid, notify_index=notify_index)
        if res.get("success"):
            published += 1
            if res.get("link"):
                links.append(res["link"])
        else:
            errors.append(f"#{pid}: {res.get('error', 'hata')}")
    return {"success": published > 0, "published": published, "errors": errors, "links": links}


def update_page_fields(
    kind: str,
    page_id: int,
    title: str = "",
    slug: str = "",
    content: str = "",
    excerpt: str = "",
    parent_id: int | None = None,
) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    fields: dict[str, Any] = {}
    if title:
        fields["title"] = title
    if slug:
        fields["slug"] = _slugify(slug)
    if content is not None and content != "":
        fields["content"] = content
    if excerpt is not None:
        fields["excerpt"] = excerpt
    if parent_id is not None:
        fields["parent"] = parent_id

    if not fields:
        return {"success": False, "error": "Güncellenecek alan yok"}

    if cfg["rest"] == "pages":
        res = api.update_page(page_id, **fields)
    else:
        res = api._request("POST", f"/wp-json/wp/v2/{cfg['rest']}/{page_id}", json_body=fields)

    if not res.get("success") and not res.get("id"):
        return {"success": False, "error": res.get("error", "Güncellenemedi")}
    return {"success": True, "page_id": page_id, "updated": fields}


def get_page_detail(kind: str, page_id: int) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    raw = api._request("GET", f"/wp-json/wp/v2/{cfg['rest']}/{page_id}")
    if not raw.get("success") and not raw.get("id"):
        return {"success": False, "error": raw.get("error", "Sayfa bulunamadı")}

    title = raw.get("title", "")
    if isinstance(title, dict):
        title = title.get("rendered", "")

    return {
        "success": True,
        "page": {
            "id": int(raw["id"]),
            "title": title,
            "slug": raw.get("slug", ""),
            "parent": int(raw.get("parent") or 0),
            "status": raw.get("status", ""),
            "link": raw.get("link", ""),
            "excerpt": _excerpt_text(raw.get("excerpt")),
            "content": _content_text(raw.get("content")),
        },
    }


def verify_page_url(kind: str, page_id: int) -> dict[str, Any]:
    detail = get_page_detail(kind, page_id)
    if not detail.get("success"):
        return detail

    link = detail["page"].get("link") or ""
    live = False
    status_code = 0
    if link:
        try:
            r = requests.get(link, timeout=15, allow_redirects=True, verify=False)
            status_code = r.status_code
            live = r.status_code == 200
        except requests.RequestException as e:
            return {"success": True, "link": link, "live": False, "status_code": 0, "error": str(e)}

    return {"success": True, "link": link, "live": live, "status_code": status_code}


def generate_preview(
    kind: str,
    keyword: str,
    city: str = DEFAULT_CITY,
    district: str = DEFAULT_DISTRICT,
    category: str = DEFAULT_CATEGORY,
    subcategory: str = DEFAULT_SUBCATEGORY,
) -> dict[str, Any]:
    kw = (keyword or "").strip()
    if not kw:
        return {"success": False, "error": "Anahtar kelime gerekli"}

    if kind == "sss":
        page = generate_sss_page(city, district, category, subcategory, kw)
        return {
            "success": True,
            "title": page.get("seo_title"),
            "slug": page.get("slug"),
            "excerpt": page.get("meta_description"),
            "content": page.get("html"),
            "ai_used": page.get("ai_ollama", False),
        }

    landing = _generate_landing_html(kw, city, district)
    return {
        "success": True,
        "title": landing.get("seo_title"),
        "slug": _slugify(kw),
        "excerpt": landing.get("meta_description"),
        "content": landing.get("html"),
        "ai_used": bool(landing.get("ai_engine")),
    }


def notify_indexnow(url: str) -> dict[str, Any]:
    if not url:
        return {"success": False, "error": "URL gerekli"}
    result = bildirim_gonder(url)
    return {"success": True, **result}


def talon_keyword_queue(
    seed_keyword: str = "",
    location: str = DEFAULT_DISTRICT,
    limit: int = 30,
) -> dict[str, Any]:
    """Skorlu keyword kuyruğu — Talon Orchestrator öncelikli."""
    seed = (seed_keyword or "").strip()
    if seed:
        try:
            from app.moduller.talon_orchestrator import get_scored_keyword_queue
            return get_scored_keyword_queue(seed, location or DEFAULT_DISTRICT, limit=limit)
        except Exception as e:
            logger.warning("Talon orchestrator kuyruk hatası: %s", e)
    return talon_keywords(limit)
