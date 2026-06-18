"""Competitor Backlink Hijacker — ücretsiz backlink analizi."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .backlink_hub import add_opportunities, log_activity
from .free_provider_clients import get_backlinks, get_backlinks_summary, provider_health
from .modul_base import simdi


def get_competitor_backlinks(domain: str, limit: int = 100, provider: str | None = None) -> dict[str, Any]:
    return get_backlinks(domain, limit=limit, provider=provider)


def health() -> dict[str, Any]:
    ph = provider_health()
    from .provider_settings import get_settings, health as ps
    prefs = get_settings()
    return {
        "status": "aktif",
        "module": "competitor_hijacker",
        "providers": ph,
        "dataforseo": ph.get("dataforseo_configured", False),
        "provider_mode": prefs.get("backlink", "auto"),
        "provider_settings": ps().get("categories", {}).get("backlink"),
    }


def analyze_competitor(
    domain: str = "",
    send_to_hunter: bool = True,
    limit: int = 100,
    provider: str | None = None,
) -> dict[str, Any]:
    domain = domain.replace("https://", "").replace("http://", "").strip("/")
    if not domain:
        return {"status": "hata", "hata": "Rakip domain gerekli"}

    summary = get_backlinks_summary(domain, provider=provider)
    full = get_backlinks(domain, limit=limit, provider=provider)
    links = full.get("links") or []

    domain_counts = Counter(ln.get("domain_from", "") for ln in links if ln.get("domain_from"))
    page_counts = Counter(ln.get("target_url", "") for ln in links if ln.get("target_url"))
    top_domains = [{"domain": d, "adet": c} for d, c in domain_counts.most_common(15)]
    top_pages = [{"url": u, "adet": c} for u, c in page_counts.most_common(10)]

    opportunities = []
    for ln in links:
        opportunities.append({
            **ln,
            "rakip": domain,
            "firsat_tipi": "competitor_backlink",
            "oncelik": ln.get("rank", 0),
        })

    forwarded = 0
    if send_to_hunter and opportunities:
        forwarded = add_opportunities(opportunities, kaynak="competitor_hijacker")

    ph = provider_health()
    from .provider_settings import resolve_mode
    mode = resolve_mode("backlink", provider)
    out = {
        "status": "aktif",
        "domain": domain,
        "ozet": summary,
        "top_referring_domains": top_domains,
        "top_linked_pages": top_pages,
        "backlink_sayisi": len(links),
        "hunter_a_aktarilan": forwarded,
        "provider": full.get("provider", "free"),
        "provider_mode": mode,
        "openseo": ph.get("openseo_live", False),
        "dataforseo": ph.get("dataforseo_configured", False),
        "free_stack": mode == "free",
        "ornek_backlinkler": links[:20],
        "tarih": simdi(),
    }
    log_activity("competitor_hijacker", "Competitor Hijacker - Analiz", {"domain": domain}, out)
    return out
