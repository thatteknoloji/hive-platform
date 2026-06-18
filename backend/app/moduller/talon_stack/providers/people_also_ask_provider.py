"""People Also Ask — SERP snippet + pattern extraction."""

from __future__ import annotations

import re

from .base import make_result

PAA_PATTERNS = [
    r"[^.?!]*\bnedir\b[^.?!]*[?!.]",
    r"[^.?!]*\bnasıl\b[^.?!]*[?!.]",
    r"[^.?!]*\bnerede\b[^.?!]*[?!.]",
    r"[^.?!]*\bne kadar\b[^.?!]*[?!.]",
    r"[^.?!]*\ben iyi\b[^.?!]*[?!.]",
    r"[^.?!]*\bfiyat\b[^.?!]*[?!.]",
    r"[^.?!]*\byorum\b[^.?!]*[?!.]",
    r"[^.?!]*\byakınımda\b[^.?!]*[?!.]",
    r"[^.?!]*\?\s*$",
]

TEMPLATE_QUESTIONS = [
    "{kw} nedir?",
    "{kw} nasıl yapılır?",
    "{kw} nerede bulunur?",
    "{kw} ne kadar?",
    "{kw} en iyi seçenekler nelerdir?",
    "{kw} fiyatları ne kadar?",
    "{kw} yorumları nasıl?",
    "{kw} yakınımda nerede?",
    "{kw} için ne zaman gidilmeli?",
    "{kw} güvenli mi?",
]


class PeopleAlsoAskProvider:
    @staticmethod
    def extract_from_snippets(query: str, snippets: list[str]) -> list[dict]:
        found: set[str] = set()
        results: list[dict] = []

        for text in snippets:
            if not text:
                continue
            for pat in PAA_PATTERNS:
                for m in re.finditer(pat, text, re.I):
                    q = m.group(0).strip()
                    if len(q) > 10 and q.lower() not in found:
                        found.add(q.lower())
                        results.append(make_result("paa", query, answer=q, snippet=q))

        return results

    @staticmethod
    def generate_from_seed(seed: str) -> list[dict]:
        results = []
        for tpl in TEMPLATE_QUESTIONS:
            q = tpl.format(kw=seed.strip())
            results.append(make_result("paa", seed, answer=q, snippet=q))
        return results

    @staticmethod
    def extract_from_serp_results(query: str, serp_results: list[dict]) -> list[dict]:
        snippets = [
            r.get("snippet") or r.get("title") or ""
            for r in serp_results
            if isinstance(r, dict)
        ]
        extracted = PeopleAlsoAskProvider.extract_from_snippets(query, snippets)
        if len(extracted) < 5:
            extracted.extend(PeopleAlsoAskProvider.generate_from_seed(query)[:10 - len(extracted)])
        return extracted[:20]
