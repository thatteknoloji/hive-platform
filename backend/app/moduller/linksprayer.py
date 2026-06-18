"""LinkSprayer — AI destekli yorum/backlink kampanyası (Therenizm/LinkSprayer mantığı)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import requests

from .backlink_hub import log_activity, load_state, save_state, set_running
from .ollama_helper import generate
from .modul_base import modul_hash, modul_sec, simdi

TARGETS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "linksprayer_targets.json"


def _default_targets() -> list[dict]:
    return [
        {"url": "https://wordpress.org/support/", "tip": "forum", "aktif": True},
        {"url": "https://www.reddit.com/r/seo/", "tip": "forum", "aktif": True},
        {"url": "https://medium.com/", "tip": "blog", "aktif": True},
    ]


def _load_targets() -> list[dict]:
    if TARGETS_FILE.exists():
        try:
            return json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    targets = _default_targets()
    TARGETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TARGETS_FILE.write_text(json.dumps(targets, indent=2), encoding="utf-8")
    return targets


def _ai_comment(hedef_url: str, keyword: str, site_url: str) -> str:
    prompt = (
        f"Türkçe, doğal, spam gibi görünmeyen kısa bir blog yorumu yaz (max 2 cümle). "
        f"Anahtar kelime: {keyword}. Site: {site_url}. Bağlam: {hedef_url}. "
        f"Sadece yorum metnini yaz, HTML yok."
    )
    text, used = generate(prompt)
    if used and text:
        return text[:400]
    h = modul_hash(f"{hedef_url}{keyword}")
    templates = [
        f"{keyword} hakkında faydalı bir kaynak, {site_url} adresine de göz atabilirsiniz.",
        f"Konuyla ilgili detaylı bilgi için {site_url} öneririm.",
        f"Güzel yazı, {keyword} konusunda {site_url} de yardımcı olabilir.",
    ]
    return modul_sec(f"ls_{h}", templates)


def _run_campaign(campaign_id: str, hedef_url: str, keyword: str, site_url: str, adet: int) -> None:
    set_running("linksprayer", True)
    targets = [t for t in _load_targets() if t.get("aktif", True)][:adet]
    results = []
    for i, t in enumerate(targets):
        comment = _ai_comment(t["url"], keyword, site_url)
        ok = False
        err = ""
        try:
            r = requests.get(t["url"], timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            ok = r.status_code < 400
        except requests.RequestException as e:
            err = str(e)
        results.append({
            "hedef": t["url"],
            "yorum": comment,
            "durum": "hazir" if ok else "beklemede",
            "hata": err,
            "zaman": simdi(),
        })
        time.sleep(0.3)

    st = load_state()
    for c in st["campaigns"]:
        if c["id"] == campaign_id:
            c["durum"] = "tamamlandi"
            c["sonuclar"] = results
            c["bitis"] = simdi()
            break
    save_state(st)
    set_running("linksprayer", False)
    log_activity(
        "linksprayer",
        "LinkSprayer - Kampanya",
        {"hedef_url": hedef_url, "keyword": keyword},
        {"status": "aktif", "kampanya_id": campaign_id, "islenen": len(results)},
    )


def start_campaign(hedef_url: str = "", keyword: str = "", site_url: str = "https://www.balkutusu.com", adet: int = 10) -> dict[str, Any]:
    if not keyword:
        return {"status": "hata", "hata": "Anahtar kelime gerekli"}
    campaign_id = f"ls_{modul_hash(simdi()) % 1000000:06d}"
    campaign = {
        "id": campaign_id,
        "hedef_url": hedef_url,
        "keyword": keyword,
        "site_url": site_url,
        "adet": adet,
        "durum": "calisiyor",
        "baslangic": simdi(),
        "sonuclar": [],
    }
    st = load_state()
    st["campaigns"].append(campaign)
    st["campaigns"] = st["campaigns"][-100:]
    save_state(st)

    threading.Thread(
        target=_run_campaign,
        args=(campaign_id, hedef_url, keyword, site_url, adet),
        daemon=True,
    ).start()

    return {
        "status": "aktif",
        "kampanya_id": campaign_id,
        "mesaj": f"LinkSprayer kampanyası başlatıldı ({adet} hedef)",
        "repo": "Therenizm/LinkSprayer entegrasyonu (Ollama AI yorum)",
    }


def campaign_status(campaign_id: str = "") -> dict[str, Any]:
    st = load_state()
    if campaign_id:
        for c in st["campaigns"]:
            if c["id"] == campaign_id:
                return {"status": "aktif", "kampanya": c}
        return {"status": "hata", "hata": "Kampanya bulunamadı"}
    return {"status": "aktif", "kampanyalar": st["campaigns"][-20:]}
