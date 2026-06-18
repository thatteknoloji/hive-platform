import os, json
from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "schedule.json"

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

def olustur(modul_id, zaman, parametreler=None):
    takvim = _yukle()
    kayit = {
        "id": f"schedule_{modul_hash(str(datetime.now().timestamp()))}",
        "modul_id": modul_id,
        "zaman": zaman,
        "parametreler": parametreler or {},
        "olusturulma": simdi(),
        "son_calisma": None,
        "sonraki_calisma": zaman,
        "durum": "aktif"
    }
    takvim.append(kayit)
    _kaydet(takvim)
    return {"status": "ok", "kayit": kayit}

def listele():
    return {"status": "ok", "toplam": len(_yukle()), "kayitlar": _yukle()}

def sil(schedule_id):
    takvim = _yukle()
    yeni = [k for k in takvim if k["id"] != schedule_id]
    if len(yeni) == len(takvim):
        return {"status": "hata", "mesaj": "Schedule bulunamadi"}
    _kaydet(yeni)
    return {"status": "ok", "mesaj": "Schedule silindi"}

def duraklat(schedule_id):
    takvim = _yukle()
    for k in takvim:
        if k["id"] == schedule_id:
            k["durum"] = "duraklatildi"
            _kaydet(takvim)
            return {"status": "ok", "mesaj": "Schedule duraklatildi"}
    return {"status": "hata", "mesaj": "Schedule bulunamadi"}

def devam_ettir(schedule_id):
    takvim = _yukle()
    for k in takvim:
        if k["id"] == schedule_id:
            k["durum"] = "aktif"
            _kaydet(takvim)
            return {"status": "ok", "mesaj": "Schedule tekrar aktif"}
    return {"status": "hata", "mesaj": "Schedule bulunamadi"}
