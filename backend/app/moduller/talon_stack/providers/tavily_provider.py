"""Tavily AI/web research provider."""

from __future__ import annotations

from .base import DEFAULT_TIMEOUT, env, make_result, safe_post


class TavilyProvider:
    @staticmethod
    def is_configured() -> bool:
        return bool(env("TAVILY_API_KEY"))

    @staticmethod
    def search(query: str, num_results: int = 10, search_depth: str = "basic") -> list[dict]:
        api_key = env("TAVILY_API_KEY")
        if not api_key:
            return []

        resp = safe_post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": search_depth,
                "max_results": num_results,
                "include_answer": True,
            },
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except ValueError:
            return []

        results = []
        answer = data.get("answer", "")
        if answer:
            results.append(make_result("tavily", query, answer=answer, raw={"type": "answer"}))

        for item in (data.get("results") or [])[:num_results]:
            results.append(make_result(
                "tavily",
                query,
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                raw=item,
            ))
        return results
