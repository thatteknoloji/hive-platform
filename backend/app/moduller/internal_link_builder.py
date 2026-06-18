"""Internal Link Builder — WP içerik + TF-IDF benzerlik önerileri."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .backlink_hub import log_activity, load_state, save_state
from .modul_base import simdi
from .wordpress_api import wp_api


def _tokenize(text: str) -> Counter:
    words = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}", (text or "").lower())
    return Counter(words)


def _tfidf_similarity(a: str, b: str, corpus_df: Counter, n_docs: int) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    shared = set(ta) & set(tb)
    score = 0.0
    for w in shared:
        tf = min(ta[w], tb[w])
        idf = math.log((n_docs + 1) / (corpus_df.get(w, 0) + 1)) + 1
        score += tf * idf
    return round(score, 3)


def _fetch_all_posts() -> list[dict]:
    wp = wp_api()
    if not wp.connected:
        return []
    posts: list[dict] = []
    for page in range(1, 6):
        res = wp.get_posts(page=page, per_page=50)
        if res.get("success") is False:
            break
        batch = res.get("posts") or res.get("data") or (res if isinstance(res, list) else [])
        if isinstance(batch, dict):
            batch = []
        if not batch:
            break
        for p in batch:
            if not isinstance(p, dict):
                continue
            posts.append({
                "id": p.get("id"),
                "title": p.get("title", {}).get("rendered", p.get("title", "")),
                "url": p.get("link", ""),
                "content": p.get("content", {}).get("rendered", p.get("content", "")),
                "type": "post",
            })
    return posts


def suggest_links(min_score: float = 1.0, limit: int = 30) -> dict[str, Any]:
    posts = _fetch_all_posts()
    if not posts:
        return {
            "status": "hata",
            "hata": "WordPress bağlantısı yok veya içerik bulunamadı. WP Manager'dan giriş yapın.",
        }

    corpus = Counter()
    for p in posts:
        corpus.update(_tokenize(p["title"] + " " + p["content"]))
    n = len(posts)

    suggestions = []
    for i, src in enumerate(posts):
        for j, tgt in enumerate(posts):
            if i == j:
                continue
            score = _tfidf_similarity(
                src["title"] + " " + src["content"][:500],
                tgt["title"] + " " + tgt["content"][:300],
                corpus,
                n,
            )
            if score >= min_score:
                suggestions.append({
                    "kaynak_id": src["id"],
                    "kaynak_baslik": src["title"],
                    "kaynak_url": src["url"],
                    "hedef_id": tgt["id"],
                    "hedef_baslik": tgt["title"],
                    "hedef_url": tgt["url"],
                    "skor": score,
                    "anchor": tgt["title"][:60],
                })

    suggestions.sort(key=lambda x: -x["skor"])
    suggestions = suggestions[:limit]

    st = load_state()
    st["link_suggestions"] = suggestions
    save_state(st)

    out = {
        "status": "aktif",
        "toplam_yazi": len(posts),
        "oneri_sayisi": len(suggestions),
        "oneriler": suggestions,
        "tarih": simdi(),
    }
    log_activity("internal_link_builder", "Internal Link Builder", {}, out)
    return out


def apply_to_wordpress(suggestion_ids: list[int] | None = None, max_apply: int = 5) -> dict[str, Any]:
    wp = wp_api()
    if not wp.connected:
        return {"status": "hata", "hata": "WordPress bağlantısı yok"}

    st = load_state()
    suggestions = st.get("link_suggestions", [])
    if suggestion_ids:
        suggestions = [s for s in suggestions if s["kaynak_id"] in suggestion_ids or s["hedef_id"] in suggestion_ids]

    applied = []
    errors = []
    for s in suggestions[:max_apply]:
        link_html = f'<p><a href="{s["hedef_url"]}">{s["anchor"]}</a></p>'
        current = wp._request("GET", f"/wp-json/wp/v2/posts/{s['kaynak_id']}")
        if not current.get("success") and "content" not in current:
            errors.append({"id": s["kaynak_id"], "hata": current.get("error", "yazı okunamadı")})
            continue
        old = current.get("content", {}).get("rendered", "") if isinstance(current.get("content"), dict) else str(current.get("content", ""))
        if s["hedef_url"] in old:
            applied.append({**s, "not": "zaten_var"})
            continue
        res = wp.update_post(s["kaynak_id"], content=old + "\n" + link_html)
        if res.get("success") or res.get("id"):
            applied.append(s)
        else:
            errors.append({"id": s["kaynak_id"], "hata": res.get("error", "bilinmiyor")})

    out = {
        "status": "aktif",
        "uygulanan": len(applied),
        "hatalar": errors,
        "detay": applied,
    }
    log_activity("internal_link_builder", "Internal Link - Uygula", {"adet": max_apply}, out)
    return out
