"""StoryForge — otomatik hikaye kategori / alt kategori ağacı + kelime tabanlı oluşturucu."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger("hive.storyforge.categories")

KEYWORD_MAP_FILE = Path(__file__).resolve().parent.parent / "storyforge_category_keywords.json"

# Ana kategori → alt kategoriler (slug → görünen ad)
CATEGORY_TREE: dict[str, dict[str, Any]] = {
    "gece-hikaye": {
        "name": "Gece Escort Hikayeleri",
        "subs": {
            "marina-gece": "Marina Gece Hikayeleri",
            "liman-gece": "Liman Gece Hikayeleri",
            "merkez-gece": "Merkez Gece Hikayeleri",
            "davutlar-gece": "Davutlar Gece Hikayeleri",
        },
    },
    "otel-hikaye": {
        "name": "Otel Escort Hikayeleri",
        "subs": {
            "butik-otel": "Butik Otel Hikayeleri",
            "sahil-otel": "Sahil Oteli Hikayeleri",
            "vip-otel": "VIP Otel Hikayeleri",
        },
    },
    "plaj-hikaye": {
        "name": "Plaj Escort Hikayeleri",
        "subs": {
            "kadinlar-denizi": "Kadınlar Denizi Hikayeleri",
            "yilanci-burnu": "Yılancı Burnu Hikayeleri",
            "gunbatimi-plaj": "Gün Batımı Plaj Hikayeleri",
        },
    },
    "vip-hikaye": {
        "name": "VIP Escort Hikayeleri",
        "subs": {
            "yat-vip": "Yat & Marina VIP",
            "ozel-davet": "Özel Davet VIP",
            "luks-gece": "Lüks Gece VIP",
        },
    },
    "oral-hikaye": {
        "name": "Oral Escort Hikayeleri",
        "subs": {
            "romantik-oral": "Romantik Oral Hikayeler",
            "sahil-oral": "Sahil Oral Hikayeler",
        },
    },
    "anal-hikaye": {
        "name": "Anal Escort Hikayeleri",
        "subs": {
            "otel-anal": "Otel Anal Hikayeleri",
            "gece-anal": "Gece Anal Hikayeleri",
        },
    },
    "cift-hikaye": {
        "name": "Çift Escort Hikayeleri",
        "subs": {
            "tatil-cift": "Tatil Çift Hikayeleri",
            "yabanci-cift": "Yabancı Çift Hikayeleri",
        },
    },
    "grup-hikaye": {
        "name": "Grup Escort Hikayeleri",
        "subs": {
            "arkadas-grup": "Arkadaş Grubu Hikayeleri",
            "parti-grup": "Parti Grubu Hikayeleri",
        },
    },
}

LOCATION_SUB_MAP: dict[str, tuple[str, str]] = {
    "marina": ("gece-hikaye", "marina-gece"),
    "liman": ("gece-hikaye", "liman-gece"),
    "kadınlar denizi": ("plaj-hikaye", "kadinlar-denizi"),
    "kadinlar denizi": ("plaj-hikaye", "kadinlar-denizi"),
    "yılancı": ("plaj-hikaye", "yilanci-burnu"),
    "yilanci": ("plaj-hikaye", "yilanci-burnu"),
    "güvercinada": ("gece-hikaye", "merkez-gece"),
    "guvercinada": ("gece-hikaye", "merkez-gece"),
    "davutlar": ("gece-hikaye", "davutlar-gece"),
    "otel": ("otel-hikaye", "butik-otel"),
    "plaj": ("plaj-hikaye", "kadinlar-denizi"),
    "vip": ("vip-hikaye", "luks-gece"),
}


_TR_MAP = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})


_SLUG_SYNONYMS = {
    "kusadas": "kusadasi",
    "kusadasi": "kusadasi",
    "escorts": "escort",
    "bayanlar": "bayan",
    "yorumlar": "yorumlari",
    "yorumlari": "yorumlari",
    "gece-hayati": "gece-hayati",
    "gece-hayat": "gece-hayati",
    "sss": "sss",
}


def _slugify(text: str) -> str:
    text = (text or "").translate(_TR_MAP).lower().strip()
    text = re.sub(r"[^a-z0-9\s\-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:60] or "kategori"


def normalize_seo_slug(text: str, *, max_words: int = 9, max_len: int = 80) -> str:
    """SEO slug — TR normalize, tekrar eden token temizliği, max kelime."""
    base = _slugify(text.replace("-", " "))
    if not base:
        return "sayfa"
    parts = [p for p in base.split("-") if p]
    cleaned: list[str] = []
    for part in parts:
        norm = _SLUG_SYNONYMS.get(part, part)
        if cleaned and cleaned[-1] == norm:
            continue
        if norm in cleaned:
            continue
        cleaned.append(norm)
    # sss tekrarı
    if cleaned.count("sss") > 1:
        cleaned = [p for i, p in enumerate(cleaned) if p != "sss" or i == cleaned.index("sss")]
    cleaned = cleaned[: max(3, min(max_words, 12))]
    slug = "-".join(cleaned).strip("-")
    if len(slug) > max_len:
        slug = "-".join(cleaned[:max_words])[:max_len].rstrip("-")
    return slug or "sayfa"


def load_keyword_map() -> dict[str, Any]:
    if KEYWORD_MAP_FILE.exists():
        try:
            data = json.loads(KEYWORD_MAP_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"entries": [], "parent_name": "Özel Hikaye Kategorileri", "parent_slug": "ozel-hikayeler"}


def save_keyword_map(data: dict[str, Any]) -> dict[str, Any]:
    merged = {**load_keyword_map(), **{k: v for k, v in data.items() if v is not None}}
    KEYWORD_MAP_FILE.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged


def parse_bulk_keywords(text: str) -> list[str]:
    lines = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # virgülle ayrılmış da kabul
        if "," in line and len(line.split(",")) > 1:
            lines.extend(p.strip() for p in line.split(",") if p.strip())
        else:
            lines.append(line)
    seen: set[str] = set()
    out: list[str] = []
    for kw in lines:
        key = kw.lower()
        if key not in seen:
            seen.add(key)
            out.append(kw)
    return out


def build_plan_from_keywords(
    keywords: list[str],
    parent_name: str = "",
    parent_slug: str = "",
) -> dict[str, Any]:
    """Her kelime/kelime grubu → alt kategori planı."""
    cfg = load_keyword_map()
    parent_name = (parent_name or cfg.get("parent_name") or "Özel Hikaye Kategorileri").strip()
    parent_slug = _slugify(parent_slug or cfg.get("parent_slug") or parent_name)

    items: list[dict[str, Any]] = []
    for kw in keywords:
        slug = _slugify(kw)
        if slug == parent_slug:
            slug = f"{slug}-alt"
        name = kw.strip().title() if kw == kw.lower() else kw.strip()
        if not name.lower().endswith("hikaye") and "hikaye" not in name.lower():
            name = f"{name} Hikayeleri"
        items.append({
            "keyword": kw,
            "name": name,
            "slug": slug,
            "parent_slug": parent_slug,
            "parent_name": parent_name,
            "level": "sub",
        })

    return {
        "parent": {"name": parent_name, "slug": parent_slug, "level": "main"},
        "items": items,
        "total": len(items) + 1,
    }


def preview_keywords(text: str, parent_name: str = "", parent_slug: str = "") -> dict[str, Any]:
    keywords = parse_bulk_keywords(text)
    if not keywords:
        return {"success": False, "error": "En az bir kelime/kelime grubu girin"}
    plan = build_plan_from_keywords(keywords, parent_name, parent_slug)
    return {"success": True, "keywords": keywords, "plan": plan}


def create_from_keywords(
    api: Any,
    text: str,
    parent_name: str = "",
    parent_slug: str = "",
    save_map: bool = True,
) -> dict[str, Any]:
    preview = preview_keywords(text, parent_name, parent_slug)
    if not preview.get("success"):
        return preview

    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    plan = preview["plan"]
    parent = plan["parent"]
    slug_to_id: dict[str, int] = {}
    existing = api.list_story_categories()
    if existing.get("success"):
        for row in existing.get("terms", []):
            slug_to_id[row["slug"]] = row["id"]

    created: list[dict[str, Any]] = []
    errors: list[str] = []

    pslug = parent["slug"]
    if pslug not in slug_to_id:
        res = api.create_story_category(parent["name"], pslug, parent=0)
        if res.get("success") and res.get("id"):
            slug_to_id[pslug] = int(res["id"])
            created.append({"type": "main", "name": parent["name"], "slug": pslug, "id": res["id"]})
        else:
            errors.append(f"Ana kategori: {res.get('error', 'hata')}")
    parent_id = slug_to_id.get(pslug, 0)

    entries: list[dict[str, Any]] = []
    for item in plan["items"]:
        slug = item["slug"]
        if slug in slug_to_id:
            entries.append({**item, "term_id": slug_to_id[slug], "existed": True})
            continue
        res = api.create_story_category(item["name"], slug, parent=parent_id)
        if res.get("success") and res.get("id"):
            slug_to_id[slug] = int(res["id"])
            created.append({"type": "sub", **item, "id": res["id"]})
            entries.append({**item, "term_id": res["id"], "existed": False})
        else:
            errors.append(f"{item['name']}: {res.get('error', 'hata')}")

    if save_map:
        old = load_keyword_map()
        merged_entries = {e["keyword"].lower(): e for e in old.get("entries", [])}
        for e in entries:
            merged_entries[e["keyword"].lower()] = {
                "keyword": e["keyword"],
                "slug": e["slug"],
                "name": e["name"],
                "parent_slug": e["parent_slug"],
                "term_id": e.get("term_id"),
            }
        save_keyword_map({
            "parent_name": parent["name"],
            "parent_slug": pslug,
            "entries": list(merged_entries.values()),
        })

    return {
        "success": bool(created) or bool(entries),
        "created": len(created),
        "created_items": created,
        "mapped": len(entries),
        "errors": errors,
        "plan": plan,
    }


def match_keyword_category(text: str) -> dict[str, Any] | None:
    """Kayıtlı kelime eşleşmesi → kategori."""
    cfg = load_keyword_map()
    lower = (text or "").lower()
    best: dict[str, Any] | None = None
    best_len = 0
    for entry in cfg.get("entries", []):
        kw = (entry.get("keyword") or "").lower()
        if kw and kw in lower and len(kw) > best_len:
            best_len = len(kw)
            best = entry
    if not best:
        return None
    parent_slug = best.get("parent_slug") or cfg.get("parent_slug", "")
    return {
        "main_slug": parent_slug,
        "main_name": cfg.get("parent_name", ""),
        "sub_slug": best.get("slug", ""),
        "sub_name": best.get("name", ""),
        "slugs": [s for s in [parent_slug, best.get("slug")] if s],
        "matched_keyword": best.get("keyword"),
    }


def list_category_tree() -> dict[str, Any]:
    cfg = load_keyword_map()
    return {
        "tree": CATEGORY_TREE,
        "main_slugs": list(CATEGORY_TREE.keys()),
        "keyword_map": cfg,
    }


def _slug_in_wp_terms(slug: str, terms: list[dict[str, Any]]) -> dict[str, Any] | None:
    norm = _norm_slug(slug)
    for t in terms:
        if _norm_slug(t.get("slug", "")) == norm:
            return t
    return None


def resolve_category_assignment(
    category_slug: str = "auto",
    title: str = "",
    content: str = "",
    lokasyon: str = "",
    wp_terms: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Kullanıcı seçimi veya otomatik — yayınlanacak ana/alt kategori."""
    slug = (category_slug or "").strip()
    if slug in ("", "auto"):
        picked = pick_categories(title=title, content=content, lokasyon=lokasyon)
        picked["mode"] = "auto"
        return picked

    cfg = load_keyword_map()
    parent_slug = cfg.get("parent_slug", "")
    for entry in cfg.get("entries", []):
        if _norm_slug(entry.get("slug", "")) == _norm_slug(slug):
            return {
                "main_slug": entry.get("parent_slug") or parent_slug,
                "main_name": cfg.get("parent_name", ""),
                "sub_slug": entry.get("slug", ""),
                "sub_name": entry.get("name", ""),
                "slugs": [s for s in [entry.get("parent_slug") or parent_slug, entry.get("slug")] if s],
                "matched_keyword": entry.get("keyword"),
                "mode": "manual",
            }
    if _norm_slug(slug) == _norm_slug(parent_slug):
        return {
            "main_slug": parent_slug,
            "main_name": cfg.get("parent_name", ""),
            "sub_slug": "",
            "sub_name": "",
            "slugs": [parent_slug] if parent_slug else [],
            "mode": "manual",
        }

    for main_slug, meta in CATEGORY_TREE.items():
        main_norm = _norm_slug(main_slug)
        if main_norm == _norm_slug(slug):
            picked = pick_categories(title=title, content=content, lokasyon=lokasyon, forced_main=main_slug)
            picked["mode"] = "manual_main"
            return picked
        subs: dict[str, str] = meta.get("subs") or {}
        for sub_slug, sub_name in subs.items():
            if _norm_slug(sub_slug) == _norm_slug(slug):
                return {
                    "main_slug": main_slug,
                    "main_name": meta.get("name", main_slug),
                    "sub_slug": sub_slug,
                    "sub_name": sub_name,
                    "slugs": [main_slug, sub_slug],
                    "mode": "manual_sub",
                }

    terms = wp_terms or []
    term = _slug_in_wp_terms(slug, terms)
    if term:
        if term.get("parent"):
            parent = next((t for t in terms if t.get("id") == term["parent"]), None)
            return {
                "main_slug": parent.get("slug", "") if parent else "",
                "main_name": parent.get("name", "") if parent else "",
                "sub_slug": term.get("slug", ""),
                "sub_name": term.get("name", ""),
                "slugs": [s for s in [(parent or {}).get("slug"), term.get("slug")] if s],
                "mode": "manual_sub",
            }
        return {
            "main_slug": term.get("slug", ""),
            "main_name": term.get("name", ""),
            "sub_slug": "",
            "sub_name": "",
            "slugs": [term.get("slug", "")] if term.get("slug") else [],
            "mode": "manual_main",
        }

    picked = pick_categories(title=title, content=content, lokasyon=lokasyon, forced_main=slug)
    picked["mode"] = "manual"
    return picked


def pick_categories(
    title: str = "",
    content: str = "",
    lokasyon: str = "",
    forced_main: str = "",
) -> dict[str, Any]:
    """İçerik/lokasyona göre ana + alt kategori seç (çeşitlilik için hash)."""
    text = f"{title} {content} {lokasyon}".lower()

    main_slug = forced_main.strip() if forced_main else ""
    sub_slug = ""

    kw_match = match_keyword_category(text)
    if kw_match:
        return kw_match

    if not main_slug:
        for key, (m, s) in LOCATION_SUB_MAP.items():
            if key in text or key in lokasyon.lower():
                main_slug, sub_slug = m, s
                break

    if not main_slug:
        mains = list(CATEGORY_TREE.keys())
        main_slug = mains[hash(text) % len(mains)]

    tree = CATEGORY_TREE.get(main_slug, {})
    subs: dict[str, str] = tree.get("subs") or {}
    if not sub_slug and subs:
        sub_slug = list(subs.keys())[hash(text + main_slug) % len(subs)]

    return {
        "main_slug": main_slug,
        "main_name": tree.get("name", main_slug),
        "sub_slug": sub_slug,
        "sub_name": (subs.get(sub_slug) or "") if sub_slug else "",
        "slugs": [s for s in [main_slug, sub_slug] if s],
    }


def _norm_slug(slug: str) -> str:
    return re.sub(r"[^a-z0-9\-]", "", slug.lower().strip())


def sync_categories_to_wordpress(api: Any) -> dict[str, Any]:
    """WP'de eksik ana/alt kategorileri oluştur."""
    if not api.connected:
        return {"success": False, "error": "WordPress bağlantısı yok"}

    created = 0
    slug_to_id: dict[str, int] = {}
    existing = api.list_story_categories()
    if existing.get("success"):
        for row in existing.get("terms", []):
            slug_to_id[row["slug"]] = row["id"]

    for main_slug, meta in CATEGORY_TREE.items():
        main_slug = _norm_slug(main_slug)
        if main_slug not in slug_to_id:
            res = api.create_story_category(meta["name"], main_slug, parent=0)
            if res.get("success") and res.get("id"):
                slug_to_id[main_slug] = int(res["id"])
                created += 1
            else:
                logger.warning("Ana kategori oluşturulamadı %s: %s", main_slug, res.get("error"))
        parent_id = slug_to_id.get(main_slug, 0)
        for sub_slug, sub_name in (meta.get("subs") or {}).items():
            sub_slug = _norm_slug(sub_slug)
            if sub_slug in slug_to_id:
                continue
            res = api.create_story_category(sub_name, sub_slug, parent=parent_id)
            if res.get("success") and res.get("id"):
                slug_to_id[sub_slug] = int(res["id"])
                created += 1

    return {"success": True, "created": created, "total_mapped": len(slug_to_id), "slug_to_id": slug_to_id}


def _name_for_slug(slug: str) -> tuple[str, str]:
    """(görünen ad, üst slug veya boş)"""
    cfg = load_keyword_map()
    parent_slug = cfg.get("parent_slug", "")
    if _norm_slug(slug) == _norm_slug(parent_slug):
        return cfg.get("parent_name", slug), ""

    for entry in cfg.get("entries", []):
        if _norm_slug(entry.get("slug", "")) == _norm_slug(slug):
            return entry.get("name", slug), entry.get("parent_slug") or parent_slug

    for main_slug, meta in CATEGORY_TREE.items():
        if _norm_slug(main_slug) == _norm_slug(slug):
            return meta.get("name", slug), ""
        for sub_slug, sub_name in (meta.get("subs") or {}).items():
            if _norm_slug(sub_slug) == _norm_slug(slug):
                return sub_name, main_slug

    return slug.replace("-", " ").title(), ""


def ensure_category_slugs(api: Any, picked: dict[str, Any]) -> list[int]:
    """Seçilen kategoriler WP'de yoksa otomatik oluştur, term ID döndür."""
    if not picked:
        return []
    sync_categories_to_wordpress(api)

    listed = api.list_story_categories()
    slug_to_id: dict[str, int] = {}
    if listed.get("success"):
        for row in listed.get("terms", []):
            slug_to_id[_norm_slug(row["slug"])] = int(row["id"])

    slugs = picked.get("slugs") or []
    for slug in slugs:
        norm = _norm_slug(slug)
        if norm in slug_to_id:
            continue
        name, parent_hint = _name_for_slug(slug)
        parent_id = 0
        if parent_hint:
            ph_norm = _norm_slug(parent_hint)
            parent_id = slug_to_id.get(ph_norm, 0)
            if not parent_id:
                pname, _ = _name_for_slug(parent_hint)
                pres = api.create_story_category(pname, ph_norm, parent=0)
                if pres.get("success") and pres.get("id"):
                    parent_id = int(pres["id"])
                    slug_to_id[ph_norm] = parent_id

        res = api.create_story_category(name, norm, parent=parent_id)
        if res.get("success") and res.get("id"):
            slug_to_id[norm] = int(res["id"])
        else:
            logger.warning("Kategori oluşturulamadı %s: %s", norm, res.get("error"))

    return api.resolve_story_category_ids(slugs)


def resolve_term_ids(api: Any, picked: dict[str, Any] | list[str]) -> list[int]:
    """Seçim veya slug listesini WP term ID'lerine çevir; eksikleri oluştur."""
    if isinstance(picked, dict):
        return ensure_category_slugs(api, picked)
    if not picked:
        return []
    return ensure_category_slugs(api, {"slugs": picked})
