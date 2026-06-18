import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi, TURKCE_ISIMLER

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "review.json"

def _yukle():
    path = os.path.join(DATA_DIR, DOSYA)
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []

def _kaydet(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, DOSYA), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def topla(url):
    veri = _yukle()
    hash_key = url + simdi()
    yorum_sayisi = 3 + modul_hash(hash_key + "count") % 18
    eklenen = 0
    for i in range(yorum_sayisi):
        rev_hash = hash_key + str(i)
        yorum = {
            "id": modul_hash(rev_hash + "id"),
            "url": url,
            "kullanici": modul_sec(rev_hash + "user", TURKCE_ISIMLER),
            "puan": 1 + modul_hash(rev_hash + "rating") % 5,
            "baslik": modul_sec(rev_hash + "title", ["Harika", "İyi", "Ortalama", "Kötü", "Mükemmel", "Fena değil", "Tavsiye ederim", "Hayal kırıklığı"]),
            "yorum": modul_sec(rev_hash + "body", ["Çok memnun kaldım, teşekkürler.", "Beklentilerimi karşıladı.", "Ortalama bir deneyimdi.", "Geliştirilmesi gerekiyor.", "Kesinlikle tavsiye ederim!", "Fiyat/performans ürünü.", "Hızlı kargo ve kaliteli ürün.", "Sorunlar var, ilgilenilmiyor."]),
            "tarih": simdi(),
            "yanitlandi": False,
            "yanit": None,
            "faydali_bulunma": modul_hash(rev_hash + "help") % 50
        }
        mevcut_idler = {r["id"] for r in veri}
        if yorum["id"] not in mevcut_idler:
            veri.append(yorum)
            eklenen += 1
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"{url} için {eklenen} yorum toplandı", "eklenen": eklenen}

def listele():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Henüz yorum yok", "yorumlar": []}
    return {"status": "ok", "toplam": len(veri), "yorumlar": sorted(veri, key=lambda r: r["tarih"], reverse=True)}

def yanitla(review_id, yanit):
    veri = _yukle()
    for r in veri:
        if r["id"] == review_id:
            r["yanit"] = yanit
            r["yanitlandi"] = True
            r["yanit_tarihi"] = simdi()
            _kaydet(veri)
            return {"status": "ok", "mesaj": "Yorum yanıtlandı", "yorum": r}
    return {"status": "hata", "mesaj": f"Yorum bulunamadı: {review_id}"}

def istatistik():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Veri yok", "toplam_yorum": 0, "ortalama_puan": 0}
    toplam = len(veri)
    ortalama = round(sum(r["puan"] for r in veri) / toplam, 2)
    puan_dagilimi = {}
    for r in veri:
        puan_dagilimi[r["puan"]] = puan_dagilimi.get(r["puan"], 0) + 1
    yanitli_sayisi = sum(1 for r in veri if r.get("yanitlandi"))
    en_faydali = max(veri, key=lambda r: r.get("faydali_bulunma", 0))
    return {
        "status": "ok",
        "toplam_yorum": toplam,
        "ortalama_puan": ortalama,
        "puan_dagilimi": dict(sorted(puan_dagilimi.items())),
        "yanitlanma_orani": round(yanitli_sayisi / toplam * 100, 1) if toplam else 0,
        "en_faydali_yorum": {"id": en_faydali["id"], "kullanici": en_faydali["kullanici"], "faydali": en_faydali.get("faydali_bulunma", 0)},
        "memnuniyet_yuzde": round(sum(1 for r in veri if r["puan"] >= 4) / toplam * 100, 1) if toplam else 0
    }
