"""
Data Miner Engine V1 — keşif ve veri çıkarımı (içerik üretmez, yayın yapmaz).

Provider zinciri: ScrapeGraphAI → Playwright → BeautifulSoup
Opsiyonel: Firecrawl adapter (hazırlık)
Arama: SearXNG / Tavily (keyword miner)
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .modul_base import modul_export_csv, modul_export_json, simdi
from .scrape_utils import fetch_html, normalize_url, parse_page, extract_contacts

logger = logging.getLogger("hive.data_miner")

STATE_FILE = Path(__file__).resolve().parent.parent / "data_miner_engine_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"

MAX_JOBS = 500
MAX_PAGES_KEYWORD = 8
MAX_PAGES_DOMAIN = 12

BRAIN_EVENTS = ("data_mining_started", "data_mining_completed", "data_entity_discovered")

ADDRESS_RE = re.compile(
    r"(?:mah\.?|mahalle|cad\.?|cadde|sok\.?|sokak|bulvar|blv\.?)[\w\s\.,\-/]{5,80}",
    re.I,
)

RECOMMENDED_SCHEMA_TYPES = frozenset({
    "Organization", "LocalBusiness", "FAQPage", "WebSite", "BreadcrumbList", "Product", "Service",
})

DEFAULT_STATE: dict[str, Any] = {
    "settings": {
        "engine_preference": "auto",
        "max_pages_per_job": 10,
        "use_playwright_fallback": True,
        "firecrawl_enabled": False,
        "respect_robots": True,
    },
    "jobs": {},
    "datasets": [],
}


# ── State ─────────────────────────────────────────────────────────────────────

def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_job_id() -> str:
    return f"dm-{uuid.uuid4().hex[:12]}"


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("settings", dict(DEFAULT_STATE["settings"]))
                data.setdefault("jobs", {})
                data.setdefault("datasets", [])
                return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("data_miner state load failed: %s", exc)
    return json.loads(json.dumps(DEFAULT_STATE))


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _emit_brain(event_type: str, *, domain: str = "", keyword: str = "", result: dict | None = None) -> None:
    if event_type not in BRAIN_EVENTS:
        return
    try:
        from app.moduller.hive_brain_engine import hive_brain
        hive_brain.record_event(
            event_type,
            "data_miner_engine",
            domain=domain,
            keyword=keyword,
            status="ok",
            result=result or {},
        )
    except Exception as exc:
        logger.debug("brain event skip: %s", exc)


# ── Providers ─────────────────────────────────────────────────────────────────

def _scrapegraph_enabled() -> bool:
    val = os.environ.get("SCRAPEGRAPH_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no", "off")


def _scrapegraph_installed() -> bool:
    try:
        import scrapegraphai  # noqa: F401
        return True
    except ImportError:
        return False


def _llm_configured() -> tuple[bool, str]:
    if not _scrapegraph_enabled():
        return False, "disabled"
    provider = (os.environ.get("SCRAPEGRAPH_LLM_PROVIDER") or "").strip().lower()
    if provider == "none":
        return False, "llm_provider_missing"

    api_key = (
        os.environ.get("SCRAPEGRAPH_API_KEY")
        or os.environ.get("SCRAPEGRAPH_LLM_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

    if provider == "openrouter":
        return (True, "openrouter") if openrouter_key or api_key else (False, "llm_provider_missing")
    if provider == "openai":
        return (True, "openai") if api_key else (False, "llm_provider_missing")
    if provider == "ollama":
        return _ollama_reachable()

    if api_key:
        return True, "openai"
    if openrouter_key:
        return True, "openrouter"
    if os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_URL") or os.environ.get("SCRAPEGRAPH_OLLAMA_MODEL"):
        return _ollama_reachable()
    return False, "llm_provider_missing"


def _ollama_reachable() -> tuple[bool, str]:
    base = (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_URL")
        or "http://localhost:11434"
    ).rstrip("/")
    try:
        import requests
        r = requests.get(f"{base}/api/tags", timeout=2)
        if r.status_code == 200:
            return True, "ollama"
    except Exception:
        pass
    if os.environ.get("SCRAPEGRAPH_OLLAMA_MODEL"):
        return True, "ollama"
    return False, "llm_provider_missing"


def _scrapegraph_ready() -> tuple[bool, str]:
    if not _scrapegraph_installed():
        return False, "package_not_installed"
    if not _scrapegraph_enabled():
        return False, "disabled"
    ok, reason = _llm_configured()
    if not ok:
        return False, reason
    return True, "ok"


def _scrapegraph_llm_config() -> dict[str, Any]:
    _, provider = _llm_configured()
    model = os.environ.get("SCRAPEGRAPH_MODEL") or os.environ.get("SCRAPEGRAPH_LLM_MODEL", "gpt-4o-mini")
    if provider == "openrouter":
        return {
            "api_key": os.environ.get("SCRAPEGRAPH_API_KEY") or os.environ.get("OPENROUTER_API_KEY"),
            "model": model if "/" in model else f"openai/{model}",
            "base_url": "https://openrouter.ai/api/v1",
        }
    if provider == "openai":
        return {
            "api_key": (
                os.environ.get("SCRAPEGRAPH_API_KEY")
                or os.environ.get("SCRAPEGRAPH_LLM_KEY")
                or os.environ.get("OPENAI_API_KEY")
            ),
            "model": model,
        }
    base = (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_URL")
        or "http://localhost:11434"
    ).rstrip("/")
    ollama_model = os.environ.get("SCRAPEGRAPH_OLLAMA_MODEL", "ollama/llama3")
    if not ollama_model.startswith("ollama/"):
        ollama_model = f"ollama/{ollama_model}"
    return {"model": ollama_model, "base_url": base, "temperature": 0, "format": "json"}


def _scrapegraph_available() -> tuple[bool, str]:
    """Backward-compatible: package installed = available."""
    if _scrapegraph_installed():
        return True, "ok"
    return False, "provider_missing"


def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


def _beautifulsoup_available() -> bool:
    try:
        import bs4  # noqa: F401
        return True
    except ImportError:
        return False


def _firecrawl_configured() -> bool:
    return bool(os.environ.get("FIRECRAWL_API_KEY", "").strip())


def _firecrawl_scrape(url: str) -> dict[str, Any]:
    """Firecrawl adapter hazırlığı — API key yoksa provider_missing."""
    api_key = os.environ.get("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        return {"success": False, "provider": "firecrawl", "error": "provider_missing"}
    try:
        import requests
        r = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"url": url, "formats": ["html", "markdown"]},
            timeout=45,
        )
        if r.status_code != 200:
            return {"success": False, "provider": "firecrawl", "error": f"http_{r.status_code}"}
        data = r.json()
        html = (data.get("data") or {}).get("html") or ""
        if not html:
            return {"success": False, "provider": "firecrawl", "error": "empty_html"}
        return {"success": True, "provider": "firecrawl", "html": html, "url": url}
    except Exception as exc:
        return {"success": False, "provider": "firecrawl", "error": str(exc)}


def _scrapegraph_extract(url: str, prompt: str = "") -> dict[str, Any]:
    ready, reason = _scrapegraph_ready()
    if not ready:
        return {"success": False, "provider": "scrapegraphai", "error": "provider_missing", "reason": reason}
    try:
        from scrapegraphai.graphs import SmartScraperGraph  # type: ignore
        graph_config = {
            "llm": _scrapegraph_llm_config(),
            "verbose": False,
            "headless": True,
        }
        extraction_prompt = prompt or (
            "Extract and return JSON with keys: entities (list of {label,type}), faqs (list of "
            "{question,answer}), phones, emails, addresses, schema_types, services, products."
        )
        graph = SmartScraperGraph(prompt=extraction_prompt, source=url, config=graph_config)
        raw = graph.run()
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                pass
        return {"success": True, "provider": "scrapegraphai", "raw": raw, "url": url}
    except Exception as exc:
        logger.warning("scrapegraphai failed %s: %s", url, exc)
        return {"success": False, "provider": "scrapegraphai", "error": str(exc)}


def _playwright_fetch(url: str) -> tuple[str | None, str | None]:
    if not _playwright_available():
        return None, "playwright_not_installed"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            html = page.content()
            browser.close()
            return html, None
    except Exception as exc:
        return None, str(exc)


def fetch_page(url: str, *, engine: str = "auto") -> dict[str, Any]:
    """Provider zinciri: ScrapeGraphAI → Playwright → BeautifulSoup (firecrawl yalnızca explicit)."""
    target = normalize_url(url)
    if not target:
        return {"success": False, "error": "invalid_url", "url": url}

    st = _load_state().get("settings") or {}
    pref = (engine or st.get("engine_preference") or "auto").lower()

    if pref == "firecrawl" and st.get("firecrawl_enabled") and _firecrawl_configured():
        fc = _firecrawl_scrape(target)
        if fc.get("success"):
            return {**fc, "url": target}
        return fc

    if pref in ("scrapegraphai", "auto"):
        ready, _ = _scrapegraph_ready()
        if ready or pref == "scrapegraphai":
            sg = _scrapegraph_extract(target)
            if sg.get("success"):
                raw = sg.get("raw")
                if isinstance(raw, (dict, list)):
                    return {"success": True, "provider": "scrapegraphai", "html": None, "structured": raw, "url": target}
            if pref == "scrapegraphai":
                return sg

    if pref in ("playwright", "auto") and st.get("use_playwright_fallback", True):
        html, pw_err = _playwright_fetch(target)
        if html:
            return {"success": True, "provider": "playwright", "html": html, "url": target}
        if pref == "playwright":
            return {"success": False, "provider": "playwright", "error": pw_err or "fetch_failed", "url": target}

    html, err = fetch_html(target)
    if err or not html:
        return {"success": False, "provider": "beautifulsoup", "error": err or "fetch_failed", "url": target}

    return {"success": True, "provider": "beautifulsoup", "html": html, "url": target}


# ── Extraction ────────────────────────────────────────────────────────────────

def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_entities(raw_entities: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in _as_list(raw_entities):
        if isinstance(item, dict):
            label = item.get("label") or item.get("name") or item.get("title") or ""
            if label:
                out.append({
                    "label": str(label)[:200],
                    "type": str(item.get("type") or item.get("@type") or "entity"),
                    "source": "scrapegraphai",
                })
        elif isinstance(item, str) and item.strip():
            out.append({"label": item.strip()[:200], "type": "entity", "source": "scrapegraphai"})
    return out[:80]


def _normalize_faqs(raw_faqs: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in _as_list(raw_faqs):
        if isinstance(item, dict):
            q = item.get("question") or item.get("name") or ""
            a = item.get("answer") or item.get("text") or ""
            if q:
                out.append({"question": str(q)[:300], "answer": str(a)[:500]})
        elif isinstance(item, str) and item.strip():
            out.append({"question": item.strip()[:300], "answer": ""})
    return out[:50]


def map_scrapegraph_raw(raw: Any, page_url: str = "") -> dict[str, Any]:
    """ScrapeGraphAI çıktısını standart extraction modeline dönüştür."""
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        raw = raw[0]
    if not isinstance(raw, dict):
        return {
            "entities": [], "faqs": [], "schema_types": [], "phones": [], "emails": [],
            "addresses": [], "categories": [], "services": [], "products": [], "links": [],
            "metadata": {"scrapegraph_raw_type": type(raw).__name__, "url": page_url},
        }
    schema = raw.get("schema_types") or raw.get("schemaTypes") or raw.get("schema") or []
    if isinstance(schema, str):
        schema = [schema]
    return {
        "entities": _normalize_entities(raw.get("entities") or raw.get("entity") or raw.get("businesses")),
        "faqs": _normalize_faqs(raw.get("faqs") or raw.get("faq")),
        "schema_types": [str(s) for s in _as_list(schema)][:30],
        "phones": [str(p) for p in _as_list(raw.get("phones") or raw.get("phone"))][:30],
        "emails": [str(e) for e in _as_list(raw.get("emails") or raw.get("email"))][:30],
        "addresses": [str(a) for a in _as_list(raw.get("addresses") or raw.get("address"))][:30],
        "categories": [str(c) for c in _as_list(raw.get("categories") or raw.get("category"))][:25],
        "services": [str(s) for s in _as_list(raw.get("services") or raw.get("service"))][:30],
        "products": [str(p) for p in _as_list(raw.get("products") or raw.get("product"))][:30],
        "links": [],
        "metadata": {"scrapegraph": True, "url": page_url},
    }


def extraction_from_fetch(fetched: dict[str, Any], page_url: str) -> dict[str, Any]:
    """fetch_page sonucundan extraction üret."""
    if fetched.get("structured") and not fetched.get("html"):
        mapped = map_scrapegraph_raw(fetched.get("structured"), page_url)
        if any(mapped.get(k) for k in ("entities", "faqs", "phones", "emails", "schema_types")):
            return mapped
        return map_scrapegraph_raw(fetched.get("structured"), page_url)
    return extract_from_html(fetched.get("html") or "", page_url)


def _parse_json_ld(soup: BeautifulSoup) -> list[Any]:
    schemas: list[Any] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                schemas.extend(data)
            else:
                schemas.append(data)
        except (json.JSONDecodeError, TypeError):
            continue
    return schemas


def _schema_types(schemas: list[Any]) -> list[str]:
    types: list[str] = []
    for sch in schemas:
        if not isinstance(sch, dict):
            continue
        t = sch.get("@type")
        if isinstance(t, list):
            types.extend(str(x) for x in t)
        elif t:
            types.append(str(t))
        for node in sch.get("@graph") or []:
            if isinstance(node, dict) and node.get("@type"):
                nt = node["@type"]
                types.append(nt if isinstance(nt, str) else str(nt))
    return list(dict.fromkeys(types))[:30]


def _extract_faqs_from_schema(schemas: list[Any]) -> list[dict[str, str]]:
    faqs: list[dict[str, str]] = []
    for sch in schemas:
        items = []
        if isinstance(sch, dict):
            if sch.get("@type") == "FAQPage":
                items = sch.get("mainEntity") or []
            for node in sch.get("@graph") or []:
                if isinstance(node, dict) and node.get("@type") == "FAQPage":
                    items.extend(node.get("mainEntity") or [])
        for item in items:
            if not isinstance(item, dict):
                continue
            q = item.get("name") or ""
            ans = item.get("acceptedAnswer") or {}
            a = ans.get("text", "") if isinstance(ans, dict) else str(ans)
            if q:
                faqs.append({"question": str(q)[:300], "answer": str(a)[:500]})
    return faqs[:50]


def _extract_faqs_from_dom(soup: BeautifulSoup) -> list[dict[str, str]]:
    faqs: list[dict[str, str]] = []
    for dt in soup.find_all("dt")[:20]:
        dd = dt.find_next_sibling("dd")
        q = dt.get_text(strip=True)
        a = dd.get_text(strip=True) if dd else ""
        if q:
            faqs.append({"question": q[:300], "answer": a[:500]})
    for h in soup.find_all(["h2", "h3", "h4"])[:25]:
        text = h.get_text(strip=True)
        if "?" in text or text.lower().startswith(("sık", "sss", "faq", "how ", "what ", "why ")):
            sib = h.find_next_sibling(["p", "div"])
            ans = sib.get_text(strip=True)[:500] if sib else ""
            faqs.append({"question": text[:300], "answer": ans})
    return faqs[:50]


def _extract_entities(soup: BeautifulSoup, schemas: list[Any], parsed: dict[str, Any]) -> list[dict[str, Any]]:
    entities: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(label: str, etype: str, source: str) -> None:
        label = (label or "").strip()[:200]
        if not label or label.lower() in seen:
            return
        seen.add(label.lower())
        entities.append({"label": label, "type": etype, "source": source})

    for sch in schemas:
        if not isinstance(sch, dict):
            continue
        name = sch.get("name") or sch.get("legalName")
        stype = sch.get("@type", "Thing")
        if name:
            add(str(name), str(stype), "schema")
        for node in sch.get("@graph") or []:
            if isinstance(node, dict) and node.get("name"):
                add(str(node["name"]), str(node.get("@type", "Thing")), "schema")

    if parsed.get("title"):
        add(parsed["title"], "page_title", "html")
    for h in parsed.get("headings") or []:
        if h.get("level") == "h1":
            add(h.get("text", ""), "heading", "html")

    return entities[:80]


def _extract_addresses(text: str, schemas: list[Any]) -> list[str]:
    addresses: list[str] = []
    for sch in schemas:
        if not isinstance(sch, dict):
            continue
        addr = sch.get("address")
        if isinstance(addr, dict):
            parts = [addr.get("streetAddress"), addr.get("addressLocality"), addr.get("addressRegion")]
            line = ", ".join(p for p in parts if p)
            if line:
                addresses.append(line[:240])
        elif isinstance(addr, str) and addr.strip():
            addresses.append(addr.strip()[:240])
    for m in ADDRESS_RE.findall(text or ""):
        addresses.append(m.strip()[:240])
    return list(dict.fromkeys(addresses))[:30]


def _extract_categories(soup: BeautifulSoup) -> list[str]:
    cats: list[str] = []
    for nav in soup.find_all("nav")[:3]:
        for a in nav.find_all("a", href=True):
            t = a.get_text(strip=True)
            if 2 < len(t) < 60:
                cats.append(t)
    for crumb in soup.select('[itemtype*="BreadcrumbList"] a, .breadcrumb a, [class*="breadcrumb"] a')[:15]:
        t = crumb.get_text(strip=True)
        if t:
            cats.append(t)
    return list(dict.fromkeys(cats))[:25]


def _extract_services_products(soup: BeautifulSoup, schemas: list[Any]) -> dict[str, list[str]]:
    services: list[str] = []
    products: list[str] = []
    for sch in schemas:
        if not isinstance(sch, dict):
            continue
        st = str(sch.get("@type", ""))
        name = sch.get("name")
        if name and "Product" in st:
            products.append(str(name)[:120])
        if name and "Service" in st:
            services.append(str(name)[:120])
    for h in soup.find_all(["h2", "h3"])[:20]:
        ht = h.get_text(strip=True).lower()
        if any(k in ht for k in ("hizmet", "service", "ürün", "product", "paket")):
            ul = h.find_next(["ul", "ol"])
            if ul:
                for li in ul.find_all("li")[:15]:
                    t = li.get_text(strip=True)
                    if t:
                        (services if "ürün" not in ht and "product" not in ht else products).append(t[:120])
    return {
        "services": list(dict.fromkeys(services))[:30],
        "products": list(dict.fromkeys(products))[:30],
    }


def extract_from_html(html: str, page_url: str, *, structured: dict | None = None) -> dict[str, Any]:
    soup = BeautifulSoup(html or "", "html.parser")
    parsed = parse_page(html, page_url)
    schemas = _parse_json_ld(soup)
    plain = soup.get_text(separator=" ", strip=True)
    contacts = extract_contacts(plain)
    sp = _extract_services_products(soup, schemas)

    faqs = _extract_faqs_from_schema(schemas)
    if not faqs:
        faqs = _extract_faqs_from_dom(soup)

    result = {
        "entities": _extract_entities(soup, schemas, parsed),
        "faqs": faqs,
        "schema_types": _schema_types(schemas),
        "phones": list(dict.fromkeys((parsed.get("phones") or []) + contacts.get("phones", [])))[:30],
        "emails": list(dict.fromkeys((parsed.get("emails") or []) + contacts.get("emails", [])))[:30],
        "addresses": _extract_addresses(plain, schemas),
        "categories": _extract_categories(soup),
        "services": sp["services"],
        "products": sp["products"],
        "links": parsed.get("links") or [],
        "metadata": {
            "title": parsed.get("title", ""),
            "meta_description": parsed.get("meta_description", ""),
            "word_count": parsed.get("word_count", 0),
            "url": page_url,
        },
    }
    if structured and isinstance(structured, dict):
        result["metadata"]["scrapegraph_structured"] = structured
    return result


def _merge_extractions(parts: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "entities": [],
        "faqs": [],
        "schema_types": [],
        "phones": [],
        "emails": [],
        "addresses": [],
        "categories": [],
        "services": [],
        "products": [],
        "links": [],
        "metadata": {"pages": []},
    }
    seen_entities: set[str] = set()
    seen_faqs: set[str] = set()
    for part in parts:
        for e in part.get("entities") or []:
            key = (e.get("label") or "").lower()
            if key and key not in seen_entities:
                seen_entities.add(key)
                merged["entities"].append(e)
        for f in part.get("faqs") or []:
            key = (f.get("question") or "").lower()
            if key and key not in seen_faqs:
                seen_faqs.add(key)
                merged["faqs"].append(f)
        for field in ("schema_types", "phones", "emails", "addresses", "categories", "services", "products"):
            merged[field] = list(dict.fromkeys((merged[field] or []) + (part.get(field) or [])))
        merged["links"].extend(part.get("links") or [])
        if part.get("metadata"):
            merged["metadata"]["pages"].append(part["metadata"])
    merged["links"] = merged["links"][:120]
    return merged


def build_result(
    job_id: str,
    source: str,
    extraction: dict[str, Any],
    *,
    extra_metadata: dict | None = None,
) -> dict[str, Any]:
    meta = extraction.get("metadata") or {}
    if extra_metadata:
        meta = {**meta, **extra_metadata}
    return {
        "job_id": job_id,
        "source": source,
        "entities": extraction.get("entities") or [],
        "faqs": extraction.get("faqs") or [],
        "schema_types": extraction.get("schema_types") or [],
        "phones": extraction.get("phones") or [],
        "emails": extraction.get("emails") or [],
        "addresses": extraction.get("addresses") or [],
        "categories": extraction.get("categories") or [],
        "services": extraction.get("services") or [],
        "products": extraction.get("products") or [],
        "links": extraction.get("links") or [],
        "metadata": meta,
    }


# ── Search (keyword miner) ────────────────────────────────────────────────────

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

    return [], "", "provider_missing"


# ── Domain gap analysis ───────────────────────────────────────────────────────

def _domain_gaps(extraction: dict[str, Any]) -> dict[str, Any]:
    schema_types = set(extraction.get("schema_types") or [])
    missing_schema = sorted(RECOMMENDED_SCHEMA_TYPES - schema_types)
    faq_count = len(extraction.get("faqs") or [])
    entities = extraction.get("entities") or []
    pages = (extraction.get("metadata") or {}).get("pages") or []
    avg_words = 0
    if pages:
        avg_words = sum(p.get("word_count", 0) for p in pages) // max(1, len(pages))

    faq_gap = []
    if faq_count < 3:
        faq_gap.append({"gap": "low_faq_coverage", "detail": f"only {faq_count} FAQs found"})
    if "FAQPage" not in schema_types and faq_count > 0:
        faq_gap.append({"gap": "faq_schema_missing", "detail": "FAQ content without FAQPage schema"})

    schema_gap = [{"type": t, "status": "missing"} for t in missing_schema[:10]]

    content_gap = []
    if avg_words < 300:
        content_gap.append({"gap": "thin_content", "detail": f"avg {avg_words} words/page"})
    if len(entities) < 2:
        content_gap.append({"gap": "low_entity_density", "detail": f"{len(entities)} entities"})

    entity_graph = {
        "nodes": [{"id": e.get("label"), "type": e.get("type")} for e in entities[:40]],
        "edges": [],
    }

    return {
        "entity_graph": entity_graph,
        "faq_gap": faq_gap,
        "schema_gap": schema_gap,
        "content_gap": content_gap,
    }


# ── HIVE read-only integrations ───────────────────────────────────────────────

_INTEGRATION_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_INTEGRATION_TTL = 120


def hive_integrations() -> dict[str, Any]:
    import time
    now = time.monotonic()
    if _INTEGRATION_CACHE.get("data") and (now - _INTEGRATION_CACHE["at"]) < _INTEGRATION_TTL:
        return dict(_INTEGRATION_CACHE["data"])

    integrations: dict[str, Any] = {}

    def probe(name: str, fn) -> None:
        try:
            res = fn()
            integrations[name] = {"ok": res.get("success", True) is not False, "detail": res}
        except Exception as exc:
            integrations[name] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller.entity_geo_graph import entity_geo_graph
        probe("entity_geo_graph", entity_geo_graph.health)
    except Exception as exc:
        integrations["entity_geo_graph"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller.opportunity_engine import opportunity_engine
        probe("opportunity_engine", opportunity_engine.health)
    except Exception as exc:
        integrations["opportunity_engine"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller import crawl_gap_engine as cge
        probe("crawl_gap_engine", cge.health)
    except Exception as exc:
        integrations["crawl_gap_engine"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller import campaign_engine as camp
        probe("campaign_engine", camp.health)
    except Exception as exc:
        integrations["campaign_engine"] = {"ok": False, "error": str(exc)}

    try:
        from app.moduller.hive_brain_engine import hive_brain
        probe("hive_brain", hive_brain.health)
    except Exception as exc:
        integrations["hive_brain"] = {"ok": False, "error": str(exc)}

    result = {
        "success": True,
        "read_only": True,
        "integrations": integrations,
        "ready": all(v.get("ok") for v in integrations.values()),
    }
    _INTEGRATION_CACHE["at"] = now
    _INTEGRATION_CACHE["data"] = result
    return result


def _read_entity_geo_hint(url: str, keyword: str = "") -> dict[str, Any] | None:
    try:
        from app.moduller.entity_geo_graph import analyze_url
        return analyze_url(url, seed_keyword=keyword)
    except Exception as exc:
        logger.debug("entity_geo read-only skip: %s", exc)
        return None


# ── Job storage ───────────────────────────────────────────────────────────────

def _store_job(job: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    jobs = state.setdefault("jobs", {})
    jobs[job["job_id"]] = job
    if len(jobs) > MAX_JOBS:
        oldest = sorted(jobs.values(), key=lambda j: j.get("created_at", ""))[: len(jobs) - MAX_JOBS]
        for o in oldest:
            jobs.pop(o.get("job_id"), None)
    dataset = {
        "id": job["job_id"],
        "type": job.get("job_type"),
        "source": job.get("source"),
        "created_at": job.get("created_at"),
        "entity_count": len((job.get("result") or {}).get("entities") or []),
        "faq_count": len((job.get("result") or {}).get("faqs") or []),
    }
    state.setdefault("datasets", []).insert(0, dataset)
    state["datasets"] = state["datasets"][:200]
    _save_state(state)
    return job


# ── Public API ────────────────────────────────────────────────────────────────

def _scrapegraph_health_entry() -> dict[str, Any]:
    sg_installed = _scrapegraph_installed()
    llm_ok, llm_provider = _llm_configured()
    enabled = _scrapegraph_enabled()
    ready = sg_installed and llm_ok and enabled
    if not sg_installed:
        reason = "package_not_installed"
    elif not enabled:
        reason = "disabled"
    elif not llm_ok:
        reason = "llm_provider_missing"
    else:
        reason = None
    return {
        "package_installed": sg_installed,
        "available": ready,
        "reason": reason,
        "error": reason,
        "llm_configured": llm_ok,
        "llm_provider": llm_provider if llm_ok else None,
        "ready": ready,
        "enabled": enabled,
    }


def health() -> dict[str, Any]:
    sg = _scrapegraph_health_entry()
    pw_ok = _playwright_available()
    bs_ok = _beautifulsoup_available()
    return {
        "success": True,
        "module": "data_miner_engine",
        "version": "v1",
        "providers": {
            "scrapegraphai": sg,
            "playwright": {"available": pw_ok, "error": None if pw_ok else "provider_missing"},
            "beautifulsoup": {"available": bs_ok, "error": None if bs_ok else "provider_missing"},
            "firecrawl": {
                "available": _firecrawl_configured(),
                "adapter": "prepared",
                "error": None if _firecrawl_configured() else "provider_missing",
            },
        },
        "provider_chain": ["scrapegraphai", "playwright", "beautifulsoup"],
        "jobs_count": len(_load_state().get("jobs") or {}),
        "no_content_generation": True,
        "no_publishing": True,
    }


def _resolve_fallback_provider() -> str:
    if _playwright_available():
        return "playwright"
    return "beautifulsoup"


def _resolve_current_provider() -> str:
    st = _load_state().get("settings") or {}
    pref = st.get("engine_preference", "auto")
    if pref != "auto":
        return pref
    ready, _ = _scrapegraph_ready()
    if ready:
        return "scrapegraphai"
    return _resolve_fallback_provider()


def dashboard() -> dict[str, Any]:
    state = _load_state()
    jobs = list((state.get("jobs") or {}).values())
    by_type: dict[str, int] = {}
    for j in jobs:
        t = j.get("job_type") or "unknown"
        by_type[t] = by_type.get(t, 0) + 1
    recent = sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)[:8]
    h = health()
    providers = h.get("providers") or {}
    sg = providers.get("scrapegraphai") or {}
    last_provider = recent[0].get("provider") if recent else None
    active = last_provider or _resolve_current_provider()
    fallback = _resolve_fallback_provider() if active != "scrapegraphai" else "playwright"
    return {
        "success": True,
        "total_jobs": len(jobs),
        "by_type": by_type,
        "recent_jobs": [{"job_id": j.get("job_id"), "type": j.get("job_type"), "source": j.get("source"), "status": j.get("status"), "provider": j.get("provider")} for j in recent],
        "providers": providers,
        "current_provider": active,
        "active_extractor": active,
        "fallback_provider": fallback if not sg.get("ready") else None,
        "engine_preference": (state.get("settings") or {}).get("engine_preference", "auto"),
        "scrapegraphai_installed": bool(sg.get("package_installed")),
        "scrapegraphai_available": bool(sg.get("available")),
        "scrapegraph_llm_provider": sg.get("llm_provider"),
        "playwright_available": bool(providers.get("playwright", {}).get("available")),
        "beautifulsoup_available": bool(providers.get("beautifulsoup", {}).get("available")),
        "datasets_count": len(state.get("datasets") or []),
    }


def crawl_url(url: str = "", engine: str = "auto") -> dict[str, Any]:
    target = normalize_url(url)
    if not target:
        return {"success": False, "error": "url gerekli"}

    job_id = _new_job_id()
    _emit_brain("data_mining_started", domain=urlparse(target).netloc, result={"job_id": job_id, "type": "url"})

    fetched = fetch_page(target, engine=engine)
    if not fetched.get("success"):
        job = {
            "job_id": job_id,
            "job_type": "url",
            "status": "failed",
            "source": target,
            "provider": fetched.get("provider"),
            "error": fetched.get("error"),
            "created_at": _now(),
        }
        _store_job(job)
        return {"success": False, "job_id": job_id, **fetched}

    if fetched.get("structured") and not fetched.get("html"):
        extraction = map_scrapegraph_raw(fetched.get("structured"), target)
    else:
        extraction = extract_from_html(fetched.get("html") or "", target)

    geo_hint = _read_entity_geo_hint(target)
    result = build_result(job_id, fetched.get("provider", "unknown"), extraction, extra_metadata={"entity_geo_hint": geo_hint})
    job = {
        "job_id": job_id,
        "job_type": "url",
        "status": "completed",
        "source": target,
        "provider": fetched.get("provider"),
        "created_at": _now(),
        "result": result,
    }
    _store_job(job)
    if result.get("entities"):
        _emit_brain("data_entity_discovered", domain=urlparse(target).netloc, result={"count": len(result["entities"])})
    _emit_brain("data_mining_completed", domain=urlparse(target).netloc, result={"job_id": job_id})
    return {"success": True, **result}


def crawl_keyword(keyword: str = "", limit: int = 5, engine: str = "auto") -> dict[str, Any]:
    kw = (keyword or "").strip()
    if not kw:
        return {"success": False, "error": "keyword gerekli"}

    urls, search_provider, search_err = _search_urls(kw, max(1, min(MAX_PAGES_KEYWORD, limit)))
    if not urls:
        return {"success": False, "error": search_err or "provider_missing", "provider": "search"}

    job_id = _new_job_id()
    _emit_brain("data_mining_started", keyword=kw, result={"job_id": job_id, "type": "keyword"})

    parts: list[dict[str, Any]] = []
    providers_used: list[str] = []
    errors: list[dict[str, str]] = []

    for u in urls:
        fetched = fetch_page(u, engine=engine)
        if not fetched.get("success"):
            errors.append({"url": u, "error": fetched.get("error", "fetch_failed")})
            continue
        providers_used.append(fetched.get("provider", "unknown"))
        if fetched.get("html"):
            parts.append(extract_from_html(fetched["html"], u))
        elif fetched.get("structured"):
            parts.append(map_scrapegraph_raw(fetched["structured"], u))

    if not parts:
        job = {
            "job_id": job_id,
            "job_type": "keyword",
            "status": "failed",
            "source": kw,
            "search_provider": search_provider,
            "error": "all_fetches_failed",
            "errors": errors,
            "created_at": _now(),
        }
        _store_job(job)
        return {"success": False, "job_id": job_id, "error": "all_fetches_failed", "errors": errors}

    merged = _merge_extractions(parts)
    merged["metadata"]["keyword"] = kw
    merged["metadata"]["search_provider"] = search_provider
    merged["metadata"]["urls_crawled"] = len(parts)
    merged["metadata"]["businesses"] = [
        {"name": e.get("label"), "type": e.get("type")}
        for e in merged.get("entities") or []
        if e.get("type") in ("LocalBusiness", "Organization", "page_title", "heading")
    ][:30]

    result = build_result(job_id, search_provider, merged, extra_metadata={"errors": errors})
    job = {
        "job_id": job_id,
        "job_type": "keyword",
        "status": "completed",
        "source": kw,
        "search_provider": search_provider,
        "providers": list(dict.fromkeys(providers_used)),
        "created_at": _now(),
        "result": result,
    }
    _store_job(job)
    _emit_brain("data_mining_completed", keyword=kw, result={"job_id": job_id, "entities": len(result.get("entities") or [])})
    return {"success": True, **result}


def crawl_domain(domain: str = "", limit: int = 8, engine: str = "auto") -> dict[str, Any]:
    dom = (domain or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    if not dom:
        return {"success": False, "error": "domain gerekli"}

    start = normalize_url(dom)
    job_id = _new_job_id()
    _emit_brain("data_mining_started", domain=dom, result={"job_id": job_id, "type": "domain"})

    fetched = fetch_page(start, engine=engine)
    if not fetched.get("success"):
        return {"success": False, "job_id": job_id, **fetched}

    parts: list[dict[str, Any]] = []
    if fetched.get("html"):
        first = extract_from_html(fetched["html"], start)
        parts.append(first)
        internal = []
        for link in first.get("links") or []:
            href = link.get("href") if isinstance(link, dict) else ""
            if href and urlparse(href).netloc.replace("www.", "") == urlparse(start).netloc.replace("www.", ""):
                internal.append(href)
        for u in list(dict.fromkeys(internal))[: max(0, min(MAX_PAGES_DOMAIN, limit) - 1)]:
            f2 = fetch_page(u, engine=engine)
            if f2.get("success") and f2.get("html"):
                parts.append(extract_from_html(f2["html"], u))

    merged = _merge_extractions(parts) if parts else extract_from_html(fetched.get("html") or "", start)
    gaps = _domain_gaps(merged)
    merged["metadata"]["domain"] = dom
    merged["metadata"]["pages_crawled"] = len(parts) or 1

    crawl_gap_hint = None
    try:
        from app.moduller import crawl_gap_engine as cge
        crawl_gap_hint = {"health": cge.health(), "read_only": True}
    except Exception:
        pass

    result = build_result(
        job_id,
        fetched.get("provider", "unknown"),
        merged,
        extra_metadata={"gaps": gaps, "crawl_gap_hint": crawl_gap_hint},
    )
    result["gaps"] = gaps

    job = {
        "job_id": job_id,
        "job_type": "domain",
        "status": "completed",
        "source": dom,
        "provider": fetched.get("provider"),
        "created_at": _now(),
        "result": result,
    }
    _store_job(job)
    _emit_brain("data_mining_completed", domain=dom, result={"job_id": job_id})
    return {"success": True, **result}


def list_jobs(limit: int = 50) -> dict[str, Any]:
    state = _load_state()
    jobs = sorted((state.get("jobs") or {}).values(), key=lambda j: j.get("created_at", ""), reverse=True)
    return {"success": True, "total": len(jobs), "jobs": jobs[: max(1, min(200, limit))]}


def get_results(job_id: str) -> dict[str, Any]:
    job = (_load_state().get("jobs") or {}).get(job_id)
    if not job:
        return {"success": False, "error": "job_not_found", "job_id": job_id}
    return {"success": True, **job}


def list_datasets() -> dict[str, Any]:
    state = _load_state()
    return {"success": True, "datasets": state.get("datasets") or []}


def get_settings() -> dict[str, Any]:
    return {"success": True, "settings": _load_state().get("settings") or DEFAULT_STATE["settings"]}


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    settings = state.setdefault("settings", dict(DEFAULT_STATE["settings"]))
    allowed = set(DEFAULT_STATE["settings"].keys())
    for k, v in (patch or {}).items():
        if k in allowed:
            settings[k] = v
    _save_state(state)
    return {"success": True, "settings": settings}


def export_report(job_id: str = "", report_format: str = "json") -> dict[str, Any]:
    if not job_id:
        return {"success": False, "error": "job_id gerekli"}
    job = (_load_state().get("jobs") or {}).get(job_id)
    if not job:
        return {"success": False, "error": "job_not_found"}
    result = job.get("result") or {}
    fields = ["job_id", "source", "entities", "faqs", "phones", "emails", "addresses", "schema_types"]
    if report_format == "csv":
        flat = [{
            "job_id": result.get("job_id"),
            "source": result.get("source"),
            "phones": ";".join(result.get("phones") or []),
            "emails": ";".join(result.get("emails") or []),
            "entity_count": len(result.get("entities") or []),
            "faq_count": len(result.get("faqs") or []),
        }]
        content = modul_export_csv(flat, ["job_id", "source", "phones", "emails", "entity_count", "faq_count"])
    else:
        content = modul_export_json([result], fields)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ext = "csv" if report_format == "csv" else "json"
    path = REPORTS_DIR / f"data_miner_{job_id}.{ext}"
    path.write_text(content, encoding="utf-8")
    return {"success": True, "format": ext, "path": str(path), "content": content}


# Module facade (opportunity_engine pattern)
data_miner_engine = type("DataMinerEngine", (), {
    "health": staticmethod(health),
    "dashboard": staticmethod(dashboard),
    "crawl_url": staticmethod(crawl_url),
    "crawl_keyword": staticmethod(crawl_keyword),
    "crawl_domain": staticmethod(crawl_domain),
    "list_jobs": staticmethod(list_jobs),
    "get_results": staticmethod(get_results),
    "list_datasets": staticmethod(list_datasets),
    "get_settings": staticmethod(get_settings),
    "update_settings": staticmethod(update_settings),
    "export_report": staticmethod(export_report),
    "hive_integrations": staticmethod(hive_integrations),
})()
