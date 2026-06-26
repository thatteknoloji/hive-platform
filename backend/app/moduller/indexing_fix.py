"""
Google indeksleme otomatik düzeltme — balkutusu.com
Cloudflare SSL, WordPress permalink/noindex, robots, IndexNow, GSC sitemap.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

import requests

from app import config
from app.moduller.replicator import SiteReplicator
from app.moduller.robots import duzenle

from app.moduller.storyforge_categories import normalize_seo_slug

logger = logging.getLogger("hive.indexing_fix")

DEFAULT_SITE = ""
DEFAULT_DOMAIN = ""
INDEXNOW_KEY = config.get("INDEXNOW_KEY", "hive-indexnow")
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

URL_TYPE_PATTERNS: list[tuple[str, str]] = [
    ("profil", r"/profil(?:ler)?/([^/]+)/?"),
    ("hikaye", r"/hikaye(?:ler)?/([^/]+)/?"),
    ("kategori", r"/(?:kategori|profil-kategori)/([^/]+)/?"),
    ("rehber", r"/rehber/([^/]+)/?"),
    ("sss", r"/sss/([^/]+)/?"),
    ("gece_mahalle", r"/gece-mahalle/([^/]+)/?"),
    ("gece_hayati", r"/gece-hayati/([^/]+)/?"),
    ("lokasyon", r"/lokasyon/([^/]+)/?"),
    ("story_query", r"[?&]story=([^&]+)"),
    ("search", r"[?&]s=|[?&]post_type="),
    ("tag", r"/tag/([^/]+)/?"),
    ("page", r"^/[^/?]+$"),
]

STORY_QUERY_SLUGS = ("luna", "bella", "aylin", "gece-modu")
PROFILE_QUERY_SLUGS = ("luna", "bella", "aylin")


def _site_url() -> str:
    raw = (config.get("GSC_SITE_URL") or config.get("WP_URL") or DEFAULT_SITE).strip()
    if not raw:
        return ""
    if not raw.startswith("http"):
        raw = f"https://{raw}"
    return raw.rstrip("/")


def _domain_from_url(url: str) -> str:
    host = urlparse(url).netloc or url
    return host.replace("www.", "").lower()


def audit_site(site_url: str | None = None) -> dict[str, Any]:
    """Canlı site indeksleme denetimi."""
    site = (site_url or _site_url()).rstrip("/")
    checks: list[dict[str, Any]] = []
    ok_count = 0

    def add(name: str, ok: bool, detail: str, fix: str = ""):
        nonlocal ok_count
        if ok:
            ok_count += 1
        checks.append({"kontrol": name, "durum": "ok" if ok else "sorun", "detay": detail, "oneri": fix})

    try:
        r = requests.get(site, timeout=25, headers={"User-Agent": "HIVE-IndexingBot/1.0"})
        html = r.text[:80000]
        add(
            "Ana sayfa erişimi",
            r.status_code == 200,
            f"HTTP {r.status_code}",
            "Site yanıt vermiyorsa VPS/Docker kontrol edin",
        )
        noindex = bool(re.search(r'noindex', html, re.I))
        add(
            "Noindex meta",
            not noindex,
            "noindex bulundu" if noindex else "noindex yok — indexlenebilir",
            "Rank Math / tema ayarlarından noindex kaldırın",
        )
        robots_meta = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', html, re.I)
        if robots_meta:
            add("Robots meta", True, robots_meta.group(1), "")
    except requests.RequestException as e:
        add("Ana sayfa erişimi", False, str(e), "DNS/SSL/WordPress kontrol edin")

    robots_url = urljoin(site + "/", "robots.txt")
    try:
        rr = requests.get(robots_url, timeout=15)
        body = rr.text
        blocks_all = False
        ua_star = False
        for block in re.split(r"\n(?=User-agent:)", body, flags=re.I):
            if re.match(r"User-agent:\s*\*", block, re.I):
                ua_star = True
                if re.search(r"^Disallow:\s*/\s*$", block, re.M | re.I):
                    blocks_all = True
                break
        has_sitemap = "sitemap" in body.lower()
        add(
            "robots.txt",
            rr.status_code == 200 and ua_star and not blocks_all,
            "Googlebot (*) için Disallow: / var" if blocks_all else f"Allow: / — Sitemap: {'var' if has_sitemap else 'yok'}",
            "robots.txt içinde User-agent: * altında Disallow: / kaldırın",
        )
    except requests.RequestException as e:
        add("robots.txt", False, str(e), "")

    sitemap_url = urljoin(site + "/", "wp-sitemap.xml")
    try:
        rs = requests.get(sitemap_url, timeout=20)
        add(
            "XML Sitemap",
            rs.status_code == 200 and "<sitemap" in rs.text.lower(),
            f"HTTP {rs.status_code} — {sitemap_url}",
            "WordPress sitemap veya Rank Math sitemap etkinleştirin",
        )
    except requests.RequestException as e:
        add("XML Sitemap", False, str(e), "")

    domain = _domain_from_url(site)
    apex_url = f"https://{domain}"
    try:
        ra = requests.get(apex_url, timeout=15, allow_redirects=False)
        loc = ra.headers.get("Location", "")
        www_ok = ra.status_code in (301, 302, 307, 308) and "www." in loc.lower()
        add(
            "Apex → www yönlendirme",
            www_ok,
            f"{apex_url} → {ra.status_code} {loc}".strip(),
            "Canonical URL olarak https://www.balkutusu.com kullanın",
        )
    except requests.RequestException as e:
        add("Apex → www yönlendirme", False, str(e), "")

    key_url = urljoin(site + "/", f"{INDEXNOW_KEY}.txt")
    try:
        rk = requests.get(key_url, timeout=10)
        add(
            "IndexNow anahtarı",
            rk.status_code == 200 and INDEXNOW_KEY in rk.text,
            key_url,
            "IndexNow key dosyası oluşturun",
        )
    except requests.RequestException as e:
        add("IndexNow anahtarı", False, str(e), "")

    total = len(checks)
    return {
        "site": site,
        "skor": f"{ok_count}/{total}",
        "hazir": ok_count >= total - 1,
        "kontroller": checks,
    }


def _wp_ssh(rep: SiteReplicator, cmd: str) -> dict[str, Any]:
    code, out, err = rep.ssh_run(cmd, timeout=180)
    return {"ok": code == 0, "code": code, "stdout": out, "stderr": err}


def fix_robots_txt(
    rep: SiteReplicator | None = None,
    site: str | None = None,
    politika: str = "seo",
) -> dict[str, Any]:
    """robots.txt üret ve WordPress docroot'a SSH ile yaz."""
    rep = rep or SiteReplicator()
    site = (site or _site_url()).rstrip("/")
    host = urlparse(site).netloc or _domain_from_url(site)

    generated = duzenle(host, politika)
    if generated.get("status") == "hata":
        return {"ok": False, "mesaj": generated.get("hata", "robots.txt üretilemedi")}

    content = enhanced_robots_content(site) if politika == "seo" else generated["icerik"]
    if politika != "seo":
        content = content.replace(
            f"Sitemap: https://{host}/sitemap.xml",
            f"Sitemap: {site}/wp-sitemap.xml",
        )

    if not rep.vps_pass:
        return {
            "ok": False,
            "atlandi": True,
            "mesaj": "VPS_SSH_PASS eksik — robots.txt yalnızca önizleme",
            "icerik": content,
        }

    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    cmd = (
        "docker exec hive_wordpress bash -c "
        f"'echo {b64} | base64 -d > /var/www/html/robots.txt && chmod 644 /var/www/html/robots.txt'"
    )
    r = _wp_ssh(rep, cmd)
    return {
        "ok": r["ok"],
        "site": site,
        "politika": politika,
        "robots_url": f"{site}/robots.txt",
        "icerik": content,
        **r,
    }


def fix_wordpress(rep: SiteReplicator | None = None, site: str | None = None) -> dict[str, Any]:
    rep = rep or SiteReplicator()
    site = (site or _site_url()).rstrip("/")
    steps = []

    for label, cmd in [
        ("siteurl/home https+www", f"docker exec hive_wordpress wp option update siteurl '{site}' --allow-root && docker exec hive_wordpress wp option update home '{site}' --allow-root"),
        ("blog_public", "docker exec hive_wordpress wp option update blog_public 1 --allow-root"),
        ("permalink", "docker exec hive_wordpress wp rewrite structure '/%postname%/' --allow-root && docker exec hive_wordpress wp rewrite flush --allow-root"),
        ("rank_math_noindex", "docker exec hive_wordpress wp option patch update rank-math-options-titles homepage_robots '[\"index\",\"follow\"]' --allow-root 2>/dev/null || true"),
        ("indexnow_key", f"docker exec hive_wordpress bash -c 'echo -n {INDEXNOW_KEY} > /var/www/html/{INDEXNOW_KEY}.txt && chmod 644 /var/www/html/{INDEXNOW_KEY}.txt'"),
    ]:
        r = _wp_ssh(rep, cmd)
        steps.append({"adim": label, **r})

    return {"site": site, "adimlar": steps, "basarili": all(s["ok"] for s in steps)}


def fix_cloudflare_ssl(mode: str = "flexible") -> dict[str, Any]:
    token = (config.get("CLOUDFLARE_API_TOKEN") or "").strip()
    zone_id = (config.get("CLOUDFLARE_ZONE_ID") or "").strip()
    domain = _domain_from_url(_site_url())

    if not token:
        return {"ok": False, "atlandi": True, "mesaj": "CLOUDFLARE_API_TOKEN eksik — API Settings'ten ekleyin"}

    rep = SiteReplicator()
    if not zone_id:
        zone_id = rep._cf_find_zone_id(domain) or ""

    if not zone_id:
        return {"ok": False, "mesaj": f"Cloudflare zone bulunamadı: {domain}"}

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        cur = requests.get(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/ssl",
            headers=headers,
            timeout=30,
        ).json()
        current = (cur.get("result") or {}).get("value", "unknown")

        if current == mode:
            return {"ok": True, "zone_id": zone_id, "ssl_mode": current, "mesaj": f"SSL zaten {mode}"}

        patch = requests.patch(
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/settings/ssl",
            headers=headers,
            json={"value": mode},
            timeout=30,
        ).json()
        if patch.get("success"):
            return {"ok": True, "zone_id": zone_id, "onceki": current, "ssl_mode": mode, "mesaj": f"SSL {current} → {mode}"}
        return {"ok": False, "mesaj": str(patch.get("errors", patch))}
    except requests.RequestException as e:
        return {"ok": False, "mesaj": str(e)}


def submit_indexnow(urls: list[str] | None = None) -> dict[str, Any]:
    site = _site_url()
    host = urlparse(site).netloc
    key = INDEXNOW_KEY
    key_location = f"{site}/{key}.txt"
    url_list = urls or [site, f"{site}/wp-sitemap.xml"]

    payload = {
        "host": host,
        "key": key,
        "keyLocation": key_location,
        "urlList": url_list[:10000],
    }
    endpoints = [
        "https://api.indexnow.org/IndexNow",
        "https://www.bing.com/indexnow",
    ]
    results = []
    for ep in endpoints:
        try:
            r = requests.post(ep, json=payload, timeout=30)
            results.append({"endpoint": ep, "status": r.status_code, "body": r.text[:300]})
            if r.status_code in (200, 202):
                return {"ok": True, "endpoint": ep, "status": r.status_code, "urls": len(url_list), "detay": results}
        except requests.RequestException as e:
            results.append({"endpoint": ep, "hata": str(e)})

    return {"ok": False, "mesaj": "IndexNow gönderilemedi (rate limit veya ağ hatası)", "detay": results}


def submit_gsc_sitemap() -> dict[str, Any]:
    client_id = (config.get("GSC_CLIENT_ID") or "").strip()
    client_secret = (config.get("GSC_CLIENT_SECRET") or "").strip()
    site = (config.get("GSC_SITE_URL") or _site_url()).strip()

    if not client_id or not client_secret:
        return {"ok": False, "atlandi": True, "mesaj": "GSC_CLIENT_ID/SECRET eksik — Search Console API ayarlayın"}

    return {
        "ok": False,
        "atlandi": True,
        "mesaj": "GSC sitemap API OAuth scope gerekli — Search Console'dan manuel sitemap gönderin",
        "sitemap": f"{site.rstrip('/')}/wp-sitemap.xml",
        "console": "https://search.google.com/search-console",
    }


def run_full_fix(site_url: str | None = None) -> dict[str, Any]:
    """Tüm indeksleme düzeltmelerini sırayla uygula."""
    site = site_url or _site_url()
    rep = SiteReplicator()

    if not rep.vps_pass:
        wp_result = {"atlandi": True, "mesaj": "VPS_SSH_PASS eksik — WordPress SSH adımları atlandı"}
        robots_result = {"atlandi": True, "mesaj": "VPS_SSH_PASS eksik — robots.txt atlandı"}
    else:
        wp_result = fix_wordpress(rep, site)
        robots_result = fix_robots_txt(rep, site, politika="seo")

    cf_result = fix_cloudflare_ssl("flexible")
    indexnow_result = submit_indexnow([
        site.rstrip("/"),
        f"{site.rstrip('/')}/wp-sitemap.xml",
        f"{site.rstrip('/')}/robots.txt",
    ])
    gsc_result = submit_gsc_sitemap()
    audit = audit_site(site)

    return {
        "site": site,
        "wordpress": wp_result,
        "robots_txt": robots_result,
        "cloudflare_ssl": cf_result,
        "indexnow": indexnow_result,
        "gsc": gsc_result,
        "denetim": audit,
        "hazir": audit.get("hazir", False),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _emit_brain(event_type: str, result: dict | None = None, reason: str = "") -> None:
    try:
        from app.moduller.hive_brain_engine import record_event
        record_event(
            event_type,
            "indexing_fix",
            domain=DEFAULT_DOMAIN,
            result=result or {},
            reason=reason,
            metadata={"engine": "balkutusu_index_recovery"},
        )
    except Exception as exc:
        logger.debug("brain skip: %s", exc)


def classify_url(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    path = parsed.path or "/"
    qs = parsed.query or ""
    full = f"{path}?{qs}" if qs else path
    content_type = "other"
    slug = ""
    for ctype, pattern in URL_TYPE_PATTERNS:
        m = re.search(pattern, full, re.I)
        if m:
            content_type = ctype
            slug = (m.group(1) if m.lastindex else "") or ""
            break
    if parsed.query and "story=" in parsed.query:
        content_type = "story_query"
        slug = parse_qs(parsed.query).get("story", [""])[0]
    issues: list[str] = []
    if "kusadas-kusadas" in path or re.search(r"(\w+)-\1(-\1)+", path):
        issues.append("duplicate_slug_tokens")
    if parsed.query and "story=" in parsed.query:
        issues.append("query_param_story")
    if "/profiller/" in path:
        issues.append("legacy_profil_path")
    if "/hikayeler/" in path:
        issues.append("legacy_hikaye_path")
    if path.endswith("-sss/") or path.rstrip("/").endswith("-sss"):
        if content_type == "other":
            content_type = "sss"
            slug = path.strip("/").split("/")[-1].replace("-sss", "")
    if path.endswith("-sss/") or path.count("-sss") > 1:
        issues.append("sss_slug_noise")
    if len([p for p in path.strip("/").split("/") if p]) > 6:
        issues.append("slug_too_long")
    return {
        "url": url,
        "path": path,
        "content_type": content_type,
        "slug": slug,
        "issues": issues,
    }


def propose_clean_url(url: str, *, content_type: str = "", slug: str = "") -> str:
    site = _site_url().rstrip("/")
    info = classify_url(url)
    ctype = content_type or info["content_type"]
    raw_slug = slug or info["slug"] or ""
    clean_slug = normalize_seo_slug(raw_slug.replace("_", "-")) if raw_slug else ""

    if ctype == "story_query" or info["issues"] and "query_param_story" in info["issues"]:
        s = normalize_seo_slug(raw_slug or "story")
        if s in PROFILE_QUERY_SLUGS:
            return f"{site}/profil/{s}/"
        return f"{site}/hikaye/{s}/"

    if ctype == "profil" or "/profiller/" in info["path"] or "/profil/" in info["path"]:
        return f"{site}/profil/{clean_slug}/" if clean_slug else f"{site}/profil/"
    if ctype == "hikaye" or "/hikayeler/" in info["path"]:
        return f"{site}/hikaye/{clean_slug}/" if clean_slug else f"{site}/hikaye/"
    if ctype == "sss" or "-sss" in info["path"]:
        path_slug = info["path"].strip("/").split("/")[-1] if info["path"] else ""
        base = clean_slug or path_slug
        base = normalize_seo_slug(base.replace("-sss", "").rstrip("-"))
        return f"{site}/sss/{base}/"
    if ctype == "gece_mahalle":
        return f"{site}/gece-mahalle/{clean_slug}/"
    if ctype == "gece_hayati":
        return f"{site}/gece-hayati/{clean_slug}/"
    if ctype == "kategori":
        return f"{site}/kategori/{clean_slug}/"
    if ctype == "rehber":
        return f"{site}/rehber/{clean_slug}/"
    if ctype == "search" or ctype == "tag":
        return url  # noindex, no redirect target change
    if clean_slug and info["issues"]:
        return f"{site}/{clean_slug}/"
    return url.split("?")[0].rstrip("/") + "/" if "?" not in url else url


def build_redirect_entry(old_url: str, new_url: str, *, reason: str, content_type: str, safe: bool = True) -> dict[str, Any]:
    return {
        "old_url": old_url,
        "new_url": new_url,
        "status": 301,
        "reason": reason,
        "content_type": content_type,
        "safe": safe and old_url.split("?")[0] != new_url.rstrip("/"),
    }


def build_redirect_map(inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redirects: list[dict[str, Any]] = []
    seen_old: set[str] = set()
    for row in inventory:
        old = row.get("url", "")
        if not old or old in seen_old:
            continue
        new = row.get("proposed_url") or propose_clean_url(old)
        needs = (
            old != new
            or row.get("redirect_required")
            or row.get("issues")
        )
        if not needs:
            continue
        reason = "canonical_merge"
        if "query_param_story" in (row.get("issues") or []):
            reason = "story_query_to_clean_url"
        elif "duplicate_slug_tokens" in (row.get("issues") or []):
            reason = "slug_deduplicate"
        elif "legacy_profil_path" in (row.get("issues") or []):
            reason = "legacy_profil_path"
        elif "legacy_hikaye_path" in (row.get("issues") or []):
            reason = "legacy_hikaye_path"
        entry = build_redirect_entry(old, new, reason=reason, content_type=row.get("content_type", ""))
        if entry["old_url"] != entry["new_url"].rstrip("/"):
            redirects.append(entry)
            seen_old.add(old)

    for slug in STORY_QUERY_SLUGS:
        old = f"{_site_url().rstrip('/')}/?story={slug}"
        new = propose_clean_url(old)
        if old not in seen_old:
            redirects.append(build_redirect_entry(old, new, reason="story_query_to_clean_url", content_type="story_query"))
            seen_old.add(old)
    return redirects


def _fetch_url_text(url: str, timeout: int = 25) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "HIVE-IndexingBot/1.0"})
    if r.status_code == 200:
        return r.text
    return ""


def _parse_sitemap_urls(xml_text: str, base: str, *, fetch_children: bool = True, _depth: int = 0) -> list[str]:
    urls: list[str] = []
    if not xml_text:
        return urls
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return urls
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    child_sitemaps: list[str] = []
    for loc in root.findall(".//sm:loc", ns):
        if loc.text:
            text = loc.text.strip()
            if fetch_children and _depth < 2 and text.endswith(".xml"):
                child_sitemaps.append(text)
            else:
                urls.append(text)
    if not urls and not child_sitemaps:
        for loc in root.iter():
            if loc.tag.endswith("loc") and loc.text:
                text = loc.text.strip()
                if fetch_children and _depth < 2 and text.endswith(".xml"):
                    child_sitemaps.append(text)
                elif not text.endswith(".xml") or _depth >= 2:
                    urls.append(text)
    if child_sitemaps:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_url_text, sm): sm for sm in child_sitemaps}
            for fut in as_completed(futures):
                sub_text = fut.result()
                if sub_text:
                    urls.extend(_parse_sitemap_urls(sub_text, base, fetch_children=False, _depth=_depth + 1))
    return urls


def fetch_sitemap_urls(site: str | None = None, *, max_urls: int = 5000) -> dict[str, Any]:
    site = (site or _site_url()).rstrip("/")
    candidates = [
        f"{site}/wp-sitemap.xml",
        f"{site}/sitemap_index.xml",
        f"{site}/sitemap.xml",
    ]
    all_urls: list[str] = []
    used = ""
    errors: list[str] = []
    for sm_url in candidates:
        try:
            text = _fetch_url_text(sm_url)
            if not text:
                errors.append(f"{sm_url}: HTTP error or empty")
                continue
            urls = _parse_sitemap_urls(text, site)
            if urls:
                all_urls = urls
                used = sm_url
                break
        except requests.RequestException as exc:
            errors.append(f"{sm_url}: {exc}")
    # dedupe preserve order
    seen: set[str] = set()
    uniq = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return {
        "success": bool(uniq),
        "sitemap_url": used,
        "urls": uniq[:max_urls],
        "count": len(uniq[:max_urls]),
        "errors": errors,
    }


def build_url_inventory(site: str | None = None, *, max_urls: int = 5000) -> dict[str, Any]:
    site = (site or _site_url()).rstrip("/")
    sm = fetch_sitemap_urls(site, max_urls=max_urls)
    urls = list(sm.get("urls") or [])
    # Ana sayfa ve bilinen query URL'leri
    urls.insert(0, site + "/")
    for slug in STORY_QUERY_SLUGS:
        urls.append(f"{site}/?story={slug}")

    inventory: list[dict[str, Any]] = []
    for url in urls[:max_urls]:
        info = classify_url(url)
        proposed = propose_clean_url(url)
        has_issues = bool(info["issues"])
        canonical_required = bool(
            ("?" in url and url.split("?")[0].rstrip("/") != proposed.rstrip("/"))
            or has_issues
        )
        redirect_required = (
            proposed.rstrip("/") != url.split("?")[0].rstrip("/")
            or has_issues
        )
        noindex = info["content_type"] in ("search", "tag", "story_query") or "query_param_story" in info["issues"]
        sitemap_include = not noindex and not has_issues and "?" not in url
        inventory.append({
            **info,
            "proposed_url": proposed,
            "redirect_required": redirect_required,
            "canonical_required": canonical_required or redirect_required,
            "canonical_url": proposed,
            "sitemap_include": sitemap_include,
            "noindex_recommended": noindex or (info["content_type"] == "tag"),
            "safe": True,
        })
    return {
        "success": True,
        "site": site,
        "sitemap": sm,
        "total_urls": len(inventory),
        "inventory": inventory,
        "generated_at": _now_iso(),
    }


def _save_json_report(name: str, payload: dict[str, Any]) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def run_balkutusu_index_recovery(
    site: str | None = None,
    *,
    apply_htaccess: bool = False,
    analyze_quality: bool = True,
    project_id: str = "",
) -> dict[str, Any]:
    """URL envanteri → redirect map → rapor. İçerik silmez."""
    from app.moduller.project_context import get_active_project_id, resolve_site_url

    site = (site or resolve_site_url(project_id) or _site_url()).strip()
    if not site:
        return {"success": False, "error": "site_required", "message": "Aktif proje veya site URL gerekli"}
    pid = (project_id or get_active_project_id() or "index-recovery").strip()
    domain = urlparse(site).netloc or site.replace("https://", "").replace("http://", "").split("/")[0]
    _emit_brain("index_recovery_started", result={"site": site, "project_id": pid})

    inv_res = build_url_inventory(site)
    inventory = inv_res.get("inventory") or []
    redirects = build_redirect_map(inventory)

    canonical_fixes = [r for r in inventory if r.get("canonical_required")]
    noindex_items = [r for r in inventory if r.get("noindex_recommended")]
    sitemap_excluded = [r for r in inventory if not r.get("sitemap_include")]
    risky = sorted(
        [r for r in inventory if r.get("issues")],
        key=lambda x: -len(x.get("issues") or []),
    )[:20]

    quality_results: list[dict] = []
    if analyze_quality:
        try:
            from app.moduller.seo_quality_gate import analyze_url
            for row in risky[:10]:
                try:
                    quality_results.append(analyze_url(row.get("proposed_url") or row.get("url", "")))
                except Exception as exc:
                    quality_results.append({"url": row.get("url"), "error": str(exc)})
        except Exception:
            pass

    # Rank watcher keywords
    rank_result: dict[str, Any] = {}
    try:
        from app.moduller.rank_index_watcher import register_project, track_keyword
        pid_rw = f"{pid}-index-recovery"
        register_project(pid_rw, domain, source="index_recovery")
        for kw in (
            "kuşadası escort", "kusadasi escort", "kuşadası escort bayan",
            "kuşadası gece hayatı", "kuşadası gece rehberi",
        ):
            track_keyword(kw, domain, project_id=pid_rw)
        rank_result = {"success": True, "project_id": pid_rw, "keywords": 5}
    except Exception as exc:
        rank_result = {"success": False, "error": str(exc)}

    # Campaign — kayıt oluştur, plan üretimi ayrı async adım (recovery'yi bloklamaz)
    campaign_result: dict[str, Any] = {}
    try:
        from app.moduller.campaign_engine import create_campaign
        c = create_campaign(
            name=f"Index Recovery — {domain}",
            target_keyword="",
            target_domain=site,
            goal="ranking",
            priority="high",
        )
        if c.get("success"):
            campaign_result = {"success": True, "campaign_id": c["campaign"]["campaign_id"], "plan": "deferred"}
    except Exception as exc:
        campaign_result = {"success": False, "error": str(exc)}

    redirect_path = _save_json_report(
        "index-recovery-redirect-map.json",
        {"generated_at": _now_iso(), "site": site, "redirects": redirects, "count": len(redirects)},
    )

    clean_sitemap_urls = [r["canonical_url"] for r in inventory if r.get("sitemap_include") and r.get("canonical_url")]

    report = {
        "generated_at": _now_iso(),
        "site": site,
        "gsc_baseline": {
            "sitemap_discovered": 1447,
            "indexed": 177,
            "index_ratio_pct": 12.2,
            "not_indexed": 1520,
            "discovered_not_indexed": 1188,
            "crawled_not_indexed": 321,
        },
        "inventory_total": len(inventory),
        "urls_cleaned": len([r for r in inventory if r.get("issues")]),
        "redirects_generated": len(redirects),
        "canonical_fixes": len(canonical_fixes),
        "sitemap_urls_excluded": len(sitemap_excluded),
        "noindex_recommended": len(noindex_items),
        "internal_links_policy": "min_5_per_indexable_page_via_hive-index-recovery.php",
        "risky_urls_top20": risky,
        "clean_sitemap_urls_sample": clean_sitemap_urls[:50],
        "clean_sitemap_url_count": len(clean_sitemap_urls),
        "projections": {
            "week_2_index_target": 300,
            "day_30_index_ratio_target_pct": 25,
            "day_60_impressions_target": 40000,
            "note": "Hedef projeksiyon — garanti değil",
        },
        "redirect_map_path": redirect_path,
        "rank_watcher": rank_result,
        "campaign": campaign_result,
        "quality_reanalysis": quality_results[:10],
        "robots_policy": "seo_enhanced_via_indexing_fix.fix_robots_txt",
        "apply_htaccess": apply_htaccess,
    }
    report_path = _save_json_report("balkutusu-index-recovery-report.json", report)

    _emit_brain("balkutusu_redirect_map_generated", result={"count": len(redirects), "path": redirect_path})
    _emit_brain("balkutusu_url_cleanup_completed", result={"inventory": len(inventory), "report": report_path})
    _emit_brain("balkutusu_internal_links_updated", result={"policy": "theme_hive_index_recovery"})

    return {
        "success": True,
        "inventory": inv_res,
        "redirects": redirects,
        "redirect_map_path": redirect_path,
        "report_path": report_path,
        "report": report,
    }


def enhanced_robots_content(site: str | None = None) -> str:
    site = (site or _site_url()).rstrip("/")
    host = urlparse(site).netloc
    generated = duzenle(host, "seo")
    content = generated.get("icerik", "")
    extra = [
        "",
        "# Balkutusu Index Recovery",
        "Disallow: /wp-admin/",
        "Disallow: /wp-json/wp/v2/users",
        "Disallow: /*?s=",
        "Disallow: /search/",
        "Allow: /profil/",
        "Allow: /hikaye/",
        "Allow: /rehber/",
        "Allow: /sss/",
        "Allow: /gece-mahalle/",
        "Allow: /gece-hayati/",
        "Allow: /kategori/",
    ]
    content = content.replace(f"Sitemap: https://{host}/sitemap.xml", f"Sitemap: {site}/wp-sitemap.xml")
    if "wp-sitemap.xml" not in content:
        content += f"\nSitemap: {site}/wp-sitemap.xml\n"
    return content + "\n".join(extra) + "\n"
