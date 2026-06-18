"""IndexNow API — gerçek bildirim."""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from app.moduller.indexing_fix import INDEXNOW_KEY, _site_url


def bildirim_gonder(url: str = "") -> dict:
    site = _site_url()
    target = (url or site).strip()
    if not target:
        return {"status": "hata", "hata": "URL belirtilmedi"}

    host = urlparse(site).netloc
    payload = {
        "host": host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{site}/{INDEXNOW_KEY}.txt",
        "urlList": [target],
    }
    try:
        r = requests.post("https://www.bing.com/indexnow", json=payload, timeout=25)
        ok = r.status_code in (200, 202)
        return {
            "url": target,
            "durum": "IndexNow bildirimi gönderildi" if ok else f"IndexNow yanıt: HTTP {r.status_code}",
            "tahmini_sure": "1-24 saat",
            "http_status": r.status_code,
            "simulasyon": False,
        }
    except requests.RequestException as e:
        return {"url": target, "durum": "hata", "hata": str(e), "simulasyon": False}
