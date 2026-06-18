"""SSS Otomatik Üretim Zinciri — Talon → SSS → WordPress → IndexNow."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.moduller.indexnow import bildirim_gonder
from app.moduller.modul_base import simdi
from app.moduller.sss_generator import (
    MIN_HTML_CHARS,
    build_html,
    generate_sss_page,
)
from app.moduller.talon import anahtar_kelime_uret, hiper_lokal_kelime_uret
from app.moduller.wordpress_api import wp_api

logger = logging.getLogger("hive.sss_automation")

STATE_FILE = Path(__file__).resolve().parent.parent / "sss_automation_state.json"

def _parse_profile_items(raw: dict[str, Any]) -> list[dict[str, Any]]:
    if not raw.get("success"):
        return []
    data = raw.get("data")
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if raw.get("id"):
        return [raw]
    return []


def _enrich_with_listing_links(wp: Any, district: str, page: dict[str, Any]) -> dict[str, Any]:
    """SSS sayfasına gerçek ilan (profil) linkleri ekler."""
    links = list(page.get("internal_links") or [])
    seen = {(l.get("url") or "").rstrip("/") for l in links}
    raw = wp.get_profiles(per_page=8, search=district)
    for item in _parse_profile_items(raw):
        url = (item.get("link") or "").strip()
        if not url or url.rstrip("/") in seen:
            continue
        title = item.get("title", {})
        if isinstance(title, dict):
            title = title.get("rendered", "")
        title = (title or "Profil").strip()
        links.append({"text": f"İlan: {title}", "url": url})
        seen.add(url.rstrip("/"))
        if len(links) >= 12:
            break
    page["internal_links"] = links
    page["html"] = build_html(page)
    if page.get("word_stats"):
        page["word_stats"]["html_chars"] = len(page["html"])
    return page


def _content_len_from_wp_item(item: dict[str, Any]) -> int:
    content = item.get("content", "")
    if isinstance(content, dict):
        content = content.get("rendered", "")
    return len(re.sub(r"<[^>]+>", "", str(content or "")).strip())


def _publish_sss_page(wp: Any, page: dict[str, Any]) -> dict[str, Any]:
    html = page.get("html") or ""
    if len(html) < MIN_HTML_CHARS:
        return {
            "success": False,
            "error": f"İçerik yetersiz ({len(html)} karakter, min {MIN_HTML_CHARS})",
        }
    slug = (page.get("slug") or "").strip()
    res = wp.upsert_page(
        title=page["seo_title"],
        content=html,
        slug=slug,
        status="publish",
        excerpt=page.get("meta_description", ""),
    )
    if res.get("success") or res.get("id"):
        if slug:
            wp.trash_conflicting_post(slug)
        return {
            **res,
            "success": True,
            "id": res.get("id"),
            "link": res.get("link", ""),
            "updated": res.get("updated", False),
            "created": res.get("created", False),
        }
    return res


LOCAL_INTENT_SUFFIXES = [
    "nerede",
    "nasıl gidilir",
    "ne zaman açık",
    "ücretli mi",
    "güvenli mi",
    "kimler gider",
    "sezon ne zaman",
    "nelere dikkat edilmeli",
    "rehberi",
    "fiyatları",
    "çalışma saatleri",
    "yakınında",
    "2025",
    "2026",
]


def _default_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "session_id": "",
        "total": 0,
        "processed": 0,
        "published": 0,
        "failed": 0,
        "indexed": 0,
        "current_step": "",
        "current_keyword": "",
        "last_page": None,
        "errors": [],
        "keywords": [],
        "report": None,
        "params": {},
        "started_at": "",
        "finished_at": "",
    }


class SSSAutomation:
    def __init__(self) -> None:
        self._state: dict[str, Any] = _default_state()
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._state = {**_default_state(), **data}
            except (json.JSONDecodeError, OSError):
                self._state = _default_state()

    def _save(self) -> None:
        try:
            STATE_FILE.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("SSS automation state kaydedilemedi: %s", e)

    def _update(self, **fields: Any) -> None:
        with self._lock:
            self._state.update(fields)
            self._save()

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            s = dict(self._state)
        remaining = max(0, s.get("total", 0) - s.get("processed", 0))
        progress_pct = 0
        if s.get("total", 0) > 0:
            progress_pct = round(s["processed"] / s["total"] * 100, 1)
        return {
            **s,
            "remaining": remaining,
            "progress_pct": progress_pct,
            "running": s.get("status") == "running",
        }

    def get_report(self) -> dict[str, Any]:
        status = self.get_status()
        report = status.get("report") or {}
        return {
            "session_id": status.get("session_id"),
            "status": status.get("status"),
            "started_at": status.get("started_at"),
            "finished_at": status.get("finished_at"),
            "keywords_generated": status.get("total", 0),
            "pages_published": status.get("published", 0),
            "pages_failed": status.get("failed", 0),
            "indexnow_sent": status.get("indexed", 0),
            "errors": status.get("errors", []),
            "last_pages": report.get("pages", [])[-10:],
            **report,
        }

    def start(
        self,
        city: str,
        district: str,
        category: str,
        subcategory: str,
        main_keyword: str,
        secondary_keywords: list[str] | str | None = None,
        keyword_count: int = 50,
        domain_id: int = 0,
        extra_keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if self._state.get("status") == "running":
                return {
                    "success": False,
                    "error": "Zaten çalışan bir üretim zinciri var. Tamamlanmasını bekleyin.",
                    "session_id": self._state.get("session_id"),
                }

        wp = wp_api(domain_id)
        if not wp.connected:
            return {
                "success": False,
                "error": "WordPress bağlantısı yok — WP Manager'dan giriş yapın.",
            }

        if isinstance(secondary_keywords, list):
            sec_kw = ", ".join(secondary_keywords)
        else:
            sec_kw = secondary_keywords or ""

        session_id = str(uuid.uuid4())[:12]
        state = _default_state()
        state.update({
            "status": "running",
            "session_id": session_id,
            "current_step": "baslatiliyor",
            "params": {
                "city": city,
                "district": district,
                "category": category,
                "subcategory": subcategory,
                "main_keyword": main_keyword,
                "secondary_keywords": sec_kw,
                "keyword_count": keyword_count,
                "domain_id": domain_id,
                "extra_keywords": extra_keywords or [],
            },
            "started_at": simdi(),
        })
        self._update(**state)

        return {
            "success": True,
            "session_id": session_id,
            "message": "SSS otomatik üretim zinciri başlatıldı",
            "keyword_count": keyword_count,
            "_run_args": (
                city, district, category, subcategory, main_keyword, sec_kw,
                keyword_count, domain_id, session_id, extra_keywords or [],
            ),
        }

    def run_pipeline_task(self, *args: Any) -> None:
        """BackgroundTasks veya daemon thread tarafından çağrılır."""
        self._run_pipeline(*args)

    def _build_keyword_pool(
        self,
        city: str,
        district: str,
        category: str,
        subcategory: str,
        main_keyword: str,
        count: int,
        extra_keywords: list[str] | None = None,
    ) -> list[str]:
        count = max(50, min(count, 100))
        keywords: list[str] = []

        for kw in (extra_keywords or []):
            k = (kw or "").strip()
            if k and k not in keywords:
                keywords.append(k)
            if len(keywords) >= count:
                return keywords[:count]

        try:
            from app.moduller.talon_orchestrator import get_sss_keyword_pool
            orch = get_sss_keyword_pool(
                main_keyword or f"{district} {subcategory}",
                district or city,
                count=count,
            )
            if orch.get("success") and orch.get("keywords"):
                for kw in orch["keywords"]:
                    if kw and kw not in keywords:
                        keywords.append(kw)
                if len(keywords) >= count:
                    return keywords[:count]
        except Exception as e:
            logger.warning("Talon orchestrator SSS havuzu: %s", e)

        try:
            talon_result, _ = hiper_lokal_kelime_uret(
                ana_kelime=main_keyword or f"{district} {subcategory}",
                adet=count,
                sehir=district or city,
            )
            keywords.extend(k["kelime"] for k in talon_result)
        except Exception as e:
            logger.warning("Talon kelime üretimi hatası: %s", e)

        bases = [
            main_keyword,
            f"{district} {subcategory}",
            f"{district} {category}",
            f"{city} {district} {subcategory}",
            f"{district} {category} {subcategory}",
        ]
        for base in bases:
            base = base.strip()
            if not base:
                continue
            for suffix in LOCAL_INTENT_SUFFIXES:
                kw = f"{base} {suffix}".strip()
                if kw not in keywords:
                    keywords.append(kw)
                if len(keywords) >= count:
                    break
            if len(keywords) >= count:
                break

        seen: set[str] = set()
        unique: list[str] = []
        for k in keywords:
            kl = k.lower().strip()
            if kl and kl not in seen:
                seen.add(kl)
                unique.append(k)
        return unique[:count]

    def _run_pipeline(
        self,
        city: str,
        district: str,
        category: str,
        subcategory: str,
        main_keyword: str,
        secondary_keywords: str,
        keyword_count: int,
        domain_id: int,
        session_id: str,
        extra_keywords: list[str] | None = None,
    ) -> None:
        report_pages: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        try:
            self._update(current_step="anahtar_kelime_havuzu")
            keywords = self._build_keyword_pool(
                city, district, category, subcategory, main_keyword, keyword_count,
                extra_keywords=extra_keywords,
            )
            self._update(total=len(keywords), keywords=keywords, current_step="sss_uretimi")

            wp = wp_api(domain_id)
            published = 0
            failed = 0
            indexed = 0

            for i, keyword in enumerate(keywords):
                self._update(
                    processed=i,
                    current_keyword=keyword,
                    current_step="sss_uretimi",
                )

                try:
                    page = generate_sss_page(
                        city=city,
                        district=district,
                        category=category,
                        subcategory=subcategory,
                        main_keyword=keyword,
                        secondary_keywords=secondary_keywords,
                    )
                    page = _enrich_with_listing_links(wp, district, page)

                    self._update(current_step="wordpress_yayini")
                    res = _publish_sss_page(wp, page)

                    if not (res.get("success") or res.get("id")):
                        failed += 1
                        err = res.get("error", "Yayın başarısız")
                        errors.append({"keyword": keyword, "step": "wordpress", "error": err})
                        self._update(failed=failed, errors=errors)
                        continue

                    post_url = res.get("link", "")
                    post_id = res.get("id")
                    published += 1

                    self._update(current_step="indexnow")
                    idx_result = bildirim_gonder(post_url) if post_url else {"durum": "atlandi"}
                    if idx_result.get("http_status") in (200, 202):
                        indexed += 1

                    stats = page.get("word_stats") or {}
                    page_record = {
                        "keyword": keyword,
                        "title": page["seo_title"],
                        "url": post_url,
                        "page_id": post_id,
                        "slug": page.get("slug"),
                        "ai_ollama": page.get("ai_ollama", False),
                        "indexnow": idx_result.get("durum", ""),
                        "updated": res.get("updated", False),
                        "intro_words": stats.get("intro_words", 0),
                        "faq_count": stats.get("faq_count", 0),
                        "html_chars": stats.get("html_chars", len(page.get("html", ""))),
                        "listing_links": sum(
                            1 for l in (page.get("internal_links") or []) if "/profil/" in (l.get("url") or "")
                        ),
                    }
                    report_pages.append(page_record)

                    self._update(
                        published=published,
                        indexed=indexed,
                        last_page=page_record,
                        report={"pages": report_pages},
                    )

                    time.sleep(1)

                except Exception as e:
                    failed += 1
                    errors.append({"keyword": keyword, "step": "pipeline", "error": str(e)})
                    self._update(failed=failed, errors=errors)
                    logger.exception("SSS pipeline hatası: %s", keyword)

                self._update(processed=i + 1)

            self._update(
                status="completed",
                current_step="tamamlandi",
                current_keyword="",
                finished_at=simdi(),
                report={
                    "pages": report_pages,
                    "summary": {
                        "keywords_generated": len(keywords),
                        "pages_published": published,
                        "pages_failed": failed,
                        "indexnow_sent": indexed,
                    },
                },
            )

        except Exception as e:
            logger.exception("SSS automation kritik hata")
            self._update(
                status="failed",
                current_step="hata",
                finished_at=simdi(),
                errors=errors + [{"keyword": "", "step": "critical", "error": str(e)}],
            )


    def preview(
        self,
        city: str,
        district: str,
        category: str,
        subcategory: str,
        main_keyword: str,
        secondary_keywords: str = "",
        domain_id: int = 0,
        include_listings: bool = True,
    ) -> dict[str, Any]:
        page = generate_sss_page(
            city=city,
            district=district,
            category=category,
            subcategory=subcategory,
            main_keyword=main_keyword,
            secondary_keywords=secondary_keywords,
        )
        if include_listings:
            wp = wp_api(domain_id)
            if wp.connected:
                page = _enrich_with_listing_links(wp, district, page)
        return {
            "success": True,
            "page": page,
            "valid_for_publish": len(page.get("html") or "") >= MIN_HTML_CHARS,
        }

    def repair_empty_pages(
        self,
        domain_id: int = 0,
        limit: int = 50,
        city: str = "",
        district: str = "",
        category: str = "",
        subcategory: str = "",
        secondary_keywords: str = "",
    ) -> dict[str, Any]:
        """Boş veya ince WP sayfalarını SSS içeriğiyle günceller."""
        wp = wp_api(domain_id)
        if not wp.connected:
            return {"success": False, "error": "WordPress bağlantısı yok"}

        params = self.get_status().get("params") or {}
        city = city or params.get("city", "Aydın")
        district = district or params.get("district", "Kuşadası")
        category = category or params.get("category", "Gece Hayatı")
        subcategory = subcategory or params.get("subcategory", "")
        secondary_keywords = secondary_keywords or params.get("secondary_keywords", "")

        report_pages = (self.get_status().get("report") or {}).get("pages") or []
        if not report_pages:
            return {"success": False, "error": "Onarılacak sayfa kaydı yok — önce üretim çalıştırın veya preview kullanın"}

        repaired = 0
        skipped = 0
        failed = 0
        results: list[dict[str, Any]] = []

        for entry in report_pages[:limit]:
            slug = (entry.get("slug") or "").strip()
            keyword = entry.get("keyword") or entry.get("title") or slug
            if not slug:
                skipped += 1
                continue

            existing = wp.find_by_slug("pages", slug)
            if existing:
                plain_len = _content_len_from_wp_item(existing)
                if plain_len >= 500:
                    skipped += 1
                    results.append({"slug": slug, "status": "skipped", "reason": "yeterli içerik"})
                    continue

            page = generate_sss_page(
                city, district, category, subcategory, keyword, secondary_keywords,
            )
            page = _enrich_with_listing_links(wp, district, page)
            res = _publish_sss_page(wp, page)
            if res.get("success") or res.get("id"):
                repaired += 1
                url = res.get("link") or entry.get("url", "")
                if url:
                    bildirim_gonder(url)
                results.append({
                    "slug": slug,
                    "status": "repaired",
                    "url": url,
                    "page_id": res.get("id"),
                })
            else:
                failed += 1
                results.append({
                    "slug": slug,
                    "status": "failed",
                    "error": res.get("error", "bilinmeyen"),
                })

        return {
            "success": True,
            "repaired": repaired,
            "skipped": skipped,
            "failed": failed,
            "results": results,
        }


sss_automation = SSSAutomation()
