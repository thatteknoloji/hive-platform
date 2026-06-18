"""Talon V2 provider base — normalize edilmiş sonuç formatı."""

from __future__ import annotations

import logging
from typing import Any, Literal

import requests

from app import config

logger = logging.getLogger("hive.talon.providers")

Source = Literal["searxng", "tavily", "exa", "autocomplete", "paa", "osm"]

DEFAULT_TIMEOUT = 15
USER_AGENT = "HIVE-Talon/2.0 (BalKutusu SEO; contact@balkutusu.com)"


_ENV_SQLITE_MAP = {
    "TAVILY_API_KEY": "tavily",
    "EXA_API_KEY": "exa",
    "SEARXNG_URL": "searxng_url",
    "OPENROUTER_API_KEY": "openrouter",
}


def env(key: str, default: str = "") -> str:
    val = (config.get(key) or "").strip()
    if val:
        return val
    sqlite_svc = _ENV_SQLITE_MAP.get(key)
    if sqlite_svc:
        from app.moduller.talon_db import api_key_getir
        db_val = (api_key_getir(sqlite_svc) or "").strip()
        if db_val:
            return db_val
    return default


def safe_get(url: str, **kwargs) -> requests.Response | None:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    try:
        r = requests.get(url, headers=headers, timeout=kwargs.pop("timeout", DEFAULT_TIMEOUT), **kwargs)
        return r
    except requests.RequestException as e:
        logger.debug("GET %s failed: %s", url[:80], type(e).__name__)
        return None


def safe_post(url: str, **kwargs) -> requests.Response | None:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    try:
        r = requests.post(url, headers=headers, timeout=kwargs.pop("timeout", DEFAULT_TIMEOUT), **kwargs)
        return r
    except requests.RequestException as e:
        logger.debug("POST %s failed: %s", url[:80], type(e).__name__)
        return None


def make_result(
    source: str,
    query: str,
    *,
    title: str = "",
    url: str = "",
    snippet: str = "",
    highlights: list[str] | None = None,
    answer: str = "",
    keyword: str = "",
    location: dict | None = None,
    raw: dict | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "query": query,
        "title": title or None,
        "url": url or None,
        "snippet": snippet or None,
        "highlights": highlights or [],
        "answer": answer or None,
        "keyword": keyword or None,
        "location": location,
        "raw": raw,
    }


def provider_health() -> dict[str, str]:
    return {
        "searxng": "configured" if env("SEARXNG_URL") else "missing",
        "tavily": "configured" if env("TAVILY_API_KEY") else "missing",
        "exa": "configured" if env("EXA_API_KEY") else "missing",
        "openstreetmap": "available",
        "autocomplete": "available",
        "paa": "available",
        "legacy_dataforseo": "configured" if env("DATAFORSEO_LOGIN") and env("DATAFORSEO_PASSWORD") else "deprecated",
        "legacy_serpapi": "configured" if env("SERPAPI_KEY") else "deprecated",
        "openrouter": "configured" if env("OPENROUTER_API_KEY") else "missing",
    }


NormalizedResult = dict[str, Any]
