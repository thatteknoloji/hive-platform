import os, json
from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "log.json"
HIVEDATA_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hive_data.json")

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

def _hive_loglari():
    if not os.path.exists(HIVEDATA_DOSYA):
        return []
    try:
        with open(HIVEDATA_DOSYA, "r") as f:
            data = json.load(f)
        return data.get("logs", []) if isinstance(data, dict) else data
    except:
        return []

def listele(module_id=None, seviye=None):
    loglar = _hive_loglari()
    sonuc = loglar[:]
    if module_id:
        sonuc = [l for l in sonuc if l.get("mod_id") == module_id or l.get("module_id") == module_id]
    if seviye:
        sonuc = [l for l in sonuc if l.get("seviye") == seviye or l.get("level") == seviye]
    ozet = []
    for l in sonuc[:200]:
        ozet.append({
            "id": l.get("id", modul_hash(str(l))),
            "mod_id": l.get("mod_id", l.get("module_id", "bilinmiyor")),
            "tarih": l.get("timestamp", l.get("tarih", "bilinmiyor")),
            "seviye": l.get("seviye", l.get("level", "info")),
            "mesaj": l.get("mesaj", str(l.get("output", {}).get("status", "-")))
        })
    return {"status": "ok", "toplam": len(loglar), "filtrelenen": len(sonuc), "loglar": ozet}

def detay(log_id):
    loglar = _hive_loglari()
    for l in loglar:
        lid = str(l.get("id", modul_hash(str(l))))
        if lid == str(log_id):
            return {"status": "ok", "detay": l}
    return {"status": "hata", "mesaj": "Log bulunamadi"}

def temizle():
    _kaydet([])
    return {"status": "ok", "mesaj": "Log dosyasi temizlendi"}

def ara(sorgu):
    loglar = _hive_loglari()
    sonuc = []
    for l in loglar:
        metin = json.dumps(l, ensure_ascii=False)
        if sorgu.lower() in metin.lower():
            sonuc.append({
                "id": l.get("id", modul_hash(str(l))),
                "mod_id": l.get("mod_id", l.get("module_id", "bilinmiyor")),
                "tarih": l.get("timestamp", l.get("tarih", "bilinmiyor")),
                "eslesme": sorgu
            })
    return {"status": "ok", "sorgu": sorgu, "eslesme_sayisi": len(sonuc), "sonuclar": sonuc[:100]}

def istatistik():
    loglar = _hive_loglari()
    modul_sayilari = {}
    seviye_sayilari = {}
    for l in loglar:
        mid = l.get("mod_id", l.get("module_id", "bilinmiyor"))
        modul_sayilari[mid] = modul_sayilari.get(mid, 0) + 1
        seviye = l.get("seviye", l.get("level", "info"))
        seviye_sayilari[seviye] = seviye_sayilari.get(seviye, 0) + 1
    return {
        "status": "ok",
        "toplam_log": len(loglar),
        "benzersiz_modul": len(modul_sayilari),
        "modul_dagilimi": modul_sayilari,
        "seviye_dagilimi": seviye_sayilari,
        "son_log": loglar[-1] if loglar else None
    }
