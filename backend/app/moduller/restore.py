import os, json
from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "restore.json"
BACKUP_DOSYA = "backup.json"

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

def _yedekleri_yukle():
    path = os.path.join(DATA_DIR, BACKUP_DOSYA)
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []

def onizle(yedek_id):
    yedekler = _yedekleri_yukle()
    for y in yedekler:
        if y.get("id") == yedek_id:
            veri = y.get("veri", [])
            return {
                "status": "ok",
                "yedek_id": yedek_id,
                "module_id": y.get("module_id"),
                "tarih": y.get("tarih"),
                "kayit_sayisi": len(veri) if isinstance(veri, list) else 1,
                "ornek_veri": veri[:3] if isinstance(veri, list) else veri,
                "boyut": y.get("boyut", 0)
            }
    return {"status": "hata", "mesaj": "Yedek bulunamadi"}

def geri_yukle(yedek_id):
    yedekler = _yedekleri_yukle()
    hedef = None
    for y in yedekler:
        if y.get("id") == yedek_id:
            hedef = y
            break
    if not hedef:
        return {"status": "hata", "mesaj": "Yedek bulunamadi"}
    mod_id = hedef.get("module_id")
    veri = hedef.get("veri")
    if veri is None:
        return {"status": "hata", "mesaj": "Yedekte veri bulunamadi"}
    hedef_dosya = os.path.join(DATA_DIR, f"{mod_id}.json")
    try:
        with open(hedef_dosya, "w") as f:
            json.dump(veri, f, indent=2, ensure_ascii=False)
    except:
        return {"status": "hata", "mesaj": "Dosyaya yazilamadi"}
    geri_yuklemeler = _yukle()
    kayit = {
        "id": f"restore_{modul_hash(str(datetime.now().timestamp()))}",
        "yedek_id": yedek_id,
        "module_id": mod_id,
        "tarih": simdi(),
        "kayit_sayisi": len(veri) if isinstance(veri, list) else 1,
        "durum": "basarili"
    }
    geri_yuklemeler.append(kayit)
    _kaydet(geri_yuklemeler)
    return {"status": "ok", "mesaj": f"{mod_id} basariyla geri yuklendi", "kayit": kayit}

def listele():
    kayitlar = _yukle()
    return {"status": "ok", "toplam": len(kayitlar), "geri_yuklemeler": kayitlar}

def sil(geri_yukleme_id):
    kayitlar = _yukle()
    yeni = [k for k in kayitlar if k["id"] != geri_yukleme_id]
    if len(yeni) == len(kayitlar):
        return {"status": "hata", "mesaj": "Geri yukleme kaydi bulunamadi"}
    _kaydet(yeni)
    return {"status": "ok", "mesaj": "Geri yukleme kaydi silindi"}
