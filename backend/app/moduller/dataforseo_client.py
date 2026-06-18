"""DataForSEO API istemcisi — .env ve Talon SQLite fallback."""

from __future__ import annotations

import base64
import logging
from typing import Any

import requests

from app import config

logger = logging.getLogger("hive.dataforseo")


def _credentials() -> tuple[str, str]:
    login = (config.get("DATAFORSEO_LOGIN") or "").strip()
    password = (config.get("DATAFORSEO_PASSWORD") or "").strip()
    if login and password:
        return login, password
    try:
        from .talon_db import api_key_getir
        login = api_key_getir("dataforseo_login") or ""
        password = api_key_getir("dataforseo_password") or ""
    except Exception:
        pass
    return login, password


def is_configured() -> bool:
    login, password = _credentials()
    return bool(login and password)


def _auth_header() -> dict[str, str]:
    login, password = _credentials()
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def _post(endpoint: str, payload: list | dict) -> dict[str, Any] | None:
    if not is_configured():
        return None
    try:
        r = requests.post(
            f"https://api.dataforseo.com{endpoint}",
            headers=_auth_header(),
            json=payload,
            timeout=90,
        )
        data = r.json()
        if data.get("status_code") == 20000:
            return data
        logger.warning("DataForSEO %s: %s", endpoint, data.get("status_message"))
    except requests.RequestException as e:
        logger.error("DataForSEO request failed: %s", e)
    return None


def _task_result(resp: dict[str, Any] | None) -> dict[str, Any] | None:
    if not resp:
        return None
    tasks = resp.get("tasks") or []
    if not tasks:
        return None
    results = tasks[0].get("result") or []
    if not results:
        return None
    first = results[0]
    return first if isinstance(first, dict) else None


def _normalize_target(target: str) -> str:
    t = (target or "").strip().lower()
    for p in ("https://", "http://", "www."):
        t = t.replace(p, "")
    return t.split("/")[0].split(":")[0]


def fetch_backlinks_summary(target: str) -> dict[str, Any] | None:
    """DataForSEO /v3/backlinks/summary/live — gerçek API."""
    dom = _normalize_target(target)
    if not dom:
        return None
    resp = _post("/v3/backlinks/summary/live", [{"target": dom, "internal_list_limit": 0}])
    data = _task_result(resp)
    if not data:
        return None
    return {
        "target": dom,
        "backlinks": data.get("backlinks") or 0,
        "referring_domains": data.get("referring_domains") or 0,
        "rank": data.get("rank") or 0,
        "simulasyon": False,
        "provider": "dataforseo",
    }


def fetch_backlinks_list(target: str, limit: int = 50) -> list[dict[str, Any]]:
    """DataForSEO /v3/backlinks/backlinks/live — gerçek API."""
    dom = _normalize_target(target)
    if not dom:
        return []
    resp = _post(
        "/v3/backlinks/backlinks/live",
        [{"target": dom, "limit": min(limit, 1000), "order_by": ["rank,desc"]}],
    )
    data = _task_result(resp)
    if not data:
        return []
    items = data.get("items") or []
    links: list[dict[str, Any]] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        links.append({
            "source_url": item.get("url_from") or "",
            "target_url": item.get("url_to") or f"https://{dom}/",
            "domain_from": item.get("domain_from") or "",
            "anchor": item.get("anchor") or "",
            "rank": item.get("domain_from_rank") or item.get("rank") or 0,
            "dofollow": item.get("dofollow", True),
            "simulasyon": False,
            "provider": "dataforseo",
        })
    return links


def fetch_backlinks_payload(target: str, limit: int = 50) -> dict[str, Any] | None:
    """Citation/backlink modülleri için normalize payload."""
    summary = fetch_backlinks_summary(target)
    if not summary:
        return None
    links = fetch_backlinks_list(target, limit=limit)
    dom = _normalize_target(target)
    return {
        "success": True,
        "domain": dom,
        "summary": summary,
        "links": links,
        "provider": "dataforseo",
    }


def backlinks_summary(target: str, provider: str | None = None) -> dict[str, Any]:
    """Provider tercihine göre özet."""
    from .provider_settings import require_dataforseo, should_try_dataforseo
    from .free_provider_clients import get_backlinks_summary

    if should_try_dataforseo("backlink", provider):
        real = fetch_backlinks_summary(target)
        if real:
            return real
        if require_dataforseo("backlink", provider):
            return {**_sim_summary(target), "error": "provider_missing", "provider": "dataforseo"}
    return get_backlinks_summary(target, provider=provider)


def backlinks_list(target: str, limit: int = 50, provider: str | None = None) -> list[dict[str, Any]]:
    from .provider_settings import require_dataforseo, should_try_dataforseo
    from .free_provider_clients import get_backlinks_list

    if should_try_dataforseo("backlink", provider):
        links = fetch_backlinks_list(target, limit=limit)
        if links:
            return links
        if require_dataforseo("backlink", provider):
            return []
    return get_backlinks_list(target, limit=limit, provider=provider)


def _sim_summary(target: str) -> dict[str, Any]:
    from .modul_base import modul_hash, modul_yuzde
    h = modul_hash(target)
    return {
        "target": target,
        "backlinks": 500 + h % 5000,
        "referring_domains": 50 + h % 500,
        "rank": 20 + h % 60,
        "simulasyon": True,
        "uyari": "DataForSEO kimlik bilgisi yok — simülasyon verisi",
    }


def keyword_search_volume(keyword: str, location_code: int = 2792, language_code: str = "tr") -> dict[str, Any] | None:
    """Google Ads arama hacmi, rekabet ve CPC."""
    keyword = (keyword or "").strip()
    if not keyword:
        return None
    resp = _post(
        "/v3/keywords_data/google_ads/search_volume/live",
        [{
            "keywords": [keyword],
            "location_code": location_code,
            "language_code": language_code,
        }],
    )
    if not resp:
        return None
    tasks = resp.get("tasks") or []
    if not tasks or not tasks[0].get("result"):
        return None
    items = tasks[0]["result"]
    if not items:
        return None
    item = items[0]
    return {
        "hacim": item.get("search_volume") or 0,
        "rekabet": item.get("competition") or 0.5,
        "cpc": item.get("cpc") or 0,
        "simulasyon": False,
    }


def _sim_backlinks(target: str, limit: int) -> list[dict[str, Any]]:
    from .modul_base import modul_hash, modul_sec
    h = modul_hash(target)
    domains = ["blogspot.com", "wordpress.com", "medium.com", "reddit.com", "forum.tr", "haber.com"]
    return [
        {
            "source_url": f"https://{modul_sec(f'd{i}_{h}', domains)}/post-{i}",
            "target_url": f"https://{target}/",
            "domain_from": modul_sec(f"df{i}_{h}", domains),
            "anchor": modul_sec(f"a{i}_{h}", ["daha fazla", "incele", target, "tıkla"]),
            "rank": 10 + (h + i) % 80,
            "dofollow": i % 3 != 0,
            "simulasyon": True,
        }
        for i in range(min(limit, 30))
    ]
