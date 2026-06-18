"""Talon V2 ana arama servisi — ücretsiz/low-cost search stack."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from app import config

from ..providers.base import env
from ..providers import (
    AutocompleteProvider,
    ExaProvider,
    OpenStreetMapProvider,
    PeopleAlsoAskProvider,
    SearXNGProvider,
    TavilyProvider,
    provider_health,
)

logger = logging.getLogger("hive.talon.search")


def _unique_urls(results: list[dict]) -> list[str]:
    urls = []
    seen: set[str] = set()
    for r in results:
        u = (r.get("url") or "").strip()
        if u and u not in seen:
            seen.add(u)
            urls.append(u)
    return urls


def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def _openrouter_synthesize(prompt: str) -> str:
    api_key = env("OPENROUTER_API_KEY")
    if not api_key:
        return ""
    try:
        import requests
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.get("OPENROUTER_MODEL") or "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
            },
            timeout=45,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.debug("OpenRouter synthesis failed: %s", type(e).__name__)
    return ""


class TalonSearchService:
    @staticmethod
    def health() -> dict:
        return {"talon": "ok", "providers": provider_health(), "stack": "v2-free"}

    @staticmethod
    def search_web(query: str, options: dict | None = None) -> dict:
        options = options or {}
        num = int(options.get("num_results", 10))
        results: list[dict] = []

        if SearXNGProvider.is_configured():
            results.extend(SearXNGProvider.search(query, num))
        if TavilyProvider.is_configured() and len(results) < num:
            results.extend(TavilyProvider.search(query, num - len(results)))
        if ExaProvider.is_configured() and len(results) < num:
            results.extend(ExaProvider.search(query, num - len(results)))

        return {
            "query": query,
            "count": len(results),
            "results": results,
            "sources_used": list({r["source"] for r in results}),
        }

    @staticmethod
    def research_topic(query: str, options: dict | None = None) -> dict:
        options = options or {}
        tavily: list[dict] = []
        exa: list[dict] = []
        serp: list[dict] = []

        if TavilyProvider.is_configured():
            tavily = TavilyProvider.search(query, options.get("num_results", 8), "advanced")
        if ExaProvider.is_configured():
            exa = ExaProvider.search(query, options.get("num_results", 8))
        if SearXNGProvider.is_configured():
            serp = SearXNGProvider.search(query, options.get("num_results", 8))

        combined = tavily + exa + serp
        synthesis = ""
        if env("OPENROUTER_API_KEY") and combined:
            snippets = "\n".join(
                f"- {r.get('title','')}: {r.get('snippet','')[:200]}"
                for r in combined[:12]
            )
            synthesis = _openrouter_synthesize(
                f"'{query}' konusunda kısa SEO araştırma özeti yaz (Türkçe, 150 kelime):\n{snippets}"
            )

        return {
            "query": query,
            "tavily_results": tavily,
            "exa_results": exa,
            "serp_results": serp,
            "synthesis": synthesis,
            "sources_used": list({r["source"] for r in combined}),
        }

    @staticmethod
    def find_competitors(query: str, options: dict | None = None) -> dict:
        options = options or {}
        serp = TalonSearchService.search_web(query, options)
        results = serp.get("results", [])

        domain_counts: dict[str, int] = {}
        for r in results:
            d = _domain_from_url(r.get("url") or "")
            if d:
                domain_counts[d] = domain_counts.get(d, 0) + 1

        competitors = sorted(
            [{"domain": d, "appearances": c} for d, c in domain_counts.items()],
            key=lambda x: -x["appearances"],
        )

        if ExaProvider.is_configured():
            exa = ExaProvider.search(f"{query} competitors sites", 5)
            for r in exa:
                d = _domain_from_url(r.get("url") or "")
                if d and not any(c["domain"] == d for c in competitors):
                    competitors.append({"domain": d, "appearances": 1, "source": "exa"})

        return {
            "query": query,
            "competitors": competitors[:20],
            "serp_urls": _unique_urls(results)[:20],
            "count": len(competitors),
        }

    @staticmethod
    def generate_keyword_ideas(seed_keyword: str, options: dict | None = None) -> dict:
        options = options or {}
        autocomplete = AutocompleteProvider.expand_seed(seed_keyword)

        extra: list[dict] = []
        for suffix in [" nedir", " fiyat", " yorum", " nerede", " en iyi"]:
            extra.extend(AutocompleteProvider.suggest(f"{seed_keyword}{suffix}"))

        seen: set[str] = set()
        keywords: list[str] = []
        for item in autocomplete + extra:
            kw = (item.get("keyword") or "").strip()
            if kw and kw.lower() not in seen:
                seen.add(kw.lower())
                keywords.append(kw)

        return {
            "seedKeyword": seed_keyword,
            "autocompleteKeywords": keywords[:50],
            "count": len(keywords),
        }

    @staticmethod
    def generate_faq_ideas(seed_keyword: str, options: dict | None = None) -> dict:
        serp = TalonSearchService.search_web(seed_keyword, {"num_results": 8})
        paa = PeopleAlsoAskProvider.extract_from_serp_results(
            seed_keyword, serp.get("results", [])
        )
        if len(paa) < 8:
            paa.extend(PeopleAlsoAskProvider.generate_from_seed(seed_keyword))

        questions = []
        seen: set[str] = set()
        for item in paa:
            q = (item.get("answer") or item.get("snippet") or "").strip()
            if q and q.lower() not in seen:
                seen.add(q.lower())
                questions.append(q)

        return {
            "seedKeyword": seed_keyword,
            "peopleAlsoAskQuestions": questions[:25],
            "count": len(questions),
        }

    @staticmethod
    def geo_seo_research(location_keyword: str, options: dict | None = None) -> dict:
        options = options or {}
        mahalleler = options.get("mahalleler") or []
        geo = OpenStreetMapProvider.geo_clusters(location_keyword, mahalleler)

        page_ideas = []
        for g in geo[:15]:
            loc = g.get("location") or {}
            name = loc.get("neighbourhood") or loc.get("district") or loc.get("city") or g.get("title", "")
            if name:
                page_ideas.append({
                    "title": f"{name} — {location_keyword} rehberi",
                    "slug": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
                    "location": loc,
                })

        local_kw = AutocompleteProvider.expand_seed(location_keyword, [
            "", " merkez", " yakını", " en iyi", " fiyat", " rehber",
        ])

        return {
            "locationKeyword": location_keyword,
            "geoEntities": geo,
            "recommendedPages": page_ideas,
            "localKeywords": [k.get("keyword") for k in local_kw[:20] if k.get("keyword")],
        }

    @staticmethod
    def full_seo_research(seed_keyword: str, options: dict | None = None) -> dict:
        options = options or {}
        serp_data = TalonSearchService.search_web(seed_keyword, options)
        serp_results = serp_data.get("results", [])

        tavily_results = TavilyProvider.search(seed_keyword, 8) if TavilyProvider.is_configured() else []
        exa_results = ExaProvider.search(seed_keyword, 8) if ExaProvider.is_configured() else []

        kw_data = TalonSearchService.generate_keyword_ideas(seed_keyword, options)
        faq_data = TalonSearchService.generate_faq_ideas(seed_keyword, options)
        comp_data = TalonSearchService.find_competitors(seed_keyword, options)
        geo_data = TalonSearchService.geo_seo_research(seed_keyword, options)

        content_angles = []
        for kw in kw_data.get("autocompleteKeywords", [])[:8]:
            content_angles.append(f"{kw} hakkında kapsamlı rehber")
        for q in faq_data.get("peopleAlsoAskQuestions", [])[:5]:
            content_angles.append(q.rstrip("?") + " — detaylı cevap")

        if env("OPENROUTER_API_KEY"):
            llm_angles = _openrouter_synthesize(
                f"'{seed_keyword}' için 5 SEO içerik başlığı öner (Türkçe, JSON array olarak sadece string listesi):"
            )
            if llm_angles:
                try:
                    match = re.search(r"\[.*\]", llm_angles, re.S)
                    if match:
                        content_angles.extend(json.loads(match.group(0)))
                except json.JSONDecodeError:
                    content_angles.extend([a.strip("- ") for a in llm_angles.split("\n") if a.strip()][:5])

        return {
            "seedKeyword": seed_keyword,
            "serpResults": serp_results,
            "tavilyResults": tavily_results,
            "exaResults": exa_results,
            "autocompleteKeywords": kw_data.get("autocompleteKeywords", []),
            "peopleAlsoAskQuestions": faq_data.get("peopleAlsoAskQuestions", []),
            "geoEntities": geo_data.get("geoEntities", []),
            "competitors": comp_data.get("competitors", []),
            "contentAngles": list(dict.fromkeys(content_angles))[:20],
            "faqIdeas": faq_data.get("peopleAlsoAskQuestions", []),
            "recommendedPages": geo_data.get("recommendedPages", []),
            "providers": provider_health(),
        }


talon_search_service = TalonSearchService()
