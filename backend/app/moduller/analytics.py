import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "analytics.json"

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

def raporla(url):
    veri = _yukle()
    mevcut = next((r for r in veri if r["url"] == url), None)
    hash_key = url + simdi()
    rapor = {
        "url": url,
        "tarih": simdi(),
        "sayfa_goruntuleme": 100 + modul_hash(hash_key + "pv") % 9900,
        "hemen_cikma_orani": round(20 + modul_yuzde(hash_key + "bounce", 0, 50), 1),
        "ortalama_oturum_suresi_sn": 30 + modul_hash(hash_key + "dur") % 270,
        "sayfa_basina_ziyaret": round(1 + modul_yuzde(hash_key + "ppv", 0, 5), 1),
        "en_populer_sayfalar": [
            f"/{modul_sec(hash_key + 'p1', ['urun', 'hakkimizda', 'iletisim', 'blog', 'ana-sayfa'])}",
            f"/{modul_sec(hash_key + 'p2', ['hizmetler', 'referanslar', 'sss', 'fiyatlandirma', 'ekip'])}",
            f"/{modul_sec(hash_key + 'p3', ['kariyer', 'gizlilik', 'kosullar', 'yardim', 'sikayet'])}"
        ],
        "ziyaretci_kaynak": modul_sec(hash_key + "src", ["organik", "direkt", "sosyal", "referans", "email"]),
        "masaustu_yuzde": round(40 + modul_yuzde(hash_key + "desk", 0, 40), 1),
        "mobil_yuzde": round(20 + modul_yuzde(hash_key + "mob", 0, 30), 1),
        "tablet_yuzde": round(1 + modul_yuzde(hash_key + "tab", 0, 15), 1)
    }
    if mevcut:
        veri[veri.index(mevcut)] = rapor
    else:
        veri.append(rapor)
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Analitik raporu oluşturuldu: {url}", "rapor": rapor}

def tum_raporlar():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Henüz analitik raporu yok", "raporlar": []}
    return {"status": "ok", "toplam": len(veri), "raporlar": sorted(veri, key=lambda r: r["tarih"], reverse=True)}

def sil(url):
    veri = _yukle()
    once = len(veri)
    veri = [r for r in veri if r["url"] != url]
    if len(veri) == once:
        return {"status": "hata", "mesaj": f"Rapor bulunamadı: {url}"}
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Rapor silindi: {url}"}

def ozet():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Veri yok", "toplam_sayfa_goruntuleme": 0, "ortalama_hemen_cikma": 0}
    toplam_pv = sum(r["sayfa_goruntuleme"] for r in veri)
    ortalama_bounce = round(sum(r["hemen_cikma_orani"] for r in veri) / len(veri), 1)
    ortalama_sure = round(sum(r["ortalama_oturum_suresi_sn"] for r in veri) / len(veri))
    en_iyi = max(veri, key=lambda r: r["sayfa_goruntuleme"])
    return {
        "status": "ok",
        "toplam_sayfa_goruntuleme": toplam_pv,
        "ortalama_hemen_cikma": ortalama_bounce,
        "ortalama_oturum_suresi_sn": ortalama_sure,
        "rapor_sayisi": len(veri),
        "en_populer_sayfa": en_iyi["url"],
        "en_populer_goruntuleme": en_iyi["sayfa_goruntuleme"]
    }
