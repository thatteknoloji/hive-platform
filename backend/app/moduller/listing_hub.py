"""Listing Hub — ilan yayınlama motoru (CRUD, medya, SEO/GEO/AEO, toplu işlem, WP)."""

from __future__ import annotations

import csv
import io
import json
import logging
import mimetypes
import re
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urlparse
from xml.etree import ElementTree as ET

import requests

from app import config
from app.moduller.storyforge_categories import _slugify
from app.moduller.wordpress_api import wp_api

logger = logging.getLogger("hive.listing_hub")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = Path(__file__).resolve().parent.parent / "listing_hub_state.json"
MEDIA_DIR = ROOT / "uploads" / "listings"

LISTING_STATUSES = ("draft", "review", "active", "passive", "expired", "rejected")
PAYMENT_METHODS = ("cash", "bank_transfer", "eft", "credit_card", "door_payment", "other")
CURRENCIES = ("TRY", "USD", "EUR")
SCHEMA_TYPES = ("Product", "Service", "LocalBusiness", "Offer")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_DOC_EXT = {".pdf"}

STATUS_ALIASES = {
    "taslak": "draft", "incelemede": "review", "aktif": "active",
    "pasif": "passive", "süresi_doldu": "expired", "reddedildi": "rejected",
}

FIELD_ALIASES = {
    "baslik": "title", "kisa_aciklama": "short_description", "detayli_aciklama": "description",
    "ana_kategori": "main_category", "alt_kategori": "sub_category", "ilan_no": "listing_no",
    "sehir": "city", "ilce": "district", "mahalle": "neighborhood", "adres": "address",
    "telefon": "phone", "fiyat": "price", "para_birimi": "currency", "category": "main_category",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _default_video_url() -> str:
    return (config.get("DEFAULT_LISTING_VIDEO_URL") or "https://www.youtube.com/watch?v=dQw4w9WgXcQ").strip()


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("listings", {})
                data.setdefault("bulk_jobs", {})
                data.setdefault("import_staging", {})
                data.setdefault("categories", [])
                data.setdefault("services", [])
                data.setdefault("home_sections", [])
                data.setdefault("counters", {"ilan_no": 10000})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "listings": {}, "bulk_jobs": {}, "import_staging": {},
        "categories": [], "services": [], "home_sections": [],
        "counters": {"ilan_no": 10000},
    }


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_ilan_no(state: dict[str, Any]) -> str:
    c = state.setdefault("counters", {})
    n = int(c.get("ilan_no", 10000)) + 1
    c["ilan_no"] = n
    return str(n)


def _normalize_payload(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        key = FIELD_ALIASES.get(k, k)
        out[key] = v
    if "status" in out:
        st = str(out["status"]).lower()
        out["status"] = STATUS_ALIASES.get(st, st)
    if "payment_methods" in out and isinstance(out["payment_methods"], str):
        out["payment_methods"] = [x.strip() for x in out["payment_methods"].split(",") if x.strip()]
    if "categories" in out and isinstance(out["categories"], str):
        out["categories"] = [x.strip() for x in out["categories"].split(",") if x.strip()]
    if "services" in out and isinstance(out["services"], str):
        out["services"] = [x.strip() for x in out["services"].split(",") if x.strip()]
    return out


def _default_listing(ilan_no: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4())[:12],
        "ilan_no": ilan_no,
        "title": "",
        "short_description": "",
        "description": "",
        "status": "draft",
        "created_at": _now(),
        "updated_at": _now(),
        "published_at": "",
        "expires_at": "",
        "main_category": "",
        "sub_category": "",
        "categories": [],
        "services": [],
        "tags": [],
        "country": "Türkiye",
        "city": "",
        "district": "",
        "neighborhood": "",
        "address": "",
        "latitude": None,
        "longitude": None,
        "map_embed_url": "",
        "map_required": True,
        "phone": "",
        "whatsapp": "",
        "email": "",
        "website": "",
        "price": None,
        "currency": "TRY",
        "price_hidden": False,
        "negotiable": False,
        "payment_methods": [],
        "cover_image": "",
        "gallery_images": [],
        "private_images": [],
        "video_url": "",
        "default_video_url": _default_video_url(),
        "video_required": True,
        "video_embed_url": "",
        "pdf_files": [],
        "show_on_home": False,
        "home_section": "",
        "category_showcase": False,
        "city_showcase": False,
        "featured": False,
        "vip": False,
        "sponsored": False,
        "slider": False,
        "slug": "",
        "meta_title": "",
        "meta_description": "",
        "canonical": "",
        "schema_type": "LocalBusiness",
        "schema_jsonld": None,
        "target_keyword": "",
        "geo_keywords": [],
        "entity_keywords": [],
        "seo_gate_report_id": "",
        "seo_score": 0,
        "geo_score": 0,
        "aeo_score": 0,
        "entity_score": 0,
        "publish_allowed": False,
        "publish_blockers": [],
        "wp_post_id": None,
        "wp_url": "",
        "wp_status": "",
    }


def _merge_listing(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for k, v in updates.items():
        if v is not None:
            merged[k] = v
    merged["updated_at"] = _now()
    return merged


def _listing_media_dir(listing_id: str, private: bool = False) -> Path:
    if ".." in listing_id or "/" in listing_id or "\\" in listing_id:
        raise ValueError("Path traversal engellendi")
    lid = re.sub(r"[^a-zA-Z0-9_-]", "", listing_id)
    if not lid:
        raise ValueError("Geçersiz listing id")
    base = MEDIA_DIR.resolve()
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    sub = "private" if private else "public"
    target = (MEDIA_DIR / lid / sub).resolve()
    if not str(target).startswith(str(base)):
        raise ValueError("Path traversal engellendi")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _validate_extension(filename: str, allow_pdf: bool = False) -> str:
    ext = Path(filename).suffix.lower()
    allowed = ALLOWED_IMAGE_EXT | (ALLOWED_DOC_EXT if allow_pdf else set())
    if ext not in allowed:
        raise ValueError(f"İzin verilmeyen dosya uzantısı: {ext}")
    return ext


def normalize_youtube_url(url: str) -> tuple[str, str]:
    """Returns (watch_url, embed_url)."""
    url = (url or "").strip()
    if not url:
        return "", ""
    if "youtu.be/" in url:
        vid = url.split("youtu.be/")[-1].split("?")[0]
    elif "v=" in url:
        vid = url.split("v=")[-1].split("&")[0]
    elif "/embed/" in url:
        vid = url.split("/embed/")[-1].split("?")[0]
    else:
        vid = ""
    if not vid:
        return url, ""
    watch = f"https://www.youtube.com/watch?v={vid}"
    embed = f"https://www.youtube.com/embed/{vid}"
    return watch, embed


def build_map_embed(listing: dict[str, Any]) -> str:
    lat, lon = listing.get("latitude"), listing.get("longitude")
    if lat is not None and lon is not None:
        return f"https://www.openstreetmap.org/export/embed.html?bbox={float(lon)-0.02}%2C{float(lat)-0.02}%2C{float(lon)+0.02}%2C{float(lat)+0.02}&layer=mapnik&marker={lat}%2C{lon}"
    loc_parts = [listing.get("address"), listing.get("neighborhood"), listing.get("district"), listing.get("city")]
    if not any(loc_parts):
        return ""
    parts = loc_parts + [listing.get("country")]
    query = ", ".join(p for p in parts if p)
    if not query:
        return ""
    q = quote_plus(query)
    return f"https://maps.google.com/maps?q={q}&output=embed"


def apply_media_defaults(listing: dict[str, Any]) -> dict[str, Any]:
    listing = dict(listing)
    if not (listing.get("video_url") or "").strip():
        listing["video_url"] = listing.get("default_video_url") or _default_video_url()
    watch, embed = normalize_youtube_url(listing["video_url"])
    if watch:
        listing["video_url"] = watch
    listing["video_embed_url"] = embed
    if listing.get("map_required", True) and not listing.get("map_embed_url"):
        listing["map_embed_url"] = build_map_embed(listing)
    return listing


def _existing_descriptions(exclude_id: str = "") -> list[str]:
    texts: list[str] = []
    for lid, l in (_load_state().get("listings") or {}).items():
        if lid == exclude_id:
            continue
        for field in ("description", "short_description"):
            t = (l.get(field) or "").strip()
            if len(t) > 40:
                texts.append(t)
    return texts


def _is_duplicate_description(text: str, exclude_id: str = "", threshold: float = 0.82) -> bool:
    t = (text or "").lower().strip()
    if len(t) < 40:
        return False
    for other in _existing_descriptions(exclude_id):
        if SequenceMatcher(None, t, other.lower()).ratio() >= threshold:
            return True
    return False


def listing_to_html(listing: dict[str, Any]) -> str:
    listing = apply_media_defaults(listing)
    parts = [f"<h1>{listing.get('title', '')}</h1>"]
    if listing.get("short_description"):
        parts.append(f"<p>{listing['short_description']}</p>")
    if listing.get("description"):
        parts.append(f"<div>{listing['description']}</div>")
    if listing.get("video_embed_url"):
        parts.append(f'<iframe src="{listing["video_embed_url"]}" title="video"></iframe>')
    if listing.get("map_embed_url"):
        parts.append(f'<iframe src="{listing["map_embed_url"]}" title="map"></iframe>')
    for img in listing.get("gallery_images") or []:
        if isinstance(img, dict) and img.get("public_url"):
            parts.append(f'<img src="{img["public_url"]}" alt="{listing.get("title", "")}" />')
    if listing.get("schema_jsonld"):
        parts.append(f'<script type="application/ld+json">{json.dumps(listing["schema_jsonld"], ensure_ascii=False)}</script>')
    return "\n".join(parts)


def validate_publish_allowed(listing: dict[str, Any], *, after_gate: bool = False) -> dict[str, Any]:
    listing = apply_media_defaults(listing)
    blockers: list[str] = []
    if not (listing.get("title") or "").strip():
        blockers.append("title_missing")
    if not listing.get("categories"):
        blockers.append("category_missing")
    if not listing.get("cover_image"):
        blockers.append("cover_missing")
    if not listing.get("video_url") or not listing.get("video_embed_url"):
        blockers.append("video_missing")
    if not listing.get("map_embed_url"):
        blockers.append("map_missing")
    if not (listing.get("phone") or "").strip() and not (listing.get("whatsapp") or "").strip():
        blockers.append("contact_missing")
    if after_gate:
        if listing.get("seo_score", 0) < 70:
            blockers.append("seo_score_low")
        if listing.get("geo_score", 0) < 70:
            blockers.append("geo_score_low")
    listing["publish_blockers"] = blockers
    listing["publish_allowed"] = len(blockers) == 0
    return listing


def build_schema_jsonld(listing: dict[str, Any], domain: str = "") -> dict[str, Any]:
    listing = apply_media_defaults(listing)
    stype = listing.get("schema_type") or "LocalBusiness"
    graph: list[dict[str, Any]] = []
    main: dict[str, Any] = {
        "@type": stype,
        "name": listing.get("title", ""),
        "description": listing.get("short_description") or (listing.get("description") or "")[:300],
        "url": listing.get("canonical") or f"{domain.rstrip('/')}/profil/{listing.get('slug', '')}/",
    }
    if listing.get("phone"):
        main["telephone"] = listing.get("phone")
    if listing.get("latitude") is not None and listing.get("longitude") is not None:
        main["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": listing.get("latitude"),
            "longitude": listing.get("longitude"),
        }
    graph.append(main)
    if listing.get("video_url"):
        graph.append({
            "@type": "VideoObject",
            "name": listing.get("title", ""),
            "embedUrl": listing.get("video_embed_url"),
            "contentUrl": listing.get("video_url"),
        })
    if listing.get("price") and not listing.get("price_hidden"):
        graph.append({
            "@type": "Offer",
            "price": listing.get("price"),
            "priceCurrency": listing.get("currency", "TRY"),
            "availability": "https://schema.org/InStock",
        })
    return {"@context": "https://schema.org", "@graph": graph}


def generate_seo_for_listing(listing: dict[str, Any], domain: str = "") -> dict[str, Any]:
    title = (listing.get("title") or "").strip()
    city = listing.get("city") or listing.get("district") or ""
    target = listing.get("target_keyword") or f"{city} {title}".strip()
    slug = listing.get("slug") or _slugify(target or title or listing.get("ilan_no", "ilan"))
    meta_title = (listing.get("meta_title") or f"{title} — {city}")[:70]
    meta_desc = (listing.get("meta_description") or listing.get("short_description") or (listing.get("description") or "")[:155])[:160]
    canonical = listing.get("canonical") or f"{domain.rstrip('/')}/profil/{slug}/"
    geo_kw = list(dict.fromkeys([city, listing.get("district", ""), listing.get("neighborhood", "")] + (listing.get("geo_keywords") or [])))
    geo_kw = [g for g in geo_kw if g]
    updated = _merge_listing(listing, {
        "slug": slug,
        "meta_title": meta_title,
        "meta_description": meta_desc,
        "canonical": canonical,
        "target_keyword": target,
        "geo_keywords": geo_kw,
        "schema_jsonld": build_schema_jsonld({**listing, "slug": slug, "canonical": canonical}, domain),
    })
    return apply_media_defaults(updated)


def generate_description_for_listing(listing: dict[str, Any], use_llm: bool = True, max_retries: int = 3) -> dict[str, Any]:
    listing = apply_media_defaults(listing)
    title = listing.get("title", "")
    city = listing.get("city", "")
    district = listing.get("district", "")
    services = ", ".join(listing.get("services") or [])
    category = listing.get("main_category") or (listing.get("categories") or [""])[0]
    seed = f"{listing.get('id', '')}-{listing.get('ilan_no', '')}"
    prompt = (
        f"İlan: {title}\nŞehir: {city}\nİlçe: {district}\nKategori: {category}\nHizmetler: {services}\n"
        f"Seed: {seed}\n"
        "Eşsiz Türkçe ilan metni üret. Şablon tekrarı yapma.\n"
        "Format:\nKISA: (2 cümle)\nDETAY: (giriş, hizmet/özellik, konum/GEO, iletişim CTA, 2 mini SSS)\n"
    )
    short, detail = listing.get("short_description", ""), listing.get("description", "")
    for attempt in range(max_retries):
        if use_llm:
            try:
                from app.moduller import llm_router
                text, engine = llm_router.generate(prompt, max_tokens=2000, min_length=120)
                if text and engine:
                    m1 = re.search(r"KISA:\s*(.+?)(?=DETAY:|$)", text, re.S | re.I)
                    m2 = re.search(r"DETAY:\s*(.+)", text, re.S | re.I)
                    if m1:
                        short = m1.group(1).strip()
                    if m2:
                        detail = m2.group(1).strip()
            except Exception as exc:
                logger.warning("LLM description: %s", exc)
        if not short:
            short = f"{title} — {district or city} bölgesinde {category} hizmeti. Detaylar için iletişime geçin."
        if not detail:
            detail = f"{short}\n\n{services} kapsamında hizmet sunulmaktadır.\n\nKonum: {district}, {city}."
        if not _is_duplicate_description(detail, listing.get("id", "")):
            break
        prompt += f"\nÖnceki metin çok benzerdi, farklı yaz (deneme {attempt + 2})."
    tags = list(dict.fromkeys(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]{3,}", f"{title} {city} {services}".lower())[:15]))
    return _merge_listing(listing, {
        "short_description": short,
        "description": detail,
        "tags": tags,
    })


def run_quality_gate(listing: dict[str, Any]) -> dict[str, Any]:
    listing = apply_media_defaults(generate_seo_for_listing(listing))
    html = listing_to_html(listing)
    page = {
        "slug": listing.get("slug", "ilan"),
        "type": "listing",
        "title": listing.get("meta_title") or listing.get("title", ""),
        "description": listing.get("meta_description", ""),
        "content_html": html,
        "keyword": listing.get("target_keyword", ""),
    }
    try:
        from app.moduller.seo_quality_gate import (
            AEO_CATEGORIES, ENTITY_CATEGORIES, GEO_CATEGORIES, SEO_CATEGORIES,
            _analyze_page_full, _calculate_score, _dimension_score,
        )
        issues, _ = _analyze_page_full(
            page,
            target_keyword=listing.get("target_keyword", ""),
            location=listing.get("city", "") or listing.get("district", ""),
            domain=urlparse(listing.get("canonical", "")).netloc or "",
            main_site=(listing.get("main_site_url") or listing.get("main_site") or "").strip(),
            strict_mode=True,
        )
        seo_score = _dimension_score(issues, SEO_CATEGORIES)
        geo_score = _dimension_score(issues, GEO_CATEGORIES)
        aeo_score = _dimension_score(issues, AEO_CATEGORIES)
        entity_score = _dimension_score(issues, ENTITY_CATEGORIES)
    except Exception as exc:
        logger.warning("Quality gate fallback: %s", exc)
        wc = len(re.findall(r"\w+", html))
        seo_score = min(100, 50 + wc // 10)
        geo_score = 80 if listing.get("map_embed_url") else 30
        aeo_score = 70 if "?" in html else 55
        entity_score = 65

    listing = _merge_listing(listing, {
        "seo_score": seo_score,
        "geo_score": geo_score,
        "aeo_score": aeo_score,
        "entity_score": entity_score,
    })
    return validate_publish_allowed(listing, after_gate=True)


def _to_wp_meta(listing: dict[str, Any]) -> dict[str, Any]:
    return {
        "telefon": listing.get("phone", ""),
        "telegram": listing.get("whatsapp", ""),
        "lokasyon": ", ".join(filter(None, [listing.get("neighborhood"), listing.get("district"), listing.get("city")])),
        "fiyat": str(listing.get("price") or ""),
        "odeme_sekli": ",".join(listing.get("payment_methods") or []),
        "hizmetler": json.dumps(listing.get("services") or [], ensure_ascii=False),
        "vip": "1" if listing.get("vip") else "0",
        "ilan_no": listing.get("ilan_no", ""),
        "listing_hub_id": listing.get("id", ""),
        "video_url": listing.get("video_url", ""),
        "map_embed_url": listing.get("map_embed_url", ""),
        "schema_jsonld": json.dumps(listing.get("schema_jsonld") or {}, ensure_ascii=False),
    }


def _sync_gallery_to_wp(listing: dict[str, Any]) -> tuple[int | None, list[dict[str, Any]]]:
    wp = wp_api()
    if not wp.connected:
        return None, listing.get("gallery_images") or []
    featured_id = None
    gallery: list[dict[str, Any]] = []
    for item in sorted(listing.get("gallery_images") or [], key=lambda x: x.get("sort_order", 0)):
        path = item.get("path")
        if item.get("wp_media_id"):
            gallery.append(item)
            if item.get("id") == listing.get("cover_image"):
                featured_id = int(item["wp_media_id"])
            continue
        if not path or not Path(path).is_file():
            gallery.append(item)
            continue
        raw = Path(path).read_bytes()
        up = wp.upload_media(item.get("filename", "photo.jpg"), raw, item.get("mime", "image/jpeg"))
        if up.get("success") and up.get("id"):
            item = {**item, "wp_media_id": int(up["id"]), "public_url": up.get("source_url", "")}
            if item.get("id") == listing.get("cover_image"):
                featured_id = int(up["id"])
        gallery.append(item)
    return featured_id, gallery


# ── Public API ──

def health() -> dict[str, Any]:
    wp = wp_api()
    return {
        "success": True,
        "module": "Listing Hub",
        "listings_count": len((_load_state().get("listings") or {})),
        "media_dir": str(MEDIA_DIR),
        "wordpress_connected": wp.connected,
        "default_video_url": _default_video_url(),
        "statuses": list(LISTING_STATUSES),
        "payment_methods": list(PAYMENT_METHODS),
    }


def stats() -> dict[str, Any]:
    items = list((_load_state().get("listings") or {}).values())
    def c(st): return sum(1 for x in items if x.get("status") == st)
    validated = [validate_publish_allowed(apply_media_defaults(x)) for x in items]
    return {
        "success": True,
        "total": len(items),
        "active": c("active"),
        "draft": c("draft"),
        "publish_allowed": sum(1 for x in validated if x.get("publish_allowed")),
        "video_missing": sum(1 for x in items if not apply_media_defaults(x).get("video_embed_url")),
        "map_missing": sum(1 for x in items if not apply_media_defaults(x).get("map_embed_url")),
        "cover_missing": sum(1 for x in items if not x.get("cover_image")),
        "seo_fail": sum(1 for x in items if x.get("seo_score", 0) and x.get("seo_score", 0) < 70),
    }


def list_listings(
    status: str = "", search: str = "", city: str = "", category: str = "",
    service: str = "", featured: bool | None = None, vip: bool | None = None,
    limit: int = 100, offset: int = 0,
) -> dict[str, Any]:
    items = list((_load_state().get("listings") or {}).values())
    if status:
        items = [x for x in items if x.get("status") == STATUS_ALIASES.get(status, status)]
    if city:
        items = [x for x in items if city.lower() in (x.get("city") or "").lower()]
    if category:
        items = [x for x in items if category.lower() in [c.lower() for c in (x.get("categories") or [])]]
    if service:
        items = [x for x in items if service.lower() in [s.lower() for s in (x.get("services") or [])]]
    if featured is not None:
        items = [x for x in items if bool(x.get("featured")) == featured]
    if vip is not None:
        items = [x for x in items if bool(x.get("vip")) == vip]
    if search:
        q = search.lower()
        items = [x for x in items if q in (x.get("title") or "").lower() or q in str(x.get("ilan_no"))]
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"success": True, "listings": items[offset:offset + limit], "total": len(items), "stats": stats()}


def get_listing(listing_id: str) -> dict[str, Any]:
    listing = (_load_state().get("listings") or {}).get(listing_id)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    return {"success": True, "listing": apply_media_defaults(listing)}


def create_listing(payload: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    data = _normalize_payload(payload)
    if not (data.get("title") or "").strip():
        return {"success": False, "error": "title zorunlu"}
    if not (data.get("city") or "").strip():
        return {"success": False, "error": "city zorunlu"}
    cats = data.get("categories") or []
    if data.get("main_category") and data["main_category"] not in cats:
        cats = [data["main_category"], *cats]
    data["categories"] = cats
    if not cats:
        return {"success": False, "error": "En az 1 kategori zorunlu"}
    if not (data.get("phone") or "").strip() and not (data.get("whatsapp") or "").strip():
        return {"success": False, "error": "phone veya whatsapp zorunlu"}

    ilan_no = str(data.get("ilan_no") or data.get("listing_no") or _next_ilan_no(state))
    listing = _default_listing(ilan_no)
    listing = _merge_listing(listing, data)
    listing = apply_media_defaults(listing)
    if not (listing.get("description") or "").strip():
        listing = generate_description_for_listing(listing, use_llm=False)
    listing = validate_publish_allowed(listing)
    state.setdefault("listings", {})[listing["id"]] = listing
    _save_state(state)
    return {"success": True, "listing": listing, "created": True}


def update_listing(listing_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    listings = state.setdefault("listings", {})
    if listing_id not in listings:
        return {"success": False, "error": "İlan bulunamadı"}
    data = _normalize_payload(payload)
    listing = _merge_listing(listings[listing_id], data)
    listing = apply_media_defaults(listing)
    listing = validate_publish_allowed(listing, after_gate=bool(listing.get("seo_score")))
    listings[listing_id] = listing
    _save_state(state)
    return {"success": True, "listing": listing, "updated": True}


def delete_listing(listing_id: str, force: bool = False) -> dict[str, Any]:
    state = _load_state()
    listing = (state.get("listings") or {}).pop(listing_id, None)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    if force and listing.get("wp_post_id"):
        wp = wp_api()
        if wp.connected:
            wp.delete_profile(int(listing["wp_post_id"]), force=True)
    _save_state(state)
    base = MEDIA_DIR / listing_id
    if base.is_dir():
        for f in base.rglob("*"):
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass
    return {"success": True, "deleted": listing_id}


def upload_media(
    listing_id: str, filename: str, file_bytes: bytes,
    mime: str = "", private: bool = False, set_cover: bool = False,
) -> dict[str, Any]:
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        return {"success": False, "error": f"Maksimum dosya boyutu {MAX_UPLOAD_BYTES // (1024*1024)}MB"}
    state = _load_state()
    listing = (state.get("listings") or {}).get(listing_id)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    _validate_extension(filename, allow_pdf=False)
    mime = mime or mimetypes.guess_type(filename)[0] or "image/jpeg"
    media_dir = _listing_media_dir(listing_id, private=private)
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)[:120]
    path = media_dir / safe
    path.write_bytes(file_bytes)
    media_id = f"{'priv' if private else 'pub'}:{safe}"
    entry = {
        "id": media_id, "filename": safe, "mime": mime, "path": str(path),
        "sort_order": 0, "wp_media_id": None, "public_url": "" if private else f"/uploads/listings/{listing_id}/{'private' if private else 'public'}/{safe}",
    }
    if private:
        gallery = list(listing.get("private_images") or [])
        entry["sort_order"] = len(gallery)
        gallery.append(entry)
        listing = _merge_listing(listing, {"private_images": gallery})
    else:
        gallery = list(listing.get("gallery_images") or [])
        entry["sort_order"] = len(gallery)
        gallery.append(entry)
        listing = _merge_listing(listing, {"gallery_images": gallery})
        if set_cover or not listing.get("cover_image"):
            listing["cover_image"] = media_id
    listing = validate_publish_allowed(apply_media_defaults(listing))
    state["listings"][listing_id] = listing
    _save_state(state)
    return {"success": True, "media": entry, "listing": listing}


def reorder_media(listing_id: str, order: list[str], private: bool = False) -> dict[str, Any]:
    state = _load_state()
    listing = (state.get("listings") or {}).get(listing_id)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    key = "private_images" if private else "gallery_images"
    gallery = {g["id"]: g for g in (listing.get(key) or []) if g.get("id")}
    reordered = []
    for i, mid in enumerate(order):
        if mid in gallery:
            item = dict(gallery[mid])
            item["sort_order"] = i
            reordered.append(item)
    for g in listing.get(key) or []:
        if g.get("id") not in order:
            reordered.append(g)
    listing = _merge_listing(listing, {key: reordered})
    state["listings"][listing_id] = listing
    _save_state(state)
    return {"success": True, "listing": listing}


def set_cover(listing_id: str, media_id: str) -> dict[str, Any]:
    return update_listing(listing_id, {"cover_image": media_id})


def delete_media(listing_id: str, media_id: str) -> dict[str, Any]:
    state = _load_state()
    listing = (state.get("listings") or {}).get(listing_id)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    for key in ("gallery_images", "private_images"):
        kept = []
        for g in listing.get(key) or []:
            if g.get("id") == media_id:
                p = g.get("path")
                if p and Path(p).is_file():
                    try:
                        Path(p).unlink()
                    except OSError:
                        pass
                continue
            kept.append(g)
        listing[key] = kept
    if listing.get("cover_image") == media_id:
        listing["cover_image"] = (listing.get("gallery_images") or [{}])[0].get("id", "")
    listing = validate_publish_allowed(apply_media_defaults(listing))
    state["listings"][listing_id] = listing
    _save_state(state)
    return {"success": True, "listing": listing}


def publish_listing(listing_id: str) -> dict[str, Any]:
    state = _load_state()
    listing = (state.get("listings") or {}).get(listing_id)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    if not (listing.get("description") or "").strip():
        listing = generate_description_for_listing(listing)
    listing = run_quality_gate(listing)
    if not listing.get("publish_allowed"):
        state["listings"][listing_id] = listing
        _save_state(state)
        return {
            "success": False,
            "error": "Yayın engellendi",
            "publish_blockers": listing.get("publish_blockers", []),
            "listing": listing,
        }

    wp = wp_api()
    integrations: dict[str, Any] = {}
    if wp.connected:
        featured_id, gallery = _sync_gallery_to_wp(listing)
        listing["gallery_images"] = gallery
        cat_ids = wp.resolve_companion_category_ids(listing.get("categories") or [])
        content = listing_to_html(listing)
        fields = {
            "title": listing["title"],
            "content": content,
            "status": "publish",
            "meta": _to_wp_meta(listing),
            "categories": cat_ids or None,
            "excerpt": listing.get("short_description", ""),
            "slug": listing.get("slug", ""),
        }
        if featured_id:
            fields["featured_media"] = featured_id
        if listing.get("wp_post_id"):
            res = wp.update_profile(int(listing["wp_post_id"]), **{k: v for k, v in fields.items() if v is not None})
        else:
            res = wp.create_profile(**{k: v for k, v in fields.items() if v is not None})
        if res.get("success") or res.get("id"):
            listing["wp_post_id"] = int(res.get("id") or listing.get("wp_post_id"))
            listing["wp_url"] = res.get("link", "")
            listing["wp_status"] = "published"
        else:
            return {"success": False, "error": res.get("error", "WordPress yayını başarısız")}
    else:
        listing["wp_status"] = "provider_missing"
        listing["wp_url"] = listing.get("canonical", "")

    listing = _merge_listing(listing, {"status": "active", "published_at": _now(), "expires_at": listing.get("expires_at") or (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")})
    state["listings"][listing_id] = listing
    _save_state(state)

    url = listing.get("wp_url") or listing.get("canonical", "")
    if url and wp.connected:
        try:
            from app.moduller.indexnow import bildirim_gonder
            integrations["indexnow"] = bildirim_gonder(url)
        except Exception as exc:
            integrations["indexnow"] = {"error": str(exc)}
        try:
            from app.moduller.rank_index_watcher import rank_index_watcher
            kw = listing.get("target_keyword") or listing.get("title", "")
            domain = urlparse(url).netloc
            if kw and domain:
                integrations["rank_watcher"] = rank_index_watcher.track_keyword(kw, domain)
        except Exception as exc:
            integrations["rank_watcher"] = {"error": str(exc)}

    return {"success": True, "listing": listing, "integrations": integrations}


def unpublish_listing(listing_id: str) -> dict[str, Any]:
    state = _load_state()
    listing = (state.get("listings") or {}).get(listing_id)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    if listing.get("wp_post_id"):
        wp = wp_api()
        if wp.connected:
            wp.update_profile(int(listing["wp_post_id"]), status="draft")
    listing = _merge_listing(listing, {"status": "passive", "wp_status": "draft"})
    state["listings"][listing_id] = listing
    _save_state(state)
    return {"success": True, "listing": listing}


def expire_listing(listing_id: str) -> dict[str, Any]:
    res = update_listing(listing_id, {"status": "expired", "expires_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    if res.get("success"):
        listing = res["listing"]
        if listing.get("wp_post_id"):
            wp = wp_api()
            if wp.connected:
                wp.update_profile(int(listing["wp_post_id"]), status="draft")
    return res


def feature_listing(listing_id: str, featured: bool = True, vip: bool | None = None) -> dict[str, Any]:
    updates: dict[str, Any] = {"featured": featured, "show_on_home": featured, "category_showcase": featured}
    if vip is not None:
        updates["vip"] = vip
    return update_listing(listing_id, updates)


def _parse_rows(content: bytes | str, fmt: str) -> list[dict[str, Any]]:
    if isinstance(content, bytes):
        text = content.decode("utf-8-sig", errors="replace")
    else:
        text = content
    fmt = fmt.lower()
    if fmt == "csv":
        return [dict(r) for r in csv.DictReader(io.StringIO(text))]
    if fmt == "json":
        data = json.loads(text)
        return data if isinstance(data, list) else data.get("listings", [data])
    if fmt == "xml":
        root = ET.fromstring(text)
        rows = []
        for item in root.findall(".//listing") + root.findall(".//ilan") + root.findall(".//item"):
            rows.append({c.tag: (c.text or "").strip() for c in item})
        return rows
    if fmt in ("xlsx", "xls", "excel"):
        try:
            import openpyxl
        except ImportError:
            raise ValueError("Excel için openpyxl gerekli") from None
        wb = openpyxl.load_workbook(io.BytesIO(content if isinstance(content, bytes) else content.encode()), read_only=True)
        ws = wb.active
        it = ws.iter_rows(values_only=True)
        headers = [str(h or "").strip() for h in next(it, [])]
        return [{headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))} for row in it]
    raise ValueError(f"Desteklenmeyen format: {fmt}")


def _suggest_mapping(headers: list[str]) -> dict[str, str]:
    suggestions = {}
    for h in headers:
        hl = h.lower().strip()
        if hl in ("title", "baslik", "başlık"):
            suggestions[h] = "title"
        elif hl in ("city", "sehir", "şehir"):
            suggestions[h] = "city"
        elif hl in ("category", "kategori", "ana_kategori"):
            suggestions[h] = "main_category"
        elif hl in ("phone", "telefon"):
            suggestions[h] = "phone"
        elif hl in ("whatsapp"):
            suggestions[h] = "whatsapp"
        elif hl in ("district", "ilce", "ilçe"):
            suggestions[h] = "district"
        elif hl in ("description", "aciklama"):
            suggestions[h] = "description"
        elif hl in ("video_url", "video"):
            suggestions[h] = "video_url"
        elif hl in ("price", "fiyat"):
            suggestions[h] = "price"
        elif hl in ("services", "hizmetler"):
            suggestions[h] = "services"
    return suggestions


def import_preview(content: bytes | str, fmt: str, mapping: dict[str, str] | None = None) -> dict[str, Any]:
    rows = _parse_rows(content, fmt)
    if not rows:
        return {"success": False, "error": "Dosyada satır yok"}
    headers = list(rows[0].keys())
    mapping = mapping or _suggest_mapping(headers)
    mapped, errors = [], []
    for i, row in enumerate(rows):
        item = _normalize_payload({mapping.get(k, k): v for k, v in row.items() if v not in (None, "")})
        row_errs = []
        if not item.get("title"):
            row_errs.append("title_missing")
        if not item.get("city"):
            row_errs.append("city_missing")
        if not item.get("categories") and not item.get("main_category"):
            row_errs.append("category_missing")
        if not item.get("phone") and not item.get("whatsapp"):
            row_errs.append("contact_missing")
        if row_errs:
            errors.append({"row": i + 1, "errors": row_errs, "data": item})
        else:
            if item.get("main_category") and not item.get("categories"):
                item["categories"] = [item["main_category"]]
            mapped.append(item)
    job_id = str(uuid.uuid4())[:12]
    state = _load_state()
    state.setdefault("import_staging", {})[job_id] = {"rows": mapped, "errors": errors, "format": fmt}
    _save_state(state)
    return {
        "success": True, "job_id": job_id, "suggested_mapping": _suggest_mapping(headers),
        "preview": mapped[:50], "errors": errors[:50], "valid_count": len(mapped), "error_count": len(errors),
    }


def import_commit(job_id: str) -> dict[str, Any]:
    state = _load_state()
    staging = (state.get("import_staging") or {}).get(job_id)
    if not staging:
        return {"success": False, "error": "Preview job bulunamadı — önce import-preview çalıştırın"}
    created, errors = [], []
    for i, row in enumerate(staging.get("rows") or []):
        res = create_listing(row)
        if res.get("success"):
            created.append(res["listing"]["id"])
        else:
            errors.append({"row": i + 1, "error": res.get("error")})
    state = _load_state()
    state.setdefault("bulk_jobs", {})[job_id] = {
        "type": "import_commit", "created": len(created), "errors": errors, "finished_at": _now(),
    }
    state.get("import_staging", {}).pop(job_id, None)
    _save_state(state)
    return {"success": True, "job_id": job_id, "created": len(created), "listing_ids": created, "errors": errors}


def bulk_media_zip(zip_bytes: bytes) -> dict[str, Any]:
    listings = _load_state().get("listings") or {}
    by_no = {str(l.get("ilan_no")): lid for lid, l in listings.items()}
    by_slug = {_slugify(l.get("title", "")): lid for lid, l in listings.items()}
    matched, errors, details = 0, [], []
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        return {"success": False, "error": "Geçersiz ZIP"}
    patterns = [
        re.compile(r"^(\d+)[_\-](\d+|cover)\.(jpe?g|png|webp|gif)$", re.I),
        re.compile(r"^ILANNO-(\d+)-(\d+)\.(jpe?g|png|webp|gif)$", re.I),
        re.compile(r"^(\d+)\.(jpe?g|png|webp|gif)$", re.I),
    ]
    for name in zf.namelist():
        if name.endswith("/"):
            continue
        base = Path(name).name
        listing_id = None
        set_cover = False
        for pat in patterns:
            m = pat.match(base)
            if m:
                key = m.group(1)
                listing_id = by_no.get(key)
                set_cover = "cover" in base.lower() or m.group(2) == "1"
                break
        if not listing_id:
            listing_id = by_slug.get(_slugify(Path(base).stem.split("_")[0]))
        if not listing_id:
            errors.append(f"Eşleşmedi: {base}")
            continue
        try:
            data = zf.read(name)
            res = upload_media(listing_id, base, data, set_cover=set_cover)
            if res.get("success"):
                matched += 1
                details.append({"file": base, "listing_id": listing_id})
            else:
                errors.append(res.get("error", base))
        except Exception as exc:
            errors.append(f"{base}: {exc}")
    job_id = str(uuid.uuid4())[:12]
    state = _load_state()
    state.setdefault("bulk_jobs", {})[job_id] = {"type": "bulk_media", "matched": matched, "errors": errors[:100], "finished_at": _now()}
    _save_state(state)
    return {"success": True, "job_id": job_id, "matched": matched, "details": details, "errors": errors}


def list_categories() -> dict[str, Any]:
    state = _load_state()
    cats = state.get("categories") or []
    if not cats:
        try:
            from app.moduller.category_hub import get_tree
            tree = get_tree("ilan")
            if tree.get("success"):
                cats = [{"id": t.get("id"), "name": t.get("name"), "slug": t.get("slug")} for t in tree.get("terms", [])]
        except Exception as exc:
            logger.debug("category hub: %s", exc)
    return {"success": True, "categories": cats}


def sync_categories_from_hub() -> dict[str, Any]:
    try:
        from app.moduller.category_hub import get_tree
        tree = get_tree("ilan")
        if not tree.get("success"):
            return {"success": False, "error": tree.get("error", "Kategori alınamadı")}
        cats = [{"id": t.get("id"), "name": t.get("name"), "slug": t.get("slug")} for t in tree.get("terms", [])]
        state = _load_state()
        state["categories"] = cats
        _save_state(state)
        return {"success": True, "count": len(cats), "categories": cats}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def list_services() -> dict[str, Any]:
    return {"success": True, "services": _load_state().get("services") or []}


def create_service(name: str, slug: str = "") -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        return {"success": False, "error": "name gerekli"}
    state = _load_state()
    services = state.setdefault("services", [])
    entry = {"id": str(uuid.uuid4())[:8], "name": name, "slug": slug or _slugify(name)}
    services.append(entry)
    _save_state(state)
    return {"success": True, "service": entry}


def list_home_sections() -> dict[str, Any]:
    return {"success": True, "home_sections": _load_state().get("home_sections") or []}


def create_home_section(name: str, slug: str = "") -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        return {"success": False, "error": "name gerekli"}
    state = _load_state()
    sections = state.setdefault("home_sections", [])
    entry = {"id": str(uuid.uuid4())[:8], "name": name, "slug": slug or _slugify(name)}
    sections.append(entry)
    _save_state(state)
    return {"success": True, "home_section": entry}


def import_media_from_url(listing_id: str, url: str) -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        return {"success": False, "error": "url gerekli"}
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        name = urlparse(url).path.rsplit("/", 1)[-1] or "image.jpg"
        return upload_media(listing_id, name, r.content, r.headers.get("content-type", ""))
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def bulk_import(
    content: bytes | str, fmt: str, mapping: dict[str, str] | None = None,
    preview_only: bool = False, publish: bool = False,
) -> dict[str, Any]:
    if preview_only:
        preview = import_preview(content, fmt, mapping)
        if preview.get("success"):
            preview["total"] = preview.get("valid_count", 0)
        return preview
    preview = import_preview(content, fmt, mapping)
    if not preview.get("success"):
        return preview
    commit = import_commit(preview["job_id"])
    if commit.get("success") and publish:
        for lid in commit.get("listing_ids") or []:
            publish_listing(lid)
    return commit


def reorder_gallery(listing_id: str, order: list[str]) -> dict[str, Any]:
    return reorder_media(listing_id, order, private=False)


listing_hub = type("ListingHub", (), {
    "health": staticmethod(health),
    "stats": staticmethod(stats),
    "list_listings": staticmethod(list_listings),
    "get_listing": staticmethod(get_listing),
    "create_listing": staticmethod(create_listing),
    "update_listing": staticmethod(update_listing),
    "delete_listing": staticmethod(delete_listing),
    "publish_listing": staticmethod(publish_listing),
    "unpublish_listing": staticmethod(unpublish_listing),
    "expire_listing": staticmethod(expire_listing),
    "feature_listing": staticmethod(feature_listing),
    "upload_media": staticmethod(upload_media),
    "upload_private_media": staticmethod(lambda lid, fn, b, m="": upload_media(lid, fn, b, m, private=True)),
    "reorder_media": staticmethod(reorder_media),
    "set_cover": staticmethod(set_cover),
    "delete_media": staticmethod(delete_media),
    "generate_seo": staticmethod(lambda lid: _wrap_id(generate_seo_for_listing, lid)),
    "generate_description": staticmethod(lambda lid, use_llm=True: _wrap_id(lambda l: generate_description_for_listing(l, use_llm), lid)),
    "run_quality_gate": staticmethod(lambda lid: _wrap_id(run_quality_gate, lid)),
    "import_preview": staticmethod(import_preview),
    "import_commit": staticmethod(import_commit),
    "bulk_import": staticmethod(bulk_import),
    "bulk_media_zip": staticmethod(bulk_media_zip),
    "import_media_from_url": staticmethod(import_media_from_url),
    "reorder_gallery": staticmethod(reorder_gallery),
    "list_categories": staticmethod(list_categories),
    "sync_categories_from_hub": staticmethod(sync_categories_from_hub),
    "list_services": staticmethod(list_services),
    "create_service": staticmethod(create_service),
    "list_home_sections": staticmethod(list_home_sections),
    "create_home_section": staticmethod(create_home_section),
})()


def _wrap_id(fn, listing_id: str) -> dict[str, Any]:
    state = _load_state()
    listing = (state.get("listings") or {}).get(listing_id)
    if not listing:
        return {"success": False, "error": "İlan bulunamadı"}
    updated = fn(listing)
    state["listings"][listing_id] = updated
    _save_state(state)
    return {"success": True, "listing": updated}
