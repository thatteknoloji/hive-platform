"""SearXNG SERP provider."""

from __future__ import annotations

from urllib.parse import quote_plus

from .base import DEFAULT_TIMEOUT, env, make_result, safe_get


class SearXNGProvider:
    @staticmethod
    def is_configured() -> bool:
        return bool(env("SEARXNG_URL"))

    @staticmethod
    def search(query: str, num_results: int = 10) -> list[dict]:
        base = env("SEARXNG_URL").rstrip("/")
        if not base:
            return []

        url = f"{base}/search?q={quote_plus(query)}&format=json&language=tr-TR"
        resp = safe_get(url, timeout=DEFAULT_TIMEOUT)
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except ValueError:
            return []

        results = []
        for item in (data.get("results") or [])[:num_results]:
            results.append(make_result(
                "searxng",
                query,
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", "") or item.get("snippet", ""),
                raw=item,
            ))
        return results

    @staticmethod
    def unavailable() -> dict:
        return {"status": "unavailable", "provider": "searxng", "message": "SEARXNG_URL not configured"}
