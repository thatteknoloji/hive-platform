"""
StoryForge V2 — URL'den hikaye çek, Kuşadası'na uyarla, WordPress'e yayınla.
"""

from __future__ import annotations

import json
import logging
import random
import re
import textwrap
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app import config
from app.moduller import llm_router
from app.moduller.storyforge_bulk import (
    count_import,
    iter_import_stories,
    load_rules,
    save_rules,
)
from app.moduller.storyforge_categories import (
    pick_categories,
    resolve_category_assignment,
    resolve_term_ids,
    sync_categories_to_wordpress,
)
from app.moduller.wordpress_api import wp_api

logger = logging.getLogger("hive.storyforge")

PENDING_FILE = Path(__file__).resolve().parent.parent / "storyforge_pending.json"
JOBS_FILE = Path(__file__).resolve().parent.parent / "storyforge_jobs.json"
PHOTOS_FILE = Path(__file__).resolve().parent.parent / "storyforge_photos.json"
PUBLISH_LOG_FILE = Path(__file__).resolve().parent.parent / "storyforge_publish_log.json"

ALLOWED_IMAGE_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

STORY_CATEGORIES = [
    ("anal-hikaye", "Anal Escort Hikayeleri", "anal escort"),
    ("oral-hikaye", "Oral Escort Hikayeleri", "oral escort"),
    ("vip-hikaye", "VIP Escort Hikayeleri", "vip escort"),
    ("otel-hikaye", "Otel Escort Hikayeleri", "otel escort"),
    ("plaj-hikaye", "Plaj Escort Hikayeleri", "plaj escort"),
    ("gece-hikaye", "Gece Escort Hikayeleri", "gece escort"),
    ("cift-hikaye", "Çift Escort Hikayeleri", "çift escort"),
    ("grup-hikaye", "Grup Escort Hikayeleri", "grup escort"),
]

STORY_LOCATIONS = [
    "Kuşadası Kadınlar Denizi",
    "Kuşadası Yılancı Burnu",
    "Kuşadası Atatürk Caddesi",
    "Kuşadası Liman Caddesi",
    "Kuşadası Merkez",
    "Kuşadası Güvercinada",
    "Kuşadası Marina",
]

STORY_NAMES = ["Elif", "Selin", "Deniz", "Ayşe", "Merve", "Ceren", "Buse", "Ece", "Zeynep", "Pınar"]

STORY_OPENERS = [
    "Yaz akşamının sıcaklığı {loc} boyunca hissediliyordu.",
    "{loc} civarında yürürken telefonum titredi — beklediğim mesaj gelmişti.",
    "Kuşadası'nın {loc} bölgesinde geçen bu anı, uzun süre unutamayacağım.",
]

STORY_BODY = [
    "Profesyonel ve zarif tavrıyla hemen güven verdi. Sohbetimiz kısa sürede samimi bir tona büründü.",
    "Randevuyu önceden netleştirmiştik; buluşma noktası tam istediğim gibiydi.",
    "Gülüşü, bakışları ve özenli duruşu ortamın enerjisini anında yükseltti.",
    "Kuşadası gecelerinin ritmini bilen biri olduğu her hareketinden belli oluyordu.",
]

STORY_CLOSERS = [
    "Gece sona ererken {keyword} deneyiminin Kuşadası'nda ne kadar özel olabileceğini anladım.",
    "{loc} artık benim için güzel anıların kayıtlı olduğu bir yer.",
    "{keyword} arayanlar için {loc} gerçekten doğru bir tercih olabilir.",
]

META_TPL = "{loc} bölgesinde {keyword} deneyimi — Kuşadası escort hikayesi."

KUSADASI_LOCATIONS = [
    "Kadınlar Denizi", "Yılancı Burnu", "Atatürk Bulvarı", "Liman Caddesi",
    "Güvercinada", "Davutlar", "Kuşadası Marina", "Kuşadası Merkez", "Türkmen",
]

STORY_SELECTORS = [
    ".b-story-body",
    ".b-story",
    "#story",
    ".story-content",
    ".user-story",
    "article.story",
    "article",
    ".post-content",
    "main",
]

USER_AGENT = "Mozilla/5.0 (compatible; HIVE-StoryForge/2.0; +https://balkutusu.com)"

# Bağlaç / edat / zamir — içerik kelime sayımında hariç
_TURKISH_STOP_WORDS = frozenset({
    "ve", "veya", "ile", "bir", "iki", "üç", "de", "da", "ki", "mi", "mu", "mı", "mü",
    "için", "gibi", "kadar", "daha", "çok", "en", "bu", "şu", "o", "ama", "fakat",
    "ancak", "çünkü", "hem", "ya", "ne", "ni", "na", "nu", "nü", "den", "dan", "ten",
    "tan", "lar", "ler", "olan", "olarak", "sonra", "önce", "bile", "sadece", "hiç",
    "her", "tüm", "bazı", "kendi", "ben", "sen", "biz", "siz", "onlar", "var", "yok",
    "ise", "eğer", "diye", "üzere", "göre", "karşı", "arasında", "içinde", "üzerinde",
    "altında", "oldu", "olur", "olan", "the", "a", "an", "in", "on", "at", "to", "of",
    "is", "it", "or", "as", "by", "be", "an", "bu", "şey", "çok", "az", "ile", "de",
    "da", "ki", "mi", "mı", "mu", "mü", "dır", "dir", "dur", "dür", "tır", "tir", "tur", "tür",
})


def _env(key: str, default: str = "") -> str:
    return config.get(key, default) or ""


class StoryForgeV2:
    def __init__(self) -> None:
        llm_router.ensure_ollama_running()
        self.ollama_model = llm_router.resolve_ollama_model()
        self.wp_url = _env("WP_URL", "https://balkutusu.com")
        self._pending: dict[str, dict[str, Any]] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._photos: list[dict[str, Any]] = []
        self._job_lock = threading.Lock()
        self._photo_lock = threading.Lock()
        self._publish_log: list[dict[str, Any]] = []
        self._load_pending()
        self._load_jobs()
        self._load_photos()
        self._load_publish_log()

    def _load_pending(self) -> None:
        if PENDING_FILE.exists():
            try:
                data = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
                self._pending = data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError):
                self._pending = {}

    def _save_pending(self) -> None:
        try:
            PENDING_FILE.write_text(
                json.dumps(self._pending, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("pending kaydedilemedi: %s", e)

    def _load_jobs(self) -> None:
        if JOBS_FILE.exists():
            try:
                data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
                self._jobs = data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError):
                self._jobs = {}

    def _save_jobs(self) -> None:
        try:
            JOBS_FILE.write_text(
                json.dumps(self._jobs, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("jobs kaydedilemedi: %s", e)

    def _load_publish_log(self) -> None:
        if PUBLISH_LOG_FILE.exists():
            try:
                data = json.loads(PUBLISH_LOG_FILE.read_text(encoding="utf-8"))
                self._publish_log = data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                self._publish_log = []

    def _save_publish_log(self) -> None:
        PUBLISH_LOG_FILE.write_text(
            json.dumps(self._publish_log[:300], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def format_display_url(url: str) -> str:
        """https://www.balkutusu.com/hikayeler/... → www.balkutusu.com/hikayeler/..."""
        if not url:
            return ""
        u = url.strip().replace("https://", "").replace("http://", "")
        return u.lstrip("/")

    @staticmethod
    def verify_live_url(url: str) -> dict[str, Any]:
        if not url or not url.strip():
            return {"live": False, "status_code": 0, "error": "URL yok"}
        try:
            r = requests.get(
                url.strip(),
                timeout=20,
                headers={"User-Agent": USER_AGENT},
                verify=False,
                allow_redirects=True,
            )
            return {
                "live": r.status_code == 200,
                "status_code": r.status_code,
                "final_url": r.url,
            }
        except requests.RequestException as e:
            return {"live": False, "status_code": 0, "error": str(e)}

    def _append_publish_log(self, entry: dict[str, Any]) -> dict[str, Any]:
        entry.setdefault("id", str(uuid.uuid4())[:10])
        entry.setdefault("published_at", datetime.now(timezone.utc).isoformat())
        self._publish_log.insert(0, entry)
        self._publish_log = self._publish_log[:300]
        self._save_publish_log()
        return entry

    def list_published(self, limit: int = 40) -> list[dict[str, Any]]:
        return self._publish_log[: max(1, min(limit, 100))]

    def _update_job(self, job_id: str, **fields: Any) -> None:
        with self._job_lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id].update(fields)
            self._jobs[job_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._save_jobs()

    def _load_photos(self) -> None:
        if PHOTOS_FILE.exists():
            try:
                data = json.loads(PHOTOS_FILE.read_text(encoding="utf-8"))
                self._photos = data if isinstance(data, list) else []
            except (json.JSONDecodeError, OSError):
                self._photos = []

    def _save_photos(self) -> None:
        try:
            PHOTOS_FILE.write_text(
                json.dumps(self._photos, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("photos kaydedilemedi: %s", e)

    def list_photos(self) -> list[dict[str, Any]]:
        return list(self._photos)

    def clear_photos(self) -> dict[str, Any]:
        with self._photo_lock:
            count = len(self._photos)
            self._photos = []
            self._save_photos()
        return {"success": True, "cleared": count}

    @staticmethod
    def _guess_mime(filename: str, content_type: str) -> str:
        if content_type in ALLOWED_IMAGE_MIME:
            return content_type
        lower = filename.lower()
        if lower.endswith(".png"):
            return "image/png"
        if lower.endswith(".webp"):
            return "image/webp"
        if lower.endswith(".gif"):
            return "image/gif"
        return "image/jpeg"

    def upload_photos(self, files: list[tuple[str, bytes, str]]) -> dict[str, Any]:
        """files: [(filename, bytes, content_type), ...]"""
        if not files:
            return {"success": False, "error": "Dosya seçilmedi"}
        api = wp_api()
        if not api.connected:
            return {"success": False, "error": "Foto yükleme için WP Manager'dan giriş yapın."}

        uploaded: list[dict[str, Any]] = []
        errors: list[str] = []
        for filename, data, content_type in files:
            if not data:
                errors.append(f"{filename}: boş dosya")
                continue
            mime = self._guess_mime(filename, content_type)
            if mime not in ALLOWED_IMAGE_MIME:
                errors.append(f"{filename}: desteklenmeyen format")
                continue
            safe_name = re.sub(r"[^\w.\-]", "_", filename)[:120] or "story.jpg"
            res = api.upload_media(safe_name, data, mime)
            if not res.get("success"):
                errors.append(f"{filename}: {res.get('error', 'yüklenemedi')}")
                continue
            entry = {
                "id": str(uuid.uuid4())[:10],
                "filename": safe_name,
                "media_id": res.get("id"),
                "source_url": res.get("source_url", ""),
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            uploaded.append(entry)

        if uploaded:
            with self._photo_lock:
                self._photos.extend(uploaded)
                self._save_photos()

        return {
            "success": bool(uploaded),
            "uploaded": len(uploaded),
            "total_photos": len(self._photos),
            "errors": errors,
            "photos": self.list_photos(),
        }

    def pick_photo_media_id(self, story_index: int) -> int | None:
        """1 foto → hepsine aynı; N foto < hikaye → rotasyon; N >= hikaye → sırayla benzersiz."""
        if not self._photos:
            return None
        idx = story_index % len(self._photos)
        media_id = self._photos[idx].get("media_id")
        return int(media_id) if media_id else None

    def generate_local_story(self, category_slug: str | None = None) -> dict[str, Any]:
        combos = [(c, loc) for c in STORY_CATEGORIES for loc in STORY_LOCATIONS]
        slug, _cat_name, keyword = random.choice(combos)
        if category_slug:
            match = next((c for c in STORY_CATEGORIES if c[0] == category_slug), None)
            if match:
                slug, _cat_name, keyword = match
        loc = random.choice(STORY_LOCATIONS)
        name = random.choice(STORY_NAMES)
        short_loc = loc.replace("Kuşadası ", "")
        title = f"{short_loc} {keyword.title()} Hikayesi – {name} ile Unutulmaz Bir Gece"
        opener = random.choice(STORY_OPENERS).format(loc=loc)
        paragraphs = [opener]
        for _ in range(random.randint(4, 6)):
            paragraphs.append(random.choice(STORY_BODY))
        paragraphs.append(random.choice(STORY_CLOSERS).format(loc=loc, keyword=keyword))
        content = "".join(f"<p>{textwrap.fill(p, width=90)}</p>" for p in paragraphs)
        excerpt = META_TPL.format(loc=loc, keyword=keyword)
        return {
            "success": True,
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "lokasyon": loc,
            "category_slug": slug,
            "engine": "local-template",
        }

    def get_stats(self) -> dict[str, Any]:
        api = wp_api()
        wp_connected = api.connected
        stories = api.count_post_type("erotic_story") if wp_connected else {"success": False}
        pending_count = len(self._pending)
        active_jobs = [j for j in self._jobs.values() if j.get("status") == "running"]
        engines = llm_router.list_engines()
        return {
            "wp_connected": wp_connected,
            "published_stories": stories.get("total", 0) if stories.get("success") else None,
            "pending_count": pending_count,
            "photo_pool_count": len(self._photos),
            "active_jobs": len(active_jobs),
            "jobs_total": len(self._jobs),
            "ai_engines": engines,
            "ollama_model": self.ollama_model,
        }

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        items = sorted(self._jobs.values(), key=lambda x: x.get("created_at", ""), reverse=True)
        return items[:limit]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)

    def start_generate_job(
        self,
        count: int = 10,
        auto_publish: bool = True,
        category_slug: str = "",
        delay_sec: float = 1.0,
    ) -> dict[str, Any]:
        if count < 1 or count > 200:
            return {"success": False, "error": "count 1-200 arası olmalı"}
        if auto_publish and not wp_api().connected:
            return {"success": False, "error": "Otomatik yayın için WP Manager'dan giriş yapın."}

        job_id = str(uuid.uuid4())[:12]
        job = {
            "id": job_id,
            "type": "generate",
            "status": "running",
            "total": count,
            "done": 0,
            "published": 0,
            "failed": 0,
            "auto_publish": auto_publish,
            "category_slug": category_slug or "",
            "results": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._job_lock:
            self._jobs[job_id] = job
            self._save_jobs()

        threading.Thread(
            target=self._run_generate_job,
            args=(job_id, count, auto_publish, category_slug, delay_sec),
            daemon=True,
        ).start()
        return {"success": True, "job_id": job_id, "message": f"{count} hikaye üretimi başlatıldı"}

    def start_url_batch_job(
        self,
        urls: list[str],
        auto_publish: bool = True,
        category_slug: str = "gece-hikaye",
        delay_sec: float = 2.0,
    ) -> dict[str, Any]:
        clean_urls = [u.strip() for u in urls if u and u.strip()]
        if not clean_urls:
            return {"success": False, "error": "En az bir URL gerekli"}
        if len(clean_urls) > 50:
            return {"success": False, "error": "Tek seferde en fazla 50 URL"}
        if auto_publish and not wp_api().connected:
            return {"success": False, "error": "Otomatik yayın için WP Manager'dan giriş yapın."}

        job_id = str(uuid.uuid4())[:12]
        job = {
            "id": job_id,
            "type": "url_batch",
            "status": "running",
            "total": len(clean_urls),
            "done": 0,
            "published": 0,
            "failed": 0,
            "auto_publish": auto_publish,
            "category_slug": category_slug,
            "results": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._job_lock:
            self._jobs[job_id] = job
            self._save_jobs()

        threading.Thread(
            target=self._run_url_batch_job,
            args=(job_id, clean_urls, auto_publish, category_slug, delay_sec),
            daemon=True,
        ).start()
        return {"success": True, "job_id": job_id, "message": f"{len(clean_urls)} URL işleniyor"}

    def _run_generate_job(
        self,
        job_id: str,
        count: int,
        auto_publish: bool,
        category_slug: str,
        delay_sec: float,
    ) -> None:
        results: list[dict[str, Any]] = []
        published = failed = done = 0
        for i in range(count):
            story = self.generate_local_story(category_slug or None)
            entry: dict[str, Any] = {
                "index": i + 1,
                "title": story["title"],
                "engine": story["engine"],
            }
            if auto_publish:
                pub = self.publish_to_wordpress(
                    title=story["title"],
                    content=story["content"],
                    lokasyon=story["lokasyon"],
                    excerpt=story["excerpt"],
                    category_slug=story["category_slug"],
                    status="publish",
                    featured_media_id=self.pick_photo_media_id(i),
                )
                if pub.get("success"):
                    published += 1
                    entry["status"] = "published"
                    entry["link"] = pub.get("link", "")
                    entry["post_id"] = pub.get("post_id")
                    entry["live"] = pub.get("live", False)
                else:
                    failed += 1
                    entry["status"] = "failed"
                    entry["error"] = pub.get("error", "Yayın hatası")
            else:
                entry["status"] = "rewritten"
            done += 1
            results.append(entry)
            self._update_job(job_id, done=done, published=published, failed=failed, results=results[-10:])
            if delay_sec > 0 and i < count - 1:
                time.sleep(delay_sec)

        self._update_job(job_id, status="completed", done=done, published=published, failed=failed, results=results[-20:])

    def _run_url_batch_job(
        self,
        job_id: str,
        urls: list[str],
        auto_publish: bool,
        category_slug: str,
        delay_sec: float,
    ) -> None:
        results: list[dict[str, Any]] = []
        published = failed = done = 0
        for i, url in enumerate(urls):
            entry: dict[str, Any] = {"index": i + 1, "url": url}
            fetched = self.fetch_and_rewrite(url)
            if not fetched.get("success"):
                failed += 1
                entry["status"] = "failed"
                entry["error"] = fetched.get("error", "Çekilemedi")
            elif auto_publish:
                pub = self.publish_to_wordpress(
                    title=fetched["suggested_title"],
                    content=fetched["rewritten"],
                    lokasyon=fetched.get("suggested_lokasyon", ""),
                    excerpt=f"Kuşadası escort hikayesi — {fetched.get('suggested_lokasyon', '')}",
                    category_slug=category_slug,
                    status="publish",
                    pending_id=fetched.get("pending_id"),
                    featured_media_id=self.pick_photo_media_id(i),
                )
                if pub.get("success"):
                    published += 1
                    entry["status"] = "published"
                    entry["title"] = fetched["suggested_title"]
                    entry["link"] = pub.get("link", "")
                    entry["live"] = pub.get("live", False)
                else:
                    failed += 1
                    entry["status"] = "failed"
                    entry["error"] = pub.get("error", "Yayın hatası")
            else:
                entry["status"] = "rewritten"
                entry["title"] = fetched.get("suggested_title", "")
                entry["pending_id"] = fetched.get("pending_id", "")
            done += 1
            results.append(entry)
            self._update_job(job_id, done=done, published=published, failed=failed, results=results[-10:])
            if delay_sec > 0 and i < len(urls) - 1:
                time.sleep(delay_sec)

        self._update_job(job_id, status="completed", done=done, published=published, failed=failed, results=results[-20:])

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def fetch_story_from_url(self, url: str) -> dict[str, Any]:
        if not url or not url.strip():
            return {"success": False, "error": "URL gerekli"}
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return {"success": False, "error": "Geçersiz URL"}

        try:
            r = requests.get(
                url.strip(),
                timeout=45,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "tr,en;q=0.9"},
            )
            r.raise_for_status()
        except requests.RequestException as e:
            return {"success": False, "error": f"Sayfa alınamadı: {e}"}

        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = ""
        h1 = soup.find("h1")
        if h1:
            title = self._clean_text(h1.get_text())
        if not title and soup.title:
            title = self._clean_text(soup.title.get_text())

        body = ""
        for sel in STORY_SELECTORS:
            node = soup.select_one(sel)
            if node:
                body = self._clean_text(node.get_text(separator="\n"))
                if len(body) > 400:
                    break

        if len(body) < 200:
            paragraphs = [self._clean_text(p.get_text()) for p in soup.find_all("p")]
            paragraphs = [p for p in paragraphs if len(p) > 40]
            body = "\n\n".join(paragraphs)

        if len(body) < 150:
            return {"success": False, "error": "Hikaye metni çıkarılamadı (selector eşleşmedi)"}

        if len(body) > 80000:
            body = body[:80000] + "…"

        return {
            "success": True,
            "source_url": url.strip(),
            "source_title": title or "İsimsiz Hikaye",
            "original": body,
            "word_count": len(body.split()),
        }

    def _fetch_geo_context(self, rules: dict[str, Any]) -> str:
        """Tavily + Exa + OSM ile GEO/SEO bağlamı (API key'ler otomatik kullanılır)."""
        city = rules.get("city") or "Kuşadası"
        kw = (rules.get("keywords") or ["escort"])[0]
        seed = f"{city} {kw} gece hayatı lokasyon"
        snippets: list[str] = []
        try:
            from app.moduller.talon_stack.providers.tavily_provider import TavilyProvider
            from app.moduller.talon_stack.providers.exa_provider import ExaProvider
            from app.moduller.talon_stack.services.talon_search_service import talon_search_service

            if TavilyProvider.is_configured():
                for row in TavilyProvider.search(seed, 4):
                    sn = (row.get("snippet") or row.get("title") or "")[:200]
                    if sn:
                        snippets.append(sn)
            if ExaProvider.is_configured():
                for row in ExaProvider.search(seed, 4):
                    sn = (row.get("snippet") or row.get("title") or "")[:200]
                    if sn:
                        snippets.append(sn)
            geo = talon_search_service.geo_seo_research(seed, {})
            for p in (geo.get("recommendedPages") or [])[:6]:
                t = (p.get("title") or "").strip()
                if t:
                    snippets.append(t)
            for lk in (geo.get("localKeywords") or [])[:8]:
                if lk:
                    snippets.append(str(lk))
        except Exception as e:
            logger.debug("GEO context atlandı: %s", e)
        if not snippets:
            locs = rules.get("locations") or KUSADASI_LOCATIONS
            return "Lokasyonlar: " + ", ".join(locs[:8])
        return "GEO/SEO araştırma notları:\n- " + "\n- ".join(snippets[:12])

    def _build_rewrite_prompt(
        self,
        original_text: str,
        source_title: str,
        rules: dict[str, Any] | None = None,
        *,
        source_min_words: int | None = None,
    ) -> str:
        r = rules or load_rules()
        locs = ", ".join((r.get("locations") or KUSADASI_LOCATIONS)[:10])
        names = ", ".join((r.get("character_names") or STORY_NAMES)[:8])
        keywords = ", ".join((r.get("keywords") or ["escort"])[:6])
        city = r.get("city") or "Kuşadası"
        custom = r.get("custom_rules") or ""
        src_wc = source_min_words or self._word_count(original_text)
        site = (r.get("site_url") or "https://www.balkutusu.com").rstrip("/")
        geo_block = self._fetch_geo_context(r) if r.get("geo_inject", True) else ""
        if src_wc >= 80:
            length_rules = (
                f"- Orijinal metinde yaklaşık {src_wc} kelime var; yeniden yazım EN AZ {src_wc} kelime olmalı\n"
                f"- KISALTMA YASAK — tüm sahneleri koru, olay örgüsünü atlama"
            )
        else:
            min_words = int(r.get("min_words") or 0)
            length_rules = (
                f"- En az {min_words} anlamlı kelime" if min_words > 0
                else "- Hikayeyi tam ve eksiksiz yaz"
            )
        return f"""Aşağıdaki hikayeyi Türkçe olarak TAMAMEN yeniden yaz.

ZORUNLU KURALLAR:
- Şehir: {city}
- GEO lokasyonlar: {locs}
- Karakter isimleri (Türkçe): {names}
- SEO anahtar kelimeler doğal geçsin: {keywords}
{length_rules}
- Detaylı, sinematik, SEO/GEO uyumlu uzun anlatım
- HTML <p> paragrafları kullan
- Başlık yazma, sadece hikaye gövdesi
- Son paragrafta {site} linkini doğal geçir
{custom}

{geo_block}

Kaynak başlık: {source_title}

Orijinal:
{original_text[:120000]}

Yeniden yazılmış hikaye (HTML <p>):"""

    @staticmethod
    def _strip_html(html: str) -> str:
        text = re.sub(r"<[^>]+>", " ", html or "")
        text = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ\s\-']", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip().lower()

    @classmethod
    def _content_word_count(cls, html: str) -> int:
        """Bağlaç/edat hariç anlamlı kelime sayısı."""
        words = cls._strip_html(html).split()
        return sum(
            1 for w in words
            if len(w) >= 2 and w not in _TURKISH_STOP_WORDS and not w.isdigit()
        )

    @classmethod
    def _word_count(cls, html: str) -> int:
        words = cls._strip_html(html).split()
        return len(words)

    def _expand_story(
        self,
        content: str,
        source_title: str,
        rules: dict[str, Any],
        current: int,
        target: int,
        attempt: int = 1,
    ) -> tuple[str | None, str]:
        r = rules or load_rules()
        max_words = int(r.get("max_words") or 1800)
        city = r.get("city") or "Kuşadası"
        need = target - current
        prompt = f"""Aşağıdaki Kuşadası hikayesini Türkçe olarak ÖNEMLİ ÖLÇÜDE UZAT.
Şu an bağlaçlar hariç {current} anlamlı kelime var — EN AZ {target} olmalı (eksik: ~{need} kelime).
- {city} GEO detayları, duygu, diyalog, mekan betimlemesi, gece atmosferi ekle
- Kısa cümle zinciri YASAK — her paragraf 4-8 cümle
- HTML <p> koru, başlık yazma, aynı hikayeyi devam ettir
- Bağlaçları (ve, ile, bir, de, ki…) abartma — anlamlı kelime üret

Kaynak başlık: {source_title}
Deneme: {attempt}

Mevcut metin:
{content[:14000]}

Genişletilmiş TAM hikaye (HTML <p>, min {target} anlamlı kelime):"""
        text, engine = llm_router.generate(prompt, max_tokens=6000, min_length=1200)
        return (text if text else None), engine

    def _pad_to_minimum(self, content: str, rules: dict[str, Any], source_title: str, need: int) -> str:
        """AI yetersiz kalırsa şablon paragraflarla anlamlı kelime sayısını tamamla."""
        r = rules or load_rules()
        city = r.get("city") or "Kuşadası"
        locs = r.get("locations") or KUSADASI_LOCATIONS
        kw = (r.get("keywords") or ["escort"])[0]
        loc = locs[hash(source_title + content) % len(locs)]
        site = (r.get("site_url") or "https://www.balkutusu.com").rstrip("/")
        pads = [
            f"{city} {loc} çevresinde akşam ilerledikçe sokakların ritmi değişiyordu; ışıklar marinadan içeri doğru uzanan yürüyüş yolunda titreşiyordu.",
            f"Sohbetimiz samimi bir tona büründüğünde {kw} deneyiminin bu şehirde ne kadar özel olabileceğini hissettim; her cümle Kuşadası'nın gece hayatına bir kapı aralıyordu.",
            f"{loc} bölgesinde dolaşırken tatilcilerin kalabalığı ile yerel mekanların sıcaklığı bir arada hissediliyordu; deniz kokusu ve müzik sesleri ortamı tamamlıyordu.",
            f"Randevu öncesinde detayları netleştirmek Kuşadası gecelerinde her zaman önemli; buluşma noktası, tempo ve beklentiler karşılıklı anlaşıldığında gece çok daha akıcı ilerliyor.",
            f"Profesyonel duruş, zarif tavır ve doğal iletişim birleşince {city} escort atmosferinin neden bu kadar arandığını anlamak zor olmuyor.",
            f"Gece yarısına yakın {loc} tarafında sakinleşen cadde, hikayenin son bölümüne doğru daha kişisel bir tona geçmemize izin verdi.",
            f"Kuşadası'nın {loc} sokaklarında geçen bu anı, tatil boyunca konuşulacak detaylarla dolu bir deneyime dönüştü.",
            f"Daha fazla {city} hikayesi ve güncel içerikler için {site} adresini ziyaret edebilirsiniz.",
        ]
        out = content
        for p in pads:
            if self._content_word_count(out) >= need:
                break
            out += f"<p>{p}</p>"
        return out

    def _ensure_min_length(
        self,
        content: str,
        source_title: str,
        rules: dict[str, Any],
        engine: str,
        source_min_words: int | None = None,
    ) -> tuple[str, str, int, int]:
        rule_min = int(rules.get("min_words") or 0)
        min_w = max(rule_min, source_min_words or 0)
        max_w = int(rules.get("max_words") or 1800)
        if source_min_words and source_min_words > max_w:
            max_w = int(source_min_words * 1.15)
        total = self._word_count(content)
        content_w = self._content_word_count(content)

        for attempt in range(1, 4):
            if content_w >= min_w:
                break
            expanded, exp_engine = self._expand_story(content, source_title, rules, content_w, min_w, attempt)
            if expanded and self._content_word_count(expanded) > content_w:
                content = expanded
                engine = f"{engine}+{exp_engine}"
                content_w = self._content_word_count(content)
                total = self._word_count(content)
            else:
                break

        if content_w < min_w:
            content = self._pad_to_minimum(content, rules, source_title, min_w)
            engine = f"{engine}+pad"
            content_w = self._content_word_count(content)
            total = self._word_count(content)

        if content_w > max_w:
            parts = re.findall(r"<p>.*?</p>", content, re.S)
            trimmed: list[str] = []
            count = 0
            for p in parts:
                trimmed.append(p)
                count += self._content_word_count(p)
                if count >= max_w:
                    break
            if trimmed:
                content = "".join(trimmed)
                content_w = self._content_word_count(content)
                total = self._word_count(content)

        return content, engine, total, content_w

    def _llm_rewrite(
        self,
        original_text: str,
        source_title: str,
        rules: dict[str, Any] | None = None,
        *,
        source_min_words: int | None = None,
    ) -> tuple[str | None, str]:
        src_wc = source_min_words or self._word_count(original_text)
        prompt = self._build_rewrite_prompt(
            original_text, source_title, rules, source_min_words=src_wc,
        )[:120000]
        max_tokens = min(16000, max(2500, int(src_wc * 2.8)))
        min_length = max(400, int(len(original_text) * 0.35))
        text, engine = llm_router.generate(prompt, max_tokens=max_tokens, min_length=min_length)
        return (text if text else None), engine

    def _fallback_rewrite(self, original_text: str, source_title: str, rules: dict[str, Any] | None = None) -> str:
        r = rules or load_rules()
        locs = r.get("locations") or KUSADASI_LOCATIONS
        city = r.get("city") or "Kuşadası"
        site = (r.get("site_url") or "https://www.balkutusu.com").rstrip("/")
        kw = (r.get("keywords") or ["escort"])[0]
        loc = locs[hash(source_title) % len(locs)]
        opener = (
            f"<p>{city}'na tatil için geldiğim ilk akşam {loc} bölgesinde dolaşırken "
            f"bu anının başlayacağını henüz bilmiyordum.</p>"
        )
        chunks = [c.strip() for c in re.split(r"\n+", original_text) if len(c.strip()) > 60]
        if not chunks:
            chunks = [original_text[:800]]
        body = opener + "".join(f"<p>{c}</p>" for c in chunks[:12])
        body += (
            f"<p>Gece {loc} çevresinde sona ererken {city} {kw} deneyimini "
            f"uzun süre unutamayacağım. Daha fazlası için "
            f'<a href="{site}">balkutusu.com</a>.</p>'
        )
        return body

    def rewrite_story(
        self,
        original_text: str,
        source_title: str = "",
        rules: dict[str, Any] | None = None,
        source_min_words: int | None = None,
    ) -> dict[str, Any]:
        src_wc = source_min_words or self._word_count(original_text)
        rewritten, engine = self._llm_rewrite(
            original_text, source_title, rules, source_min_words=src_wc,
        )
        if not rewritten:
            rewritten = self._fallback_rewrite(original_text, source_title, rules)
            engine = "template"

        if not rewritten.strip().startswith("<"):
            paragraphs = [p.strip() for p in rewritten.split("\n\n") if p.strip()]
            rewritten = "".join(f"<p>{p}</p>" for p in paragraphs)

        r = rules or load_rules()
        rewritten, engine, total_wc, content_wc = self._ensure_min_length(
            rewritten, source_title, r, engine, source_min_words=src_wc if src_wc >= 80 else None,
        )

        suggested_title = self._suggest_title(source_title, rewritten, rules)
        lokasyon = self._suggest_lokasyon(rewritten, rules)
        excerpt = self._suggest_excerpt(suggested_title, lokasyon, rules)
        cats = pick_categories(title=suggested_title, content=rewritten, lokasyon=lokasyon)

        return {
            "success": True,
            "rewritten": rewritten,
            "suggested_title": suggested_title,
            "suggested_lokasyon": lokasyon,
            "suggested_excerpt": excerpt,
            "suggested_categories": cats,
            "engine": engine,
            "word_count": total_wc,
            "content_word_count": content_wc,
        }

    def _suggest_lokasyon(self, content: str, rules: dict[str, Any] | None = None) -> str:
        r = rules or load_rules()
        locs = r.get("locations") or KUSADASI_LOCATIONS
        city = r.get("city") or "Kuşadası"
        loc = locs[hash(content) % len(locs)]
        return f"{city} {loc}"

    def _suggest_excerpt(self, title: str, lokasyon: str, rules: dict[str, Any] | None = None) -> str:
        r = rules or load_rules()
        kw = (r.get("keywords") or ["escort"])[0]
        text = f"{lokasyon} bölgesinde {kw} hikayesi — {title}"
        return text[:155]

    def _suggest_title(self, source_title: str, content: str, rules: dict[str, Any] | None = None) -> str:
        r = rules or load_rules()
        locs = r.get("locations") or KUSADASI_LOCATIONS
        names = r.get("character_names") or STORY_NAMES
        keywords = r.get("keywords") or ["escort"]
        tpl = r.get("title_template") or "{location} {keyword} Hikayesi – Kuşadası"
        max_len = int(r.get("seo_title_max") or 60)
        loc = locs[hash(content) % len(locs)]
        name = names[hash(source_title) % len(names)]
        kw = keywords[hash(source_title + content) % len(keywords)]
        title = tpl.format(location=loc, keyword=kw, name=name, city=r.get("city") or "Kuşadası")
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) > max_len:
            title = title[: max_len - 1].rsplit(" ", 1)[0]
        return title or f"{loc} Hikayesi | Kuşadası"

    def quick_rewrite_publish(
        self,
        text: str,
        title: str = "",
        auto_publish: bool = True,
        category_slug: str = "gece-hikaye",
        preview_only: bool = False,
    ) -> dict[str, Any]:
        content = (text or "").strip()
        if len(content) < 80:
            return {"success": False, "error": "Hikaye en az 80 karakter olmalı"}

        rewritten = self.rewrite_story(content, title)
        if not rewritten.get("success"):
            return rewritten

        result: dict[str, Any] = {
            "success": True,
            "rewritten": rewritten["rewritten"],
            "suggested_title": rewritten["suggested_title"],
            "suggested_lokasyon": rewritten.get("suggested_lokasyon", ""),
            "suggested_excerpt": rewritten.get("suggested_excerpt", ""),
            "engine": rewritten.get("engine", ""),
            "word_count": rewritten.get("word_count", 0),
            "content_word_count": rewritten.get("content_word_count", 0),
            "suggested_categories": rewritten.get("suggested_categories"),
            "published": False,
        }

        if preview_only or not auto_publish:
            return result

        pub = self.publish_to_wordpress(
            title=rewritten["suggested_title"],
            content=rewritten["rewritten"],
            lokasyon=rewritten.get("suggested_lokasyon", ""),
            excerpt=rewritten.get("suggested_excerpt", ""),
            category_slug=category_slug,
            status="publish",
            featured_media_id=self.pick_photo_media_id(0),
        )
        if not pub.get("success"):
            result["publish_error"] = pub.get("error", "Yayın hatası")
            return result

        result["published"] = True
        result["post_id"] = pub.get("post_id")
        result["link"] = pub.get("link", "")
        result["display_url"] = pub.get("display_url", self.format_display_url(pub.get("link", "")))
        result["live"] = pub.get("live", False)
        result["status_code"] = pub.get("status_code", 0)
        result["published_categories"] = pub.get("categories")
        result["message"] = pub.get("message", f"Yayınlandı: {result['display_url']}")
        return result

    def paste_and_run_bulk(
        self,
        text: str,
        filename: str = "paste.txt",
        auto_publish: bool = True,
        category_slug: str = "gece-hikaye",
        delay_sec: float = 2.0,
        offset: int = 0,
        limit: int = 0,
    ) -> dict[str, Any]:
        from app.moduller.storyforge_bulk import import_from_text

        imported = import_from_text(text, filename)
        if not imported.get("success"):
            return imported
        job = self.start_bulk_import_job(
            import_id=imported["import_id"],
            auto_publish=auto_publish,
            category_slug=category_slug,
            delay_sec=delay_sec,
            offset=offset,
            limit=limit,
        )
        if not job.get("success"):
            return job
        return {
            **job,
            "import_id": imported["import_id"],
            "import_count": imported["count"],
            "preview": imported.get("preview", []),
        }

    def fetch_and_rewrite(self, url: str) -> dict[str, Any]:
        fetched = self.fetch_story_from_url(url)
        if not fetched.get("success"):
            return fetched

        rewritten = self.rewrite_story(
            fetched["original"],
            fetched.get("source_title", ""),
            source_min_words=fetched.get("word_count"),
        )
        if not rewritten.get("success"):
            return rewritten

        pending_id = str(uuid.uuid4())[:12]
        entry = {
            "id": pending_id,
            "source_url": fetched["source_url"],
            "source_title": fetched["source_title"],
            "original": fetched["original"],
            "rewritten": rewritten["rewritten"],
            "suggested_title": rewritten["suggested_title"],
            "suggested_lokasyon": rewritten["suggested_lokasyon"],
            "engine": rewritten["engine"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._pending[pending_id] = entry
        self._save_pending()

        return {
            "success": True,
            "pending_id": pending_id,
            "source_url": fetched["source_url"],
            "source_title": fetched["source_title"],
            "original": fetched["original"],
            "original_preview": fetched["original"][:500] + ("…" if len(fetched["original"]) > 500 else ""),
            "rewritten": rewritten["rewritten"],
            "suggested_title": rewritten["suggested_title"],
            "suggested_lokasyon": rewritten["suggested_lokasyon"],
            "engine": rewritten["engine"],
            "word_count": len(rewritten["rewritten"].split()),
        }

    def list_pending(self) -> list[dict[str, Any]]:
        return sorted(self._pending.values(), key=lambda x: x.get("created_at", ""), reverse=True)

    def publish_to_wordpress(
        self,
        title: str,
        content: str,
        lokasyon: str = "",
        excerpt: str = "",
        category_slug: str = "gece-hikaye",
        status: str = "publish",
        pending_id: str | None = None,
        featured_media_id: int | None = None,
    ) -> dict[str, Any]:
        api = wp_api()
        if not api.connected:
            return {"success": False, "error": "WordPress bağlantısı yok. WP Manager'dan giriş yapın."}

        meta: dict[str, str] = {}
        if lokasyon:
            meta["story_lokasyon"] = lokasyon

        wp_terms: list[dict[str, Any]] = []
        listed = api.list_story_categories()
        if listed.get("success"):
            wp_terms = listed.get("terms", [])

        cat_info = resolve_category_assignment(
            category_slug=category_slug,
            title=title,
            content=content,
            lokasyon=lokasyon,
            wp_terms=wp_terms,
        )
        term_ids = resolve_term_ids(api, cat_info)

        res = api.create_erotic_story(
            title=title,
            content=content,
            status=status,
            excerpt=excerpt,
            meta=meta,
            categories=term_ids if term_ids else None,
            featured_media=featured_media_id,
        )
        if not res.get("success"):
            return res

        post_id = res.get("id")
        link = res.get("link", "")
        live_check = self.verify_live_url(link) if link else {"live": False, "status_code": 0}

        display_url = self.format_display_url(link)
        self._append_publish_log({
            "title": title,
            "link": link,
            "display_url": display_url,
            "post_id": post_id,
            "category_slug": cat_info.get("main_slug", category_slug),
            "sub_category": cat_info.get("sub_slug", ""),
            "categories": cat_info,
            "lokasyon": lokasyon,
            "word_count": self._word_count(content),
            "content_word_count": self._content_word_count(content),
            "live": live_check.get("live", False),
            "status_code": live_check.get("status_code", 0),
            "source": "wordpress",
        })

        if pending_id and pending_id in self._pending:
            del self._pending[pending_id]
            self._save_pending()

        live_msg = "Sayfa canlı ✓" if live_check.get("live") else f"WP yayınlandı (HTTP {live_check.get('status_code', '?')})"
        return {
            "success": True,
            "post_id": post_id,
            "link": link,
            "display_url": display_url,
            "live": live_check.get("live", False),
            "status_code": live_check.get("status_code", 0),
            "categories": cat_info,
            "word_count": self._word_count(content),
            "content_word_count": self._content_word_count(content),
            "message": f"{live_msg} — {display_url}",
        }

    def start_bulk_import_job(
        self,
        import_id: str,
        auto_publish: bool = True,
        category_slug: str = "gece-hikaye",
        delay_sec: float = 3.0,
        offset: int = 0,
        limit: int = 0,
    ) -> dict[str, Any]:
        total = count_import(import_id)
        if total == 0:
            return {"success": False, "error": "import_id bulunamadı veya boş"}
        if offset < 0:
            offset = 0
        if offset >= total:
            return {"success": False, "error": f"offset ({offset}) toplam ({total}) dışında"}
        if auto_publish and not wp_api().connected:
            return {"success": False, "error": "Otomatik yayın için WP Manager'dan giriş yapın."}

        remaining = total - offset
        batch_size = limit if limit > 0 else remaining
        batch_size = min(batch_size, remaining, 50000)
        rules = load_rules()

        job_id = str(uuid.uuid4())[:12]
        job = {
            "id": job_id,
            "type": "bulk_import",
            "status": "running",
            "import_id": import_id,
            "total": batch_size,
            "done": 0,
            "published": 0,
            "failed": 0,
            "offset": offset,
            "auto_publish": auto_publish,
            "category_slug": category_slug,
            "results": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._job_lock:
            self._jobs[job_id] = job
            self._save_jobs()

        threading.Thread(
            target=self._run_bulk_import_job,
            args=(job_id, import_id, auto_publish, category_slug, delay_sec, offset, batch_size, rules),
            daemon=True,
        ).start()
        return {
            "success": True,
            "job_id": job_id,
            "import_id": import_id,
            "total": batch_size,
            "message": f"{batch_size} hikaye yeniden yazılıp {'yayınlanacak' if auto_publish else 'hazırlanacak'}",
        }

    def _run_bulk_import_job(
        self,
        job_id: str,
        import_id: str,
        auto_publish: bool,
        category_slug: str,
        delay_sec: float,
        offset: int,
        batch_size: int,
        rules: dict[str, Any],
    ) -> None:
        results: list[dict[str, Any]] = []
        published = failed = done = 0
        skipped = 0

        for story in iter_import_stories(import_id):
            if skipped < offset:
                skipped += 1
                continue
            if done >= batch_size:
                break

            idx = offset + done + 1
            source_title = str(story.get("title") or "")
            original = str(story.get("content") or "")
            entry: dict[str, Any] = {"index": idx, "source_title": source_title[:80]}

            if len(original) < 80:
                failed += 1
                entry["status"] = "failed"
                entry["error"] = "İçerik çok kısa"
                done += 1
                results.append(entry)
                self._update_job(job_id, done=done, published=published, failed=failed, results=results[-10:])
                continue

            rewritten = self.rewrite_story(original, source_title, rules)
            if not rewritten.get("success"):
                failed += 1
                entry["status"] = "failed"
                entry["error"] = rewritten.get("error", "Yeniden yazılamadı")
            elif auto_publish:
                pub = self.publish_to_wordpress(
                    title=rewritten["suggested_title"],
                    content=rewritten["rewritten"],
                    lokasyon=rewritten.get("suggested_lokasyon", ""),
                    excerpt=rewritten.get("suggested_excerpt", ""),
                    category_slug=category_slug,
                    status="publish",
                    featured_media_id=self.pick_photo_media_id(done),
                )
                if pub.get("success"):
                    published += 1
                    entry["status"] = "published"
                    entry["title"] = rewritten["suggested_title"]
                    entry["link"] = pub.get("link", "")
                    entry["post_id"] = pub.get("post_id")
                    entry["live"] = pub.get("live", False)
                    entry["engine"] = rewritten.get("engine", "")
                else:
                    failed += 1
                    entry["status"] = "failed"
                    entry["error"] = pub.get("error", "Yayın hatası")
            else:
                entry["status"] = "rewritten"
                entry["title"] = rewritten.get("suggested_title", "")
                entry["engine"] = rewritten.get("engine", "")

            done += 1
            results.append(entry)
            self._update_job(job_id, done=done, published=published, failed=failed, results=results[-10:])
            if delay_sec > 0 and done < batch_size:
                time.sleep(delay_sec)

        self._update_job(
            job_id,
            status="completed",
            done=done,
            published=published,
            failed=failed,
            results=results[-20:],
        )


storyforge = StoryForgeV2()
