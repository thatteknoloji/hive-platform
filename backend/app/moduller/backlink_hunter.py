"""Backlink Hunter — OpenSEO (localhost:3001) + DataSEO MCP yedek."""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import shutil
import subprocess
from typing import Any
from urllib.parse import urlparse

import requests

from .backlink_hub import add_opportunities, get_opportunities, log_activity
from .modul_base import modul_export_json, simdi

logger = logging.getLogger("hive.backlink_hunter")

OPENSEO_URL = os.environ.get("OPENSEO_URL", "http://localhost:3001").rstrip("/")
MCP_BACKLINK_TIMEOUT = int(os.environ.get("MCP_BACKLINK_TIMEOUT", "45"))


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    for p in ("https://", "http://", "www."):
        d = d.replace(p, "")
    return d.split("/")[0].split(":")[0]


def _host_from_url(url: str) -> str:
    try:
        return urlparse(url if "://" in url else f"https://{url}").netloc
    except Exception:
        return ""


def _normalize_links(raw: dict[str, Any], domain: str, provider: str, limit: int) -> dict[str, Any]:
    dom = _normalize_domain(domain)
    overview = raw.get("overview") or raw.get("backlinks_overview") or raw.get("summary") or {}
    if isinstance(overview, list) and overview:
        overview = overview[0] if isinstance(overview[0], dict) else {}

    links_raw = (
        raw.get("backlinks")
        or raw.get("backlinks_list")
        or raw.get("items")
        or raw.get("links")
        or []
    )
    links: list[dict] = []
    for ln in links_raw[:limit]:
        if not isinstance(ln, dict):
            continue
        links.append({
            "source_url": ln.get("url_from") or ln.get("urlFrom") or ln.get("source_url") or ln.get("url") or "",
            "target_url": ln.get("url_to") or ln.get("urlTo") or ln.get("target_url") or f"https://{dom}/",
            "domain_from": ln.get("domain_from") or _host_from_url(ln.get("url_from") or ln.get("urlFrom") or ln.get("source_url") or ""),
            "anchor": ln.get("anchor") or ln.get("anchor_text") or "",
            "rank": ln.get("domain_rating") or ln.get("domainRating") or ln.get("rank") or 0,
            "dofollow": ln.get("dofollow", True),
            "provider": provider,
        })

    summary = {
        "target": dom,
        "backlinks": overview.get("backlinks") or overview.get("backlinks_total") or len(links),
        "referring_domains": overview.get("referring_domains") or overview.get("refDomains") or overview.get("referring_domains_count") or 0,
        "rank": overview.get("domain_rating") or overview.get("domainRating") or overview.get("rank") or 0,
        "provider": provider,
    }
    return {
        "success": True,
        "domain": dom,
        "summary": summary,
        "links": links,
        "backlinks": links,
        "provider": provider,
        "count": len(links),
    }


def _openseo_backlinks(domain: str, limit: int = 50) -> dict[str, Any] | None:
    """OpenSEO HTTP API — http://localhost:3001"""
    dom = _normalize_domain(domain)
    if not dom:
        return None

    endpoints = [
        (f"{OPENSEO_URL}/api/backlinks", {"domain": dom, "limit": limit}),
        (f"{OPENSEO_URL}/api/v1/backlinks", {"domain": dom, "limit": limit}),
        (f"{OPENSEO_URL}/backlinks", {"domain": dom, "limit": limit}),
        (f"{OPENSEO_URL}/api/backlinks/overview", {"target": dom, "limit": limit}),
    ]
    for url, params in endpoints:
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code != 200:
                continue
            data = r.json()
            if not isinstance(data, dict):
                continue
            if data.get("backlinks") or data.get("items") or data.get("links") or data.get("backlinks_list"):
                return _normalize_links(data, dom, "openseo", limit)
        except Exception as exc:
            logger.debug("openseo %s: %s", url, exc)

    try:
        r = requests.post(
            f"{OPENSEO_URL}/api/backlinks/lookup",
            json={"target": dom, "limit": limit},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                return _normalize_links(data, dom, "openseo", limit)
    except Exception as exc:
        logger.debug("openseo post lookup: %s", exc)

    return None


def _dataseo_mcp_backlinks(domain: str, limit: int = 50) -> dict[str, Any] | None:
    """DataSEO MCP — npx veya yerel modül."""
    dom = _normalize_domain(domain)
    if not dom:
        return None

    local_mcp = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "..", "third_party", "dataseo-mcp", "src",
    )
    if os.path.isdir(local_mcp):
        try:
            import sys
            if local_mcp not in sys.path:
                sys.path.insert(0, local_mcp)
            from seo_mcp import services  # type: ignore
            res = services.get_backlinks_list(dom)
            if res and isinstance(res, dict):
                return _normalize_links(res, dom, "dataseo_mcp", limit)
        except Exception as exc:
            logger.debug("dataseo local mcp: %s", exc)

    if shutil.which("npx"):
        cmd = ["npx", "-y", "dataseo-mcp", "backlinks", dom]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=MCP_BACKLINK_TIMEOUT)
            if proc.returncode == 0 and (proc.stdout or "").strip():
                data = json.loads(proc.stdout)
                return _normalize_links(data, dom, "dataseo_mcp", limit)
        except Exception as exc:
            logger.debug("dataseo npx mcp: %s", exc)

    return None


def get_backlinks(domain: str, limit: int = 50) -> dict[str, Any]:
    """OpenSEO → DataSEO MCP zinciri — gerçek API, simülasyon yok."""
    dom = _normalize_domain(domain)
    if not dom:
        return {"success": False, "error": "domain_required"}

    openseo = _openseo_backlinks(dom, limit=limit)
    if openseo and openseo.get("success"):
        openseo["query_type"] = "backlinks"
        return openseo

    dataseo = _dataseo_mcp_backlinks(dom, limit=limit)
    if dataseo and dataseo.get("success"):
        dataseo["query_type"] = "backlinks"
        dataseo["fallback_from"] = "openseo"
        return dataseo

    return {
        "success": False,
        "error": "provider_unavailable",
        "message": f"OpenSEO ({OPENSEO_URL}) ve DataSEO MCP erişilemedi",
        "domain": dom,
        "hint": "OpenSEO Docker'ı başlatın veya npx dataseo-mcp kurulu olduğundan emin olun",
    }


def get_competitor_backlinks(domain: str, limit: int = 50) -> dict[str, Any]:
    """Rakip domain backlink listesi — aynı provider zinciri."""
    res = get_backlinks(domain, limit=limit)
    if res.get("success"):
        res["query_type"] = "competitor_backlinks"
        res["competitor_domain"] = _normalize_domain(domain)
    return res


def health() -> dict[str, Any]:
    openseo_ok = False
    try:
        r = requests.get(f"{OPENSEO_URL}/api/health", timeout=4)
        openseo_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status": "aktif",
        "module": "backlink_hunter",
        "openseo_url": OPENSEO_URL,
        "openseo_live": openseo_ok,
        "dataseo_mcp": bool(shutil.which("npx")),
        "api_key_required": False,
        "free_stack": True,
        "providers": ["openseo", "dataseo_mcp"],
    }


def opportunities(
    competitors: list[str] | None = None,
    our_domain: str = "",
    limit: int = 50,
    provider: str | None = None,
) -> dict[str, Any]:
    _ = provider  # legacy param — always free stack
    competitors = competitors or ["example.com"]
    our_domain = our_domain.replace("https://", "").replace("http://", "").strip("/")
    all_items: list[dict] = []
    providers_used: set[str] = set()

    for comp in competitors[:5]:
        comp = comp.replace("https://", "").replace("http://", "").strip("/")
        res = get_competitor_backlinks(comp, limit=limit)
        if not res.get("success"):
            continue
        providers_used.add(res.get("provider", "unknown"))
        for ln in res.get("links") or []:
            if our_domain in (ln.get("target_url") or ""):
                continue
            ln["rakip"] = comp
            ln["firsat_tipi"] = "rakip_backlink"
            ln["oncelik"] = ln.get("rank", 0)
            ln["kaynak_provider"] = ln.get("provider") or res.get("provider")
            all_items.append(ln)

    added = add_opportunities(all_items, kaynak="backlink_hunter")
    out = {
        "status": "aktif",
        "toplam": len(all_items),
        "yeni_eklenen": added,
        "firsatlar": all_items[:limit],
        "provider": list(providers_used) or ["openseo", "dataseo_mcp"],
        "openseo": "openseo" in providers_used,
        "dataseo_mcp": "dataseo_mcp" in providers_used,
        "free_stack": True,
        "tarih": simdi(),
    }
    log_activity("backlink_hunter", "Backlink Hunter - Fırsatlar", {"competitors": competitors}, out)
    return out


def export_opportunities(fmt: str = "json") -> dict[str, Any]:
    items = get_opportunities(500)
    if fmt == "csv":
        buf = io.StringIO()
        if items:
            keys = list(items[0].keys())
            w = csv.DictWriter(buf, fieldnames=keys)
            w.writeheader()
            w.writerows(items)
        content = buf.getvalue()
        return {"status": "aktif", "format": "csv", "content": content, "satir": len(items)}
    return modul_export_json(items, "backlink_opportunities")
