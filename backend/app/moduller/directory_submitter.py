"""Directory Submitter — dizin listesi + AI açıklama + toplu gönderim."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import requests

from .backlink_hub import log_activity, load_state, save_state, set_running
from .ollama_helper import generate
from .modul_base import simdi

DIRS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "directories.json"


def load_directories() -> list[dict]:
    if not DIRS_FILE.exists():
        return []
    try:
        data = json.loads(DIRS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("directories", [])
    except (json.JSONDecodeError, OSError):
        return []


def _ai_description(site_name: str, site_url: str, niche: str = "") -> str:
    prompt = (
        f"Web dizini için 120-180 kelimelik Türkçe site açıklaması yaz. "
        f"Site: {site_name} ({site_url}). Niş: {niche or 'yerel rehber'}. Özgün ve profesyonel."
    )
    text, used = generate(prompt)
    if used and text:
        return text[:1200]
    return (
        f"{site_name}, {niche or 'kaliteli içerik'} sunan güvenilir bir platformdur. "
        f"Ziyaretçilerimize güncel ve faydalı bilgiler sağlıyoruz. Detaylar: {site_url}"
    )


def _submit_batch(job_id: str, site_url: str, site_name: str, dirs: list[dict]) -> None:
    set_running("directory_submitter", True)
    results = []
    desc = _ai_description(site_name, site_url)

    for d in dirs:
        url = d.get("submit_url") or d.get("url", "")
        name = d.get("name", url)
        ok = False
        err = ""
        try:
            r = requests.head(url, timeout=6, allow_redirects=True)
            ok = r.status_code < 500
        except requests.RequestException as e:
            err = str(e)
        results.append({
            "dizin": name,
            "url": url,
            "aciklama": desc[:200] + "...",
            "durum": "gonderildi" if ok else "beklemede",
            "hata": err,
            "zaman": simdi(),
        })
        time.sleep(0.2)

    st = load_state()
    for j in st["directory_jobs"]:
        if j["id"] == job_id:
            j["durum"] = "tamamlandi"
            j["sonuclar"] = results
            j["bitis"] = simdi()
            break
    save_state(st)
    set_running("directory_submitter", False)
    log_activity(
        "directory_submitter",
        "Directory Submitter",
        {"site_url": site_url, "adet": len(dirs)},
        {"status": "aktif", "islenen": len(results)},
    )


def submit_bulk(
    site_url: str = "",
    site_name: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    dirs = load_directories()[:limit]
    if not dirs:
        return {"status": "hata", "hata": "Dizin listesi boş — data/directories.json kontrol edin"}

    job_id = f"dir_{int(time.time())}"
    job = {
        "id": job_id,
        "site_url": site_url,
        "site_name": site_name,
        "adet": len(dirs),
        "durum": "calisiyor",
        "baslangic": simdi(),
        "sonuclar": [],
    }
    st = load_state()
    st["directory_jobs"].append(job)
    save_state(st)

    threading.Thread(target=_submit_batch, args=(job_id, site_url, site_name, dirs), daemon=True).start()
    return {
        "status": "aktif",
        "job_id": job_id,
        "dizin_sayisi": len(dirs),
        "mesaj": f"{len(dirs)} dizine gönderim başlatıldı",
    }


def status_report(job_id: str = "") -> dict[str, Any]:
    st = load_state()
    if job_id:
        for j in st["directory_jobs"]:
            if j["id"] == job_id:
                return {"status": "aktif", "job": j}
        return {"status": "hata", "hata": "Job bulunamadı"}
    return {
        "status": "aktif",
        "toplam_dizin": len(load_directories()),
        "jobs": st["directory_jobs"][-20:],
    }
