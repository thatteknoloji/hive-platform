"""Web Scraper — gerçek HTTP/HTML kazıma (requests + BeautifulSoup)."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from .modul_base import modul_export_csv, modul_export_json, simdi
from .scrape_utils import fetch_html, normalize_url, parse_page, same_domain

STATE_FILE = Path(__file__).resolve().parent.parent / "webscraper_state.json"
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"


def _load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("jobs", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"jobs": []}


def _save_state(state: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def health() -> dict[str, Any]:
    return {
        "success": True,
        "module": "webscraper",
        "engine": "requests+beautifulsoup",
        "robots_respect": True,
        "jobs_count": len(_load_state().get("jobs") or []),
    }


def kazi(url: str = "", derinlik: int = 1, max_pages: int = 10) -> dict[str, Any]:
    try:
        start = normalize_url(url)
        if not start:
            return {"status": "hata", "hata": "URL belirtilmedi"}

        depth_limit = max(1, min(3, int(derinlik or 1)))
        page_limit = max(1, min(25, int(max_pages or 10)))

        queue: deque[tuple[str, int]] = deque([(start, 0)])
        visited: set[str] = set()
        sayfalar: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []

        while queue and len(sayfalar) < page_limit:
            cur, depth = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)

            html, err = fetch_html(cur)
            if err or not html:
                errors.append({"url": cur, "error": err or "boş yanıt"})
                continue

            parsed = parse_page(html, cur)
            sayfalar.append({
                "url": cur,
                "depth": depth,
                **parsed,
                "bulunan_veri": len(parsed.get("links", [])) + len(parsed.get("images", [])) + len(parsed.get("headings", [])),
                "tipler": _detect_types(parsed),
            })

            if depth < depth_limit:
                for link in parsed.get("internal_links") or []:
                    if link not in visited and same_domain(start, link):
                        queue.append((link, depth + 1))

        if not sayfalar:
            return {
                "status": "hata",
                "hata": "fetch_failed",
                "mesaj": errors[0]["error"] if errors else "Sayfa alınamadı",
                "url": start,
                "errors": errors,
            }

        job = {
            "id": f"ws-{len(sayfalar)}-{simdi()}",
            "url": start,
            "derinlik": depth_limit,
            "taranan_sayfa": len(sayfalar),
            "at": simdi(),
        }
        st = _load_state()
        st.setdefault("jobs", []).insert(0, job)
        st["jobs"] = st["jobs"][:100]
        _save_state(st)

        return {
            "success": True,
            "url": start,
            "derinlik": depth_limit,
            "taranan_sayfa": len(sayfalar),
            "toplam_veri_noktasi": sum(s.get("bulunan_veri", 0) for s in sayfalar),
            "toplam_link": sum(len(s.get("links") or []) for s in sayfalar),
            "toplam_gorsel": sum(len(s.get("images") or []) for s in sayfalar),
            "kaynak": "http_scrape",
            "sayfalar": sayfalar,
            "ornek_veri": [
                {
                    "sayfa": s["url"],
                    "baslik": s.get("title", ""),
                    "bulunan_veri": s.get("bulunan_veri", 0),
                    "tipler": s.get("tipler", []),
                }
                for s in sayfalar[:8]
            ],
            "errors": errors or None,
        }
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def _detect_types(parsed: dict[str, Any]) -> list[str]:
    types: list[str] = []
    if parsed.get("title"):
        types.append("başlık")
    if parsed.get("meta_description"):
        types.append("meta açıklama")
    if parsed.get("images"):
        types.append("resim URL")
    if parsed.get("links"):
        types.append("link")
    if parsed.get("paragraphs") or parsed.get("text_excerpt"):
        types.append("içerik")
    if parsed.get("headings"):
        types.append("başlık yapısı")
    if parsed.get("emails"):
        types.append("e-posta")
    if parsed.get("phones"):
        types.append("telefon")
    return types


def export(url: str, format: str = "csv", derinlik: int = 1) -> dict[str, Any]:
    try:
        sonuc = kazi(url, derinlik=derinlik, max_pages=10)
        if sonuc.get("status") == "hata":
            return sonuc
        rows = []
        for s in sonuc.get("sayfalar") or []:
            rows.append({
                "url": s.get("url"),
                "title": s.get("title"),
                "meta_description": s.get("meta_description"),
                "word_count": s.get("word_count"),
                "links": len(s.get("links") or []),
                "images": len(s.get("images") or []),
                "emails": ", ".join(s.get("emails") or []),
            })
        if format == "json":
            payload = modul_export_json(rows)
        else:
            payload = modul_export_csv(rows)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ext = "json" if format == "json" else "csv"
        safe_ts = simdi().replace(" ", "_").replace(":", "-")
        path = REPORTS_DIR / f"webscraper-{safe_ts}.{ext}"
        path.write_text(payload, encoding="utf-8")
        return {"format": format, "icerik": payload, "path": str(path), "rows": len(rows)}
    except Exception as e:
        return {"status": "hata", "hata": str(e)}


def list_jobs(limit: int = 20) -> dict[str, Any]:
    jobs = (_load_state().get("jobs") or [])[: max(1, min(limit, 50))]
    return {"success": True, "count": len(jobs), "jobs": jobs}
