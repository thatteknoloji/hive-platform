import os, json, time
from datetime import datetime
from .modul_base import modul_hash, modul_sec, modul_yuzde, simdi

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "talon_data")
DOSYA = "monitor.json"

def _yukle():
    path = os.path.join(DATA_DIR, DOSYA)
    if not os.path.exists(path):
        return {"kayitlar": [], "ayarlar": {"kontrol_araligi": 60, "bildirim": True, "kritik_esik": 90}}
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {"kayitlar": [], "ayarlar": {"kontrol_araligi": 60, "bildirim": True, "kritik_esik": 90}}

def _kaydet(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, DOSYA), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def kontrol_et():
    durum = {
        "timestamp": simdi(),
        "backend": "aktif" if os.path.exists(os.path.join(DATA_DIR, "..", "app", "hive_data.json")) else "kontrol_gerekli",
        "talon_data": "ok" if os.path.exists(DATA_DIR) else "eksik",
        "modul_sayisi": len([m for m in os.listdir(os.path.join(DATA_DIR, "..", "app", "moduller")) if m.endswith(".py")]) if os.path.exists(os.path.join(DATA_DIR, "..", "app", "moduller")) else 0,
        "hive_data_boyut": os.path.getsize(os.path.join(DATA_DIR, "..", "app", "hive_data.json")) if os.path.exists(os.path.join(DATA_DIR, "..", "app", "hive_data.json")) else 0,
        "dsk_kullanim": _dsk_kullanim()
    }
    monitor = _yukle()
    kayit = {
        "id": f"mon_{modul_hash(str(datetime.now().timestamp()))}",
        "timestamp": simdi(),
        "durum": durum
    }
    monitor.setdefault("kayitlar", []).append(kayit)
    if len(monitor["kayitlar"]) > 1000:
        monitor["kayitlar"] = monitor["kayitlar"][-1000:]
    _kaydet(monitor)
    return {"status": "ok", "kontrol": durum}

def _dsk_kullanim():
    try:
        import shutil
        toplam, kullanilan, bos = shutil.disk_usage(DATA_DIR)
        return {"toplam_gb": round(toplam / (1024**3), 2), "kullanilan_gb": round(kullanilan / (1024**3), 2), "bos_gb": round(bos / (1024**3), 2), "yuzde": round(kullanilan / toplam * 100, 1)}
    except:
        return {"hata": "disk bilgisi alinamadi"}

def listele():
    monitor = _yukle()
    kayitlar = monitor.get("kayitlar", [])
    return {"status": "ok", "toplam": len(kayitlar), "kayitlar": kayitlar[-50:]}

def detay(monitor_id):
    monitor = _yukle()
    for k in monitor.get("kayitlar", []):
        if k["id"] == monitor_id:
            return {"status": "ok", "detay": k}
    return {"status": "hata", "mesaj": "Monitor kaydi bulunamadi"}

def ayarlar():
    monitor = _yukle()
    return {"status": "ok", "ayarlar": monitor.get("ayarlar", {})}

def ayarlari_kaydet(ayarlar):
    monitor = _yukle()
    monitor["ayarlar"] = ayarlar
    _kaydet(monitor)
    return {"status": "ok", "mesaj": "Ayarlar kaydedildi", "ayarlar": ayarlar}
