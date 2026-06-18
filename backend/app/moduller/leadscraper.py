# -*- coding: utf-8 -*-
"""Lead Scraper - URL veya arama sonuclarindan e-posta/telefon toplama."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .modul_base import modul_export_csv, modul_export_json, simdi
from .scrape_utils import fetch_html, normalize_url, parse_page

STATE_FILE = Path(__file__).resolve().parent.parent / "leadscraper_state.json"


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("runs", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"runs": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _search_urls(query: str, limit: int) -> tuple[list[str], str, str | None]:
    from app.moduller.talon_stack.providers.searxng_provider import SearXNGProvider
    from app.moduller.talon_stack.providers.tavily_provider import TavilyProvider

    if SearXNGProvider.is_configured():
        results = SearXNGProvider.search(query, num_results=limit)
        urls = [r.get("url") for r in results if r.get("url")]
        if urls:
            return urls, "searxng", None

    if TavilyProvider.is_configured():
        results = TavilyProvider.search(query, num_results=limit)
        urls = [r.get("url") for r in results if r.get("url")]
        if urls:
            return urls, "tavily", None

    return [], "", "Arama icin SEARXNG_URL veya TAVILY_API_KEY gerekli ? veya dogrudan URL verin"


def _scrape_leads_from_url(page_url: str) -> list[dict[str, Any]]:
    leads: list[dict[str, Any]] = []
    html, err = fetch_html(page_url)
    if err or not html:
        return leads
    parsed = parse_page(html, page_url)
    title = parsed.get("title") or page_url
    for email in parsed.get("emails") or []:
        leads.append({
            "type": "email",
            "value": email,
            "source_url": page_url,
            "page_title": title,
        })
    for phone in parsed.get("phones") or []:
        leads.append({
            "type": "phone",
            "value": phone,
            "source_url": page_url,
            "page_title": title,
        })
    contact_hints = [l["href"] for l in parsed.get("links") or [] if _is_contact_link(l)]
    for extra in contact_hints[:3]:
        if extra == page_url:
            continue
        html2, err2 = fetch_html(extra)
        if err2 or not html2:
            continue
        p2 = parse_page(html2, extra)
        for email in p2.get("emails") or []:
            leads.append({
                "type": "email",
                "value": email,
                "source_url": extra,
                "page_title": p2.get("title") or extra,
            })
        for phone in p2.get("phones") or []:
            leads.append({
                "type": "phone",
                "value": phone,
                "source_url": extra,
                "page_title": p2.get("title") or extra,
            })
    return leads


def _is_contact_link(link: dict[str, str]) -> bool:
    href = (link.get("href") or "").lower()
    text = (link.get("text") or "").lower()
    keys = ("contact", "iletisim", "about", "hakkimizda", "bize-ulasin")
    return any(k in href or k in text for k in keys)


def health() -> dict[str, Any]:
    from app.moduller.talon_stack.providers.searxng_provider import SearXNGProvider
    from app.moduller.talon_stack.providers.tavily_provider import TavilyProvider

    return {
        "success": True,
        "module": "leadscraper",
        "searxng": SearXNGProvider.is_configured(),
        "tavily": TavilyProvider.is_configured(),
        "ready": True,
        "note": "Dogrudan URL ile her zaman calisir; anahtar kelime aramasi icin SearXNG veya Tavily gerekir",
    }


def topla(kelime: str = "", adet: int = 50, url: str = "") -> dict[str, Any]:
    try:
        limit = max(1, min(50, int(adet or 50)))
        leads: list[dict[str, Any]] = []
        kaynak = ""
        search_error = None

        if url:
            target = normalize_url(url)
            if not target:
                return {"status": "hata", "hata": "URL gecersiz", "mesaj": "Gecerli bir http(s) URL girin"}
            urls = [target]
            kaynak = "direct_url"
        elif kelime:
            urls, kaynak, search_error = _search_urls(kelime.strip(), min(limit, 15))
            if not urls:
                return {
                    "status": "hata",
                    "hata": "provider_missing",
                    "mesaj": search_error or "Arama sonucu bulunamadi",
                    "kelime": kelime,
                }
        else:
            return {"status": "hata", "hata": "keyword veya url gerekli"}

        seen: set[tuple[str, str]] = set()
        scraped_pages = 0
        for page_url in urls:
            if len(leads) >= limit:
                break
            page_leads = _scrape_leads_from_url(page_url)
            scraped_pages += 1
            for lead in page_leads:
                key = (lead["type"], lead["value"].lower())
                if key in seen:
                    continue
                seen.add(key)
                leads.append(lead)
                if len(leads) >= limit:
                    break

        run = {
            "kelime": kelime or None,
            "url": url or None,
            "bulunan_lead": len(leads),
            "kaynak": kaynak,
            "scraped_pages": scraped_pages,
            "at": simdi(),
        }
        st = _load_state()
        st.setdefault("runs", []).insert(0, run)
        st["runs"] = st["runs"][:100]
        _save_state(st)

        return {
            "success": True,
            "kelime": kelime or "",
            "url": url or "",
            "bulunan_lead": len(leads),
            "leads": leads,
            "kaynak": kaynak,
            "scraped_pages": scraped_pages,
            "durum": f"{len(leads)} lead bulundu ({kaynak})",
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def export_leads(kelime: str = "", adet: int = 50, url: str = "", format: str = "csv") -> dict[str, Any]:
    res = topla(kelime=kelime, adet=adet, url=url)
    if res.get("status") == "hata":
        return res
    rows = res.get("leads") or []
    if format == "json":
        return {"format": "json", "icerik": modul_export_json(rows), "count": len(rows)}
    return {"format": "csv", "icerik": modul_export_csv(rows), "count": len(rows)}
