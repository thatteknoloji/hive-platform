"""SEO Content Agent — AI makale üret + WP yayınla/zamanla."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from typing import Any

from .backlink_hub import log_activity, load_state, save_state
from .ollama_helper import generate
from .modul_base import modul_hash, modul_sec, simdi
from .wordpress_api import wp_api


def _generate_article(konu: str, keyword: str, kelime: int = 700) -> tuple[str, str, bool]:
    prompt = (
        f"Türkçe SEO uyumlu bir blog makalesi yaz. Konu: {konu}. Anahtar kelime: {keyword}. "
        f"Yaklaşık {kelime} kelime. H1 başlık, 3-4 H2 alt başlık, giriş ve sonuç paragrafları. "
        f"HTML formatında (<h2>, <p>, <ul> kullan). Anahtar kelimeyi doğal şekilde 3-5 kez geçir."
    )
    content, used = generate(prompt, max_tokens=2000)
    if used and content:
        title = konu[:80]
        if "<h1>" in content.lower():
            import re
            m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.I | re.S)
            if m:
                title = re.sub(r"<[^>]+>", "", m.group(1)).strip()[:80]
        return title, content, True

    h = modul_hash(f"{konu}{keyword}")
    title = konu or keyword
    paras = [
        f"<p>{keyword} konusunda kapsamlı bir rehber hazırladık. {konu} hakkında bilmeniz gerekenleri bu yazıda bulacaksınız.</p>",
        f"<h2>{keyword} Nedir?</h2><p>{keyword}, günümüzde önemli bir konu haline gelmiştir. Doğru bilgi ve güncel kaynaklarla hareket etmek kritiktir.</p>",
        f"<h2>Pratik Öneriler</h2><ul><li>Güvenilir kaynakları takip edin</li><li>{keyword} ile ilgili güncel gelişmeleri izleyin</li><li>Uzman görüşlerine başvurun</li></ul>",
        f"<h2>Sonuç</h2><p>{konu} ve {keyword} hakkında özetle, bilinçli tercihler yapmak uzun vadede fayda sağlar.</p>",
    ]
    return title, "\n".join(paras), False


def generate_and_publish(
    konu: str = "",
    keyword: str = "",
    publish: bool = True,
    status: str = "publish",
) -> dict[str, Any]:
    if not konu and not keyword:
        return {"status": "hata", "hata": "Konu veya anahtar kelime gerekli"}

    konu = konu or keyword
    keyword = keyword or konu
    title, content, ai_used = _generate_article(konu, keyword)

    wp = wp_api()
    if not wp.connected:
        return {
            "status": "hata",
            "hata": "WordPress bağlantısı yok — WP Manager'dan giriş yapın",
            "onizleme": {"title": title, "content": content[:500]},
        }

    post_status = status if publish else "draft"
    res = wp.create_post(title=title, content=content, status=post_status)
    if not (res.get("success") or res.get("id")):
        return {"status": "hata", "hata": res.get("error", "Yayın başarısız"), "title": title}

    out = {
        "status": "aktif",
        "title": title,
        "post_id": res.get("id"),
        "url": res.get("link", ""),
        "yayin": post_status,
        "ai_ollama": ai_used,
        "tarih": simdi(),
    }
    log_activity("seo_content_agent", "SEO Content Agent - Yayınla", {"konu": konu, "keyword": keyword}, out)
    return out


def _run_scheduled(job_id: str) -> None:
    st = load_state()
    job = next((j for j in st["scheduled_posts"] if j["id"] == job_id), None)
    if not job:
        return
    delay = max(0, job.get("publish_at_ts", 0) - time.time())
    if delay > 0:
        time.sleep(min(delay, 86400))
    result = generate_and_publish(
        konu=job.get("konu", ""),
        keyword=job.get("keyword", ""),
        publish=True,
    )
    st = load_state()
    for j in st["scheduled_posts"]:
        if j["id"] == job_id:
            j["durum"] = "yayinlandi" if result.get("status") == "aktif" else "hata"
            j["sonuc"] = result
            j["bitis"] = simdi()
            break
    save_state(st)


def schedule_post(
    konu: str = "",
    keyword: str = "",
    publish_at: str = "",
    delay_minutes: int = 60,
) -> dict[str, Any]:
    if not konu and not keyword:
        return {"status": "hata", "hata": "Konu veya anahtar kelime gerekli"}

    if publish_at:
        try:
            ts = datetime.fromisoformat(publish_at.replace("Z", "")).timestamp()
        except ValueError:
            return {"status": "hata", "hata": "Geçersiz tarih formatı (ISO 8601 kullanın)"}
    else:
        ts = time.time() + delay_minutes * 60

    job_id = f"seo_{modul_hash(simdi()) % 1000000:06d}"
    job = {
        "id": job_id,
        "konu": konu or keyword,
        "keyword": keyword or konu,
        "publish_at": datetime.fromtimestamp(ts).isoformat(),
        "publish_at_ts": ts,
        "durum": "zamanlandi",
        "olusturuldu": simdi(),
    }
    st = load_state()
    st["scheduled_posts"].append(job)
    save_state(st)

    threading.Thread(target=_run_scheduled, args=(job_id,), daemon=True).start()

    out = {
        "status": "aktif",
        "job_id": job_id,
        "yayin_zamani": job["publish_at"],
        "mesaj": f"Makale {job['publish_at']} için zamanlandı",
    }
    log_activity("seo_content_agent", "SEO Content Agent - Zamanla", job, out)
    return out


def list_scheduled() -> dict[str, Any]:
    st = load_state()
    return {"status": "aktif", "zamanlanmis": st.get("scheduled_posts", [])[-30:]}
