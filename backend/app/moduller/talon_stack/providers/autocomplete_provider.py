"""Google Autocomplete keyword suggestion provider."""

from __future__ import annotations

import json
from urllib.parse import quote

from .base import DEFAULT_TIMEOUT, make_result, safe_get

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"


class AutocompleteProvider:
    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def suggest(query: str, lang: str = "tr") -> list[dict]:
        if not query or not query.strip():
            return []

        url = f"{SUGGEST_URL}?client=firefox&hl={lang}&q={quote(query.strip())}"
        resp = safe_get(url, timeout=8)
        if not resp or resp.status_code != 200:
            return []

        try:
            data = json.loads(resp.text)
        except (json.JSONDecodeError, ValueError):
            return []

        suggestions = data[1] if isinstance(data, list) and len(data) > 1 else []
        results = []
        for s in suggestions:
            kw = s if isinstance(s, str) else str(s)
            if kw:
                results.append(make_result("autocomplete", query, keyword=kw, snippet=kw))
        return results

    @staticmethod
    def expand_seed(seed: str, suffixes: list[str] | None = None) -> list[dict]:
        suffixes = suffixes or [
            "", " nedir", " nasıl", " nerede", " fiyat", " yorum",
            " en iyi", " yakınımda", " 2025", " 2026",
        ]
        seen: set[str] = set()
        out: list[dict] = []
        for suf in suffixes:
            q = f"{seed}{suf}".strip()
            for item in AutocompleteProvider.suggest(q):
                kw = item.get("keyword") or ""
                if kw and kw.lower() not in seen:
                    seen.add(kw.lower())
                    out.append(item)
        return out[:50]
