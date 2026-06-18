"""Rank & Index Watcher — gerçek GSC / DataForSEO ile index ve sıra takibi."""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from app import config

logger = logging.getLogger("hive.rank_index_watcher")

ROOT = Path(__file__).resolve().parent.parent.parent.parent
STATE_FILE = Path(__file__).resolve().parent.parent / "rank_index_watcher_state.json"
REPORTS_DIR = ROOT / "reports"
GENERATED_DIR = ROOT / "generated-sites"
SEO_GATE_STATE = Path(__file__).resolve().parent.parent / "seo_quality_gate_state.json"
ASTRO_STATE = Path(__file__).resolve().parent.parent / "astro_factory_state.json"

USER_AGENT = "HIVE-RankIndexWatcher/1.0"
DECAY_CTR_DROP = 0.003
DECAY_POSITION_DROP = 2.0
DECAY_CLICKS_DROP_PCT = 0.15
RESEARCH_PACK = "v2"


def _default_keyword_metrics() -> dict[str, Any]:
    return {
        "ranking_velocity": 0.0,
        "ranking_momentum": 0.0,
        "ranking_decay_score": 0,
        "ranking_recovery_score": 0,
        "keyword_strength_score": 50,
        "trend_direction": "flat",
    }


def _parse_metric_ts(at: str) -> float | None:
    if not at:
        return None
    text = at.replace(" UTC", "").strip()[:19].replace("T", " ")
    try:
        return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def compute_keyword_rank_metrics(
    history: list[dict[str, Any]],
    last_position: int | None = None,
) -> dict[str, Any]:
    """SerpBear-inspired: velocity, momentum, decay, recovery, strength, trend."""
    metrics = _default_keyword_metrics()
    valid = [(h.get("position"), h.get("at", "")) for h in history if h.get("position") is not None]
    if not valid:
        if last_position is not None:
            metrics["keyword_strength_score"] = max(0, min(100, 101 - int(last_position)))
        return metrics

    positions = [int(v[0]) for v in valid]
    cur = positions[0]

    if len(valid) >= 2:
        p0, t0 = valid[0]
        p1, t1 = valid[1]
        ts0, ts1 = _parse_metric_ts(t0), _parse_metric_ts(t1)
        days = max((ts0 - ts1) / 86400, 0.01) if ts0 and ts1 else 1.0
        metrics["ranking_velocity"] = round((int(p0) - int(p1)) / days, 3)

    deltas: list[float] = []
    for i in range(min(3, len(positions) - 1)):
        deltas.append(float(positions[i] - positions[i + 1]))
    if deltas:
        weights = [3, 2, 1][: len(deltas)]
        metrics["ranking_momentum"] = round(
            sum(d * w for d, w in zip(deltas, weights)) / sum(weights), 3,
        )

    if len(positions) >= 2:
        window = positions[: min(4, len(positions))]
        worst_drop = max(0, window[0] - window[-1])
        metrics["ranking_decay_score"] = min(100, int(worst_drop * 12))

    if len(positions) >= 3:
        prev_trend = positions[1] - positions[2]
        curr_trend = positions[0] - positions[1]
        if prev_trend > 2 and curr_trend < -1:
            metrics["ranking_recovery_score"] = min(100, int(abs(curr_trend) * 15 + 20))
            metrics["trend_direction"] = "recovering"
        elif curr_trend > 3:
            metrics["trend_direction"] = "decaying"
        elif curr_trend < -2:
            metrics["trend_direction"] = "up"
        else:
            metrics["trend_direction"] = "flat"
    elif len(positions) >= 2:
        diff = positions[0] - positions[1]
        if diff > 3:
            metrics["trend_direction"] = "decaying"
        elif diff < -3:
            metrics["trend_direction"] = "up"

    pos_score = max(0, min(80, 101 - cur))
    momentum_bonus = max(-15, min(15, -int(metrics["ranking_momentum"] * 3)))
    decay_penalty = metrics["ranking_decay_score"] // 5
    recovery_bonus = metrics["ranking_recovery_score"] // 10
    metrics["keyword_strength_score"] = max(
        0, min(100, pos_score + momentum_bonus - decay_penalty + recovery_bonus),
    )
    return metrics


def _apply_keyword_metrics(entry: dict[str, Any]) -> None:
    entry.update(compute_keyword_rank_metrics(entry.get("history") or [], entry.get("last_position")))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("projects", {})
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"projects": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_domain(domain: str) -> str:
    text = (domain or "").strip()
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = f"https://{text}"
    parsed = urlparse(text)
    if not parsed.netloc:
        raise ValueError("Geçersiz domain")
    return f"{parsed.scheme}://{parsed.netloc}"


def _domain_host(domain: str) -> str:
    return urlparse(_normalize_domain(domain)).netloc.lower().replace("www.", "")


def _safe_project_id(project_id: str) -> str:
    pid = (project_id or "").strip()
    if not pid or ".." in pid or "/" in pid or "\\" in pid:
        raise ValueError("Geçersiz project_id")
    return pid


def _gsc_site_url() -> str:
    return (
        (config.get("GOOGLE_SEARCH_CONSOLE_SITE_URL") or "").strip()
        or (config.get("GSC_SITE_URL") or "").strip()
    )


def _gsc_oauth_configured() -> bool:
    client_id = (config.get("GOOGLE_CLIENT_ID") or config.get("GSC_CLIENT_ID") or "").strip()
    client_secret = (
        (config.get("GOOGLE_CLIENT_SECRET") or config.get("GSC_CLIENT_SECRET") or "").strip()
    )
    refresh = (config.get("GOOGLE_REFRESH_TOKEN") or "").strip()
    site = _gsc_site_url()
    return bool(client_id and client_secret and refresh and site)


def _dataforseo_configured() -> bool:
    from app.moduller.dataforseo_client import is_configured

    return is_configured()


def _active_providers() -> list[dict[str, Any]]:
    providers: list[dict[str, Any]] = []
    if _gsc_oauth_configured():
        providers.append({"id": "search_console", "active": True, "label": "Google Search Console"})
    if _dataforseo_configured():
        providers.append({"id": "dataforseo", "active": True, "label": "DataForSEO SERP"})
    return providers


def health() -> dict[str, Any]:
    providers = _active_providers()
    state = _load_state()
    try:
        from app.moduller.provider_settings import get_settings, health as ps_health
        prefs = get_settings()
        ps = ps_health()
    except Exception:
        prefs = {}
        ps = {}
    return {
        "success": True,
        "status": "ok",
        "search_console": _gsc_oauth_configured(),
        "rank_provider": _dataforseo_configured(),
        "providers": providers,
        "provider_settings": {
            "rank": prefs.get("rank", "auto"),
            "ai_overview": prefs.get("ai_overview", "auto"),
            "serp": prefs.get("serp", "auto"),
        },
        "provider_health": ps.get("categories", {}),
        "project_count": len(state.get("projects", {})),
        "reports_dir": str(REPORTS_DIR),
        "checked_at": _now(),
        "research_pack": RESEARCH_PACK,
    }


def _gsc_credentials():
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        return None, "google-auth paketi yüklü değil"

    client_id = (config.get("GOOGLE_CLIENT_ID") or config.get("GSC_CLIENT_ID") or "").strip()
    client_secret = (
        (config.get("GOOGLE_CLIENT_SECRET") or config.get("GSC_CLIENT_SECRET") or "").strip()
    )
    refresh = (config.get("GOOGLE_REFRESH_TOKEN") or "").strip()
    if not client_id or not client_secret or not refresh:
        return None, "GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN eksik"

    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    try:
        creds.refresh(Request())
    except Exception as exc:
        return None, f"GSC token yenileme hatası: {exc}"
    return creds, ""


def _gsc_service():
    creds, err = _gsc_credentials()
    if not creds:
        return None, err or "search_console_not_configured"
    try:
        from googleapiclient.discovery import build

        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        return service, ""
    except ImportError:
        return None, "google-api-python-client yüklü değil"
    except Exception as exc:
        return None, str(exc)


def register_project(project_id: str, domain: str, *, source: str = "manual") -> dict[str, Any]:
    pid = _safe_project_id(project_id)
    dom = _normalize_domain(domain)
    state = _load_state()
    projects = state.setdefault("projects", {})
    existing = projects.get(pid, {})
    project = {
        "project_id": pid,
        "domain": dom,
        "keywords": existing.get("keywords", []),
        "index_status": existing.get("index_status", []),
        "performance_history": existing.get("performance_history", []),
        "alerts": existing.get("alerts", []),
        "tracked_urls": existing.get("tracked_urls", []),
        "seo_gate_flags": existing.get("seo_gate_flags", []),
        "registered_at": existing.get("registered_at") or _now(),
        "updated_at": _now(),
        "source": source,
    }
    projects[pid] = project
    _save_state(state)
    return {"success": True, "project": project}


def list_projects() -> dict[str, Any]:
    state = _load_state()
    projects = list(state.get("projects", {}).values())
    return {"success": True, "projects": projects, "count": len(projects)}


def get_project(project_id: str) -> dict[str, Any]:
    pid = _safe_project_id(project_id)
    state = _load_state()
    project = state.get("projects", {}).get(pid)
    if not project:
        return {"success": False, "error": "Proje bulunamadı"}
    return {"success": True, "project": project}


def _append_unique_keywords(project: dict[str, Any], keywords: list[str]) -> list[str]:
    seen = {k.lower() for k in project.get("keywords", []) if k}
    added: list[str] = []
    for kw in keywords:
        text = (kw or "").strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        added.append(text)
        project.setdefault("keywords", []).append({
            "keyword": text,
            "added_at": _now(),
            "last_position": None,
            "last_url": "",
            "history": [],
            **_default_keyword_metrics(),
        })
    return added


def _read_astro_data(project_id: str) -> tuple[dict[str, Any] | None, str]:
    if not ASTRO_STATE.exists():
        return None, "astro_factory_state.json yok"
    try:
        astro = json.loads(ASTRO_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, str(exc)
    proj = (astro.get("projects") or {}).get(project_id)
    if not proj:
        return None, "Astro projesi bulunamadı"
    slug = proj.get("slug") or ""
    if not slug or ".." in slug or "/" in slug:
        return None, "Geçersiz proje slug"
    data_dir = GENERATED_DIR / slug / "src" / "data"
    if not data_dir.is_dir():
        return None, f"Proje veri dizini yok: {data_dir}"
    pages = json.loads((data_dir / "pages.json").read_text(encoding="utf-8"))
    faqs = json.loads((data_dir / "faqs.json").read_text(encoding="utf-8"))
    blog = json.loads((data_dir / "blog.json").read_text(encoding="utf-8"))
    return {"pages": pages, "faqs": faqs, "blog": blog, "astro": proj}, ""


def _extract_keywords_from_astro(data: dict[str, Any]) -> list[str]:
    from app.moduller.seo_quality_gate import _collect_pages_from_data

    pages_data = data.get("pages") or {}
    keywords: list[str] = []
    seed = (pages_data.get("seed_keyword") or "").strip()
    if seed:
        keywords.append(seed)
    astro = data.get("astro") or {}
    if astro.get("seed_keyword"):
        keywords.append(astro["seed_keyword"].strip())
    for page in _collect_pages_from_data(pages_data, data.get("faqs") or [], data.get("blog") or []):
        for field in ("keyword", "title"):
            val = (page.get(field) or "").strip()
            if val and len(val) > 3:
                keywords.append(val)
    # dedupe preserve order
    out: list[str] = []
    seen: set[str] = set()
    for kw in keywords:
        low = kw.lower()
        if low not in seen:
            seen.add(low)
            out.append(kw)
    return out


def _load_seo_gate_failures(project_id: str) -> list[dict[str, Any]]:
    if not SEO_GATE_STATE.exists():
        return []
    try:
        gate = json.loads(SEO_GATE_STATE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    flags: list[dict[str, Any]] = []
    for report in (gate.get("reports") or {}).values():
        if report.get("project_id") != project_id:
            continue
        if report.get("status") == "fail" or (report.get("overall_score") or 100) < 70:
            for page in report.get("pages") or []:
                flags.append({
                    "slug": page.get("slug") or page.get("page_id") or "",
                    "title": page.get("title", ""),
                    "overall_score": page.get("overall_score"),
                    "report_id": report.get("report_id"),
                    "flagged_at": _now(),
                })
    return flags


def bulk_track(project_id: str) -> dict[str, Any]:
    pid = _safe_project_id(project_id)
    state = _load_state()
    project = state.get("projects", {}).get(pid)
    if not project:
        return {"success": False, "error": "Önce register-project ile projeyi kaydedin"}

    data, err = _read_astro_data(pid)
    if not data:
        return {"success": False, "error": err or "Astro verisi okunamadı"}

    keywords = _extract_keywords_from_astro(data)
    added = _append_unique_keywords(project, keywords)
    project["seo_gate_flags"] = _load_seo_gate_failures(pid)
    project["updated_at"] = _now()
    state["projects"][pid] = project
    _save_state(state)

    track_results: list[dict[str, Any]] = []
    for entry in project.get("keywords", [])[-len(added):]:
        kw = entry.get("keyword", "")
        if kw:
            tr = track_keyword(kw, project.get("domain", ""), save=False)
            track_results.append(tr)

    return {
        "success": True,
        "project_id": pid,
        "keywords_extracted": len(keywords),
        "keywords_added": len(added),
        "seo_gate_flags": len(project.get("seo_gate_flags", [])),
        "track_results": track_results,
    }


def index_status(url: str, *, save: bool = True, project_id: str = "") -> dict[str, Any]:
    target = (url or "").strip()
    if not target.startswith(("http://", "https://")):
        return {"success": False, "error": "Geçerli http(s) URL gerekli"}

    if not _gsc_oauth_configured():
        return {
            "success": False,
            "error": "search_console_not_configured",
            "message": "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN ve GOOGLE_SEARCH_CONSOLE_SITE_URL gerekli",
            "indexed": None,
            "coverage": "unknown",
            "last_checked": _now(),
        }

    service, err = _gsc_service()
    if not service:
        return {
            "success": False,
            "error": "search_console_error",
            "message": err,
            "indexed": None,
            "coverage": "unknown",
            "last_checked": _now(),
        }

    site_url = _gsc_site_url()
    try:
        resp = (
            service.urlInspection()
            .index()
            .inspect(body={"inspectionUrl": target, "siteUrl": site_url})
            .execute()
        )
    except Exception as exc:
        return {
            "success": False,
            "error": "search_console_api_error",
            "message": str(exc),
            "indexed": None,
            "coverage": "error",
            "last_checked": _now(),
        }

    result = resp.get("inspectionResult", {}) or {}
    index_result = result.get("indexStatusResult", {}) or {}
    verdict = (index_result.get("verdict") or "").upper()
    coverage = (index_result.get("coverageState") or index_result.get("indexingState") or "unknown").lower()
    indexed = verdict in ("PASS", "NEUTRAL") or coverage in ("indexed", "submitted_and_indexed")

    payload = {
        "success": True,
        "url": target,
        "indexed": indexed,
        "coverage": coverage,
        "verdict": verdict,
        "last_checked": _now(),
        "source": "search_console_url_inspection",
        "raw": {
            "page_fetch_state": index_result.get("pageFetchState"),
            "robots_txt_state": index_result.get("robotsTxtState"),
            "last_crawl_time": index_result.get("lastCrawlTime"),
        },
    }

    if save and project_id:
        pid = _safe_project_id(project_id)
        state = _load_state()
        proj = state.get("projects", {}).get(pid)
        if proj:
            proj.setdefault("index_status", []).insert(0, payload)
            proj["index_status"] = proj["index_status"][:200]
            proj["updated_at"] = _now()
            _save_state(state)

    return payload


def _http_get(url: str, timeout: int = 25) -> tuple[int, str, str]:
    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        return r.status_code, r.text or "", r.url
    except requests.RequestException as exc:
        return 0, "", str(exc)


def _parse_sitemap_urls(content: str, base: str, max_urls: int = 5000) -> list[str]:
    urls: list[str] = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return urls
    tag = root.tag.lower()
    if tag.endswith("sitemapindex"):
        for sm in root.findall(".//{*}sitemap/{*}loc"):
            if sm.text:
                urls.append(sm.text.strip())
        return urls[:50]
    for loc in root.findall(".//{*}url/{*}loc"):
        if loc.text:
            urls.append(loc.text.strip())
            if len(urls) >= max_urls:
                break
    return urls


def sitemap_status(domain: str) -> dict[str, Any]:
    base = _normalize_domain(domain)
    host = urlparse(base).netloc

    robots_url = urljoin(base + "/", "robots.txt")
    code, robots_body, robots_final = _http_get(robots_url)
    robots_exists = code == 200 and bool(robots_body.strip())
    sitemap_urls_declared: list[str] = []
    if robots_exists:
        for line in robots_body.splitlines():
            if line.lower().startswith("sitemap:"):
                sm = line.split(":", 1)[-1].strip()
                if sm:
                    sitemap_urls_declared.append(sm)

    sitemap_candidates = sitemap_urls_declared or [urljoin(base + "/", "sitemap.xml")]
    sitemap_info: list[dict[str, Any]] = []
    all_page_urls: list[str] = []

    for sm_url in sitemap_candidates[:5]:
        sc, body, final = _http_get(sm_url)
        entry = {
            "url": sm_url,
            "status_code": sc,
            "final_url": final or sm_url,
            "exists": sc == 200 and "<" in body,
        }
        if entry["exists"]:
            parsed = _parse_sitemap_urls(body, sm_url)
            if parsed and parsed[0].endswith(".xml"):
                entry["type"] = "index"
                entry["child_sitemaps"] = len(parsed)
            else:
                entry["type"] = "urlset"
                entry["url_count"] = len(parsed)
                all_page_urls.extend(parsed)
        sitemap_info.append(entry)

    indexed_count: int | None = None
    indexed_ratio: float | None = None
    gsc_note = ""

    if _gsc_oauth_configured() and all_page_urls:
        service, err = _gsc_service()
        if service:
            sample = all_page_urls[:20]
            indexed_hits = 0
            checked = 0
            for page_url in sample:
                ins = index_status(page_url, save=False)
                if ins.get("success"):
                    checked += 1
                    if ins.get("indexed"):
                        indexed_hits += 1
            if checked:
                indexed_count = indexed_hits
                indexed_ratio = round(indexed_hits / checked, 4)
                gsc_note = f"Örneklem: {checked}/{len(all_page_urls)} URL GSC ile kontrol edildi"
        else:
            gsc_note = err
    else:
        gsc_note = "Index oranı için Search Console gerekli"

    alerts: list[dict[str, Any]] = []
    if not robots_exists:
        alerts.append({"level": "critical", "type": "robots_missing", "message": f"robots.txt erişilemiyor ({robots_url})"})
    if not any(s.get("exists") for s in sitemap_info):
        alerts.append({"level": "critical", "type": "sitemap_missing", "message": "sitemap.xml bulunamadı"})

    return {
        "success": True,
        "domain": base,
        "robots": {
            "url": robots_url,
            "exists": robots_exists,
            "status_code": code,
            "has_sitemap_declaration": bool(sitemap_urls_declared),
            "preview": robots_body[:500] if robots_exists else "",
        },
        "sitemaps": sitemap_info,
        "url_count": len(all_page_urls),
        "indexed_sample_count": indexed_count,
        "indexed_ratio": indexed_ratio,
        "indexed_ratio_note": gsc_note,
        "alerts": alerts,
        "last_checked": _now(),
    }


def _dataforseo_serp(keyword: str) -> dict[str, Any] | None:
    from app.moduller.dataforseo_client import _auth_header, is_configured

    if not is_configured():
        return None
    payload = [{
        "keyword": keyword,
        "location_code": 2792,
        "language_code": "tr",
        "device": "desktop",
        "os": "windows",
        "depth": 100,
    }]
    try:
        r = requests.post(
            "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
            headers=_auth_header(),
            json=payload,
            timeout=120,
        )
        data = r.json()
        if data.get("status_code") != 20000:
            return {"error": data.get("status_message", "DataForSEO hata")}
        tasks = data.get("tasks") or []
        if not tasks or not tasks[0].get("result"):
            return {"error": "DataForSEO boş sonuç"}
        return tasks[0]["result"][0]
    except requests.RequestException as exc:
        return {"error": str(exc)}


def track_keyword(keyword: str, domain: str, *, save: bool = True, project_id: str = "") -> dict[str, Any]:
    kw = (keyword or "").strip()
    dom = (domain or "").strip()
    if not kw:
        return {"success": False, "error": "keyword gerekli"}
    if not dom:
        return {"success": False, "error": "domain gerekli"}

    if not _dataforseo_configured():
        return {
            "success": False,
            "error": "provider_missing",
            "message": "Rank provider yapılandırılmadı — DATAFORSEO_LOGIN ve DATAFORSEO_PASSWORD ekleyin",
        }

    serp = _dataforseo_serp(kw)
    if not serp:
        return {"success": False, "error": "provider_missing", "message": "DataForSEO yanıt vermedi"}
    if serp.get("error"):
        return {"success": False, "error": "provider_error", "message": serp["error"]}

    host = _domain_host(dom)
    items = serp.get("items") or []
    position: int | None = None
    first_url = ""
    serp_snapshot: list[dict[str, Any]] = []

    for item in items:
        itype = (item.get("type") or "").lower()
        if itype in ("organic", "featured_snippet"):
            rank = item.get("rank_group") or item.get("rank_absolute")
            url = item.get("url") or ""
            serp_snapshot.append({
                "position": rank,
                "url": url,
                "title": item.get("title", ""),
                "type": itype,
            })
            item_host = urlparse(url).netloc.lower().replace("www.", "")
            if position is None and host and item_host and host in item_host:
                position = int(rank) if rank is not None else None
                first_url = url

    result = {
        "success": True,
        "keyword": kw,
        "domain": dom,
        "position": position,
        "first_url": first_url,
        "serp_snapshot": serp_snapshot[:15],
        "provider": "dataforseo",
        "checked_at": _now(),
    }

    if save:
        state = _load_state()
        for proj in state.get("projects", {}).values():
            if _domain_host(proj.get("domain", "")) != host:
                continue
            for entry in proj.get("keywords", []):
                if (entry.get("keyword") or "").lower() == kw.lower():
                    entry["last_position"] = position
                    entry["last_url"] = first_url
                    entry.setdefault("history", []).insert(0, {
                        "position": position,
                        "at": _now(),
                    })
                    entry["history"] = entry["history"][:50]
                    _apply_keyword_metrics(entry)
            proj["updated_at"] = _now()
        if project_id:
            pid = _safe_project_id(project_id)
            if pid in state.get("projects", {}):
                state["projects"][pid]["updated_at"] = _now()
        _save_state(state)

    return result


def ai_overview(keyword: str, provider: str | None = None) -> dict[str, Any]:
    kw = (keyword or "").strip()
    if not kw:
        return {"success": False, "error": "keyword gerekli"}

    from app.moduller.provider_settings import require_dataforseo, resolve_mode
    mode = resolve_mode("ai_overview", provider)
    if mode == "free":
        return {
            "success": False,
            "error": "provider_missing",
            "message": "AI Overview — ücretsiz mod seçildi, DataForSEO kapalı",
            "provider_mode": mode,
        }

    if not _dataforseo_configured():
        msg = "AI Overview için DataForSEO gerekli"
        if require_dataforseo("ai_overview", provider):
            msg = "DataForSEO seçildi — DATAFORSEO_LOGIN/PASSWORD gerekli"
        return {
            "success": False,
            "error": "provider_missing",
            "message": msg,
            "provider_mode": mode,
        }

    serp = _dataforseo_serp(kw)
    if not serp or serp.get("error"):
        return {
            "success": False,
            "error": "provider_error",
            "message": (serp or {}).get("error", "SERP alınamadı"),
        }

    items = serp.get("items") or []
    ai_items = [
        it for it in items
        if "ai" in (it.get("type") or "").lower() or "overview" in (it.get("type") or "").lower()
    ]
    sources: list[dict[str, str]] = []
    for it in ai_items:
        for ref in it.get("references") or it.get("items") or []:
            if isinstance(ref, dict):
                sources.append({
                    "url": ref.get("url", ""),
                    "title": ref.get("title", ""),
                    "source": ref.get("source", ""),
                })
            elif isinstance(ref, str):
                sources.append({"url": ref, "title": "", "source": ""})

    return {
        "success": True,
        "keyword": kw,
        "has_ai_overview": bool(ai_items),
        "ai_overview_count": len(ai_items),
        "sources": sources[:20],
        "provider": "dataforseo",
        "checked_at": _now(),
    }


def performance(domain: str, *, project_id: str = "", days: int = 28) -> dict[str, Any]:
    dom = _normalize_domain(domain)
    if not _gsc_oauth_configured():
        return {
            "success": False,
            "error": "search_console_not_configured",
            "message": "Search Console OAuth gerekli",
        }

    service, err = _gsc_service()
    if not service:
        return {"success": False, "error": "search_console_error", "message": err}

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=max(1, days))
    site_url = _gsc_site_url()
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": ["query"],
        "rowLimit": 250,
    }
    try:
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except Exception as exc:
        return {"success": False, "error": "search_console_api_error", "message": str(exc)}

    rows = resp.get("rows") or []
    clicks = sum(r.get("clicks", 0) for r in rows)
    impressions = sum(r.get("impressions", 0) for r in rows)
    ctr = (clicks / impressions) if impressions else 0.0
    positions = [r.get("position", 0) for r in rows if r.get("position")]
    avg_position = round(sum(positions) / len(positions), 2) if positions else None

    snapshot = {
        "domain": dom,
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(ctr, 4),
        "avg_position": avg_position,
        "query_count": len(rows),
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "top_queries": [
            {
                "query": r.get("keys", [""])[0],
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0),
                "position": r.get("position"),
            }
            for r in rows[:25]
        ],
        "checked_at": _now(),
        "source": "search_console",
    }

    if project_id:
        pid = _safe_project_id(project_id)
        state = _load_state()
        proj = state.get("projects", {}).get(pid)
        if proj:
            proj.setdefault("performance_history", []).insert(0, snapshot)
            proj["performance_history"] = proj["performance_history"][:100]
            proj["updated_at"] = _now()
            _save_state(state)

    return {"success": True, **snapshot}


def decay_detector(project_id: str) -> dict[str, Any]:
    pid = _safe_project_id(project_id)
    state = _load_state()
    project = state.get("projects", {}).get(pid)
    if not project:
        return {"success": False, "error": "Proje bulunamadı"}

    history = project.get("performance_history") or []
    alerts: list[dict[str, Any]] = list(project.get("alerts") or [])

    if len(history) < 2:
        return {
            "success": True,
            "project_id": pid,
            "alerts": alerts,
            "note": "Decay analizi için en az 2 performance snapshot gerekli — performance endpoint çağırın",
        }

    latest, previous = history[0], history[1]
    if previous.get("clicks", 0) > 0:
        drop = (previous["clicks"] - latest.get("clicks", 0)) / previous["clicks"]
        if drop >= DECAY_CLICKS_DROP_PCT:
            alerts.append({
                "level": "warning",
                "type": "traffic_drop",
                "message": f"Trafik düşüşü: %{drop * 100:.1f}",
                "previous": previous.get("clicks"),
                "current": latest.get("clicks"),
            })

    if previous.get("ctr") and latest.get("ctr") is not None:
        if previous["ctr"] - latest["ctr"] >= DECAY_CTR_DROP:
            alerts.append({
                "level": "warning",
                "type": "ctr_drop",
                "message": f"CTR düşüşü: {previous['ctr']:.4f} → {latest['ctr']:.4f}",
            })

    if previous.get("avg_position") and latest.get("avg_position") is not None:
        if latest["avg_position"] - previous["avg_position"] >= DECAY_POSITION_DROP:
            alerts.append({
                "level": "warning",
                "type": "rank_drop",
                "message": f"Pozisyon düşüşü: {previous['avg_position']} → {latest['avg_position']}",
            })

    for kw in project.get("keywords", []):
        _apply_keyword_metrics(kw)
        if kw.get("ranking_decay_score", 0) >= 36:
            alerts.append({
                "level": "warning",
                "type": "keyword_decay",
                "keyword": kw.get("keyword"),
                "message": f"'{kw.get('keyword')}' decay skoru {kw.get('ranking_decay_score')} — trend: {kw.get('trend_direction')}",
                "decay_score": kw.get("ranking_decay_score"),
                "velocity": kw.get("ranking_velocity"),
            })
        elif kw.get("trend_direction") == "recovering":
            alerts.append({
                "level": "info",
                "type": "keyword_recovery",
                "keyword": kw.get("keyword"),
                "message": f"'{kw.get('keyword')}' toparlanıyor (recovery {kw.get('ranking_recovery_score')})",
            })
        hist = kw.get("history") or []
        if len(hist) >= 2:
            p0, p1 = hist[0].get("position"), hist[1].get("position")
            if p0 is not None and p1 is not None and p0 > p1 + 3:
                alerts.append({
                    "level": "warning",
                    "type": "keyword_rank_drop",
                    "keyword": kw.get("keyword"),
                    "message": f"'{kw.get('keyword')}' pozisyonu {p1} → {p0}",
                })

    project["alerts"] = alerts[-100:]
    project["updated_at"] = _now()
    state["projects"][pid] = project
    _save_state(state)

    return {"success": True, "project_id": pid, "alerts": alerts}


def opportunity_finder(project_id: str) -> dict[str, Any]:
    pid = _safe_project_id(project_id)
    state = _load_state()
    project = state.get("projects", {}).get(pid)
    if not project:
        return {"success": False, "error": "Proje bulunamadı"}

    opportunities: list[dict[str, Any]] = []
    perf = (project.get("performance_history") or [{}])[0]
    top_queries = perf.get("top_queries") or []

    for row in top_queries:
        pos = row.get("position")
        ctr = row.get("ctr") or 0
        q = row.get("query", "")
        if pos is None or not q:
            continue
        if 4 <= pos <= 15 and ctr < 0.01:
            opportunities.append({
                "keyword": q,
                "position": pos,
                "ctr": ctr,
                "suggestions": ["title değiştir", "meta description güçlendir"],
                "priority": "high",
            })
        elif 8 <= pos <= 20:
            opportunities.append({
                "keyword": q,
                "position": pos,
                "ctr": ctr,
                "suggestions": ["FAQ ekle", "schema markup ekle"],
                "priority": "medium",
            })

    for flag in project.get("seo_gate_flags") or []:
        opportunities.append({
            "keyword": flag.get("title") or flag.get("slug"),
            "position": None,
            "suggestions": ["SEO Quality Gate fail — içerik ve schema iyileştir"],
            "priority": "critical",
            "seo_gate_score": flag.get("overall_score"),
        })

    return {"success": True, "project_id": pid, "opportunities": opportunities}


def export_report(project_id: str, fmt: str = "json") -> dict[str, Any]:
    pid = _safe_project_id(project_id)
    got = get_project(pid)
    if not got.get("success"):
        return got

    project = got["project"]
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^\w\-]", "_", pid)[:64]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if fmt == "md":
        lines = [
            f"# Rank & Index Watcher — {pid}",
            "",
            f"**Domain:** {project.get('domain')}",
            f"**Güncelleme:** {_now()}",
            "",
            "## Keywords",
        ]
        for kw in project.get("keywords", [])[:50]:
            lines.append(
                f"- {kw.get('keyword')} — pozisyon: {kw.get('last_position', '—')}"
            )
        lines.extend(["", "## Alerts"])
        for a in project.get("alerts", [])[:30]:
            lines.append(f"- [{a.get('level')}] {a.get('type')}: {a.get('message')}")
        content = "\n".join(lines) + "\n"
        path = REPORTS_DIR / f"rank_watcher_{safe_name}_{ts}.md"
        path.write_text(content, encoding="utf-8")
    else:
        content = json.dumps(project, ensure_ascii=False, indent=2)
        path = REPORTS_DIR / f"rank_watcher_{safe_name}_{ts}.json"
        path.write_text(content, encoding="utf-8")

    try:
        rel = str(path.relative_to(ROOT))
    except ValueError:
        rel = str(path.relative_to(REPORTS_DIR.parent)) if REPORTS_DIR.parent in path.parents else path.name

    return {
        "success": True,
        "format": fmt,
        "path": rel,
        "absolute_path": str(path.resolve()),
    }


def on_astro_project_created(project_id: str, domain: str) -> dict[str, Any]:
    """Astro Factory hook — yeni proje izlemeye alınır."""
    return register_project(project_id, domain, source="astro_factory")


def on_talon_keyword_priority(project_id: str, keywords: list[str]) -> dict[str, Any]:
    """Talon hook — ileride keyword önceliği için."""
    pid = _safe_project_id(project_id)
    state = _load_state()
    project = state.get("projects", {}).get(pid)
    if not project:
        return {"success": False, "error": "Proje kayıtlı değil", "hook": "talon"}
    added = _append_unique_keywords(project, keywords)
    project["talon_hook"] = {"last_keywords": keywords[:20], "at": _now()}
    project["updated_at"] = _now()
    state["projects"][pid] = project
    _save_state(state)
    return {"success": True, "hook": "talon", "keywords_added": len(added)}


rank_index_watcher = type("RankIndexWatcher", (), {
    "health": staticmethod(health),
    "register_project": staticmethod(register_project),
    "list_projects": staticmethod(list_projects),
    "get_project": staticmethod(get_project),
    "index_status": staticmethod(index_status),
    "sitemap_status": staticmethod(sitemap_status),
    "track_keyword": staticmethod(track_keyword),
    "bulk_track": staticmethod(bulk_track),
    "ai_overview": staticmethod(ai_overview),
    "performance": staticmethod(performance),
    "decay_detector": staticmethod(decay_detector),
    "opportunity_finder": staticmethod(opportunity_finder),
    "export_report": staticmethod(export_report),
    "on_astro_project_created": staticmethod(on_astro_project_created),
    "on_talon_keyword_priority": staticmethod(on_talon_keyword_priority),
})()
