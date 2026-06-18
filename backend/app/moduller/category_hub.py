"""Kategori Merkezi — ilan + hikaye kategorileri, oluşturma, gönderme, birleştirme."""

from __future__ import annotations

import difflib
import logging
import re
from typing import Any
from urllib.parse import urljoin

import requests

from app.moduller.storyforge_categories import (
    _slugify,
    create_from_keywords,
    preview_keywords,
    sync_categories_to_wordpress,
)
from app.moduller.storyforge_v2 import storyforge
from app.moduller.talon_db import favori_listele
from app.moduller.wordpress_api import ensure_wp_connected, wp_api

logger = logging.getLogger("hive.category_hub")

TAXONOMIES: dict[str, dict[str, str]] = {
    "ilan": {
        "taxonomy": "companion_category",
        "post_type": "companion_profile",
        "label": "İlan",
        "cat_field": "companion_category",
    },
    "hikaye": {
        "taxonomy": "story_category",
        "post_type": "erotic_story",
        "label": "Hikaye",
        "cat_field": "story_category",
    },
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _cfg(kind: str) -> dict[str, str]:
    k = (kind or "ilan").strip().lower()
    if k not in TAXONOMIES:
        raise ValueError(f"Geçersiz tür: {kind}")
    return TAXONOMIES[k]


def _parse_term_batch(raw: dict[str, Any]) -> list[dict[str, Any]]:
    batch = raw.get("data") if isinstance(raw.get("data"), list) else []
    if not batch and raw.get("id"):
        batch = [raw]
    out: list[dict[str, Any]] = []
    for t in batch:
        if not isinstance(t, dict) or not t.get("id"):
            continue
        out.append({
            "id": int(t["id"]),
            "name": t.get("name", ""),
            "slug": t.get("slug", ""),
            "parent": int(t.get("parent") or 0),
            "count": int(t.get("count") or 0),
            "description": t.get("description") or "",
            "link": t.get("link") or "",
        })
    return out


def _list_terms(
    api: Any,
    taxonomy: str,
    per_page: int = 100,
    max_pages: int = 3,
    parent: int | None = None,
    search: str = "",
) -> list[dict[str, Any]]:
    """WP taxonomy — sayfalı; varsayılan max 3 sayfa (performans)."""
    terms: list[dict[str, Any]] = []
    page = 1
    while page <= max_pages:
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if parent is not None:
            params["parent"] = parent
        if search:
            params["search"] = search
        raw = api._request("GET", f"/wp-json/wp/v2/{taxonomy}", params=params)
        if not raw.get("success"):
            break
        batch = _parse_term_batch(raw)
        if not batch:
            break
        terms.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return terms


def _count_terms(api: Any, taxonomy: str) -> int:
    if not api.connected:
        return 0
    try:
        import requests
        url = f"{api._base()}/wp-json/wp/v2/{taxonomy}"
        r = requests.get(
            url,
            headers={**api._auth_headers(), "Accept": "application/json"},
            auth=api._auth(),
            params={"per_page": 1, "page": 1},
            timeout=20,
            verify=False,
        )
        if r.status_code == 200:
            return int(r.headers.get("X-WP-Total", 0) or 0)
    except Exception:
        pass
    return 0


def _build_tree(terms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_parent: dict[int, list[dict[str, Any]]] = {}
    for t in terms:
        by_parent.setdefault(t["parent"], []).append(t)
    for kids in by_parent.values():
        kids.sort(key=lambda x: x["name"].lower())

    def nest(parent_id: int) -> list[dict[str, Any]]:
        out = []
        for t in by_parent.get(parent_id, []):
            out.append({**t, "children": nest(t["id"])})
        return out

    return nest(0)


def connect_wordpress() -> dict[str, Any]:
    """`.env` ile WP oturumu aç veya yenile."""
    st = ensure_wp_connected(verify=True)
    api = wp_api()
    return {
        "success": bool(st.get("connected") or api.connected),
        "wp_connected": bool(st.get("connected") or api.connected),
        "wp_url": st.get("url") or (api.status().get("url", "") if api.connected else ""),
        "message": st.get("message") or st.get("error", ""),
        "auto_connected": st.get("auto_connected", False),
    }


def hub_status() -> dict[str, Any]:
    st = connect_wordpress()
    return {
        "wp_connected": st.get("wp_connected", False),
        "wp_url": st.get("wp_url", ""),
        "kinds": list(TAXONOMIES.keys()),
        "message": st.get("message", ""),
    }


def get_tree(kind: str = "ilan", search: str = "") -> dict[str, Any]:
    cfg = _cfg(kind)
    connect_wordpress()
    api = wp_api()
    if not api.connected:
        return {
            "success": True,
            "kind": kind,
            "taxonomy": cfg["taxonomy"],
            "terms": [],
            "tree": [],
            "total": 0,
            "wp_connected": False,
            "error": "WordPress bağlantısı yok — .env WP_URL / WP_USERNAME / WP_APP_PASSWORD kontrol et",
        }

    q = (search or "").strip()
    wp_total = _count_terms(api, cfg["taxonomy"])

    if kind == "hikaye" and wp_total == 0:
        sync_categories_to_wordpress(api)
        wp_total = _count_terms(api, cfg["taxonomy"])

    if q:
        terms = _list_terms(api, cfg["taxonomy"], max_pages=5, search=q)
    else:
        roots = _list_terms(api, cfg["taxonomy"], max_pages=2, parent=0)
        terms = list(roots)
        for root in roots[:12]:
            children = _list_terms(api, cfg["taxonomy"], max_pages=1, parent=root["id"])
            terms.extend(children)

    return {
        "success": True,
        "kind": kind,
        "taxonomy": cfg["taxonomy"],
        "terms": terms,
        "tree": _build_tree(terms),
        "total": len(terms),
        "wp_total": wp_total,
        "truncated": wp_total > len(terms),
        "wp_connected": True,
    }


def check_duplicate(
    kind: str,
    name: str = "",
    slug: str = "",
    parent_id: int = 0,
) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    slug = _slugify(slug or name)
    name_norm = _norm(name)
    terms = _list_terms(api, cfg["taxonomy"])

    exact_slug = next((t for t in terms if _norm(t["slug"]) == _norm(slug)), None)
    exact_name = next((t for t in terms if _norm(t["name"]) == name_norm and t["parent"] == parent_id), None)

    similar: list[dict[str, Any]] = []
    for t in terms:
        if t["parent"] != parent_id:
            continue
        ratio = difflib.SequenceMatcher(None, name_norm, _norm(t["name"])).ratio()
        if ratio >= 0.82 and _norm(t["name"]) != name_norm:
            similar.append({**t, "similarity": round(ratio, 2)})

    blocked = bool(exact_slug)
    warnings: list[str] = []
    if exact_slug:
        warnings.append(f"Aynı slug zaten var: {exact_slug['name']} (#{exact_slug['id']})")
    if exact_name:
        warnings.append(f"Aynı isim bu üst kategoride var: {exact_name['name']} (#{exact_name['id']})")
    for s in similar[:5]:
        warnings.append(f"Benzer isim: {s['name']} (%{int(s['similarity']*100)})")

    return {
        "success": True,
        "slug": slug,
        "blocked": blocked,
        "has_warnings": bool(warnings),
        "warnings": warnings,
        "exact_slug": exact_slug,
        "exact_name": exact_name,
        "similar": similar[:5],
        "can_force": not blocked,
    }


def create_category(
    kind: str,
    name: str,
    slug: str = "",
    parent_id: int = 0,
    force: bool = False,
) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        return {"success": False, "error": "Kategori adı gerekli"}

    dup = check_duplicate(kind, name, slug, parent_id)
    if not dup.get("success"):
        return dup
    if dup.get("blocked") and not force:
        return {"success": False, "error": dup["warnings"][0], "duplicate": dup}
    if dup.get("has_warnings") and not force and dup.get("exact_name"):
        return {"success": False, "error": dup["warnings"][0], "duplicate": dup, "needs_confirm": True}

    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    final_slug = dup.get("slug") or _slugify(name)
    if kind == "hikaye":
        res = api.create_story_category(name, final_slug, parent=parent_id)
    else:
        res = api.create_category(name, cfg["taxonomy"], parent_id, final_slug)

    if not res.get("success") and not res.get("id"):
        return {"success": False, "error": res.get("error", "Oluşturulamadı")}

    term_id = int(res.get("id") or 0)
    return {
        "success": True,
        "created": True,
        "term": {"id": term_id, "name": name, "slug": final_slug, "parent": parent_id},
        "warnings": dup.get("warnings", []),
    }


def create_bulk_keywords(
    kind: str,
    keywords: str,
    parent_name: str = "",
    parent_slug: str = "",
    force: bool = False,
) -> dict[str, Any]:
    if kind == "hikaye":
        preview = preview_keywords(keywords, parent_name, parent_slug)
        if not preview.get("success"):
            return preview
        if not force:
            for item in preview["plan"]["items"]:
                dup = check_duplicate("hikaye", item["name"], item["slug"], 0)
                if dup.get("blocked"):
                    return {
                        "success": False,
                        "error": f"Çift kategori: {item['name']} — {dup['warnings'][0]}",
                        "duplicate": dup,
                        "needs_confirm": True,
                    }
        return create_from_keywords(wp_api(), keywords, parent_name, parent_slug, save_map=True)

    cfg = _cfg(kind)
    from app.moduller.storyforge_categories import build_plan_from_keywords

    preview = preview_keywords(keywords, parent_name, parent_slug)
    if not preview.get("success"):
        return preview

    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    plan = preview["plan"]
    parent = plan["parent"]
    terms = _list_terms(api, cfg["taxonomy"])
    slug_to_id = {t["slug"]: t["id"] for t in terms}
    created = 0
    errors: list[str] = []
    items_created: list[dict[str, Any]] = []

    pslug = parent["slug"]
    if pslug not in slug_to_id:
        dup = check_duplicate("ilan", parent["name"], pslug, 0)
        if dup.get("blocked") and not force:
            return {"success": False, "error": dup["warnings"][0], "duplicate": dup, "needs_confirm": True}
        res = api.create_category(parent["name"], cfg["taxonomy"], 0, pslug)
        if res.get("id"):
            tid = int(res["id"])
            slug_to_id[pslug] = tid
            created += 1
            items_created.append({
                "id": tid, "name": parent["name"], "slug": pslug, "parent": 0,
                "link": res.get("link", ""),
            })
        else:
            errors.append(f"Ana: {res.get('error')}")
    parent_id = slug_to_id.get(pslug, 0)

    for item in plan["items"]:
        dup = check_duplicate("ilan", item["name"], item["slug"], parent_id)
        if dup.get("blocked"):
            errors.append(f"{item['name']}: zaten var")
            continue
        if item["slug"] in slug_to_id:
            continue
        res = api.create_category(item["name"], cfg["taxonomy"], parent_id, item["slug"])
        if res.get("id"):
            tid = int(res["id"])
            slug_to_id[item["slug"]] = tid
            created += 1
            items_created.append({
                "id": tid, "name": item["name"], "slug": item["slug"], "parent": parent_id,
                "link": res.get("link", ""),
            })
        else:
            errors.append(f"{item['name']}: {res.get('error')}")

    return {
        "success": created > 0 or not errors,
        "created": created,
        "errors": errors,
        "items": items_created,
        "plan": plan,
        "mapped": len(plan["items"]),
    }


def sync_default_tree(kind: str = "hikaye") -> dict[str, Any]:
    if kind != "hikaye":
        return {"success": False, "error": "Varsayılan ağaç sadece hikaye kategorileri için"}
    api = wp_api()
    return sync_categories_to_wordpress(api)


def list_term_content(kind: str, term_id: int, page: int = 1, per_page: int = 20) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    raw = api._request(
        "GET",
        f"/wp-json/wp/v2/{cfg['post_type']}",
        params={
            "page": page,
            "per_page": per_page,
            cfg["taxonomy"]: term_id,
            "status": "publish,draft",
        },
    )
    if not raw.get("success"):
        return raw

    rows = raw.get("data") if isinstance(raw.get("data"), list) else []
    items = []
    for p in rows:
        if not isinstance(p, dict):
            continue
        items.append({
            "id": p.get("id"),
            "title": p.get("title", {}).get("rendered", p.get("title", "")) if isinstance(p.get("title"), dict) else p.get("title", ""),
            "link": p.get("link", ""),
            "status": p.get("status", ""),
        })
    return {"success": True, "items": items, "page": page, "per_page": per_page}


def list_uncategorized(kind: str, limit: int = 50) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    raw = api._request(
        "GET",
        f"/wp-json/wp/v2/{cfg['post_type']}",
        params={"per_page": min(limit, 100), "page": 1, "status": "publish,draft"},
    )
    if not raw.get("success"):
        return raw

    rows = raw.get("data") if isinstance(raw.get("data"), list) else []
    uncategorized = []
    for p in rows:
        if not isinstance(p, dict):
            continue
        cats = p.get(cfg["cat_field"]) or []
        if not cats:
            uncategorized.append({
                "id": p.get("id"),
                "title": p.get("title", {}).get("rendered", "") if isinstance(p.get("title"), dict) else str(p.get("title", "")),
                "link": p.get("link", ""),
                "status": p.get("status", ""),
            })
    return {"success": True, "items": uncategorized[:limit], "count": len(uncategorized)}


def assign_content(
    kind: str,
    post_ids: list[int],
    term_ids: list[int],
    mode: str = "add",
) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}
    if not post_ids or not term_ids:
        return {"success": False, "error": "İçerik ve kategori seçin"}

    updated = 0
    errors: list[str] = []
    field = cfg["cat_field"]

    for pid in post_ids:
        raw = api._request("GET", f"/wp-json/wp/v2/{cfg['post_type']}/{pid}")
        if not raw.get("success") and not raw.get("id"):
            errors.append(f"#{pid}: bulunamadı")
            continue
        current = raw.get(field) or []
        if mode == "replace":
            new_cats = list(term_ids)
        else:
            new_cats = list({*current, *term_ids})
        res = api._request(
            "POST",
            f"/wp-json/wp/v2/{cfg['post_type']}/{pid}",
            json_body={field: new_cats},
        )
        if res.get("success") or res.get("id"):
            updated += 1
        else:
            errors.append(f"#{pid}: {res.get('error', 'hata')}")

    return {"success": updated > 0, "updated": updated, "errors": errors}


def publish_profile(
    title: str,
    content: str = "",
    term_ids: list[int] | None = None,
    status: str = "publish",
) -> dict[str, Any]:
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}
    res = api.create_profile(title, content, status=status, categories=term_ids)
    if not res.get("success") and not res.get("id"):
        return {"success": False, "error": res.get("error", "İlan oluşturulamadı")}
    return {
        "success": True,
        "post_id": res.get("id"),
        "link": res.get("link", ""),
        "title": title,
    }


def publish_story(
    text: str,
    title: str = "",
    term_slug: str = "auto",
    auto_publish: bool = True,
) -> dict[str, Any]:
    return storyforge.quick_rewrite_publish(
        text=text,
        title=title,
        auto_publish=auto_publish,
        category_slug=term_slug or "auto",
    )


def update_term(
    kind: str,
    term_id: int,
    name: str = "",
    slug: str = "",
    description: str = "",
) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    fields: dict[str, Any] = {}
    if name:
        fields["name"] = name
    if slug:
        fields["slug"] = _slugify(slug)
    if description is not None:
        fields["description"] = description

    if kind == "hikaye":
        raw = api._request("POST", f"/wp-json/wp/v2/{cfg['taxonomy']}/{term_id}", json_body=fields)
    else:
        raw = api.update_category(term_id, cfg["taxonomy"], **fields)

    if not raw.get("success") and not raw.get("id"):
        return {"success": False, "error": raw.get("error", "Güncellenemedi")}
    return {"success": True, "term_id": term_id, "updated": fields}


def merge_terms(kind: str, source_id: int, target_id: int) -> dict[str, Any]:
    if source_id == target_id:
        return {"success": False, "error": "Kaynak ve hedef aynı olamaz"}
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    moved = 0
    page = 1
    while page <= 30:
        batch = list_term_content(kind, source_id, page=page, per_page=50)
        items = batch.get("items") or []
        if not items:
            break
        ids = [int(i["id"]) for i in items if i.get("id")]
        if ids:
            res = assign_content(kind, ids, [target_id], mode="add")
            moved += res.get("updated", 0)
        if len(items) < 50:
            break
        page += 1

    if kind == "hikaye":
        del_res = api._request("DELETE", f"/wp-json/wp/v2/{cfg['taxonomy']}/{source_id}", params={"force": True})
    else:
        del_res = api.delete_category(source_id, cfg["taxonomy"])

    return {
        "success": True,
        "moved_posts": moved,
        "source_deleted": bool(del_res.get("success")),
        "target_id": target_id,
    }


def verify_term_url(kind: str, term_id: int) -> dict[str, Any]:
    cfg = _cfg(kind)
    api = wp_api()
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    raw = api._request("GET", f"/wp-json/wp/v2/{cfg['taxonomy']}/{term_id}")
    link = raw.get("link") or ""
    if not link:
        terms = _list_terms(api, cfg["taxonomy"])
        term = next((t for t in terms if t["id"] == term_id), None)
        link = term.get("link", "") if term else ""

    if not link:
        base = api._base()
        term = next((t for t in _list_terms(api, cfg["taxonomy"]) if t["id"] == term_id), None)
        if term:
            link = urljoin(base + "/", f"{cfg['taxonomy']}/{term['slug']}/")

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


def talon_keywords(limit: int = 30) -> dict[str, Any]:
    favs = favori_listele() or []
    keywords = [f.get("kelime", "").strip() for f in favs if f.get("kelime")]
    seen: set[str] = set()
    out: list[str] = []
    for kw in keywords:
        key = kw.lower()
        if key not in seen:
            seen.add(key)
            out.append(kw)
    return {"success": True, "keywords": out[:limit], "total": len(out)}
