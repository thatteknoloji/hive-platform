import os, json
from datetime import datetime, timedelta
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "conversion.json"

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

def takip_et(url):
    veri = _yukle()
    hash_key = url + simdi()
    donusum = {
        "id": modul_hash(hash_key + "id"),
        "url": url,
        "tarih": simdi(),
        "tamamlanma": modul_sec(hash_key + "comp", ["kayit", "satinalma", "indirme", "form_gonderim", "teklif_talebi"]),
        "deger": round(10 + modul_yuzde(hash_key + "val", 0, 990), 2),
        "kaynak": modul_sec(hash_key + "src", ["organik", "reklam", "email", "sosyal", "direkt"]),
        "donusum_orani": round(1 + modul_yuzde(hash_key + "cr", 0, 14), 2),
        "toplam_ziyaret": 50 + modul_hash(hash_key + "vis") % 950,
        "toplam_donusum": 1 + modul_hash(hash_key + "conv") % 50
    }
    veri.append(donusum)
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Dönüşüm takip ediliyor: {url}", "donusum": donusum}

def listele():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Henüz dönüşüm kaydı yok", "donusumler": []}
    return {"status": "ok", "toplam": len(veri), "donusumler": sorted(veri, key=lambda d: d["tarih"], reverse=True)}

def istatistik():
    veri = _yukle()
    if not veri:
        return {"status": "bos", "mesaj": "Veri yok", "toplam_donusum": 0, "ortalama_donusum_orani": 0}
    toplam_donusum = sum(d["toplam_donusum"] for d in veri)
    toplam_ziyaret = sum(d["toplam_ziyaret"] for d in veri)
    ortalama_cr = round(sum(d["donusum_orani"] for d in veri) / len(veri), 2)
    toplam_deger = round(sum(d["deger"] for d in veri), 2)
    kaynak_dagilimi = {}
    for d in veri:
        kaynak_dagilimi[d["kaynak"]] = kaynak_dagilimi.get(d["kaynak"], 0) + 1
    return {
        "status": "ok",
        "toplam_donusum": toplam_donusum,
        "toplam_ziyaret": toplam_ziyaret,
        "genel_donusum_orani": round((toplam_donusum / toplam_ziyaret * 100) if toplam_ziyaret else 0, 2),
        "ortalama_donusum_orani": ortalama_cr,
        "toplam_parasal_deger": toplam_deger,
        "kaynak_dagilimi": kaynak_dagilimi,
        "kayit_sayisi": len(veri)
    }

def hedef_ekle(hedef):
    veri = _yukle()
    if any(h.get("hedef") == hedef for h in veri if h.get("hedef")):
        return {"status": "hata", "mesaj": f"Hedef zaten mevcut: {hedef}"}
    kayit = {
        "id": modul_hash(hedef),
        "hedef": hedef,
        "olusturma": simdi(),
        "hedef_deger": round(10 + modul_yuzde(hedef, 0, 990), 2)
    }
    veri.append(kayit)
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Hedef eklendi: {hedef}", "kayit": kayit}

def hedef_sil(hedef):
    veri = _yukle()
    once = len(veri)
    veri = [h for h in veri if h.get("hedef") != hedef]
    if len(veri) == once:
        return {"status": "hata", "mesaj": f"Hedef bulunamadı: {hedef}"}
    _kaydet(veri)
    return {"status": "ok", "mesaj": f"Hedef silindi: {hedef}"}
