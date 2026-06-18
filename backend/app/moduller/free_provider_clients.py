"""
Ücretsiz + opsiyonel DataForSEO SEO/domain provider istemcileri.

Provider zinciri (kullanıcı seçimi: auto | free | dataforseo):
- Domain: agent-domain-service-mcp → whois CLI → DNS
- Backlink: DataForSEO (opsiyonel) → OpenSEO → DataSEO MCP → dataseo_integration cache
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import subprocess
import shutil
from typing import Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger("hive.free_providers")

OPENSEO_URL = os.environ.get("OPENSEO_URL", "http://localhost:3001").rstrip("/")
MCP_DOMAIN_TIMEOUT = int(os.environ.get("MCP_DOMAIN_TIMEOUT", "25"))
MCP_BACKLINK_TIMEOUT = int(os.environ.get("MCP_BACKLINK_TIMEOUT", "45"))


def _normalize_domain(domain: str) -> str:
    d = (domain or "").strip().lower()
    for p in ("https://", "http://", "www."):
        d = d.replace(p, "")
    return d.split("/")[0].split(":")[0]


def _dns_resolves(domain: str) -> bool:
    try:
        socket.getaddrinfo(domain, None, proto=socket.IPPROTO_TCP)
        return True
    except socket.gaierror:
        return False


def _whois_available(domain: str) -> dict[str, Any]:
    """whois CLI — API anahtarı gerektirmez."""
    if not shutil.which("whois"):
        return {"success": False, "error": "whois_not_installed"}
    try:
        proc = subprocess.run(
            ["whois", domain],
            capture_output=True,
            text=True,
            timeout=15,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        low = text.lower()
        available_markers = (
            "no match", "not found", "no entries found", "status: free",
            "no data found", "domain not found", "available for registration",
        )
        taken_markers = (
            "domain name:", "registrar:", "creation date:", "registry domain id:",
        )
        if any(m in low for m in available_markers):
            return {"success": True, "available": True, "provider": "whois", "raw_hint": "available"}
        if any(m in low for m in taken_markers):
            return {"success": True, "available": False, "provider": "whois", "registered": True}
        if _dns_resolves(domain):
            return {"success": True, "available": False, "provider": "whois+dns", "registered": True}
        return {"success": True, "available": True, "provider": "whois", "uncertain": True}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "whois_timeout"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _mcp_check_domain(domain: str) -> dict[str, Any] | None:
    """agent-domain-service-mcp — npx ile, API key yok."""
    if not shutil.which("npx"):
        return None
    cmd = ["npx", "-y", "agent-domain-service-mcp", "check_domain", domain]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=MCP_DOMAIN_TIMEOUT)
        if proc.returncode != 0:
            logger.debug("mcp domain fail: %s", proc.stderr[:200])
            return None
        out = (proc.stdout or "").strip()
        if not out:
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {"domain": domain, "raw": out, "available": "available" in out.lower()}
        data.setdefault("provider", "agent-domain-service-mcp")
        data["success"] = True
        return data
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.debug("mcp domain: %s", exc)
        return None


def check_domain(domain: str, provider: str | None = None) -> dict[str, Any]:
    """Tek domain müsaitlik — DataForSEO domain sorgu yapmaz, free zincir kullanılır."""
    from .provider_settings import resolve_mode
    dom = _normalize_domain(domain)
    if not dom or "." not in dom:
        return {"success": False, "error": "invalid_domain", "domain": domain}
    _ = resolve_mode("domain", provider)

    mcp = _mcp_check_domain(dom)
    if mcp and mcp.get("success"):
        avail = mcp.get("available")
        if avail is None:
            avail = mcp.get("is_available")
        if avail is None and "status" in mcp:
            avail = str(mcp["status"]).lower() in ("available", "free", "unregistered")
        return {
            "success": True,
            "domain": dom,
            "available": bool(avail) if avail is not None else not _dns_resolves(dom),
            "provider": mcp.get("provider", "agent-domain-service-mcp"),
            "details": mcp,
        }

    whois = _whois_available(dom)
    if whois.get("success"):
        return {
            "success": True,
            "domain": dom,
            "available": whois.get("available", False),
            "provider": whois.get("provider", "whois"),
            "details": whois,
        }

    resolves = _dns_resolves(dom)
    return {
        "success": True,
        "domain": dom,
        "available": not resolves,
        "provider": "dns",
        "registered": resolves,
        "details": {"dns_resolves": resolves},
    }


def check_bulk_domains(domains: list[str], provider: str | None = None) -> list[dict[str, Any]]:
    """Toplu domain sorgusu (max 50)."""
    out: list[dict] = []
    for dom in (domains or [])[:50]:
        out.append(check_domain(dom, provider=provider))
    return out


def _openseo_backlinks(domain: str, limit: int = 50) -> dict[str, Any] | None:
    """OpenSEO Docker / HTTP API."""
    dom = _normalize_domain(domain)
    endpoints = (
        f"{OPENSEO_URL}/api/backlinks",
        f"{OPENSEO_URL}/api/v1/backlinks",
        f"{OPENSEO_URL}/backlinks",
    )
    for url in endpoints:
        try:
            r = requests.get(url, params={"domain": dom, "limit": limit}, timeout=12)
            if r.status_code != 200:
                continue
            data = r.json()
            if isinstance(data, dict) and (data.get("backlinks") or data.get("items") or data.get("backlinks_list")):
                data["provider"] = "openseo"
                data["success"] = True
                return data
        except Exception as exc:
            logger.debug("openseo %s: %s", url, exc)
    try:
        r = requests.get(f"{OPENSEO_URL}/api/health", timeout=5)
        if r.status_code == 200:
            logger.debug("openseo health ok but backlinks endpoint missing for %s", dom)
    except Exception:
        pass
    return None


def _dataseo_mcp_backlinks(domain: str, limit: int = 50) -> dict[str, Any] | None:
    """DataSEO MCP subprocess veya yerel third_party modül."""
    dom = _normalize_domain(domain)

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
                return _normalize_dataseo_payload(dom, res, limit, provider="dataseo_mcp_local")
        except Exception as exc:
            logger.debug("dataseo local: %s", exc)

    if shutil.which("npx"):
        cmd = ["npx", "-y", "dataseo-mcp", "backlinks", dom]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=MCP_BACKLINK_TIMEOUT)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                return _normalize_dataseo_payload(dom, data, limit, provider="dataseo_mcp")
        except Exception as exc:
            logger.debug("dataseo npx: %s", exc)
    return None


def _dataseo_integration_backlinks(domain: str, limit: int = 50) -> dict[str, Any]:
    """HIVE dataseo_integration — ücretsiz, cache'li."""
    from .dataseo_integration import dataseo_backlinks
    raw = dataseo_backlinks(domain)
    return _normalize_dataseo_payload(domain, raw, limit, provider="dataseo_free")


def _normalize_dataseo_payload(domain: str, raw: dict, limit: int, provider: str) -> dict[str, Any]:
    dom = _normalize_domain(domain)
    overview = raw.get("overview") or raw.get("backlinks_overview") or {}
    if isinstance(overview, list) and overview:
        overview = overview[0] if isinstance(overview[0], dict) else {}

    links_raw = (
        raw.get("backlinks")
        or raw.get("backlinks_list")
        or raw.get("items")
        or []
    )
    links: list[dict] = []
    for ln in links_raw[:limit]:
        if not isinstance(ln, dict):
            continue
        links.append({
            "source_url": ln.get("url_from") or ln.get("urlFrom") or ln.get("source_url") or "",
            "target_url": ln.get("url_to") or ln.get("urlTo") or ln.get("target_url") or f"https://{dom}/",
            "domain_from": ln.get("domain_from") or _host_from_url(ln.get("url_from") or ln.get("urlFrom") or ""),
            "anchor": ln.get("anchor") or "",
            "rank": ln.get("domain_rating") or ln.get("domainRating") or ln.get("rank") or 0,
            "dofollow": ln.get("dofollow", True),
            "simulasyon": ln.get("simulasyon", provider == "dataseo_free"),
        })

    summary = {
        "target": dom,
        "backlinks": overview.get("backlinks") or overview.get("backlinks_total") or len(links),
        "referring_domains": overview.get("referring_domains") or overview.get("refDomains") or overview.get("referring_domains_count") or 0,
        "rank": overview.get("domain_rating") or overview.get("domainRating") or overview.get("rank") or 0,
        "simulasyon": overview.get("simulasyon", provider == "dataseo_free"),
        "provider": provider,
    }
    return {"success": True, "domain": dom, "summary": summary, "links": links, "provider": provider}


def _host_from_url(url: str) -> str:
    try:
        return urlparse(url if "://" in url else f"https://{url}").netloc
    except Exception:
        return ""


def _dataforseo_backlinks(domain: str, limit: int = 50) -> dict[str, Any] | None:
    """DataForSEO — yapılandırılmışsa gerçek backlink verisi."""
    try:
        from .dataforseo_client import fetch_backlinks_payload, is_configured
        if not is_configured():
            return None
        return fetch_backlinks_payload(domain, limit=limit)
    except Exception as exc:
        logger.debug("dataforseo backlinks: %s", exc)
        return None


def get_backlinks(domain: str, limit: int = 50, provider: str | None = None) -> dict[str, Any]:
    """Provider tercihine göre backlink zinciri."""
    from .provider_settings import provider_chain, require_dataforseo, resolve_mode

    dom = _normalize_domain(domain)
    if not dom:
        return {"success": False, "error": "domain_required"}

    chain = provider_chain("backlink", provider)
    fn_map = {
        "dataforseo": _dataforseo_backlinks,
        "openseo": _openseo_backlinks,
        "dataseo_mcp": _dataseo_mcp_backlinks,
    }

    for pid in chain:
        if pid == "dataseo_free":
            res = _dataseo_integration_backlinks(dom, limit=limit)
        elif pid in fn_map:
            res = fn_map[pid](dom, limit=limit)
        else:
            continue
        if res and res.get("success"):
            if res.get("links") or pid == "dataforseo":
                res["provider_mode"] = resolve_mode("backlink", provider)
                return res

    if require_dataforseo("backlink", provider):
        return {
            "success": False,
            "error": "provider_missing",
            "message": "DataForSEO seçildi — DATAFORSEO_LOGIN ve DATAFORSEO_PASSWORD gerekli",
            "provider": "dataforseo",
        }

    res = _dataseo_integration_backlinks(dom, limit=limit)
    res["fallback"] = True
    res["provider_mode"] = resolve_mode("backlink", provider)
    return res


def get_backlinks_list(domain: str, limit: int = 50, provider: str | None = None) -> list[dict[str, Any]]:
    """backlink_hunter uyumlu liste."""
    res = get_backlinks(domain, limit=limit, provider=provider)
    return res.get("links") or []


def get_backlinks_summary(domain: str, provider: str | None = None) -> dict[str, Any]:
    """competitor_hijacker uyumlu özet."""
    res = get_backlinks(domain, limit=5, provider=provider)
    s = res.get("summary") or {}
    return {
        "target": _normalize_domain(domain),
        "backlinks": s.get("backlinks", 0) or len(res.get("links") or []),
        "referring_domains": s.get("referring_domains", 0),
        "rank": s.get("rank", 0),
        "simulasyon": s.get("simulasyon", res.get("provider") == "dataseo_free"),
        "provider": res.get("provider", "free"),
    }


def provider_health() -> dict[str, Any]:
    """Tüm provider durumu + kullanıcı tercihleri."""
    from .provider_settings import get_settings, health as ps_health

    domain_ok = bool(shutil.which("npx")) or bool(shutil.which("whois"))
    openseo_ok = False
    try:
        r = requests.get(f"{OPENSEO_URL}/api/health", timeout=4)
        openseo_ok = r.status_code == 200
    except Exception:
        pass
    dfs_ok = False
    try:
        from .dataforseo_client import is_configured
        dfs_ok = is_configured()
    except Exception:
        pass
    prefs = get_settings()
    return {
        "domain_mcp": bool(shutil.which("npx")),
        "whois": bool(shutil.which("whois")),
        "openseo_url": OPENSEO_URL,
        "openseo_live": openseo_ok,
        "dataseo_mcp": bool(shutil.which("npx")),
        "dataseo_integration": True,
        "dataforseo": dfs_ok,
        "dataforseo_configured": dfs_ok,
        "namecheap_required": False,
        "dataforseo_required": False,
        "domain_ready": domain_ok,
        "backlink_ready": dfs_ok or openseo_ok or True,
        "provider_settings": prefs,
        "backlink_chain": ps_health().get("categories", {}).get("backlink", {}).get("chain", []),
    }
