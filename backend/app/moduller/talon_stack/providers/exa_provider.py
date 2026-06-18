"""Exa semantic search provider."""

from __future__ import annotations

from .base import DEFAULT_TIMEOUT, env, make_result, safe_post


class ExaProvider:
    @staticmethod
    def is_configured() -> bool:
        return bool(env("EXA_API_KEY"))

    @staticmethod
    def search(
        query: str,
        num_results: int = 10,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> list[dict]:
        api_key = env("EXA_API_KEY")
        if not api_key:
            return []

        body: dict = {
            "query": query,
            "type": "auto",
            "numResults": num_results,
            "contents": {"highlights": True},
        }
        if include_domains:
            body["includeDomains"] = include_domains
        if exclude_domains:
            body["excludeDomains"] = exclude_domains

        resp = safe_post(
            "https://api.exa.ai/search",
            json=body,
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except ValueError:
            return []

        results = []
        for item in (data.get("results") or [])[:num_results]:
            highlights = item.get("highlights") or []
            if isinstance(highlights, str):
                highlights = [highlights]
            results.append(make_result(
                "exa",
                query,
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("text", "")[:500] if item.get("text") else "",
                highlights=highlights,
                raw=item,
            ))
        return results
